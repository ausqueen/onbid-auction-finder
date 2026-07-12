import os
import logging
import datetime
import re
import subprocess
import sys
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import case
from typing import List
import glob

from ...database import get_db, SessionLocal
from ...models.bankruptcy import BankruptcyProperty
from ...models.user import User
from ...models.favorite import UserFavoriteBankruptcy
from ...models.read import UserReadBankruptcy
from ...schemas.bankruptcy import BankruptcyPropertyResponse
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
from ...services.scourt_scraper import collect_all_notices, collect_all_notices_ex, scrape_bankruptcy_notices
from ...services.gemini_service import analyze_bankruptcy_notice
from ...api.endpoints.auth import get_current_user

router = APIRouter(prefix="/bankruptcy", tags=["bankruptcy"])
logger = logging.getLogger(__name__)

from ...sync_status import get_status, set_status


# ── 헬퍼 ──────────────────────────────────────────────

def delete_expired_properties(db: Session):
    try:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        properties = db.query(BankruptcyProperty).all()
        deleted_count = 0
        for prop in properties:
            deadline = prop.sale_deadline
            if not deadline or deadline in ("미정", "해당 없음"):
                continue
            match = re.search(r"\d{4}-\d{2}-\d{2}", deadline)
            if match and match.group(0) < today_str:
                logger.info(f"만료 공고 삭제: {prop.title} (기일: {match.group(0)})")
                db.delete(prop)
                deleted_count += 1

        if deleted_count > 0:
            db.commit()
            logger.info(f"기일 경과 {deleted_count}건 삭제 완료")
    except Exception as e:
        logger.error(f"만료 공고 삭제 에러: {e}")


# ── Phase 1: 빠른 목록 수집 ─────────────────────────────

async def phase1_collect():
    """
    공고게시판 전체 목록(최대 50페이지) 기본정보를 빠르게 DB에 저장.
    PDF 다운로드·Gemini 분석 없음. is_analyzed=False로 저장.
    """
    set_status(phase="collecting", message="목록 수집 시작...")
    db = SessionLocal()
    try:
        notices, reached_end = await collect_all_notices_ex(max_pages=200)
        new_count = 0
        for info in notices:
            try:
                exists = db.query(BankruptcyProperty).filter(
                    BankruptcyProperty.notice_url == info["notice_url"]
                ).first()
                if exists:
                    continue

                prop = BankruptcyProperty(
                    title=info["title"],
                    court_name=info["court_name"],
                    post_date=info.get("post_date") or None,
                    notice_url=info["notice_url"],
                    is_analyzed=False,
                )
                db.add(prop)
                db.commit()
                new_count += 1
                set_status(phase="collecting", message=f"{new_count}건 저장됨")
            except Exception as e:
                db.rollback()
                logger.error(f"[Phase1] DB 저장 에러 ({info.get('title', '제목없음')}): {e}")

        total = db.query(BankruptcyProperty).count()
        set_status(phase="done", message=f"목록 수집 완료: {new_count}건 신규 저장 (DB 총 {total}건)")
        logger.info(f"[Phase1] 완료: {new_count}건 신규 저장 (DB 총 {total}건)")

        # 만료/삭제된 공고 정합성 맞추기 — 전체 수집(reached_end)+충분량일 때만(부분 수집 시 대량 오삭제 방지)
        if not reached_end:
            logger.warning("[Phase1] 목록 부분 수집(캡/실패) — 삭제 정합성 스킵(오삭제 방지)")
        if reached_end and len(notices) > 100:
            valid_urls = {info["notice_url"] for info in notices}
            db_props = db.query(BankruptcyProperty).all()
            deleted_count = 0
            for prop in db_props:
                if prop.notice_url not in valid_urls:
                    # 게시판에서 내려간 공고의 로컬 첨부파일도 정리
                    if prop.attachment_filename:
                        from ...services.scourt_scraper import DOWNLOAD_DIR
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
                logger.info(f"[Phase1] 게시판에서 사라진 공고 {deleted_count}건 DB·파일 삭제 완료")

    except Exception as e:
        set_status(phase="error", message=f"오류: {e}")
        logger.error(f"[Phase1] 실패: {e}")
    finally:
        db.close()


# ── Phase 2: 상세 페이지 메타데이터 파싱 헬퍼 ────────────────

async def _parse_detail_meta(page) -> dict:
    """
    대법원 공고 상세 페이지(RealNoticeView.work)의 테이블에서
    매각기관, 관할법원, 작성일, 공고만료일, 첨부파일명, 전화번호를 파싱합니다.

    예시 테이블 구조:
      매각기관  | 채무자 주식회사 금영엔지니어링의 파산관재인 ○○○
      관할법원  | 서울회생법원
      제목      | 파산매각공고       조회수  | 201
      작성일    | 2026.04.28         공고만료일 | 2026.05.20
      첨부파일  | 2025하합625 주식회사 금영엔지니어링 채권매각공고.hwp
      전화번호  | 031-211-5902
    """
    result = {}
    try:
        # th-td 쌍으로 행 데이터 파싱
        rows = await page.locator("table.tableWri tr").element_handles()
        for row in rows:
            ths = await row.query_selector_all("th")
            tds = await row.query_selector_all("td")
            for i, th in enumerate(ths):
                label = (await th.inner_text()).strip()
                if i < len(tds):
                    value = (await tds[i].inner_text()).strip()
                else:
                    continue

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
                    a_tag = await tds[i].query_selector("a")
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




# ── 기존 deep-scan (debug.py 전환용) ──────────────────

async def sync_bankruptcy_properties():
    """debug.py에서 호출되는 레거시 함수 — Phase1 수집 수행."""
    await phase1_collect()


# ── API 라우트 ─────────────────────────────────────

@router.get("/progress", dependencies=[Depends(get_current_user)])
def get_progress():
    """Phase1/Phase2a/Phase2b 진행 상태를 반환합니다."""
    db = SessionLocal()
    try:
        total = db.query(BankruptcyProperty).count()
        not_analyzed = db.query(BankruptcyProperty).filter(
            BankruptcyProperty.is_analyzed == False
        ).count()
        analyzed = total - not_analyzed

        # 로컬 파일 보유 현황 (파일 동기화 상태 파악용)
        from ...services.scourt_scraper import DOWNLOAD_DIR
        try:
            synced_files = len(glob.glob(os.path.join(DOWNLOAD_DIR, "*.*")))
        except Exception:
            synced_files = -1

        status = get_status()
        return {
            **status,
            "total_in_db": total,
            "analyzed_in_db": analyzed,
            "pending_analysis": not_analyzed,
            "synced_files": synced_files,
        }
    finally:
        db.close()


def _run_in_proactor_thread(coro_func, *args, **kwargs):
    import asyncio
    import sys
    
    def sync_worker():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_func(*args, **kwargs))
        finally:
            loop.close()

    return asyncio.to_thread(sync_worker)


@router.get("/check-new", dependencies=[Depends(get_current_user)])
async def check_new_notices(db: Session = Depends(get_db)):
    """최신 1페이지를 조회하여 DB에 없는 신규 공고가 있는지 확인"""
    import asyncio
    from ...services.scourt_scraper import collect_all_notices
    try:
        notices = await _run_in_proactor_thread(collect_all_notices, max_pages=1)
        new_count = 0
        for info in notices:
            exists = db.query(BankruptcyProperty).filter(
                BankruptcyProperty.notice_url == info["notice_url"]
            ).first()
            if not exists:
                new_count += 1
        return {"has_new": new_count > 0, "new_count_in_page_1": new_count}
    except Exception as e:
        logger.error(f"check-new error: {e}")
        return {"has_new": False, "new_count_in_page_1": 0}


@router.post("/sync", dependencies=[Depends(get_current_user)])
def trigger_phase1_sync():
    """Phase 1: 공고게시판 전체 목록 빠른 수집 (AI 분석 없음). 독립 subprocess로 실행."""
    status = get_status()
    if status.get("phase") in ("collecting", "analyzing", "file_syncing"):
        return {"message": "이미 작업이 진행 중입니다.", "status": "already_running"}

    script_path = Path(__file__).parent.parent.parent.parent / "debug.py"
    subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    set_status(phase="collecting", message="목록 수집 프로세스 시작됨")
    return {
        "message": "공고게시판 전체 목록 수집을 시작했습니다. (AI 분석 없이 기본 정보 먼저 수집)",
        "status": "started",
    }


@router.post("/file-sync", dependencies=[Depends(get_current_user)])
def trigger_phase2a_file_sync(mode: str = "quick"):
    """
    Phase 2a: 파일 동기화 (다운로드 전용, AI 분석 없음). 독립 subprocess로 실행.

    mode=quick (기본): 로컬 파일 없거나 크기 0인 항목만 다운로드
    mode=full        : 전체 항목 대상 — 파일명 변경·크기 변경·미존재 시 재다운로드
    """
    if mode not in ("quick", "full"):
        mode = "quick"

    status = get_status()
    if status.get("phase") in ("collecting", "analyzing", "file_syncing"):
        return {"message": "이미 작업이 진행 중입니다.", "status": "already_running"}

    script_path = Path(__file__).parent.parent.parent.parent / "download_sync_worker.py"
    subprocess.Popen(
        [sys.executable, str(script_path), mode],
        cwd=str(script_path.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    set_status(phase="file_syncing", message=f"파일 동기화 프로세스 시작됨 (mode={mode})")
    return {
        "message": f"파일 동기화를 시작했습니다. (mode={mode})",
        "status": "started",
        "mode": mode,
    }


@router.post("/analyze", dependencies=[Depends(get_current_user)])
def trigger_phase2b_analyze():
    """Phase 2b: 미분석 항목 AI 분석 (분당 8건 속도 제한). 독립 subprocess로 실행."""
    status = get_status()
    if status.get("phase") in ("collecting", "analyzing", "file_syncing"):
        return {"message": "이미 작업이 진행 중입니다.", "status": "already_running"}

    script_path = Path(__file__).parent.parent.parent.parent / "analyze_worker.py"
    subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    set_status(phase="analyzing", message="AI 분석 프로세스 시작됨")
    return {
        "message": "미분석 항목 AI 분석을 시작했습니다. (분당 약 8건 처리)",
        "status": "started",
    }


@router.get("/", response_model=List[BankruptcyPropertyResponse])
def get_bankruptcy_properties(
    address: str | None = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """파산/회생 매각 공고 목록을 반환합니다.
    - `address` (optional): 부분 주소 문자열을 제공하면 해당 주소가 포함된 공고를 반환합니다.
    공고게시판 번호(board_no) 내림차순 (예: 446, 445...)으로 최신 공고 먼저.
    """
    query = db.query(BankruptcyProperty)
    if address:
        # 주소가 있거나 제목에 포함된 경우만 검색
        from sqlalchemy import or_
        query = query.filter(
            or_(
                BankruptcyProperty.address.ilike(f"%{address}%"),
                BankruptcyProperty.title.ilike(f"%{address}%")
            )
        )

    fav_ids = {
        f.bankruptcy_id for f in db.query(UserFavoriteBankruptcy)
        .filter(UserFavoriteBankruptcy.user_id == current_user.id).all()
    }

    read_ids = {
        r.bankruptcy_id for r in db.query(UserReadBankruptcy)
        .filter(UserReadBankruptcy.user_id == current_user.id).all()
    }

    items = (
        query.order_by(
            # SQLite는 NULLS LAST 미지원 → case/when으로 NULL을 뒤로
            case((BankruptcyProperty.board_no.is_(None), 1), else_=0),
            BankruptcyProperty.board_no.desc()
        )
        .all()
    )

    for item in items:
        item.is_favorite = item.id in fav_ids
        item.is_read = item.id in read_ids

    return items

@router.get("/{property_id}/download")
def download_attachment(
    property_id: int, 
    filename: str | None = None, 
    token: str | None = None,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None)
):
    """로컬에 저장된 첨부파일을 다운로드/조회합니다."""
    # ── Token Verification (Header or Query Param) ──
    actual_token = token
    if not actual_token and authorization and authorization.startswith("Bearer "):
        actual_token = authorization.split(" ")[1]
        
    if not actual_token:
        raise HTTPException(status_code=401, detail="인증 토큰이 유효하지 않거나 만료되었습니다.")
        
    try:
        import jwt
        from ...config import get_settings
        settings = get_settings()
        payload = jwt.decode(actual_token, settings.jwt_secret_key, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=401, detail="인증 토큰이 유효하지 않거나 만료되었습니다.")

    # 승인된 사용자만 다운로드 허용 (get_current_user 와 동일 정책 — 자체 디코드 경로라 누락돼 있던 검증 보강)
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_approved:
        raise HTTPException(status_code=403, detail="다운로드 권한이 없습니다.")

    # 자동 읽음(체크) 처리 추가
    try:
        if user:
            existing_read = db.query(UserReadBankruptcy).filter(
                UserReadBankruptcy.user_id == user.id,
                UserReadBankruptcy.bankruptcy_id == property_id
            ).first()
            if not existing_read:
                read_record = UserReadBankruptcy(user_id=user.id, bankruptcy_id=property_id)
                db.add(read_record)
                db.commit()
    except Exception as e:
        logger.error(f"Download auto-read failed for property_id={property_id}: {e}")

    prop = db.query(BankruptcyProperty).filter(BankruptcyProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="공고 정보를 찾을 수 없습니다.")
    
    # SQLAlchemy identity map 캐시 무효화 - 항상 최신 DB 내용 사용
    try:
        db.refresh(prop)
    except Exception:
        pass

    # attachments가 None인데 DB에 실제 JSON이 있을 경우 직접 sqlite3로 폴백
    if prop.attachments is None:
        try:
            import sqlite3 as _sqlite3, json as _json
            from ...database import engine as _engine
            db_path = str(_engine.url).replace("sqlite:///", "")
            _conn = _sqlite3.connect(db_path)
            _row = _conn.execute(
                "SELECT attachments FROM bankruptcy_properties WHERE id=?", (property_id,)
            ).fetchone()
            _conn.close()
            if _row and _row[0]:
                prop.attachments = _json.loads(_row[0])
        except Exception:
            pass
    
    from ...services.scourt_scraper import DOWNLOAD_DIR
    
    if filename:
        local_filename = None
        if prop.attachments:
            for att in prop.attachments:
                if att.get("filename") == filename:
                    local_filename = att.get("local_filename")
                    break
        
        if not local_filename:
            safe_fname = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
            local_filename = f"{property_id}_{safe_fname}"
            
        file_path = os.path.join(DOWNLOAD_DIR, local_filename)
        if not os.path.exists(file_path):
            # 1. property_title 기반 파일명이 있는지 우선 확인
            safe_title = prop.title.replace("/", "_").replace("\\", "_")[:30]
            title_based_filename = f"{property_id}_{safe_title}{filename[-4:]}"
            title_based_path = os.path.join(DOWNLOAD_DIR, title_based_filename)
            if os.path.exists(title_based_path):
                file_path = title_based_path
            else:
                # 2. 와일드카드 매칭 폴백 (파일명 키워드 우선, ID 키워드 차선)
                search_pattern = os.path.join(DOWNLOAD_DIR, f"{property_id}_*{filename[-4:]}")
                files_found = glob.glob(search_pattern)
                # _OLD_ 파일 제외
                files_found = [f for f in files_found if not os.path.basename(f).startswith('_OLD_')]
                if files_found:
                    matched_file = None
                    clean_fname = "".join([c for c in filename if c.isalnum()]).strip()
                    clean_title = "".join([c for c in prop.title if c.isalnum()]).strip()
                    # 파일명 키워드 우선 매칭
                    for f in files_found:
                        f_base = os.path.basename(f)
                        clean_f_base = "".join([c for c in f_base if c.isalnum()]).strip()
                        if clean_fname and clean_fname in clean_f_base:
                            matched_file = f
                            break
                    # ID 키워드 차선 매칭
                    if not matched_file:
                        for f in files_found:
                            f_base = os.path.basename(f)
                            clean_f_base = "".join([c for c in f_base if c.isalnum()]).strip()
                            if clean_title and clean_title in clean_f_base:
                                matched_file = f
                                break
                    file_path = matched_file if matched_file else files_found[0]
                else:
                    raise HTTPException(status_code=404, detail="서버에 파일이 존재하지 않습니다.")
        
        resp = FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    else:
        if not prop.attachment_filename:
            raise HTTPException(status_code=404, detail="첨부파일 정보를 찾을 수 없습니다.")
            
        # 1. 파일명 기반 경로 확인
        safe_fname = "".join([c for c in prop.attachment_filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        file_path = os.path.join(DOWNLOAD_DIR, f"{property_id}_{safe_fname}")
        
        # 2. 존재하지 않으면 ID 기반 경로 확인
        if not os.path.exists(file_path):
            safe_title = prop.title.replace("/", "_").replace("\\", "_")[:30]
            title_based_path = os.path.join(DOWNLOAD_DIR, f"{property_id}_{safe_title}{prop.attachment_filename[-4:]}")
            if os.path.exists(title_based_path):
                file_path = title_based_path
        
        # 3. 그래도 존재하지 않으면 glob 폴백
        if not os.path.exists(file_path):
            search_pattern = os.path.join(DOWNLOAD_DIR, f"{property_id}_*.*")
            files = glob.glob(search_pattern)
            if not files:
                raise HTTPException(status_code=404, detail="서버에 파일이 존재하지 않습니다.")
            
            matched_file = None
            clean_title = "".join([c for c in prop.title if c.isalnum()]).strip()
            clean_fname = "".join([c for c in prop.attachment_filename if c.isalnum()]).strip()
            for f in files:
                f_base = os.path.basename(f)
                clean_f_base = "".join([c for c in f_base if c.isalnum()]).strip()
                if clean_fname in clean_f_base or clean_title in clean_f_base:
                    matched_file = f
                    break
            
            file_path = matched_file if matched_file else files[0]
            
        out_filename = prop.attachment_filename
        if prop.attachments:
            base_file = os.path.basename(file_path)
            for att in prop.attachments:
                if att.get("local_filename") == base_file:
                    out_filename = att.get("filename")
                    break
                    
        resp = FileResponse(
            path=file_path,
            filename=out_filename,
            media_type="application/octet-stream"
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


@router.post("/{bankruptcy_id}/read", response_model=dict)
def mark_bankruptcy_as_read(
    bankruptcy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """파산 물건을 읽음 상태로 표시"""
    bp = db.query(BankruptcyProperty).filter(BankruptcyProperty.id == bankruptcy_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="파산 물건을 찾을 수 없습니다.")

    existing = db.query(UserReadBankruptcy).filter(
        UserReadBankruptcy.user_id == current_user.id,
        UserReadBankruptcy.bankruptcy_id == bankruptcy_id
    ).first()

    if not existing:
        read_record = UserReadBankruptcy(user_id=current_user.id, bankruptcy_id=bankruptcy_id)
        db.add(read_record)
        db.commit()

    return {"message": "읽음 상태로 표시되었습니다.", "is_read": True}


@router.delete("/{bankruptcy_id}/read", response_model=dict)
def mark_bankruptcy_as_unread(
    bankruptcy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """파산 물건을 안읽음 상태로 표시"""
    read_record = db.query(UserReadBankruptcy).filter(
        UserReadBankruptcy.user_id == current_user.id,
        UserReadBankruptcy.bankruptcy_id == bankruptcy_id
    ).first()

    if read_record:
        db.delete(read_record)
        db.commit()

    return {"message": "안읽음 상태로 표시되었습니다.", "is_read": False}
