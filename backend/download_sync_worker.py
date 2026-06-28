"""
download_sync_worker.py — Phase 2a: 파일 동기화 (다운로드 전용)
AI 분석(Phase 2b)과 분리된 독립 스크립트입니다.

실행 모드:
  quick (기본): 로컬 파일이 없거나 크기가 0인 항목만 법원 상세페이지 방문 → 다운로드
  full        : 전체 항목 상세페이지 방문 → 아래 3가지 조건 중 하나라도 해당하면 재다운로드
                  ① 로컬 파일 없음
                  ② 법원 사이트 첨부파일명 변경
                  ③ 법원 사이트 파일 크기 변경 (다운로드 후 비교)
"""
import sys
import os
import asyncio
import glob
import logging
import traceback
import tempfile
import shutil

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.permissions import ensure_file_permissions
ensure_file_permissions("file_sync_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("file_sync_log.txt", encoding="utf-8"),
    ],
)
logger = logging.getLogger("download_sync_worker")

LOCK_FILE = os.path.join(tempfile.gettempdir(), "download_sync_worker.lock")
DOWNLOAD_DELAY_SEC = 2  # quick 모드: 분당 ~30건
FULL_DELAY_SEC = 3      # full 모드: 다운로드 포함으로 여유 있게


async def _get_attachment_filename(page) -> str | None:
    """상세 페이지에서 현재 첨부파일명을 파싱합니다."""
    try:
        rows = await page.locator("table.tableVer tr").element_handles()
        for row in rows:
            ths = await row.query_selector_all("th")
            tds = await row.query_selector_all("td")
            for i, th in enumerate(ths):
                label = (await th.inner_text()).strip()
                if "첨부파일" in label and i < len(tds):
                    a_tag = await tds[i].query_selector("a")
                    if a_tag:
                        fname = (await a_tag.inner_text()).strip()
                        if fname:
                            return fname
                    value = (await tds[i].inner_text()).strip()
                    if value:
                        return value
    except Exception as e:
        logger.warning(f"첨부파일명 파싱 실패: {e}")
    return None


async def _download_attachments_to_temp(page, prop_id: int) -> list:
    """
    상세 페이지의 모든 첨부파일을 임시 디렉토리에 다운로드합니다.
    PDF > DOC > HWP 우선순위 정렬.
    반환: [{"filename", "tmp_path", "ext", "file_size"}, ...]
    """
    results = []
    tmp_dir = tempfile.mkdtemp(prefix=f"oas_{prop_id}_")
    try:
        links = await page.locator('a[href^="javascript:download"]').element_handles()
        attachments = []
        for idx, link in enumerate(links):
            fname = (await link.inner_text()).strip() or f"attachment_{idx}"
            href_val = await link.get_attribute("href") or ""
            ext = None
            for e in (".pdf", ".hwp", ".doc"):
                if e in href_val.lower() or e in fname.lower():
                    ext = e
                    break
            if ext:
                attachments.append({"element": link, "filename": fname, "ext": ext})

        attachments.sort(
            key=lambda x: 0 if x["ext"] == ".pdf" else (1 if x["ext"] == ".doc" else 2)
        )

        for idx, attach in enumerate(attachments):
            try:
                async with page.expect_download(timeout=15000) as dl_info:
                    await attach["element"].click()
                download = await dl_info.value

                safe_fname = "".join(
                    c for c in attach["filename"] if c.isalnum() or c in (" ", ".", "_", "-")
                ).strip() or f"attachment_{idx}{attach['ext']}"
                tmp_path = os.path.join(tmp_dir, safe_fname)
                await download.save_as(tmp_path)
                file_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0

                results.append({
                    "filename": attach["filename"],
                    "safe_fname": safe_fname,
                    "tmp_path": tmp_path,
                    "ext": attach["ext"],
                    "file_size": file_size,
                })
            except Exception as e:
                logger.error(f"임시 다운로드 실패 (id={prop_id}, {attach['filename']}): {e}")
    except Exception as e:
        logger.error(f"첨부파일 목록 오류 (id={prop_id}): {e}")

    return results, tmp_dir


def _get_local_file_size(download_dir: str, prop_id: int) -> int:
    """로컬에 저장된 첫 번째 파일의 크기를 반환합니다. 없으면 -1."""
    files = glob.glob(os.path.join(download_dir, f"{prop_id}_*.*"))
    if not files:
        return -1
    try:
        return os.path.getsize(files[0])
    except Exception:
        return -1


def _get_stored_file_size(prop) -> int:
    """DB의 attachments JSON에 저장된 첫 번째 파일 크기를 반환합니다. 없으면 -1."""
    try:
        if prop.attachments and isinstance(prop.attachments, list):
            return prop.attachments[0].get("file_size", -1)
    except Exception:
        pass
    return -1


def run(mode: str = "quick"):
    import atexit

    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                logger.warning(f"download_sync_worker 이미 실행 중 (PID {old_pid}). 종료합니다.")
                return
            else:
                os.remove(LOCK_FILE)
        except Exception:
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    def _cleanup():
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    atexit.register(_cleanup)

    from dotenv import load_dotenv
    load_dotenv(override=True)

    async def main():
        from playwright.async_api import async_playwright
        from app.database import SessionLocal
        from app.models.bankruptcy import BankruptcyProperty
        from app.services.scourt_scraper import DOWNLOAD_DIR
        from app.sync_status import set_status

        db = SessionLocal()
        set_status(phase="file_syncing", message=f"파일 동기화 시작 (mode={mode})")

        try:
            all_props = (
                db.query(BankruptcyProperty)
                .filter(BankruptcyProperty.notice_url.isnot(None))
                .order_by(BankruptcyProperty.id.asc())
                .all()
            )

            # ── quick 모드: 로컬 파일 없거나 크기 0인 항목만 ─────────────
            if mode == "quick":
                targets = []
                for p in all_props:
                    local_size = _get_local_file_size(DOWNLOAD_DIR, p.id)
                    if local_size <= 0:  # 파일 없음(-1) 또는 빈 파일(0)
                        targets.append(p)

            # ── full 모드: 전체 항목 (파일명·크기 비교 포함) ─────────────
            else:
                targets = all_props

            total = len(targets)
            logger.info(f"[Phase2a] 처리 대상: {total}건 (mode={mode})")
            set_status(phase="file_syncing", message=f"대상 {total}건 동기화 시작 (mode={mode})")

            if not targets:
                set_status(phase="done", message="파일 동기화 완료: 동기화 대상 없음")
                return

            delay = FULL_DELAY_SEC if mode == "full" else DOWNLOAD_DELAY_SEC

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    accept_downloads=True,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                synced = 0
                skipped = 0

                for i, prop in enumerate(targets, 1):
                    await asyncio.sleep(delay)
                    set_status(
                        phase="file_syncing",
                        message=f"[{i}/{total}] {prop.title[:30]} 처리 중..."
                    )
                    tmp_dir = None
                    try:
                        await page.goto(prop.notice_url, timeout=30000, wait_until="domcontentloaded")

                        if mode == "full":
                            # ── full 모드: 파일명·크기 3단계 비교 ─────────
                            current_fname = await _get_attachment_filename(page)
                            local_size = _get_local_file_size(DOWNLOAD_DIR, prop.id)
                            fname_changed = (
                                current_fname and current_fname != prop.attachment_filename
                            )
                            file_missing = local_size <= 0

                            if not file_missing and not fname_changed:
                                # 파일 있고 이름도 같음 → 크기 비교를 위해 다운로드
                                downloaded_list, tmp_dir = await _download_attachments_to_temp(
                                    page, prop.id
                                )
                                if downloaded_list:
                                    new_size = downloaded_list[0]["file_size"]
                                    if new_size == local_size:
                                        # 크기도 동일 → 변경 없음, 스킵
                                        skipped += 1
                                        logger.debug(f"[Phase2a] 변경 없음 스킵 id={prop.id}")
                                        continue
                                    else:
                                        logger.info(
                                            f"[Phase2a] 파일 크기 변경 id={prop.id}: "
                                            f"{local_size}B → {new_size}B"
                                        )
                                        # 기존 파일 삭제 후 임시파일을 정식 위치로 이동
                                        for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{prop.id}_*.*")):
                                            try:
                                                os.remove(f)
                                            except Exception:
                                                pass
                                        saved = []
                                        for att in downloaded_list:
                                            local_name = f"{prop.id}_{att['safe_fname']}"
                                            dest = os.path.join(DOWNLOAD_DIR, local_name)
                                            shutil.move(att["tmp_path"], dest)
                                            saved.append({
                                                "filename": att["filename"],
                                                "local_filename": local_name,
                                                "ext": att["ext"],
                                                "file_size": att["file_size"],
                                            })
                                        prop.attachments = saved
                                        prop.attachment_filename = saved[0]["filename"]
                                        db.commit()
                                        synced += 1
                                        continue
                                else:
                                    skipped += 1
                                    continue
                            else:
                                if fname_changed:
                                    logger.info(
                                        f"[Phase2a] 파일명 변경 id={prop.id}: "
                                        f"{prop.attachment_filename!r} → {current_fname!r}"
                                    )
                                # 기존 파일 삭제
                                for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{prop.id}_*.*")):
                                    try:
                                        os.remove(f)
                                    except Exception:
                                        pass
                                # 이미 임시 다운로드가 완료된 경우와 아닌 경우 분기
                                if tmp_dir is None:
                                    downloaded_list, tmp_dir = await _download_attachments_to_temp(
                                        page, prop.id
                                    )

                        else:
                            # ── quick 모드: 파일 없으므로 바로 다운로드 ──────
                            downloaded_list, tmp_dir = await _download_attachments_to_temp(
                                page, prop.id
                            )

                        # 임시 파일 → 정식 경로로 이동
                        if downloaded_list:
                            saved = []
                            for att in downloaded_list:
                                local_name = f"{prop.id}_{att['safe_fname']}"
                                dest = os.path.join(DOWNLOAD_DIR, local_name)
                                shutil.move(att["tmp_path"], dest)
                                saved.append({
                                    "filename": att["filename"],
                                    "local_filename": local_name,
                                    "ext": att["ext"],
                                    "file_size": att["file_size"],
                                })
                            prop.attachments = saved
                            prop.attachment_filename = saved[0]["filename"]
                            db.commit()
                            synced += 1
                            logger.info(
                                f"[Phase2a] 저장 완료 [{i}/{total}] id={prop.id} "
                                f"→ {saved[0]['filename']} ({saved[0]['file_size']}B)"
                            )
                        else:
                            logger.warning(f"[Phase2a] 다운로드할 파일 없음 id={prop.id}")

                    except Exception as e:
                        logger.error(f"[Phase2a] 실패 id={prop.id}: {e}")
                    finally:
                        if tmp_dir and os.path.exists(tmp_dir):
                            shutil.rmtree(tmp_dir, ignore_errors=True)

                await browser.close()

            msg = f"파일 동기화 완료: {synced}건 동기화, {skipped}건 스킵"
            logger.info(f"[Phase2a] {msg}")
            set_status(phase="done", message=msg)

        except Exception as e:
            logger.error(f"[Phase2a] 전체 오류: {e}")
            traceback.print_exc()
            set_status(phase="error", message=f"파일 동기화 오류: {e}")
        finally:
            db.close()

    asyncio.run(main())


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    run(mode)
