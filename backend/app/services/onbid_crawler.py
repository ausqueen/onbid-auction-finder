import asyncio
import logging
import re
from typing import Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def crawl_tenant_deposit(notice_no: str) -> int:
    """
    온비드 웹사이트에 Playwright를 통해 접속하여,
    물건관리번호(notice_no)로 검색한 후 상세 페이지의 '임대차정보' 탭에서 보증금을 추출합니다.
    """
    deposit = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            logger.info(f"[{notice_no}] 온비드 메인 페이지 접근 중...")
            await page.goto('https://www.onbid.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=15000)

            # 1. 검색어 입력
            # 여러 형태의 검색창 input title/placeholder 대비
            search_input = page.locator('input#mainSwd, input[placeholder*="검색어"], input#searchKeyword').first
            
            if await search_input.count() == 0:
                logger.error(f"[{notice_no}] 메인 페이지 검색창을 찾을 수 없습니다.")
                return 0

            # UI상 감춰져 있을 수 있으므로 force=True 적용
            await search_input.fill(notice_no, force=True)
            await search_input.press('Enter')
            
            logger.info(f"[{notice_no}] 검색 수행, 결과 대기 중...")
            
            # 2. 결과 클릭
            # AJAX 렌더링 대기를 위해 단순 sleep 대신 선택자 대기
            try:
                await page.wait_for_selector(f'text="{notice_no}"', timeout=15000)
            except Exception:
                logger.warning(f"[{notice_no}] 검색 결과에 해당 물건을 찾을 수 없습니다 (타임아웃).")
                return 0

            # 물건관리번호 텍스트가 있는 링크 클릭
            item_link = page.locator(f'text="{notice_no}"').first
            
            # 팝업으로 열리는지, 현재 탭에서 열리는지 모를 때를 대비
            detail_page = None
            try:
                # 팝업 대기
                async with context.expect_page(timeout=5000) as new_page_info:
                    await item_link.click()
                detail_page = await new_page_info.value
            except Exception:
                # 팝업이 발생하지 않으면 현재 페이지가 상세 페이지로 이동한 것
                detail_page = page
                
            logger.info(f"[{notice_no}] 상세 페이지 렌더링 대기 중...")
            await detail_page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(3) # 추가 UI 렌더링 딜레이

            # 3. 임대차정보 탭 클릭
            lease_tab = detail_page.locator('text="임대차정보"').first
            if await lease_tab.count() > 0:
                logger.info(f"[{notice_no}] 임대차정보 탭 클릭 중...")
                await lease_tab.click()
                await asyncio.sleep(3) # 탭 내부 테이블 렌더링 대기
                
                # HTML 추출
                html = await detail_page.content()
                
                # 금액 추출 (원화 표기)
                # 1) 명확한 보증금 매칭
                matches_won = re.findall(r'(?:보증금|임차금|계약금)[^\d]*([0-9]{1,4}(?:,[0-9]{3}){1,})', html)
                for m in matches_won:
                    val = int(m.replace(',', ''))
                    if val > deposit and val < 5000000000: # 50억 초과는 쓰레기값 간주
                        deposit = val
                
                # 2) 7자리 이상의 단순 금액 나열 (표 내부)
                if deposit == 0:
                    matches_won = re.findall(r'([0-9][0-9,]{5,})\s*원', html)
                    for m in matches_won:
                        val = int(m.replace(',', ''))
                        if val > deposit and val < 5000000000:
                            deposit = val
                
                logger.info(f"[{notice_no}] 크롤링 완료. 찾은 보증금: {deposit}")
                return deposit
            else:
                logger.info(f"[{notice_no}] 임대차정보 탭이 없습니다.")
                return 0

        except Exception as e:
            logger.error(f"[{notice_no}] 온비드 크롤러 수행 중 오류 발생: {e}")
            return 0
        finally:
            await browser.close()

if __name__ == "__main__":
    # 단독 테스트 실행
    import sys
    test_notice = sys.argv[1] if len(sys.argv) > 1 else '2024-035651-00'
    res = asyncio.run(crawl_tenant_deposit(test_notice))
    print(f"Result Deposit: {res}")
