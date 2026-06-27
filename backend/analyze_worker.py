"""
analyze_worker.py — Phase 2 AI 분석 독립 스크립트
uvicorn 이벤트 루프와 분리하여 subprocess로 실행됩니다.
미분석(is_analyzed=False) 항목을 분당 ~8건 속도로 Gemini 분석합니다.

개선사항:
- 상세 페이지에서 메타데이터(매각기관/관할법원/전화번호/첨부파일명/공고만료일/작성일) 파싱
- PDF 이외의 첨부파일(HWP, DOC, DOCX, XLS, XLSX, PPT, PPTX, 이미지 등)은 AI 분석을 건너뛰고 메타데이터만 저장
"""
import traceback
import sys
import asyncio
import os
import time
import logging

# backend 디렉토리를 sys.path에 추가 (subprocess로 실행 시 경로 보정)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.permissions import ensure_file_permissions
ensure_file_permissions("analyze_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("analyze_log.txt", encoding="utf-8"),
    ],
)
logger = logging.getLogger("analyze_worker")

ANALYSIS_DELAY_SEC = 7.5  # 분당 ~8건


async def _parse_detail_meta(page) -> dict:
    """
    대법원 공고 상세 페이지(RealNoticeView.work)의 테이블에서
    매각기관, 관할법원, 작성일, 공고만료일, 첨부파일명, 전화번호를 파싱합니다.

    예시 테이블 구조 (table.tableWri):
      매각기관  | 채무자 주식회사 금영엔지니어링의 파산관재인 이원익
      관할법원  | 수원회생법원
      제목      | 자산매각공고       조회수 | 201
      작성일    | 2026.04.28         공고만료일 | 2026.05.20
      첨부파일  | 2025하합625 주식회사 금영엔지니어링 채권매각공고안.hwp
      전화번호  | 031-211-5902

    주의: 작성일/공고만료일은 같은 <tr>에 th/td 쌍이 2개 존재합니다.
    th[0]↔td[0], th[1]↔td[1] 순서로 매핑합니다.
    """
    result = {}
    try:
        rows = await page.locator("table.tableVer tr").element_handles()
        for row in rows:
            # th와 td를 각각 순서대로 가져와서 인덱스 기반으로 매핑
            ths = await row.query_selector_all("th")
            tds = await row.query_selector_all("td")

            for i, th in enumerate(ths):
                label = (await th.inner_text()).strip()
                if i >= len(tds):
                    continue
                td = tds[i]
                value = (await td.inner_text()).strip()

                if "매각기관" in label:
                    result["selling_agency"] = value
                elif "관할법원" in label or "법원" in label:
                    if not result.get("court_name"):
                        result["court_name"] = value
                elif "작성일" in label:
                    result["post_date"] = value.replace(".", "-") if "." in value else value
                elif "공고만료일" in label or "만료일" in label:
                    result["notice_expire_date"] = value.replace(".", "-") if "." in value else value
                elif "첨부파일" in label:
                    a_tag = await td.query_selector("a")
                    if a_tag:
                        fname = (await a_tag.inner_text()).strip()
                        if fname:
                            result["attachment_filename"] = fname
                    elif value:
                        result["attachment_filename"] = value
                elif "전화번호" in label or "전화" in label:
                    result["phone_number"] = value
    except Exception as e:
        logger.warning(f"[_parse_detail_meta] 파싱 실패: {e}")

    return result


# PDF 이외의 첨부파일은 AI 분석 불가로 처리
# (HWP, DOC, DOCX, XLS, XLSX, PPT, PPTX, 이미지 등)
ANALYZABLE_EXTENSIONS = {".pdf"}


def _is_unanalyzable(filename: str | None) -> bool:
    """첨부파일이 자동 분석 불가한 형식인지 판별합니다."""
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]  # e.g. ".hwp"
    return bool(ext) and ext not in ANALYZABLE_EXTENSIONS


LOCK_FILE = r"c:\antigravity\onbid-auction-finder\backend\analyze_worker.lock"

def run():
    import atexit

    # ── 중복 실행 방지: 락 파일로 단일 인스턴스 보장 ──
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                logger.warning(f"analyze_worker 이미 실행 중 (PID {old_pid}). 종료합니다.")
                return
            else:
                logger.info(f"이전 락 파일(PID {old_pid})은 종료된 프로세스. 락 제거 후 시작.")
                os.remove(LOCK_FILE)
        except Exception:
            os.remove(LOCK_FILE)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    def _cleanup():
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    atexit.register(_cleanup)

    from dotenv import load_dotenv
    load_dotenv(
        r"c:\antigravity\onbid-auction-finder\backend\.env",
        override=True,
    )

    async def main():
        from playwright.async_api import async_playwright
        from app.database import SessionLocal
        from app.models.bankruptcy import BankruptcyProperty
        from app.services.gemini_service import analyze_bankruptcy_notice
        from app.services.scourt_scraper import DOWNLOAD_DIR
        from app.sync_status import set_status

        # WAL 모드 직접 활성화 (uvicorn 프로세스와 동시 접근 충돌 방지)
        import sqlite3 as _sqlite3
        _db_path = r"c:\antigravity\onbid-auction-finder\backend\onbid.db"
        _conn = _sqlite3.connect(_db_path)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=15000")
        _conn.close()

        db = SessionLocal()
        set_status(phase="analyzing", message="독립 프로세스: AI 분석 시작")
        try:
            pending = (
                db.query(BankruptcyProperty)
                .filter(BankruptcyProperty.is_analyzed == False)
                .order_by(BankruptcyProperty.id.asc())
                .all()
            )
            logger.info(f"[Phase2] 분석 대상: {len(pending)}건")

            analyzed_count = 0

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
                detail_page = await context.new_page()

                for prop in pending:
                    await asyncio.sleep(ANALYSIS_DELAY_SEC)

                    downloaded_file_path = None
                    attachment_filename_val = None

                    try:
                        await detail_page.goto(prop.notice_url, timeout=30000)

                        # ── 상세 페이지 메타데이터 파싱 ──
                        try:
                            detail_meta = await _parse_detail_meta(detail_page)
                            if detail_meta.get("selling_agency"):
                                prop.selling_agency = detail_meta["selling_agency"]
                            if detail_meta.get("phone_number"):
                                prop.phone_number = detail_meta["phone_number"]
                            if detail_meta.get("attachment_filename"):
                                attachment_filename_val = detail_meta["attachment_filename"]
                                prop.attachment_filename = attachment_filename_val
                            if detail_meta.get("notice_expire_date"):
                                prop.notice_expire_date = detail_meta["notice_expire_date"]
                            if detail_meta.get("post_date") and not prop.post_date:
                                prop.post_date = detail_meta["post_date"]
                        except Exception as meta_err:
                            logger.warning(f"메타데이터 파싱 실패 ({prop.id}): {meta_err}")

                        # ── 첨부파일 다운로드 및 우선순위 정렬 (PDF > DOC > HWP) ──
                        try:
                            links = await detail_page.locator('a[href^="javascript:download"]').element_handles()
                            attachments = []
                            for idx, link in enumerate(links):
                                fname = (await link.inner_text()).strip()
                                if not fname:
                                    fname = f"attachment_{idx}"
                                
                                href_val = await link.get_attribute("href")
                                ext = None
                                if href_val:
                                    for e in (".pdf", ".hwp", ".doc"):
                                        if e in href_val.lower():
                                            ext = e
                                            break
                                    if not ext:
                                        for e in (".pdf", ".hwp", ".doc"):
                                            if e in fname.lower():
                                                ext = e
                                                break
                                
                                if ext:
                                    attachments.append({
                                        "element": link,
                                        "filename": fname,
                                        "ext": ext
                                    })
                            
                            # PDF 우선 정렬 (.pdf = 0, .doc = 1, .hwp = 2)
                            if attachments:
                                attachments.sort(key=lambda x: 0 if x["ext"] == '.pdf' else (1 if x["ext"] == '.doc' else 2))
                                
                                downloaded_attachments_info = []
                                for idx, attach in enumerate(attachments):
                                    try:
                                        async with detail_page.expect_download(timeout=15000) as dl_info:
                                            await attach["element"].click()
                                        download = await dl_info.value
                                        
                                        orig_name = attach["filename"]
                                        safe_fname = "".join([c for c in orig_name if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                                        if not safe_fname:
                                            safe_fname = f"attachment_{idx}{attach['ext']}"
                                            
                                        local_name = f"{prop.id}_{safe_fname}"
                                        path = os.path.join(DOWNLOAD_DIR, local_name)
                                        await download.save_as(path)
                                        
                                        downloaded_attachments_info.append({
                                            "filename": orig_name,
                                            "local_filename": local_name,
                                            "ext": attach["ext"]
                                        })
                                        
                                        # 첫 파일(우선순위 정렬에 의해 PDF)이면서 HWP가 아닌 경우 AI 분석용 파일로 지정
                                        if idx == 0 and attach["ext"] != '.hwp':
                                            downloaded_file_path = path
                                    except Exception as single_dl_err:
                                        logger.error(f"[Phase2] 개별 파일 다운 실패 ({prop.id}, {attach['filename']}): {single_dl_err}")
                                
                                if downloaded_attachments_info:
                                    prop.attachments = downloaded_attachments_info
                                    prop.attachment_filename = downloaded_attachments_info[0]["filename"]
                                    attachment_filename_val = downloaded_attachments_info[0]["filename"]
                        except Exception as dl_err:
                            logger.error(f"파일 다운 실패 ({prop.id}): {dl_err}")

                    except Exception as e:
                        logger.error(f"상세 페이지 오류 ({prop.id}): {e}")

                    # ── Gemini 분석 (분석불가 파일이면 건너뜀) ──
                    effective_filename = attachment_filename_val or prop.attachment_filename
                    is_hwp_attach = effective_filename and effective_filename.lower().endswith(".hwp")
                    try:
                        if is_hwp_attach:
                            # 분석불가 파일(HWP): 메타데이터만 저장, AI 분석 없이 완료 처리
                            prop.is_analyzed = True
                            prop.ai_summary = None
                            db.commit()
                            analyzed_count += 1
                            logger.info(f"[HWP] 분석불가 파일 — 메타데이터만 저장: {prop.title[:40]}")
                        else:
                            extracted = analyze_bankruptcy_notice(downloaded_file_path, prop.title)
                            if not extracted or not extracted.get("summary"):
                                raise ValueError("Gemini API가 비어 있는 요약을 반환했습니다. 오류로 간주하여 분석 대기 상태를 유지합니다.")

                            target_str = extracted.get("target_property")
                            if isinstance(target_str, list):
                                target_str = ", ".join(map(str, target_str))

                            prop.asset_type = extracted.get("asset_type")
                            prop.target_property = target_str
                            prop.address = extracted.get("address")
                            prop.min_price = extracted.get("min_price")
                            prop.manager_contact = extracted.get("manager_contact")
                            prop.sale_deadline = extracted.get("sale_deadline")
                            prop.ai_summary = extracted.get("summary")
                            prop.is_recommended = extracted.get("is_recommended", False)
                            prop.is_analyzed = True
                            db.commit()

                            analyzed_count += 1
                            logger.info(
                                f"분석 완료: {prop.title[:40]} "
                                f"({analyzed_count}/{len(pending)})"
                            )
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Gemini 에러 ({prop.id}): {e}")

                await browser.close()

            logger.info(f"[Phase2] 완료: {analyzed_count}건 분석")

        except Exception as e:
            logger.error(f"[Phase2] 실패: {e}")
            traceback.print_exc()
        finally:
            db.close()
            set_status(phase="done", message="분석 프로세스 완료")

    asyncio.run(main())


if __name__ == "__main__":
    run()
