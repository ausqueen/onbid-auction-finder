# hyunsung 서버 컨텍스트 (구 wonrealty, Contabo — 5.104.87.178)

## 서버 정보
- **호스트명**: hyunsung (구 wonrealty, 2026-07-03 변경 — 도메인 wonrealty.kr과 무관)
- **IP**: 5.104.87.178
- **도메인**: wonrealty.kr, portainer.wonrealty.kr (HTTPS 운영 중)
- **OS**: Ubuntu 24.04 LTS
- **Timezone**: Asia/Seoul (KST)

## 계정
| ID | 비밀번호 | 권한 |
|----|----------|------|
| root | `<관리자 보관 — 평문 미기재>` | root |
| ausqueen | `<관리자 보관 — 평문 미기재>` | sudo |
| hyunsung567 | `<관리자 보관 — 평문 미기재>` | sudo |

> 🔐 **비밀번호는 이 파일에 평문으로 적지 않음**(2026-06-29). 실제 값은 별도 보관(패스워드 매니저 등).
> `ausqueen` sudo는 NOPASSWD라 비번 입력 불필요. SSH 비밀번호 인증은 유지 중.

> ⚠️ **SSH 보안**: root 직접 SSH 로그인 **차단됨**(`PermitRootLogin no`, 2026-06-28).
> 반드시 `ausqueen` 또는 `hyunsung567`로 접속 후 `sudo` 사용. 비밀번호 인증은 유지.
> sshd 설정 백업: `/etc/ssh/sshd_config.bak.20260628`

## 주요 경로
| 경로 | 설명 |
|------|------|
| `/opt/onbid-auction-finder` | 메인 프로젝트 (GitHub clone) |
| `/opt/onbid-auction-finder/data/onbid.db` | SQLite DB → 컨테이너 `/app/onbid.db` 로 마운트 |
| `/opt/onbid-auction-finder/data/tmp_downloads` | PDF 첨부파일 저장소 → 컨테이너 `/app/tmp_downloads` |
| `/opt/onbid-auction-finder/backend/.env` | 환경변수 |
| `/opt/onbid-auction-finder/scripts/renew-cert.sh` | 인증서 자동 갱신 스크립트 |
| `/mnt/nas` | NAS 마운트 (ausqueen.synology.me:/volume2/vpsshr/linux, NFS) — **여러 서버 공유** |
| `/mnt/nas/hyunsung/backend/.env` | NAS 백업 .env |
| `/mnt/nas/hyunsung/backend/onbid.db` | NAS 백업 DB |
| `/mnt/nas/hyunsung/_archive_orphans/` | 옛 프로토타입 잔재 보관 (scourt_auction·downloads·temp, 2026-07-03 정리) |
| `/mnt/nas/abb_agent/install.run` | Synology ABB 에이전트 설치 파일 |

> ⚠️ **NAS 공유 마운트 — 서버별 하위폴더 격리**: 같은 `/volume2/vpsshr/linux`가 **hyunsung·realty99 양쪽 `/mnt/nas`에 마운트**됨.
> `/mnt/nas/X` == NAS 실제 `/volume2/vpsshr/linux/X`. 서버 구분은 하위폴더로: **이 서버(hyunsung)=`hyunsung/`** (구 `wonrealty/`, 2026-07-03 개명), **realty99=`daon/`·`backup/`**, 공용=`abb_agent/`.
> 이 서버(onbid)는 `/mnt/nas`를 자동으로 쓰지 않음(컨테이너·크론 미참조). `hyunsung/*`는 마이그레이션 때 수동 1회 백업본. (ABB 백업은 `/mnt/nas` NFS 경유 아님 — 별도 저장소)

> ⚠️ **컨테이너 경로 주의**: 볼륨 마운트는 `./data/onbid.db:/app/onbid.db`, `./data/tmp_downloads:/app/tmp_downloads`.
> 컨테이너 내부에 `/app/data/` 디렉터리는 **없음**. DB=`/app/onbid.db`, 첨부=`/app/tmp_downloads`.
> 워커 스크립트(debug.py, download_sync_worker.py, analyze_worker.py)는 `/app/` 에 위치. 앱 패키지는 `/app/app/`.

## Docker 컨테이너
```bash
cd /opt/onbid-auction-finder
docker compose ps          # 상태 확인
docker compose logs -f backend   # 백엔드 로그
docker compose logs -f nginx     # nginx 로그
docker compose restart backend   # 재시작
docker compose build backend && docker compose up -d backend   # 코드 수정 후 재빌드(코드는 이미지에 baked-in)
```

| 컨테이너 | 이미지 | 포트 |
|----------|--------|------|
| onbid-backend | onbid-auction-finder-backend (Playwright v1.60.0-noble) | 8001 (expose) |
| onbid-nginx | nginx:1.27-alpine | 80, 443 |
| portainer | portainer/portainer-ce:latest (2.39.4) | 호스트 미노출, nginx 프록시 |
| onbid-certbot | certbot/certbot:latest | profile=certbot (갱신 시만) |

## 서비스 구조
- **FastAPI** 백엔드 (포트 8001) — uvicorn `app.main:app`
- **React/Vite** 프론트엔드 — `/opt/onbid-auction-finder/frontend/dist`
- **SQLite** DB — WAL 모드
- **Playwright** (Chromium) — 파산공매 스크래핑
- **PLAYWRIGHT_BROWSERS_PATH=/ms-playwright** (Docker ENV)

## Phase 구성 & 자동 스케줄 (APScheduler, Asia/Seoul)
앱 내장 스케줄러(`backend/app/scheduler.py`)가 lifespan에서 시작됨. main.py에서 `start_scheduler()` 호출.

| Phase | 스크립트(컨테이너 경로) | 역할 | 자동 실행(KST) |
|-------|----------|------|------|
| Phase 1 | debug.py (scourt_scraper 래핑) | 대법원 공매 목록 수집 | 08:30, 13:30 |
| Phase 2a | download_sync_worker.py (quick/full) | PDF 파일 동기화 | 08:35, 13:35 |
| Phase 2b | analyze_worker.py | Gemini AI 분석 | 08:40, 13:40 |
| ~~(온비드)~~ | ~~sync_properties()~~ | ~~온비드 일일 동기화~~ | **비활성화(2026-06-29)** |

수동 실행 예:
```bash
docker exec -d onbid-backend bash -c 'cd /app && python debug.py'                       # Phase 1
docker exec -d onbid-backend bash -c 'cd /app && python download_sync_worker.py quick'  # Phase 2a
docker exec -d onbid-backend bash -c 'cd /app && python analyze_worker.py'              # Phase 2b
```
상태파일: 컨테이너 `/app/app/sync_status.json`. Phase1 로그: `/app/debug_log.txt`.

## SSL 인증서
- **발급**: Let's Encrypt (certbot, Docker `certbot` 프로파일, webroot=`/var/www/certbot`)
- **경로**: `/opt/onbid-auction-finder/certbot/conf/live/wonrealty.kr/`
- **SAN 도메인**: wonrealty.kr, www.wonrealty.kr, **portainer.wonrealty.kr**
- **만료**: 2026-09-26
- **자동 갱신**: systemd timer `certbot-renew.timer` (매일 00·12시 + 랜덤지연 1h)
  → `scripts/renew-cert.sh` 실행(certbot renew → nginx reload). 로그: `/var/log/certbot-renew.log`
  ```bash
  systemctl list-timers certbot-renew.timer
  systemctl start certbot-renew.service   # 수동 1회 실행(미도래 시 skip)
  ```

## Portainer (Docker 관리 UI)
- **접속**: https://portainer.wonrealty.kr (관리자 계정 생성 완료)
- **구성**: 호스트 포트 미노출. compose 네트워크(`onbid-auction-finder_default`)에 연결되어
  nginx가 `portainer:9000` 으로 리버스 프록시 (WebSocket 지원). 볼륨 `portainer_data`.
- **재설치 시 setup token**: `docker logs portainer | grep setup_token`

## Antigravity CLI (agy)
- hyunsung(구 wonrealty) 서버에 v1.0.13 설치 — `~/.local/bin/agy` (ausqueen 계정)
- 설치: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
- 사용 전 Google 로그인 필요(SSH 세션은 인증 URL 출력 → 로컬 브라우저 로그인)

## Synology Active Backup for Business (ABB) 에이전트
- wonrealty에 설치(2026-06-28). 드라이버 `synosnap`(dkms) + 서비스 3.2.0-5053
- 서비스: `synology-active-backup-business-linux-service` (systemd, enabled)
- NAS 연결: `ausqueen.synology.me`, 계정 `hyunsung567`
- 명령: `sudo abb-cli -s`(상태) / `sudo abb-cli -c`(연결) / `sudo abb-cli -h`(도움말)
- 호스트 볼륨 블록 백업 → `/opt/.../data`(DB·PDF) 포함. (WAL DB 일관성 위해 향후 사전 스냅샷 훅 권장)

## GitHub
- **Repo**: ausqueen/onbid-auction-finder (private)
- **PAT**: `<평문 미기재>` — 실제 토큰은 서버 git remote URL에만 저장(`git -C /opt/onbid-auction-finder remote get-url origin`). 폐기·재발급 시 remote URL도 교체.
- **최신 커밋**: 532d5e9 (feat(frontend): 온비드 데이터 수집 버튼 비활성화 + 안내 문구)
  - ca862d5 (fix: 온비드 일일 동기화 비활성화 — data.go.kr 상세 API 429 쿼터 초과)

## 연결된 서버
| 서버 | IP | 역할 | 비고 |
|------|----|------|------|
| Oracle | 161.33.4.54 | 구 개발/테스트 (운영 이전됨) | |
| Contabo (운영) | 5.104.87.178 | 운영 서버 (hostname: hyunsung, 구 wonrealty) | 현재 운영. onbid + hsrealty(예정) |
| Contabo (realty99) | 5.104.87.20 | realty99.co.kr — 금강 다온 부동산 중개 사이트(**daon**) | Next.js14+FastAPI+PostgreSQL16(daondb)+Redis, 컨테이너 `daon_*`/`realty99_*`. `/mnt/nas` NFS 공유 |

> 🔑 **서버 간 SSH (2026-07-03)**: `hyunsung ↔ realty99` **양방향 무비번**(ed25519 키). ausqueen 계정.
> - hyunsung→realty99: 이 서버 `~/.ssh/id_ed25519` → realty99 authorized_keys 등록.
> - realty99→hsrealty(=hyunsung): realty99 `~/.ssh/id_ed25519` → 이 서버 authorized_keys 등록.
> - hsrealty.co.kr(5.104.87.178)로도 접속됨(DNS·포트22 정상). root SSH는 양쪽 차단 유지.

## 마이그레이션 완료 일자
2026-06-28 — Oracle → Contabo 전환 완료

## 2026-06-28 작업 이력
- PDF 첨부파일 다운로드 오류 해결 → Phase 2a 동기화 완료 (498/498, 누락 0)
- certbot 자동 갱신 systemd timer 구성
- root SSH 직접 로그인 차단
- Antigravity CLI(agy) 설치
- Synology ABB 에이전트 설치 + NAS 연결, 첫 백업 수행
- Portainer 설치(portainer.wonrealty.kr) + 인증서 SAN 확장
- 앱 내장 스케줄러 재활성화 (Contabo 이전 후 비활성 상태였음) + 워커 경로 버그 수정
- 스케줄러에 Phase 2a(PDF 동기화) 작업 추가 → 수집→동기화→분석 완전 자동화

## 2026-06-29 작업 이력
- **스케줄러 타임존 버그 수정** — 운영 컨테이너가 timezone 수정 반영 전 코드로 가동 중이라
  스케줄러가 KST가 아닌 **UTC로 발화**(예: Phase1 08:30/13:30 KST 의도 → 실제 17:30/22:30 KST)하던 배포 불일치 발견.
  이미지엔 `BackgroundScheduler(timezone="Asia/Seoul")`(`backend/app/scheduler.py:85`)가 baked-in 돼 있었으나 가동 프로세스에 미적용 상태였음.
  → `docker compose build backend && up -d backend` 재빌드·재기동으로 해소. 컨테이너 내 트리거 next_run이 `+0900 KST`로 정상화됨을 확인
  (Phase1/2a/2b 13:30/13:35/13:40 KST, 온비드 익일 09:00 KST).
  ※ 교훈: 코드 수정 후 반드시 재빌드·재기동해야 baked-in 코드가 실제 적용됨.
- **온비드 일일 동기화 비활성화** — 수동 전체 동기화 중 data.go.kr OnBid 상세 API가
  **429(호출 쿼터 초과) 2,737건** 발생(2,400+건 일괄 상세조회가 원인). 당분간 동기화 미수행으로 결정.
  - 플래그 추가: `backend/app/config.py`의 `onbid_sync_enabled: bool = False`(기본 비활성).
    `backend/app/scheduler.py`의 `daily_sync` 잡을 `if settings.onbid_sync_enabled:`로 가드.
  - **재개 방법**: `backend/.env`에 `ONBID_SYNC_ENABLED=true` 추가 → `docker compose build backend && up -d backend`.
    재기동 로그에 "온비드 일일 동기화 비활성화됨 … 잡 미등록" 대신 `Added job "온비드 일일 동기화"`가 찍히면 정상.
  - 백업: `config.py.bak.20260629`, `scheduler.py.bak.20260629`. ⚠️ 이 변경은 **로컬 수정**이며 GitHub 미push 상태.
  - 재개 전 **증분 동기화 + 병렬화 + 쿼터 확인**(아래 미완료 항목) 먼저 적용 권장.
- **프론트 온비드 '데이터 수집' 버튼 비활성화 + 안내 문구** (커밋 532d5e9) — 백엔드 동기화 비활성화에 맞춰
  온비드 탭(`frontend/src/pages/Dashboard.tsx`)의 "데이터 수집" 버튼을 비활성화하고, 옆에 안내 표시:
  *"현재 수집 기능 수정 중입니다. 수집이 일시 중단되어, 표시되는 데이터는 과거 데이터입니다."*
  - 플래그: `const COLLECTION_DISABLED: boolean = true` → **재개 시 `false`로 변경 후 재빌드**.
  - 빌드/배포: `cd frontend && npm install --legacy-peer-deps && npm run build` (vite peer 충돌로 `--legacy-peer-deps` 필요).
    산출물 `frontend/dist`는 nginx가 직접 서빙(`./frontend/dist:/usr/share/nginx/html`) — **재빌드만 하면 즉시 반영**(nginx 재시작 불필요, 기존 접속자는 새로고침 필요). `dist/`는 .gitignore.
  - 백업: `Dashboard.tsx.bak.20260629`. ※ 이 repo 파일들은 CRLF 줄바꿈 — 편집 시 보존 주의.

## 2026-07-03 작업 이력
- **OS 호스트명 변경** `wonrealty` → `hyunsung` (`sudo hostnamectl set-hostname hyunsung`).
  무중단 적용 — Docker(onbid-backend/nginx)·ABB·서비스 재시작 불필요, 정상 확인.
  - **도메인 `wonrealty.kr`과 무관**(호스트명 ≠ DNS 도메인). SSL·nginx·웹서비스 영향 없음.
    nginx 설정 파일명 `wonrealty.conf`, NAS 백업 경로 `/mnt/nas/hyunsung/…`는 호스트명이 아니므로 **그대로 유지**.
  - ABB 백업: 장비 식별은 `device_uuid`(Machine ID `61e1389a…`)+token 기준이라 **백업 이력·체인 유지**.
    NAS UI 표시명만 다음 에이전트 인증 시 `hyunsung`으로 갱신됨.
  - 재부팅 리버트 방지: `/etc/cloud/cloud.cfg`의 `preserve_hostname: false` → **`true`** 로 변경.
- **개발/테스트 서버(Contabo test, 84.247.164.65) 폐기** — 더 이상 존재하지 않음. 관련 문서 항목 전부 삭제.
- **realty99 서버 파악 + NAS 서버별 격리 + 서버간 SSH 키**:
  - realty99(5.104.87.20) 정체 확인 = **금강 다온 부동산 중개 사이트(daon)**. `/opt/daon`, Next.js14+FastAPI+PG16(daondb)+Redis. NAS `/mnt/nas/daon/`(media·upload) 사용.
  - `/mnt/nas`가 hyunsung·realty99 **공유 마운트**임을 확인 → 서버별 하위폴더 격리 규칙 문서화(위 NAS 주의 참조).
  - 이 서버의 고아 잔재(`scourt_auction`·`downloads`·`temp` = 옛 대법원공매 프로토타입, 양 서버 미사용) → `hyunsung/_archive_orphans/`로 이동 정리. **이 서버 NAS 폴더 규칙: `/mnt/nas/hyunsung/`** (구 wonrealty에서 개명, 이후 이 서버의 NAS 사용은 여기 하위로).
  - **hyunsung ↔ realty99 양방향 무비번 SSH** 구성(ed25519, ausqueen). realty99→hsrealty.co.kr 접속 정상 검증(hostname `hyunsung` 확인).

## 미완료 항목
- [x] ~~PDF 파일 동기화~~ — 완료 (498/498)
- [x] ~~certbot 자동 갱신 설정~~ — 완료 (systemd timer)
- [ ] VWorld API 도메인 인증 (wonrealty.kr 등록 필요 — map.vworld.kr 개발자 콘솔)
- [ ] (권장) SSH 키 등록 후 `PasswordAuthentication no` + fail2ban
- [ ] (권장) ABB 백업 전 WAL DB 사전 스냅샷(`sqlite3 .backup`) 훅
- [ ] **온비드 일일 동기화 성능 개선** (2026-06-29 진단, 수정 보류 / **현재 동기화 비활성 상태** — 위 작업이력 참조) — `sync_properties`가 느린 원인은
  Playwright가 **아니라** `backend/app/services/sync_service.py`의 **직렬 처리 구조**임.
  (참고: 온비드 동기화는 Playwright 미사용 — `onbid_client`가 OnBid OpenAPI(data.go.kr)를 httpx로 호출,
   시세는 `molit_client` 국토부 API. Playwright는 대법원 스크래핑·`onbid_crawler` 보증금 추출에만 사용.)
  병목 3가지: ① 물건마다 `time.sleep(0.3)`(sync_service.py:95) → ~2,400건이면 sleep만 ~12분,
  ② 상세(`fetch_property_detail`)·시세를 1건씩 **순차 HTTP 호출**, ③ 매일 **전체 재조회**(증분 아님).
  개선안(효과순): **증분 동기화**(변경분만 상세 조회) > **상세·시세 병렬화**(httpx async/스레드풀 5~10 동시) >
  sleep 축소 > 시세 캐싱. ⚠️ 선행 확인: **data.go.kr 발급키 일일 호출쿼터/TPS**(현 0.3s 딜레이가 그 방어로 추정).
  로그의 `지원하지 않는 시도: …`는 에러 아님 — `molit_client.py:93`, 미지원 시·도 시세 조회 스킵 경고.
