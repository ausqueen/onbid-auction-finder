"""
backfill_meta.py — 기존 수집 레코드에 상세 메타데이터 채우기
---------------------------------------------------------------
is_analyzed 여부와 관계없이, post_date / notice_expire_date /
phone_number / selling_agency / attachment_filename 이 비어있는
레코드를 대상으로 대법원 상세 페이지에 재접속하여 파싱합니다.

실행:
    .venv\\Scripts\\python.exe backfill_meta.py [--limit N] [--delay D]

옵션:
    --limit N   처리할 최대 건수 (기본: 전체)
    --delay D   건당 대기 시간(초) 기본: 2.0
"""
import sys
import os
import asyncio
import logging
import argparse
import traceback

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.permissions import ensure_file_permissions
ensure_file_permissions("backfill_meta.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backfill_meta.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("backfill_meta")


async def _parse_detail_meta(page) -> dict:
    """
    대법원 공고 상세 페이지에서 메타데이터를 파싱합니다.
    (analyze_worker._parse_detail_meta 와 동일한 로직)
    """
    result = {}
    try:
        rows = await page.locator("table.tableVer tr").element_handles()
        for row in rows:
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
        logger.warning(f"[parse] 파싱 실패: {e}")
    return result


async def main(limit: int | None, delay: float):
    from dotenv import load_dotenv
    load_dotenv(
        r"c:\antigravity\onbid-auction-finder\backend\.env",
        override=True,
    )
    from playwright.async_api import async_playwright
    from app.database import SessionLocal
    from app.models.bankruptcy import BankruptcyProperty

    db = SessionLocal()
    try:
        # post_date 가 None 인 레코드 = 메타데이터 미수집
        q = (
            db.query(BankruptcyProperty)
            .filter(BankruptcyProperty.post_date.is_(None))
            .order_by(BankruptcyProperty.id.asc())
        )
        if limit:
            q = q.limit(limit)
        targets = q.all()
        logger.info(f"대상 레코드: {len(targets)}건 (delay={delay}s/건)")

        if not targets:
            logger.info("채울 데이터가 없습니다.")
            return

        updated = 0
        failed = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            for idx, prop in enumerate(targets, 1):
                await asyncio.sleep(delay)
                try:
                    await page.goto(prop.notice_url, timeout=30000, wait_until="domcontentloaded")
                    meta = await _parse_detail_meta(page)

                    changed = False
                    # post_date: 비어있으면 채움
                    if meta.get("post_date") and not prop.post_date:
                        prop.post_date = meta["post_date"]
                        changed = True
                    # notice_expire_date
                    if meta.get("notice_expire_date") and not prop.notice_expire_date:
                        prop.notice_expire_date = meta["notice_expire_date"]
                        changed = True
                    # phone_number
                    if meta.get("phone_number") and not prop.phone_number:
                        prop.phone_number = meta["phone_number"]
                        changed = True
                    # selling_agency
                    if meta.get("selling_agency") and not prop.selling_agency:
                        prop.selling_agency = meta["selling_agency"]
                        changed = True
                    # attachment_filename
                    if meta.get("attachment_filename") and not prop.attachment_filename:
                        prop.attachment_filename = meta["attachment_filename"]
                        changed = True
                    # court_name (덮어쓰지 않고 비어있을 때만)
                    if meta.get("court_name") and not prop.court_name:
                        prop.court_name = meta["court_name"]
                        changed = True

                    if changed:
                        db.commit()
                        updated += 1
                        logger.info(
                            f"[{idx}/{len(targets)}] ✅ 업데이트: ID={prop.id} "
                            f"post={meta.get('post_date')} "
                            f"expire={meta.get('notice_expire_date')} "
                            f"phone={meta.get('phone_number')}"
                        )
                    else:
                        logger.info(f"[{idx}/{len(targets)}] ⏭ 변경 없음: ID={prop.id}")

                except Exception as e:
                    db.rollback()
                    failed += 1
                    logger.error(f"[{idx}/{len(targets)}] ❌ 실패: ID={prop.id} URL={prop.notice_url} — {e}")

            await browser.close()

        logger.info(f"\n완료: 업데이트={updated}건, 실패={failed}건, 변경없음={len(targets)-updated-failed}건")

    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="대법원 공고 메타데이터 backfill")
    parser.add_argument("--limit", type=int, default=None, help="처리 건수 제한 (기본: 전체)")
    parser.add_argument("--delay", type=float, default=2.0, help="건당 대기시간(초) 기본: 2.0")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, delay=args.delay))
