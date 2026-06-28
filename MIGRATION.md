# wonrealty.kr 서버 Windows → Linux 마이그레이션

## 서버 정보

| 항목 | 내용 |
|------|------|
| 도메인 | wonrealty.kr |
| 현재 OS | Windows Server 2025 (10.0.26100) |
| 목표 OS | Ubuntu 24.04.4 LTS |
| 호스팅 | Contabo (일본 리전) |
| IP | 5.104.87.178 |
| 호스트명 | realty99 |
| RDP 접속 | admin / Realty!@34 |
| SSH 접속 | admin / Realty!@34 (포트 22, 84.247.164.65만 허용) |

> SSH는 이번 작업 중 설치 완료. 방화벽은 유럽 서버 IP(84.247.164.65)만 허용.

---

## 앱 구조

### 서비스명
온비드/파산공매 추천 서비스 (`onbid-auction-finder`)

### 경로
```
C:\antigravity\onbid-auction-finder\
  ├── backend\
  │   ├── app\
  │   │   ├── main.py
  │   │   ├── scheduler.py      # APScheduler 내장 (별도 cron 불필요)
  │   │   ├── database.py
  │   │   ├── config.py
  │   │   ├── api\endpoints\    # auth, admin, properties, analysis, sync, bankruptcy, users
  │   │   ├── models\           # property, user, favorite, read, bankruptcy
  │   │   ├── schemas\
  │   │   └── services\         # gemini, molit, onbid, crawler, price/risk analyzer, scourt
  │   ├── .venv\                # Python 가상환경 (이전 불필요)
  │   ├── .env                  # 환경변수 (이전 필요)
  │   ├── onbid.db              # SQLite DB (이전 필요, ~2.8MB)
  │   ├── onbid.db-wal
  │   ├── onbid.db-shm
  │   ├── tmp_downloads\        # PDF 파일 (이전 불필요, sync 후 자동 복구)
  │   ├── requirements.txt
  │   ├── debug.py              # sync Phase 1: 법원경매 스크래퍼
  │   └── analyze_worker.py     # sync Phase 2: AI 분석
  ├── frontend\                 # React + Vite + Tailwind
  │   ├── src\
  │   ├── dist\
  │   ├── package.json
  │   └── vite.config.ts
  ├── run_all_sync.bat          # 외부 동기화 스크립트 (Linux에서 불필요)
  └── run_hidden.vbs            # 백그라운드 실행용 (Linux에서 불필요)
```

### 기술 스택
| 구분 | 스택 |
|------|------|
| 백엔드 | Python 3.11 + FastAPI + Uvicorn (포트 8001) |
| 프론트엔드 | React 18 + TypeScript + Vite + Tailwind CSS |
| DB | SQLite (onbid.db) |
| 웹서버 | nginx (80→443 리다이렉트, SSL termination) |
| SSL | win-acme → Linux에서 certbot으로 대체 |
| AI | Google Gemini API |
| 스크래핑 | Playwright (Chromium) |
| 문서파싱 | PyMuPDF, pyhwp |
| 스케줄러 | APScheduler 앱 내장 (외부 cron 불필요) |

---

## 스케줄러 구조 (중요)

APScheduler가 FastAPI 앱 내부에 통합되어 있어 **별도 외부 cron 없이** 자동 실행됨.

| 스케줄 | 내용 | 방식 |
|--------|------|------|
| 매일 09:00 | 온비드 물건 동기화 | APScheduler 내장 |
| 매일 08:30, 13:30 | 법원 파산 공고 수집 (debug.py) | APScheduler 내장 |
| 매일 08:40, 13:40 | AI 분석 (analyze_worker.py) | APScheduler 내장 |
| 매일 00:00, 12:00, 18:00 | 추가 동기화 (Windows 전용) | 필요 시 cron 추가 |

> Linux/Windows 플랫폼 분기도 코드에 이미 처리됨 (`sys.platform == "win32"` 조건)

---

## 환경변수 (.env)

```env
ONBID_API_KEY=<NAS /wonrealty/backend/.env 참조>
MOLIT_API_KEY=<NAS /wonrealty/backend/.env 참조>
GEMINI_API_KEY=<NAS /wonrealty/backend/.env 참조>
NAVER_CLIENT_ID=<NAS /wonrealty/backend/.env 참조>
NAVER_CLIENT_SECRET=<NAS /wonrealty/backend/.env 참조>
KAKAO_JS_API_KEY=<NAS /wonrealty/backend/.env 참조>
VWORLD_API_KEY=<NAS /wonrealty/backend/.env 참조>
APP_NAME=온비드 공매 추천 서비스
DEBUG=false
DB_URL=sqlite:///./onbid.db
PLAYWRIGHT_BROWSERS_PATH=C:\Users\admin\AppData\Local\ms-playwright
SYNC_HOUR=9
SYNC_MINUTE=0
MIN_GAP_PCT=10.0
TOP_N=20
MAX_PAGES=50
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Linux 이전 시 .env 수정 항목

| 항목 | 기존 값 | 변경 값 |
|------|---------|---------|
| `PLAYWRIGHT_BROWSERS_PATH` | `C:\Users\admin\AppData\Local\ms-playwright` | `/root/.cache/ms-playwright` |
| `JWT_SECRET_KEY` | 미설정 (기본값 사용 중 ⚠️) | 강력한 랜덤 키로 신규 추가 |
| `ALLOWED_ORIGINS` | localhost만 허용 | `https://wonrealty.kr` 추가 |

---

## nginx 설정 요약

```nginx
# HTTP → HTTPS 리다이렉트 (wonrealty.kr, www.wonrealty.kr)
# HTTPS 443:
#   /api/  → http://127.0.0.1:8001  (FastAPI)
#   /      → 정적 파일 dist/ 서빙 (Linux에서 Vite dev 서버 대신 빌드본 사용)
```

---

## SSL 인증서

Linux에서 certbot으로 재발급:
- `wonrealty.kr` + `www.wonrealty.kr`

---

## 파일 이전 구조

```
Windows 서버 (일본)               NAS                        Linux 서버
Z:\vpsshr\wonrealty\   ←WebDAV→   /volume2/vpsshr/linux   ←NFS→   /mnt/nas/
```

> ⚠️ Z: 드라이브는 SSH 세션에서 접근 불가 (WebDAV는 사용자 세션 종속)
> 파일 복사는 RDP 접속 후 수동 복사 또는 scp 직접 전송 사용

### 이전 대상 파일

| 파일 | 크기 | 이전 방법 | 비고 |
|------|------|-----------|------|
| `backend/onbid.db` | ~2.8MB | scp 또는 NAS 경유 | 회원정보, 물건분석 데이터 |
| `backend/onbid.db-wal` | 소량 | scp 또는 NAS 경유 | SQLite WAL |
| `backend/onbid.db-shm` | 소량 | scp 또는 NAS 경유 | SQLite SHM |
| `backend/.env` | 소량 | scp 또는 NAS 경유 | API 키 등 환경변수 |
| `tmp_downloads/` | ~970MB | ❌ 불필요 | 배포 후 UI "파일 동기화(빠른)" 버튼으로 재다운로드 (~16분) |
| 소스코드 | - | ❌ GitHub clone | PAT 필요 (비공개 저장소) |

---

## 마이그레이션 진행 상태

- [x] 서버 구조 파악
- [x] 앱 스택 분석
- [x] .env 내용 확인
- [x] scheduler.py 분석 (APScheduler 내장 확인)
- [x] SSH 설치 및 접속 확인 (포트 22, IP 84.247.164.65 허용)
- [x] GitHub 저장소 URL 확인 (https://github.com/yskwon911259-dev/onbid-auction-finder.git, 비공개)
- [x] test 서버 hostname → test, timezone → Asia/Seoul
- [x] test 서버 Python 3.11.15 / Node.js v20.20.2 / npm 10.8.2 설치
- [x] NAS NFS 마운트 (ausqueen.synology.me:/volume2/vpsshr/linux → /mnt/nas, fstab 등록)
- [x] Windows↔NAS WebDAV 연결 확인 (Z:\vpsshr\wonrealty, SSH에서는 접근 불가)
- [x] GitHub PAT 발급 후 소스코드 클론 → ausqueen/onbid-auction-finder (새 저장소)
- [x] Windows 서버 git remote → ausqueen/onbid-auction-finder 로 변경
- [x] onbid.db / onbid.db-wal / onbid.db-shm / .env → scp로 Linux 이전
- [x] .env 수정 (PLAYWRIGHT_BROWSERS_PATH, JWT_SECRET_KEY, ALLOWED_ORIGINS)
- [x] Python 3.11 가상환경 구성 및 pip install -r requirements.txt
- [x] Playwright Chromium 설치 (/root/.cache/ms-playwright)
- [x] 프론트엔드 빌드 (npm install --legacy-peer-deps && npm run build)
- [x] nginx 설치 및 설정 (정적 파일 서빙, HTTPS 주석으로 준비)
- [x] systemd 서비스 등록 (onbid-backend.service, 부팅 자동시작)
- [x] config.py 수정 (vworld_api_key 필드 추가, extra=ignore) → GitHub push
- [x] 동작 확인 (/health: DB 물건 1,761개, nginx /api/ 프록시 정상)
- [x] **1차 마이그레이션: Oracle 서버(161.33.4.54) Docker 배포** (2026-06-28)
- [x] Oracle 서버 iptables + VCN Security List 포트 80/443 오픈
- [x] certbot SSL 인증서 발급 (wonrealty.kr, 만료: 2026-09-26)
- [x] DNS wonrealty.kr → 161.33.4.54 전환 및 HTTPS 서비스 정상 확인
- [x] 토지이음(vworld_map.html, ol.js, ol.css, lucide.min.js) GitHub 추가
- [x] Playwright Docker 이미지 v1.52.0 → v1.60.0 업데이트
- [x] 배포 설정 파일 GitHub 추가 (docker-compose.yml, nginx/wonrealty.conf, .dockerignore)
- [x] Oracle 서버 DB → test 서버 복사 (2026-06-28 14:40)
- [x] `.env` PLAYWRIGHT_BROWSERS_PATH `/root/.cache/ms-playwright` → `/ms-playwright` 수정 (Oracle + test 서버)
- [x] **파산공매 Phase 1 (법원공매 목록 수집) 정상 동작 확인** — 498건 수집 (2026-06-28)
- [x] **파산공매 Phase 2 (AI 분석) 정상 동작 확인** — 0건 (기존 데이터라 신규 없음, 정상)
- [x] **파산공매 Phase 2a/2b 분리** — download_sync_worker.py(파일 동기화), analyze_worker.py(AI 분석) 독립화
- [x] Oracle 서버 PDF 파일 497건 재다운로드 완료 (download_sync_worker.py quick 모드)
- [ ] **VWorld API 도메인 인증 (wonrealty.kr 등록 필요)** — 토지이음 지도 표시용
- [ ] Contabo 재설치 완료 후 최종 마이그레이션 (5.104.87.178)
- [ ] **DNS wonrealty.kr: 161.33.4.54 → 5.104.87.178 전환** (Contabo 배포 완료 후)
- [ ] certbot SSL 재발급 (Contabo 서버에서)
- [ ] Contabo 배포 후 Phase 2a 파일 동기화 실행 (UI에서 "파일 동기화(빠른)" 클릭)

---

## Oracle 서버 현재 상태 (2026-06-28)

| 항목 | 내용 |
|------|------|
| IP | 161.33.4.54 |
| OS | Ubuntu 24.04.4 LTS |
| 접속 | ausqueen / Os390r10@@ |
| Docker | 29.6.1 |
| 소스코드 | /opt/onbid-auction-finder (GitHub main) |
| 백엔드 | onbid-backend (Docker, 포트 8001 internal) |
| nginx | onbid-nginx (Docker, 포트 80/443) |
| SSL | certbot (wonrealty.kr, 만료: 2026-09-26) |
| DB 물건 수 | 1,761개 |
| DNS | wonrealty.kr → 161.33.4.54 (현재 서비스 중) |
| VWorld | ⚠️ 도메인 인증 필요 (토지이음 지도) |

---

## test 서버 현재 상태 (2026-06-28)

| 항목 | 내용 |
|------|------|
| OS | Ubuntu 24.04.4 LTS |
| hostname | test |
| timezone | Asia/Seoul (KST) |
| Python | 3.11.15 |
| Node.js | v20.20.2 |
| npm | 10.8.2 |
| NAS 마운트 | ausqueen.synology.me:/volume2/vpsshr/linux → /mnt/nas (NFS, fstab 등록) |
| 소스코드 | /root/antigravity/onbid-auction-finder |
| GitHub | ausqueen/onbid-auction-finder (main) |
| 백엔드 서비스 | onbid-backend.service (active, 포트 8001) |
| nginx | active (포트 80, HTTPS 주석 준비) |
| DB 물건 수 | 1,761개 확인 |
| DB 최신본 | /root/antigravity/onbid-auction-finder/backend/onbid.db (2026-06-28 14:40 Oracle에서 복사) |

---

## 이전 전 최종 체크리스트 (재설치 전 반드시 확인)

| 항목 | 상태 | 조치 |
|------|------|------|
| **onbid.db (최신본)** | ⚠️ 재복사 필요 | 이전 직전 Windows→Docker 서버로 scp 재복사 (Windows 서버가 매일 업데이트 중) |
| **onbid.db-wal 체크포인트** | ⚠️ 주의 | 복사 전 백엔드 중지 또는 `PRAGMA wal_checkpoint(FULL)` 실행 후 복사 |
| .env | ✅ 완료 | 모든 키 일치 확인 (MAX_PAGES=50 포함) |
| 소스코드 | ✅ 완료 | GitHub ausqueen/onbid-auction-finder push 완료 |
| tmp_downloads (~970MB) | ✅ 불필요 | 스케줄러가 자동 재다운로드 |
| SSL 인증서 | ✅ 재발급 예정 | certbot으로 대체 (win-acme 불필요) |
| NAS | ✅ 영향 없음 | 별도 서버, 재마운트만 하면 됨 |
| nginx 설정 | ✅ 문서화 | docker-compose nginx로 대체 |

### ⚠️ 스케줄 차이 주의

**Windows 작업 스케줄러** (현재 실행 중):
- `Onbid_Auction_Sync_0000` → 매일 **00:00** → debug.py + analyze_worker.py
- `Onbid_Auction_Sync_1200` → 매일 **12:00** → debug.py + analyze_worker.py
- `Onbid_Auction_Sync_1800` → 매일 **18:00** → debug.py + analyze_worker.py

**APScheduler** (Linux에서 실행될 스케줄):
- 매일 **09:00** → OnBid 동기화 (sync_properties)
- 매일 **08:30 / 13:30** → 파산공매 Phase1 (debug.py)
- 매일 **08:40 / 13:40** → 파산공매 Phase2 (analyze_worker.py)

> Windows에서 00:00 / 18:00에 추가 실행하던 것이 Linux에서는 없어짐.
> 필요시 `scheduler.py`에 시간 추가 가능 (현재 08:30/13:30 → 00:30/08:30/13:30 등으로 변경).
> 단, 현재 13:30에 1회만 해도 서비스 운영에 문제없으면 변경 불필요.

### 이전 직전 DB 복사 명령

> ✅ **완료 (2026-06-27 21:12):** Windows 재설치 전 test 서버로 DB 복사 완료  
> 경로: `/root/antigravity/onbid-auction-finder/backend/onbid.db` (물건 1,761개, 회원 10명)  
> WAL checkpoint(FULL) 실행 완료

```bash
# [Contabo 재설치 완료 후] test 서버 → wonrealty.kr 서버로 DB 복사 (test 서버에서 실행)
scp /root/antigravity/onbid-auction-finder/backend/onbid.db \
  root@5.104.87.178:/opt/onbid-auction-finder/data/onbid.db
```

---

## 남은 작업 계획 (wonrealty.kr 본서버 이전)

---

### Phase 1: wonrealty.kr Ubuntu 재설치 + Docker 환경 구성

#### 1-1. Contabo 패널에서 Ubuntu 재설치
- [ ] Contabo Customer Panel 로그인
- [ ] wonrealty.kr 서버(5.104.87.178) 선택 → OS 재설치
- [ ] Ubuntu 24.04 LTS 선택
- [ ] 재설치 완료 후 SSH 접속 확인

```bash
ssh root@5.104.87.178
# 비밀번호: os390r10
```

#### 1-2. 서버 기본 설정 (재설치 직후 가장 먼저 실행)
```bash
# 1) timezone 한국으로 설정 (필수 — 스케줄러가 Asia/Seoul 기준으로 동작)
timedatectl set-timezone Asia/Seoul
timedatectl   # 확인

# 2) hostname 변경
hostnamectl set-hostname wonrealty

# 3) 패키지 업데이트
apt-get update && apt-get upgrade -y

# 4) 방화벽 설정 (선택사항 — 마이그레이션 완료 후 적용 권장)
# Ubuntu 기본 설치 시 ufw inactive 상태 → 모든 포트 열림
# 서비스 안정화 후 아래 절차로 진행

# [Step 1] 현재 열린 포트 확인 (ufw 적용 전 반드시 실행)
# ss -tlnp                        # OS 레벨 리스닝 포트 전체 확인
# docker compose ps               # Docker 컨테이너 포트 매핑 확인
#
# 예상 포트:
#   22   → SSH (필수 허용)
#   80   → nginx HTTP (필수 허용)
#   443  → nginx HTTPS (필수 허용)
#   8001 → backend (Docker internal expose만 사용, 외부 불필요)

# [Step 2] 확인 후 필요한 포트만 허용 후 활성화 (SSH 먼저 — 순서 중요)
# ufw allow 22
# ufw allow 80
# ufw allow 443
# ufw enable
# ufw status
```

#### 1-3. Docker + Docker Compose 설치
```bash
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | tee /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker && systemctl start docker
```

#### 1-4. 소스코드 클론 및 디렉토리 구성
```bash
cd /opt
# ⚠️ PAT 만료 시 GitHub → Settings → Developer settings → Personal access tokens 에서 재발급
git clone https://<GitHub-PAT>@github.com/ausqueen/onbid-auction-finder.git
# ⚠️ PAT는 GitHub → Settings → Developer settings → Personal access tokens 에서 발급
# NAS /wonrealty/README.md 또는 로컬 메모에 보관
cd /opt/onbid-auction-finder

# Docker용 데이터 디렉토리 생성 (nginx/wonrealty.conf, Dockerfile, docker-compose.yml은 GitHub에 포함됨)
mkdir -p data/tmp_downloads certbot/conf certbot/www
```

> ✅ **GitHub clone 시 자동 포함 파일** (별도 작성 불필요):
> - `backend/Dockerfile` (v1.60.0-noble)
> - `backend/.dockerignore`
> - `docker-compose.yml`
> - `nginx/wonrealty.conf`
> - `backend/download_sync_worker.py` (Phase 2a 파일 동기화)
> - `backend/analyze_worker.py` (Phase 2b AI 분석)

#### 1-5. DB 파일 및 .env 복사

> ⚠️ **DB 출처**: Windows 서버 다운 → 최신 DB는 **Oracle 서버(161.33.4.54)** 또는 **NAS**에 있음.
> test 서버 DB는 구버전일 수 있으므로 Oracle 또는 NAS에서 복사할 것.

```bash
# 방법 A: Oracle 서버에서 직접 복사 (최신 DB 권장) — test 서버에서 실행
scp ausqueen@161.33.4.54:/opt/onbid-auction-finder/data/onbid.db \
  root@5.104.87.178:/opt/onbid-auction-finder/data/onbid.db

# 방법 B: NAS 백업본 복사 — Contabo 서버에서 실행 (NAS 마운트 후)
cp /mnt/nas/wonrealty/backend/onbid.db /opt/onbid-auction-finder/data/onbid.db

# [test 서버 또는 Contabo에서 실행] .env 복사 (Linux용, PLAYWRIGHT_BROWSERS_PATH=/ms-playwright 설정됨)
scp /mnt/nas/wonrealty/backend/.env \
  root@5.104.87.178:/opt/onbid-auction-finder/backend/.env

# .env의 PLAYWRIGHT_BROWSERS_PATH 확인 — /ms-playwright 이어야 함 (Docker ENV와 일치)
grep PLAYWRIGHT /opt/onbid-auction-finder/backend/.env
```

#### 1-6. Docker 파일 작성

> ✅ GitHub clone 시 자동 포함 — 아래 내용은 참고용 (별도 작성 불필요)

**Dockerfile (backend)**
```dockerfile
# /opt/onbid-auction-finder/backend/Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium (이미지에 이미 포함, 경로 확인용)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**.dockerignore (backend)**
```
# /opt/onbid-auction-finder/backend/.dockerignore
.env
onbid.db
onbid.db-wal
onbid.db-shm
tmp_downloads/
.venv/
__pycache__/
*.pyc
```

**nginx 설정 (Docker용 — HTTP 전용, ACME challenge 포함)**  
파일 위치: `/opt/onbid-auction-finder/nginx/wonrealty.conf`
```nginx
server {
    listen 80;
    server_name wonrealty.kr www.wonrealty.kr;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    location /health {
        proxy_pass http://backend:8001/health;
    }

    location /api/ {
        proxy_pass         http://backend:8001;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_buffering    off;
        client_max_body_size 50M;
        proxy_read_timeout   300s;
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

**docker-compose.yml**  
파일 위치: `/opt/onbid-auction-finder/docker-compose.yml`
```yaml
services:
  backend:
    build: ./backend
    container_name: onbid-backend
    restart: unless-stopped
    env_file: ./backend/.env
    volumes:
      - ./data/onbid.db:/app/onbid.db
      - ./data/tmp_downloads:/app/tmp_downloads
    expose:
      - "8001"

  nginx:
    image: nginx:1.27-alpine
    container_name: onbid-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/wonrealty.conf:/etc/nginx/conf.d/default.conf
      - ./frontend/dist:/usr/share/nginx/html
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - backend

  certbot:
    image: certbot/certbot:latest
    container_name: onbid-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    # 평상시 중지 상태. 발급/갱신 시 수동 실행.
    profiles:
      - certbot
```

#### 1-7. 프론트엔드 빌드 (본서버에서 직접 빌드 또는 dist 복사)
```bash
# 방법 A: test 서버 dist/ 를 본서버로 복사 (빠름, test 서버에서 실행)
scp -r /root/antigravity/onbid-auction-finder/frontend/dist \
    root@5.104.87.178:/opt/onbid-auction-finder/frontend/

# 방법 B: 본서버(wonrealty.kr)에서 직접 빌드 (Node.js 설치 필요)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
cd /opt/onbid-auction-finder/frontend
npm install --legacy-peer-deps
npm run build
```

#### 1-8. NAS NFS 마운트 (필요시)
```bash
apt-get install -y nfs-common
mkdir -p /mnt/nas
echo "ausqueen.synology.me:/volume2/vpsshr/linux  /mnt/nas  nfs  defaults,_netdev  0  0" >> /etc/fstab
mount -a && ls /mnt/nas
```

#### 1-9. Docker 이미지 빌드 및 서비스 기동
```bash
cd /opt/onbid-auction-finder
docker compose build --no-cache
docker compose up -d
docker compose ps                  # 상태 확인
docker compose logs -f backend     # 백엔드 로그 확인
curl http://localhost/health       # 백엔드 응답 확인 (/health 는 /api prefix 없음)
curl http://localhost/             # 프론트엔드 확인
```

#### 1-10. PDF 파일 동기화 (첫 기동 후 필수)

> `tmp_downloads`는 빈 상태로 시작됨. DB에 저장된 파산공매 공고의 PDF 첨부파일을
> 법원 사이트에서 재다운로드해야 파일 열람이 가능함.

```bash
# 방법 A: UI에서 실행 (권장)
# https://wonrealty.kr 로그인 → 파산공매 탭 → "파일 동기화 (빠른)" 버튼 클릭
# → 파일 없는 항목만 자동 다운로드 (약 498건 × 2초 = 약 16분 소요)

# 방법 B: 컨테이너 내에서 직접 실행
docker cp backend/download_sync_worker.py onbid-backend:/app/download_sync_worker.py
docker exec -d onbid-backend bash -c \
  'cd /app && python3 -u download_sync_worker.py quick > /tmp/file_sync.log 2>&1'
# 진행 확인
docker exec onbid-backend tail -f /tmp/file_sync.log
```

---

### Phase 2: certbot SSL 발급 (Docker 서비스 기동 직후)

> **참고:** wonrealty.kr 서버는 Windows→Ubuntu 재설치 시 IP(5.104.87.178) 변경 없음.
> DNS 레코드 변경 불필요. Docker 서비스(nginx 80포트)가 뜬 즉시 발급 가능.

#### 2-1. SSL 인증서 발급 (webroot 방식)
```bash
cd /opt/onbid-auction-finder

# nginx가 80 포트에서 ACME challenge를 서빙 중인 상태에서 실행
docker compose --profile certbot run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email ausqueen@gmail.com \
  --agree-tos \
  --no-eff-email \
  -d wonrealty.kr \
  -d www.wonrealty.kr
```

#### 2-2. nginx HTTPS 설정 활성화
`/opt/onbid-auction-finder/nginx/wonrealty.conf` 를 아래 내용으로 교체:
```nginx
# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name wonrealty.kr www.wonrealty.kr;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl;
    server_name wonrealty.kr www.wonrealty.kr;
    ssl_certificate     /etc/letsencrypt/live/wonrealty.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wonrealty.kr/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    add_header Strict-Transport-Security "max-age=15768000; includeSubDomains" always;
    client_max_body_size 50M;
    proxy_read_timeout   300s;

    location /health {
        proxy_pass http://backend:8001/health;
    }

    location /api/ {
        proxy_pass         http://backend:8001;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_buffering    off;
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# nginx 설정 재로드
cd /opt/onbid-auction-finder
docker compose exec nginx nginx -s reload
```

#### 2-3. 인증서 자동 갱신 설정 (cron)
```bash
# /etc/cron.d/certbot-renew 파일 생성
cat > /etc/cron.d/certbot-renew << 'EOF'
0 3 * * * root cd /opt/onbid-auction-finder && docker compose --profile certbot run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
EOF
```

#### 2-4. HTTPS 동작 최종 확인
```bash
curl -I https://wonrealty.kr
curl -s https://wonrealty.kr/health
```

---

### Phase 3: DNS 전환 및 서비스 전환 완료 확인

> **DNS 변경 필요.** 현재 wonrealty.kr은 Oracle(161.33.4.54)을 가리키고 있음.
> Contabo(5.104.87.178)로 전환 후 DNS를 변경해야 함.

#### 3-0. DNS 전환
- [ ] DNS 관리 패널에서 wonrealty.kr A 레코드: `161.33.4.54` → `5.104.87.178` 변경
- [ ] TTL 전파 대기 (보통 수 분 ~ 1시간)
- [ ] `nslookup wonrealty.kr` 으로 IP 확인

> ⚠️ DNS 전환 전 Contabo 서버에서 certbot SSL 발급이 완료되어 있어야 함.

#### 3-1. HTTPS 최종 확인
```bash
curl -I https://wonrealty.kr
curl -s https://wonrealty.kr/health
```

#### 3-2. 기능 확인 체크리스트
```bash
cd /opt/onbid-auction-finder
docker compose ps                                      # 전체 컨테이너 상태
docker compose logs backend | grep -i schedul          # 스케줄러 시작 확인
curl -s https://wonrealty.kr/health                # API 응답 확인
ls /mnt/nas                                            # NAS 마운트 확인
```
- [ ] https://wonrealty.kr 브라우저 접속 확인
- [ ] 로그인 동작 확인 (root / Realty!@34)
- [ ] 공매 물건 목록 조회 확인
- [ ] 스케줄러 로그에서 "00:30 / 08:30 / 13:30" 시간 확인

#### 3-3. Windows 서버 정리
- [ ] Contabo 패널에서 Windows 서버 중단 (이미 Ubuntu로 재설치됐으므로 해당 없음)

---

## 참고: 주요 접속 및 명령어

```bash
# wonrealty.kr Ubuntu 서버 접속
ssh root@5.104.87.178          # 비밀번호: os390r10

# Windows 서버 SSH (재설치 전까지)
sshpass -p 'Realty!@34' ssh -o StrictHostKeyChecking=no admin@5.104.87.178 "powershell -command \"...\""

# Oracle → Contabo DB 복사 (test 서버에서 실행, Windows 서버 다운으로 Oracle이 최신본)
sshpass -p 'Os390r10@@' scp -o StrictHostKeyChecking=no \
  ausqueen@161.33.4.54:/opt/onbid-auction-finder/data/onbid.db \
  root@5.104.87.178:/opt/onbid-auction-finder/data/onbid.db

# Docker 운영 명령 (wonrealty.kr 서버에서)
cd /opt/onbid-auction-finder
docker compose ps
docker compose logs -f backend
docker compose restart backend
docker compose exec nginx nginx -s reload

# NAS 마운트 확인
ls /mnt/nas && df -h /mnt/nas
```
