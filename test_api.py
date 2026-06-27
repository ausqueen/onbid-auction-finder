"""
온비드 API 직접 테스트 - 실제 응답 확인
"""
import sys
import os
sys.path.insert(0, 'backend')
os.chdir('backend')

# .env 로드
from dotenv import load_dotenv
load_dotenv('.env')

import httpx
import logging
logging.basicConfig(level=logging.INFO)

api_key = os.getenv('ONBID_API_KEY', '')
print(f"API KEY: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")

url = "https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2"
params = {
    "serviceKey": api_key,
    "numOfRows": 5,
    "pageNo": 1,
    "resultType": "xml",
    "prptDivCd": "0007,0005,0010,0002",
    "pvctTrgtYn": "N",
}

print("\n온비드 API 호출 중...")
try:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, params=params)
    print(f"HTTP 상태: {resp.status_code}")
    print(f"응답 (처음 1000자):\n{resp.text[:1000]}")
except Exception as e:
    print(f"오류: {e}")
