import os
import json
import logging
import subprocess

import fitz  # PyMuPDF
from google import genai
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BankruptcyExtraction(BaseModel):
    asset_type: str
    target_property: str
    address: str
    min_price: str
    manager_contact: str
    sale_deadline: str
    summary: str


def extract_text_from_file(file_path: str) -> str:
    """HWP 파일에서 텍스트를 추출합니다. PDF는 Gemini File API로 직접 처리합니다."""
    if not os.path.exists(file_path):
        return ""

    ext = file_path.lower().split('.')[-1]
    text = ""

    try:
        if ext == 'hwp':
            # HWP 파일은 CP949(EUC-KR) 인코딩이 일반적 - UTF-8 우선, 실패 시 CP949 재시도
            for encoding in ('utf-8', 'cp949', 'euc-kr'):
                try:
                    result = subprocess.run(
                        ["hwp5txt", file_path],
                        capture_output=True,
                        text=True,
                        encoding=encoding,
                        timeout=30,
                    )
                    if result.returncode == 0 and result.stdout:
                        text = result.stdout
                        break
                except (UnicodeDecodeError, subprocess.TimeoutExpired):
                    continue
    except Exception as e:
        logger.error(f"파일 텍스트 추출 에러 ({file_path}): {e}")

    return text[:15000]  # 토큰 초과 방지


def analyze_bankruptcy_notice(file_path: str, title: str) -> dict:
    """Gemini API로 파산 공고문에서 핵심 투자 지표를 구조화된 JSON으로 추출합니다."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY가 등록되지 않았습니다.")
        return {}

    # SDK가 환경변수를 직접 읽는 경우도 대비해 명시적으로 설정
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key

    client = genai.Client(api_key=api_key)

    document_text = ""
    ext = ""
    if file_path and os.path.exists(file_path):
        ext = file_path.lower().split('.')[-1]
        if ext != 'pdf':
            document_text = extract_text_from_file(file_path)

    prompt = f"""
    당신은 20년 경력의 파산 자산 매각 공고문을 분석하는 최고 전문가입니다.
    아래에 제공된 제목과 공고문 원본을 읽고, 다음 항목을 추출해서 한글로 반환해주세요.
    발견되지 않는 항목은 "내용 없음"라고 적어주세요.

    [특별 지시사항]
    1. asset_type은 반드시 ["부동산", "유체동산", "채권", "기타"] 중 하나로만 대답해주세요.
    2. summary 속성에는 본문/위치/가격을 종합적으로 고려하여, "이 물건이 투자/매수할 가치가 있는지"
       장단점을 포함한 전문가적 추천 관점의 요약 브리핑(3~4문장)을 작성해주세요.
    3. 본문에서 물건지의 정확한 소재지(도로명 주소 또는 지번 주소)를 찾아 "address" 속성에 문자열로 응답하세요. 주소가 여러 개면 가장 대표적인 1개만 적어주세요.
    4. sale_deadline(매각기일 혹은 입찰마감일)은 반드시 "YYYY-MM-DD" 형식의 날짜 문자열(예: "2026-05-15")로 변환해서 응답하세요. 기일이 정해지지 않았거나 수시/상시매각인 경우 "미정"이라고 반환하세요.
    5. 당신의 분석 결과, 이 물건이 일반적인 기준으로 볼 때 "투자 또는 매수할 가치가 충분한 추천 물건"에 해당하는지 여부를 true / false 로 응답하세요. (is_recommended)
    6. 결과물은 무조건 마크다운 없이 순수 JSON 형태({{}}) 여야 합니다. 다음과 같은 키를 포함하세요:
       "asset_type", "target_property", "address", "min_price", "manager_contact", "sale_deadline", "summary", "is_recommended"

    [제목]
    {title}
    """

    contents_list = [prompt]
    uploaded_file = None

    try:
        # PDF 파일이거나 텍스트가 추출되지 않은 경우 Gemini File API 직접 업로드 사용
        if file_path and os.path.exists(file_path) and (ext == 'pdf' or len(document_text.strip()) < 50):
            logger.info(f"네이티브 파일 업로드 모드 작동 (PDF 또는 파싱 실패): {file_path}")
            uploaded_file = client.files.upload(file=file_path)
            contents_list.append(uploaded_file)
        else:
            contents_list.append(f"\n[공고문 원문]\n{document_text}")

        import time
        time.sleep(4.5)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_list
        )
        text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
    except Exception as e:
        logger.error(f"Gemini API 호출 에러: {e}")
        return {}
    finally:
        # 할당량 초과 방지를 위해 업로드한 객체는 분석이 끝나면 즉시 파기
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                logger.warning(f"임시 파일 파기 실패: {e}")

    return result
