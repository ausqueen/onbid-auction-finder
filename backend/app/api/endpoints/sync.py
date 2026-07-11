from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...config import get_settings
from ...services.sync_service import sync_properties, get_last_synced_at, get_sync_progress

router = APIRouter(prefix="/sync", tags=["sync"])
settings = get_settings()

_is_syncing = False


@router.post("")
def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """수동 데이터 동기화 트리거"""
    global _is_syncing
    # 온비드 동기화 비활성화 시(ONBID_SYNC_ENABLED=false) API 직접 호출도 차단 —
    # 프론트 버튼만 막고 엔드포인트는 열려 있어 429 쿼터 초과가 재발하던 문제 방지.
    if not settings.onbid_sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="온비드 동기화가 비활성화되어 있습니다 (ONBID_SYNC_ENABLED=false).",
        )
    if _is_syncing:
        return {"message": "동기화가 이미 진행 중입니다", "status": "running"}

    _is_syncing = True

    def run_sync():
        global _is_syncing
        from ...database import SessionLocal
        bg_db = SessionLocal()
        try:
            sync_properties(bg_db)
        except Exception as e:
            import logging
            logging.error(f"동기화 중 오류 발생: {e}")
        finally:
            bg_db.close()
            _is_syncing = False

    background_tasks.add_task(run_sync)
    return {"message": "동기화를 시작했습니다", "status": "started"}


@router.get("/status")
def get_sync_status():
    """동기화 상태 및 진행률 조회"""
    progress = get_sync_progress()
    return {
        "is_syncing": _is_syncing,
        "last_synced_at": get_last_synced_at().isoformat() if get_last_synced_at() else None,
        "progress": progress,
    }
