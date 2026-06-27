"""
대법원 공고 상세 페이지의 실제 테이블 행/셀 구조를 확인합니다.
"""
import asyncio

async def test():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.scourt.go.kr/portal/notice/realestate/RealNoticeView.work?pageIndex=1&seq_id=33310"
        print(f"접속: {url}")
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await asyncio.sleep(2)

        # tableVer 테이블의 모든 행 순회
        rows = await page.locator("table.tableVer tr").element_handles()
        print(f"\ntableVer 행 수: {len(rows)}")
        for i, row in enumerate(rows):
            ths = await row.query_selector_all("th")
            tds = await row.query_selector_all("td")
            th_texts = [(await th.inner_text()).strip() for th in ths]
            td_texts = [(await td.inner_text()).strip()[:60] for td in tds]
            print(f"  행[{i}]: th={th_texts} | td={td_texts}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
