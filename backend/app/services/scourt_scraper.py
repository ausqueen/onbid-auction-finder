"""
대법원 파산/회생 자산 매각 공고 스크래퍼
----------------------------------------------
Phase 1 (collect_all_notices): 
  - 공고게시판 전체 목록(~449건) 기본정보만 빠르게 수집
  - PDF 다운로드 / Gemini 분석 없음
  - 속도: 페이지당 3초, 항목당 1초 대기

Phase 2 (scrape_bankruptcy_notices / legacy deep scan):
  - 미분석 항목 PDF 다운로드 + Gemini 분석
  - 분당 8건 제한 (7.5초/건)
"""
import os
import time
import logging
import asyncio
import sys
import re
from typing import List, Dict, Optional

if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────
SCOURT_LIST_URL = "https://www.scourt.go.kr/portal/notice/realestate/RealNoticeList.work"

# 공고게시판 직접 URL 후보 (클릭 실패 시 폴백)
BOARD_URL_CANDIDATES = [
    "https://www.scourt.go.kr/portal/notice/realestate/RealNoticeList.work?noticeClss=2",
    "https://www.scourt.go.kr/portal/notice/realestate/RealNoticeList.work?noticeType=board",
]

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tmp_downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 속도 제한
PAGE_DELAY_SEC = 3          # 목록 페이지 이동 간격
ITEM_DELAY_SEC = 1          # Phase1 항목 접근 간격 (URL 구성만 하므로 실제론 거의 없음)
ANALYSIS_DELAY_SEC = 7.5    # Phase2 Gemini 분석 간격 (분당 ~8건)


# ── 헬퍼 ─────────────────────────────────────────

async def _navigate_to_board(list_page: Page) -> bool:
    """
    공고게시판으로 진입합니다.
    기본 URL(RealNoticeList.work)이 이미 공고게시판 전체 목록을 보여줍니다.
    (번호 449번까지의 전체 공고 목록이 있음 - 실제 페이지 분석으로 확인됨)
    """
    try:
        await list_page.goto(
            SCOURT_LIST_URL,
            timeout=60000,
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(2)
        rows = await list_page.locator("table.tableHor tbody tr").count()
        logger.info(f"공고게시판 진입 완료 (행 수: {rows})")
        return rows > 0
    except Exception as e:
        logger.error(f"공고게시판 진입 실패: {e}")
        return False



async def _parse_page_rows(list_page: Page) -> List[Dict]:
    """현재 목록 페이지에서 게시글 기본 정보 목록을 추출합니다.
    
    실제 테이블 구조:
      td[0]: 번호
      td[1]: 법원명 (class="tit mhid")
      td[2]: 채무자명
      td[3]: 제목 + href 링크 (a 태그)
      td[4]: 조회수
    """
    items = []
    try:
        rows = await list_page.locator("table.tableHor tbody tr").element_handles()
    except Exception:
        return items

    for row in rows:
        try:
            tds = await row.query_selector_all("td")
            if len(tds) < 4:
                continue

            # td[0]: 번호(board_no), td[1]: 법원명, td[2]: 채무자명, td[3]: 제목+링크
            board_no_text = (await tds[0].inner_text()).strip()
            board_no = int(board_no_text) if board_no_text.isdigit() else None

            court_name = (await tds[1].inner_text()).strip()
            a_tag = await tds[3].query_selector("a")
            if not a_tag:
                continue

            title = (await a_tag.inner_text()).strip()
            href = await a_tag.get_attribute("href") or ""

            # href에서 seq_id 추출
            seq_match = re.search(r"seq_id=(\d+)", href)
            if not seq_match:
                seq_match = re.search(r"goNoticeView\(['\"]?(\d+)['\"]?\)", href)
                
            if seq_match:
                seq_id = seq_match.group(1)
                detail_url = f"https://www.scourt.go.kr/portal/notice/realestate/RealNoticeView.work?seq_id={seq_id}"
                
                items.append(
                    {
                        "title": title,
                        "court_name": court_name,
                        "post_date": None,
                        "notice_url": detail_url,
                        "seq_id": seq_id,
                        "board_no": board_no,
                    }
                )
        except Exception:
            continue

    return items




async def _go_next_page(list_page: Page, pg: int) -> bool:
    """페이지 이동: fn_egov_select_brdMstr(pg) JS 호출 + form submit 폴백."""
    for attempt in range(3):
        try:
            # 방법 1: fn_egov_select_brdMstr 함수 호출
            try:
                async with list_page.expect_navigation(timeout=30000, wait_until="domcontentloaded"):
                    await list_page.evaluate(f"fn_egov_select_brdMstr({pg})")
                await asyncio.sleep(PAGE_DELAY_SEC)
                return True
            except Exception:
                pass

            # 방법 2: 폼 직접 submit
            try:
                async with list_page.expect_navigation(timeout=30000, wait_until="domcontentloaded"):
                    await list_page.evaluate(f"""
                        document.frm.pageIndex.value = '{pg}';
                        document.frm.submit();
                    """)
                await asyncio.sleep(PAGE_DELAY_SEC)
                return True
            except Exception:
                pass

        except Exception as e:
            wait_sec = 2 ** (attempt + 1)
            logger.warning(f"페이지 {pg} 이동 시도 {attempt + 1}/3 실패: {e} → {wait_sec}초 대기")
            await asyncio.sleep(wait_sec)
    return False


# ── Phase 1: 전체 목록 빠른 수집 ─────────────────

async def collect_all_notices(max_pages: int = 50) -> List[Dict]:
    """
    Phase 1: PDF 다운로드/Gemini 없이 공고게시판 전체 목록 기본정보만 수집.
    반환 형식: [{"title", "court_name", "post_date", "notice_url"}, ...]
    """
    all_items: List[Dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        list_page = await context.new_page()

        try:
            await _navigate_to_board(list_page)

            for pg in range(1, max_pages + 1):
                logger.info(f"[Phase1] 페이지 {pg} 수집 중...")

                try:
                    await list_page.wait_for_selector("table.tableHor tbody tr", timeout=30000)
                except Exception as e:
                    logger.warning(f"[Phase1] 페이지 {pg} 테이블 렌더링 실패: {e}")
                    break

                items = await _parse_page_rows(list_page)
                if not items:
                    logger.info(f"[Phase1] 페이지 {pg}: 항목 없음 → 마지막 페이지")
                    break

                all_items.extend(items)
                logger.info(f"[Phase1] 페이지 {pg}: {len(items)}건 수집 (누계: {len(all_items)}건)")

                if pg >= max_pages:
                    break

                if not await _go_next_page(list_page, pg + 1):
                    logger.error(f"[Phase1] 페이지 {pg + 1} 이동 실패 → 수집 종료")
                    break

        except Exception as e:
            logger.error(f"[Phase1] 스크래핑 에러: {e}")
        finally:
            await browser.close()

    logger.info(f"[Phase1] 수집 완료: 총 {len(all_items)}건")
    return all_items


# ── Phase 2: 상세 페이지 + PDF 다운로드 (기존 legacy) ──

async def scrape_bankruptcy_notices(max_pages: int = 45) -> List[Dict]:
    """
    Phase 2 (legacy deep scan): 목록 수집 + PDF 다운로드.
    분당 약 8건 처리 (ANALYSIS_DELAY_SEC=7.5 초 대기).
    반환 형식에 "file_path" 포함.
    """
    notices = []

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
        list_page = await context.new_page()
        detail_page = await context.new_page()

        try:
            await _navigate_to_board(list_page)

            for pg in range(1, max_pages + 1):
                logger.info(f"[Phase2] 페이지 {pg} 수집 중...")

                try:
                    await list_page.wait_for_selector("table.tableHor tbody tr", timeout=30000)
                except Exception as e:
                    logger.warning(f"[Phase2] 페이지 {pg} 테이블 렌더링 실패: {e}")
                    break

                items = await _parse_page_rows(list_page)
                if not items:
                    logger.info(f"[Phase2] 페이지 {pg}: 항목 없음 → 마지막 페이지")
                    break

                # 상세 탭에서 PDF 다운로드
                for item in items:
                    await asyncio.sleep(ANALYSIS_DELAY_SEC)  # 분당 ~8건 속도 제한
                    seq_id = item["seq_id"]
                    detail_url = item["notice_url"]
                    downloaded_file_path = None

                    try:
                        await detail_page.goto(detail_url, timeout=30000)
                        files = await detail_page.locator('a[href^="javascript:download"]').element_handles()

                        for f in files:
                            href_val = await f.get_attribute("href")
                            if href_val and any(ext in href_val.lower() for ext in (".pdf", ".hwp", ".doc")):
                                try:
                                    async with detail_page.expect_download(timeout=15000) as dl_info:
                                        await f.click()
                                    download = await dl_info.value
                                    safe_title = item["title"].replace("/", "_").replace("\\", "_")[:30]
                                    ext = (
                                        "pdf" if ".pdf" in href_val.lower()
                                        else ("hwp" if ".hwp" in href_val.lower() else "doc")
                                    )
                                    path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{int(time.time())}.{ext}")
                                    await download.save_as(path)
                                    downloaded_file_path = path
                                    break
                                except Exception as dl_err:
                                    logger.error(f"[Phase2] 다운로드 실패 ({seq_id}): {dl_err}")
                    except Exception as e:
                        logger.error(f"[Phase2] 상세 페이지 오류 ({seq_id}): {e}")

                    notices.append(
                        {
                            "title": item["title"],
                            "court_name": item["court_name"],
                            "post_date": item["post_date"],
                            "notice_url": detail_url,
                            "file_path": downloaded_file_path,
                        }
                    )

                if pg >= max_pages:
                    break

                if not await _go_next_page(list_page, pg + 1):
                    logger.error(f"[Phase2] 페이지 {pg + 1} 이동 실패 → 수집 종료")
                    break

        except Exception as e:
            logger.error(f"[Phase2] 스크래핑 에러: {e}")
        finally:
            await browser.close()

    return notices
