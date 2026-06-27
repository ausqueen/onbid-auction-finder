"""
APScheduler: 매일 09:00 자동 동기화, 파산공매 하루 3회 (00:30/08:30/13:30)
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import SessionLocal
from .services.sync_service import sync_properties
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def _scheduled_sync():
    """스케줄러에서 호출되는 동기화 함수"""
    db = SessionLocal()
    try:
        logger.info("스케줄러: 자동 동기화 시작")
        result = sync_properties(db)
        logger.info(f"스케줄러: 자동 동기화 완료 - {result}")
    except Exception as e:
        logger.error(f"스케줄러: 동기화 오류 - {e}")
    finally:
        db.close()


def _scheduled_bankruptcy_phase1():
    """스케줄러: 대법원 파산 공고 목록 수집 (하루 3회)"""
    import subprocess
    import sys
    from pathlib import Path
    logger.info("스케줄러: 대법원 파산 공고 수집(Phase 1) 시작")
    script_path = Path(__file__).parent.parent.parent / "debug.py"
    try:
        subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception as e:
        logger.error(f"스케줄러: 대법원 공고 수집 실행 오류 - {e}")

def _scheduled_bankruptcy_phase2():
    """스케줄러: 대법원 파산 공고 AI 분석 (Phase 1 직후 하루 3회)"""
    import subprocess
    import sys
    from pathlib import Path
    logger.info("스케줄러: 대법원 파산 공고 AI 분석(Phase 2) 시작")
    script_path = Path(__file__).parent.parent.parent / "analyze_worker.py"
    try:
        subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception as e:
        logger.error(f"스케줄러: 대법원 공고 분석 실행 오류 - {e}")


def start_scheduler():
    """스케줄러 시작"""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    _scheduler.add_job(
        _scheduled_sync,
        trigger=CronTrigger(
            hour=settings.sync_hour,
            minute=settings.sync_minute,
        ),
        id="daily_sync",
        name="온비드 일일 동기화",
        replace_existing=True,
    )
    
    # 대법원 파산 공고 수집 (자정 00:30, 오전 08:30, 오후 13:30 — 하루 3회)
    _scheduler.add_job(
        _scheduled_bankruptcy_phase1,
        trigger=CronTrigger(hour="0,8,13", minute="30"),
        id="bankruptcy_sync_phase1",
        name="대법원 공고 수집",
        replace_existing=True,
    )

    # 대법원 파산 공고 분석 (자정 00:40, 오전 08:40, 오후 13:40 — 하루 3회)
    _scheduler.add_job(
        _scheduled_bankruptcy_phase2,
        trigger=CronTrigger(hour="0,8,13", minute="40"),
        id="bankruptcy_sync_phase2",
        name="대법원 공고 AI 분석",
        replace_existing=True,
    )
    
    _scheduler.start()
    logger.info(
        f"스케줄러 시작: 매일 {settings.sync_hour:02d}:{settings.sync_minute:02d} 동기화 예약"
    )


def stop_scheduler():
    """스케줄러 종료"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
