"""
이미 AI 분석이 완료된 항목들의 첨부파일을 다운로드 받아 로컬에 저장합니다.
저장 경로: tmp_downloads/{prop.id}_{safe_title}.{ext}
"""
import asyncio
import os
import time

async def main():
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from playwright.async_api import async_playwright
    from app.database import SessionLocal
    from app.models.bankruptcy import BankruptcyProperty
    from app.services.scourt_scraper import DOWNLOAD_DIR

    db = SessionLocal()
    try:
        # attachment_filename이 있고, hwp가 아닌 속성들 조회
        props = db.query(BankruptcyProperty).filter(
            BankruptcyProperty.attachment_filename.isnot(None),
            BankruptcyProperty.is_analyzed == True
        ).all()
        
        targets = []
        for prop in props:
            # 파일이 이미 존재하는지 확인
            import glob
            search_pattern = os.path.join(DOWNLOAD_DIR, f"{prop.id}_*.*")
            if not glob.glob(search_pattern):
                targets.append(prop)
                
        print(f"다운로드 대상: {len(targets)}건")
        if not targets:
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()

            for i, prop in enumerate(targets, 1):
                print(f"[{i}/{len(targets)}] {prop.id}번 첨부파일 다운로드 중...")
                await asyncio.sleep(2)
                try:
                    await page.goto(prop.notice_url, timeout=30000, wait_until="domcontentloaded")
                    files = await page.locator('a[href^="javascript:download"]').element_handles()
                    
                    downloaded_attachments_info = []
                    for idx, f in enumerate(files):
                        orig_name = (await f.inner_text()).strip()
                        if not orig_name:
                            orig_name = f"attachment_{idx}"
                            
                        href_val = await f.get_attribute("href")
                        ext = None
                        if href_val:
                            for e in (".pdf", ".hwp", ".doc"):
                                if e in href_val.lower():
                                    ext = e
                                    break
                            if not ext:
                                for e in (".pdf", ".hwp", ".doc"):
                                    if e in orig_name.lower():
                                        ext = e
                                        break
                        if not ext:
                            continue
                            
                        async with page.expect_download(timeout=15000) as dl_info:
                            await f.click()
                        download = await dl_info.value
                        
                        safe_fname = "".join([c for c in orig_name if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                        if not safe_fname:
                            safe_fname = f"attachment_{idx}{ext}"
                            
                        local_name = f"{prop.id}_{safe_fname}"
                        path = os.path.join(DOWNLOAD_DIR, local_name)
                        await download.save_as(path)
                        print(f"  -> 저장됨: {path}")
                        
                        downloaded_attachments_info.append({
                            "filename": orig_name,
                            "local_filename": local_name,
                            "ext": ext
                        })
                        
                    if downloaded_attachments_info:
                        prop.attachments = downloaded_attachments_info
                        prop.attachment_filename = downloaded_attachments_info[0]["filename"]
                        db.commit()
                        print(f"  -> DB 업데이트 완료")
                except Exception as e:
                    print(f"  -> 실패: {e}")

            await browser.close()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
