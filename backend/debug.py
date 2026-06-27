"""
debug.py — Phase 1 빠른 목록 수집 독립 스크립트
uvicorn 이벤트 루프와 분리하여 subprocess로 실행됩니다.

변경사항:
- board_no(공고 번호) 저장
- 기존 board_no가 없는 레코드(이전 스크래퍼 수집분)는 삭제 후 재수집
- 이미 있는 notice_url은 board_no만 업데이트
"""
import traceback
import sys
import os
import asyncio
import logging

# backend 디렉토리를 sys.path에 추가 (subprocess로 실행 시 경로 보정)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.permissions import ensure_file_permissions
ensure_file_permissions("debug_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("debug_log.txt", encoding="utf-8"),
    ],
)
logger = logging.getLogger("debug_worker")

# Windows에서 Playwright subprocess 실행을 위해 반드시 필요
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def run():
    from dotenv import load_dotenv
    load_dotenv(
        r"c:\antigravity\onbid-auction-finder\backend\.env",
        override=True,
    )

    async def main():
        from app.services.scourt_scraper import collect_all_notices
        from app.database import SessionLocal
        from app.models.bankruptcy import BankruptcyProperty
        from app.sync_status import set_status

        db = SessionLocal()
        set_status(phase="collecting", message="독립 프로세스: 목록 수집 시작")
        try:
            # ── Step A: board_no가 없는 기존 레코드 삭제 (이전 스크래퍼 오수집분)
            invalid = db.query(BankruptcyProperty).filter(
                BankruptcyProperty.board_no == None
            ).all()
            invalid_count = len(invalid)
            if invalid_count > 0:
                logger.info(f"[Cleanup] board_no 없는 레코드 {invalid_count}건 삭제 중...")
                for p in invalid:
                    db.delete(p)
                db.commit()
                logger.info(f"[Cleanup] {invalid_count}건 삭제 완료")

            # ── Step B: 공고게시판 전체 목록 수집
            logger.info("[Phase1] 공고게시판 목록 수집 시작")
            notices = await collect_all_notices(max_pages=50)
            logger.info(f"[Phase1] 수집 완료: {len(notices)}건")

            new_count = 0
            updated_count = 0
            for info in notices:
                try:
                    exists = db.query(BankruptcyProperty).filter(
                        BankruptcyProperty.notice_url == info["notice_url"]
                    ).first()

                    if exists:
                        # 이미 있으면 board_no만 갱신
                        if exists.board_no != info.get("board_no"):
                            exists.board_no = info.get("board_no")
                            db.commit()
                            updated_count += 1
                        continue

                    prop = BankruptcyProperty(
                        title=info["title"],
                        court_name=info["court_name"],
                        post_date=info.get("post_date") or None,
                        notice_url=info["notice_url"],
                        board_no=info.get("board_no"),
                        is_analyzed=False,
                    )
                    db.add(prop)
                    db.commit()
                    new_count += 1
                    if new_count % 10 == 0:
                        logger.info(f"[Phase1] {new_count}건 저장됨...")
                except Exception as e:
                    db.rollback()
                    logger.error(f"DB 저장 에러 ({info.get('title', '?')}): {e}")

            total = db.query(BankruptcyProperty).count()
            logger.info(
                f"[Phase1] 완료: {new_count}건 신규 저장 / {updated_count}건 board_no 갱신 | DB 총 {total}건"
            )

            # 만료/삭제된 공고 정합성 맞추기 (스크래핑이 정상적으로 수행되었을 때만)
            if len(notices) > 50:
                valid_urls = {info["notice_url"] for info in notices}
                db_props = db.query(BankruptcyProperty).all()
                deleted_count = 0
                for prop in db_props:
                    if prop.notice_url not in valid_urls:
                        # 게시판에서 내려간 공고는 로컬 첨부파일도 정리
                        if prop.attachment_filename:
                            from app.services.scourt_scraper import DOWNLOAD_DIR
                            import glob
                            import os
                            search_pattern = os.path.join(DOWNLOAD_DIR, f"{prop.id}_*.*")
                            for f in glob.glob(search_pattern):
                                try:
                                    os.remove(f)
                                except:
                                    pass
                        
                        db.delete(prop)
                        deleted_count += 1
                
                if deleted_count > 0:
                    db.commit()
                    logger.info(f"[Phase1] 게시판에서 삭제된 공고 {deleted_count}건 DB 및 파일 삭제 완료")

        except Exception as e:
            logger.error(f"[Phase1] 실패: {e}")
            traceback.print_exc()
        finally:
            db.close()
            set_status(phase="done", message="수집 프로세스 완료")

    asyncio.run(main())


if __name__ == "__main__":
    run()
