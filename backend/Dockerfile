FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

# 2026-07-25: 상류가 v1.60.0-noble 태그를 재빌드하지 않아(마지막 빌드 2026-05-18) 베이스에
# OS 보안 업데이트 74건이 누적돼 있었음. Playwright 버전은 그대로 두고(브라우저 번들 정합 유지)
# 배포판 패키지만 최신화한다. Chromium 실행에 필요한 라이브러리도 같은 noble 저장소에서 올라옴.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# constraints.txt = 2026-07-12 운영 이미지의 pip freeze 전량(전이 의존성 포함).
# 이게 없으면 재빌드마다 전이 의존성이 제멋대로 올라감(실제로 pydantic 이 알파 2.14.0a1 로 튐).
COPY requirements.txt constraints.txt ./
# ⚠️ 위 apt upgrade 로 python3 패키지가 갱신되면서 PEP 668 표시(EXTERNALLY-MANAGED)가 생겨
#    pip 가 시스템 파이썬 설치를 거부함. 이 이미지는 원래부터 venv 없이 시스템 파이썬에
#    설치해 왔고 CMD(uvicorn)도 그 경로를 쓰므로, 기존 동작 그대로 유지하도록 명시 허용한다.
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt -c constraints.txt

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
