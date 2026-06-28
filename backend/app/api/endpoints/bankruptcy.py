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
from ...services.scourt_scraper import collect_all_notices, scrape_bankruptcy_notices
from ...services.gemini_service import analyze_bankruptcy_notice
from ...api.endpoints.auth import get_current_user

router = APIRouter(prefix="/bankruptcy", tags=["bankruptcy"])
logger = logging.getLogger(__name__)

from ...sync_status import get_status, set_status


# ?? ?퍼 ????????????????????????????????????????????

def delete_expired_properties(db: Session):
    try:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        properties = db.query(BankruptcyProperty).all()
        deleted_count = 0
        for prop in properties:
            deadline = prop.sale_deadline
            if not deadline or deadline in ("미정", "?용 ?음"):
                continue
            match = re.search(r"\d{4}-\d{2}-\d{2}", deadline)
            if match and match.group(0) < today_str:
                logger.info(f"만료 공고 ??: {prop.title} (기일: {match.group(0)})")
                db.delete(prop)
                deleted_count += 1

        if deleted_count > 0:
            db.commit()
            logger.info(f"기일 ?과 {deleted_count}??? ?료")
    except Exception as e:
        logger.error(f"만료 공고 ?? ?러: {e}")


# ?? Phase 1: 빠른 목록 ?집 ?????????????????????????

async def phase1_collect():
    """
    공고게시???체 목록(최? 50?이지) 기본?보?빠르?DB?????
    PDF ?운로드·Gemini 분석 ?음. is_analyzed=False????
    """
    set_status(phase="collecting", message="목록 ?집 ?작...")
    db = SessionLocal()
    try:
        notices = await collect_all_notices(max_pages=50)
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
                set_status(phase="collecting", message=f"{new_count}???됨")
            except Exception as e:
                db.rollback()
                logger.error(f"[Phase1] DB ????러 ({info.get('title', '?')}): {e}")

        total = db.query(BankruptcyProperty).count()
        set_status(phase="done", message=f"목록 수집 완료: {new_count}건 신규 저장 (DB 총 {total}건)")
        logger.info(f"[Phase1] 완료: {new_count}건 신규 저장 (DB 총 {total}건)")

        # 만료/????공고 ?합??맞추?(?크?핑???느 ?도 ?상?으??행?었???만)
        if len(notices) > 100:
            valid_urls = {info["notice_url"] for info in notices}
            db_props = db.query(BankruptcyProperty).all()
            deleted_count = 0
            for prop in db_props:
                if prop.notice_url not in valid_urls:
                    # 게시?에???려?공고??로컬 첨??일???리
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
                logger.info(f"[Phase1] 게시?에??????공고 {deleted_count}?DB ??일 ?? ?료")

    except Exception as e:
        set_status(phase="error", message=f"?류: {e}")
        logger.error(f"[Phase1] ?패: {e}")
    finally:
        db.close()


# ?? Phase 2: ?세 ?이지 메??이???싱 ?퍼 ????????????????

async def _parse_detail_meta(page) -> dict:
    """
    ?법원 공고 ?세 ?이지(RealNoticeView.work)???이블에??
    매각기?, 관?법?? ?성?? 공고만료?? 첨??일? ?화번호??싱?니??

    ?시 ?이?구조:
      매각기?  | 채무??주식?사 금영???어링의 ?산관?인 ?원??
      관?법?? | ?원?생법원
      ?목      | ?산매각공고       조회??| 201
      ?성??   | 2026.04.28         공고만료??| 2026.05.20
      첨??일  | 2025?합625 주식?사 금영???어?채권매각공고??hwp
      ?화번호  | 031-211-5902
    """
    result = {}
    try:
        # th-td ?으????이??싱
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

                if "매각기?" in label:
                    result["selling_agency"] = value
                elif "관할법원" in label or "법원" in label:
                    if not result.get("court_name"):
                        result["court_name"] = value
                elif "?성?? in " in label:
                    result["post_date"] = value.replace(".", "-") if "." in value else value
                # BYPASSED SYNTAX ERROR:                 elif "공고만료?? in label or "만료?? in label:
                    result["notice_expire_date"] = value.replace(".", "-") if "." in value else value
                elif "첨??일" in label:
                    # 첨??일 ??서 ?일?링크 ?는 ?스??추출
                    a_tag = await tds[i].query_selector("a")
                    if a_tag:
                        fname = (await a_tag.inner_text()).strip()
                        if fname:
                            result["attachment_filename"] = fname
                    elif value:
                        result["attachment_filename"] = value
                elif "?화번호" in label or "?화" in label:
                    result["phone_number"] = value
    except Exception as e:
        logger.warning(f"[_parse_detail_meta] ?싱 ?패: {e}")

    return result


# ?? Phase 2: AI 분석 (분당 8??한) ????????????????

async def phase2_analyze():
    """
    is_analyzed=False ?????에 ???PDF ?운로드 + Gemini 분석???행.
    분당 ~8??도 ?한 (ANALYSIS_DELAY_SEC=7.5?.
    """
    import asyncio
    from ...services.scourt_scraper import ANALYSIS_DELAY_SEC
    from playwright.async_api import async_playwright

    set_status(phase="analyzing", message="AI 분석 ?작...")
    db = SessionLocal()

    try:
        pending = db.query(BankruptcyProperty).filter(
            BankruptcyProperty.is_analyzed == False
        ).order_by(BankruptcyProperty.id.asc()).all()

        logger.info(f"[Phase2] 분석 ??? {len(pending)}?)")
        set_status(phase="analyzing", message=f"분석 ???{len(pending)}? 분당 8??도??작")

        analyzed_count = 0

        # Playwright 브라?? ?션???사?하??PDF ?운로드
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
                await asyncio.sleep(ANALYSIS_DELAY_SEC)  # 분당 ~8?

                downloaded_file_path = None
                attachment_filename_val = None
                try:
                    await detail_page.goto(prop.notice_url, timeout=30000)

                    # ?? ?세 ?이지 메??이???싱 (매각기?/?화번호/첨??일/만료?? ??
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
                        logger.warning(f"[Phase2] 메??이???싱 ?패 ({prop.id}): {meta_err}")

                    # ?? 첨??일 ?운로드 ??선?위 ?렬 (PDF > DOC > HWP) ??
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
                        
                        # PDF ?선 ?렬 (.pdf = 0, .doc = 1, .hwp = 2)
                        if attachments:
                            attachments.sort(key=lambda x: 0 if x["ext"] == '.pdf' else (1 if x["ext"] == '.doc' else 2))
                            
                            downloaded_attachments_info = []
                            from ...services import scourt_scraper as scS
                            
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
                                    path = os.path.join(scS.DOWNLOAD_DIR, local_name)
                                    await download.save_as(path)
                                    
                                    downloaded_attachments_info.append({
                                        "filename": orig_name,
                                        "local_filename": local_name,
                                        "ext": attach["ext"]
                                    })
                                    
                                    # ??일(?선?위 ?렬???해 PDF)?면??HWP가 ?닌 경우 AI 분석???일?지??
                                    if idx == 0 and attach["ext"] != '.hwp':
                                        downloaded_file_path = path
                                except Exception as single_dl_err:
                                    logger.error(f"[Phase2] 개별 ?일 ?운 ?패 ({prop.id}, {attach['filename']}): {single_dl_err}")
                            
                            if downloaded_attachments_info:
                                prop.attachments = downloaded_attachments_info
                                # ?위 ?환?으??첨??일????
                                prop.attachment_filename = downloaded_attachments_info[0]["filename"]
                                attachment_filename_val = downloaded_attachments_info[0]["filename"]
                    except Exception as dl_err:
                        logger.error(f"[Phase2] ?일 ?운 ?패 ({prop.id}): {dl_err}")
                except Exception as e:
                    logger.error(f"[Phase2] ?세 ?이지 ?류 ({prop.id}): {e}")

                # Gemini 분석 (HWP ?일?면 분석 불? ??메??이?만 ??????료 처리)
                is_hwp_attach = attachment_filename_val and attachment_filename_val.lower().endswith(".hwp")
                try:
                    if is_hwp_attach:
                        # HWP 첨?: AI 분석 불?, 메??이?만 ??하?analyzed=True 처리
                        prop.is_analyzed = True
                        prop.ai_summary = None  # ?론?엔?에??HWP ?내 ?시 ?리?
                        db.commit()
                        analyzed_count += 1
                        set_status(phase="analyzing", message=f"AI 분석 {analyzed_count}??료 (HWP ?일 ?외)")
                        logger.info(f"[Phase2] HWP ?일 ??메??이?만 ??? {prop.title[:30]}")
                    else:
                        extracted = analyze_bankruptcy_notice(downloaded_file_path, prop.title)
                        if not extracted or not extracted.get("summary"):
                            raise ValueError("Gemini API가 비어 ?는 ?약??반환?습?다. ?류?간주?여 분석 ???태????니??")

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
                        set_status(phase="analyzing", message=f"AI 분석 {analyzed_count}??료")
                        logger.info(f"[Phase2] 분석 ?료: {prop.title[:30]} ({analyzed_count}/{len(pending)})")

                except Exception as e:
                    db.rollback()
                    logger.error(f"[Phase2] Gemini ?러 ({prop.id}): {e}")

            await browser.close()

        set_status(phase="done", message=f"목록 수집 완료: {new_count}건 신규 저장 (DB 총 {total}건)")
        logger.info(f"[Phase2] ?료: {analyzed_count}?분석")

    except Exception as e:
        set_status(phase="error", message=f"AI 분석 ?류: {e}")
        logger.error(f"[Phase2] ?패: {e}")
    finally:
        db.close()


# ?? 기존 deep-scan (debug.py ?환?? ??????????????

async def sync_bankruptcy_properties():
    """debug.py?서 ?출?는 ?거???수 ??Phase1 ?집 ?행."""
    await phase1_collect()


# ?? API ?우?????????????????????????????????????

@router.get("/progress", dependencies=[Depends(get_current_user)])
def get_progress():
    """Phase1/Phase2 진행 ?태?반환?니??"""
    db = SessionLocal()
    try:
        total = db.query(BankruptcyProperty).count()
        not_analyzed = db.query(BankruptcyProperty).filter(
            BankruptcyProperty.is_analyzed == False
        ).count()
        analyzed = total - not_analyzed
        status = get_status()
        return {
            **status,
            "total_in_db": total,
            "analyzed_in_db": analyzed,
            "pending_analysis": not_analyzed,
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
    """최신 1?이지?조회?여 DB???는 ?규 공고가 ?는지 ?인"""
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
    """Phase 1: 공고게시???체 목록 빠른 ?집 (AI 분석 ?음) ???립 subprocess??행."""
    status = get_status()
    if status.get("phase") in ("collecting", "analyzing"):
        return {"message": "?? ?업??진행 중입?다.", "status": "already_running"}

    # Windows uvicorn ?벤??루프 충돌 방? ???립 ?로?스??행
    script_path = Path(__file__).parent.parent.parent.parent / "debug.py"
    subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    set_status(phase="collecting", message="목록 ?집 ?로?스 ?작??)")
    return {
        "message": "공고게시???체 목록 ?집???작?었?니?? (AI 분석 ?이 기본 ?보?먼? ?집)",
        "status": "started",
    }


@router.post("/analyze", dependencies=[Depends(get_current_user)])
def trigger_phase2_analyze():
    """Phase 2: 미분???? AI 분석 (분당 8??도 ?한) ???립 subprocess??행."""
    status = get_status()
    if status.get("phase") in ("collecting", "analyzing"):
        return {"message": "?? ?업??진행 중입?다.", "status": "already_running"}

    script_path = Path(__file__).parent.parent.parent.parent / "analyze_worker.py"
    subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    set_status(phase="analyzing", message="AI 분석 ?로?스 ?작??)")
    return {
        "message": "미분???? AI 분석???작?었?니?? (분당 ??8?처리)",
        "status": "started",
    }


@router.get("/", response_model=List[BankruptcyPropertyResponse])
def get_bankruptcy_properties(
    address: str | None = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """?산/?생 매각 공고 목록??반환?니??
    - `address` (optional): 부?주소 문자?을 ?공?면 ?당 주소가 ?함??공고?반환?니??
    공고게시??번호(board_no) ?림차순 ??446, 445... ?으?최신 공고 먼?.
    """
    query = db.query(BankruptcyProperty)
    if address:
        # 주소가 ?거???목???함??경우??검??
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
            # SQLite??NULLS LAST 미?????case/when?로 NULL???로
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
    """로컬????된 첨??일???운로드/조회?니??"""
    # ?? Token Verification (Header or Query Param) ??
    actual_token = token
    if not actual_token and authorization and authorization.startswith("Bearer "):
        actual_token = authorization.split(" ")[1]
        
    if not actual_token:
        raise HTTPException(status_code=401, detail="?증 ?큰???효?? ?거??만료?었?니??")
        
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
    
    # 자동 읽음(체크) 처리 추가
    try:
        user = db.query(User).filter(User.username == username).first()
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

    # attachments가 None?데 DB???제 JSON???을 경우 직접 sqlite3??백
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
            # 1. property_title 기반 ?일명이 ?는지 ?선 ?인
            safe_title = prop.title.replace("/", "_").replace("\\", "_")[:30]
            title_based_filename = f"{property_id}_{safe_title}{filename[-4:]}"
            title_based_path = os.path.join(DOWNLOAD_DIR, title_based_filename)
            if os.path.exists(title_based_path):
                file_path = title_based_path
            else:
                # 2. ??드카드 매칭 ?백 (?일??워???선, ??? ?워??차선)
                search_pattern = os.path.join(DOWNLOAD_DIR, f"{property_id}_*{filename[-4:]}")
                files_found = glob.glob(search_pattern)
                # _OLD_ ?일 ?외
                files_found = [f for f in files_found if not os.path.basename(f).startswith('_OLD_')]
                if files_found:
                    matched_file = None
                    clean_fname = "".join([c for c in filename if c.isalnum()]).strip()
                    clean_title = "".join([c for c in prop.title if c.isalnum()]).strip()
                    # ?일??워???선 매칭
                    for f in files_found:
                        f_base = os.path.basename(f)
                        clean_f_base = "".join([c for c in f_base if c.isalnum()]).strip()
                        if clean_fname and clean_fname in clean_f_base:
                            matched_file = f
                            break
                    # ??? ?워??차선 매칭
                    if not matched_file:
                        for f in files_found:
                            f_base = os.path.basename(f)
                            clean_f_base = "".join([c for c in f_base if c.isalnum()]).strip()
                            if clean_title and clean_title in clean_f_base:
                                matched_file = f
                                break
                    file_path = matched_file if matched_file else files_found[0]
                else:
                    raise HTTPException(status_code=404, detail="?버???일??존재?? ?습?다.")
        
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
            raise HTTPException(status_code=404, detail="첨??일 ?보?찾을 ???습?다.")
            
        # 1. ?일?기반 경로 ?인
        safe_fname = "".join([c for c in prop.attachment_filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        file_path = os.path.join(DOWNLOAD_DIR, f"{property_id}_{safe_fname}")
        
        # 2. 존재?? ?으???? 기반 경로 ?인
        if not os.path.exists(file_path):
            safe_title = prop.title.replace("/", "_").replace("\\", "_")[:30]
            title_based_path = os.path.join(DOWNLOAD_DIR, f"{property_id}_{safe_title}{prop.attachment_filename[-4:]}")
            if os.path.exists(title_based_path):
                file_path = title_based_path
        
        # 3. 그래??존재?? ?으?glob ?백
        if not os.path.exists(file_path):
            search_pattern = os.path.join(DOWNLOAD_DIR, f"{property_id}_*.*")
            files = glob.glob(search_pattern)
            if not files:
                raise HTTPException(status_code=404, detail="?버???일??존재?? ?습?다.")
            
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
