# hyunsung 서버 컨텍스트 (구 wonrealty, Contabo — 5.104.87.178)

> ⭐ **서비스 위상(2026-07-05)**: 이 서버의 **메인 서비스 = hsrealty(WooCommerce 쇼핑몰, `/opt/hsrealty`)**.
> **onbid-auction-finder = 서브 서비스**. 우선순위·리소스·장애대응 판단 시 **hsrealty 우선**.
> (이 CLAUDE.md 파일은 `/opt/onbid-auction-finder/`에 위치하지만 서버 전체 컨텍스트 문서임.)

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
| `/opt/onbid-auction-finder/data/onbid.db` | SQLite DB → 컨테이너 `/app/data/onbid.db` (디렉터리 마운트, 2026-07-11 변경) |
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

> ⚠️ **컨테이너 경로 주의**(2026-07-11 마운트 변경): 볼륨 마운트는 **`./data:/app/data`**(디렉터리) + `./data/tmp_downloads:/app/tmp_downloads`.
> DB=**`/app/data/onbid.db`**(`.env` `DB_URL=sqlite:////app/data/onbid.db`), 첨부=`/app/tmp_downloads`.
> ⚠️ **왜 디렉터리 마운트인가**: 예전 단일파일 마운트(`./data/onbid.db:/app/onbid.db`)는 SQLite `-wal/-shm`이 컨테이너 전용이라 **재빌드(컨테이너 재생성) 시 미체크포인트 WAL이 유실**됐음(#20, root 비번 재설정이 실제로 날아갔음). 디렉터리 마운트로 `-wal/-shm`이 호스트에 상주 → 유실 방지. 되돌리기 백업: `docker-compose.yml.bak.20260711`, `backend/.env.bak.20260711`, DB백업 `data/onbid.db.premount.20260711`.
> raw sqlite3 접근(analyze_worker.py:154, bankruptcy.py:622)은 `str(engine.url)`에서 경로 유도라 DB_URL만 따라옴. dev 스크립트 `clean_db.py`·`fix_bad_ai.py`는 `__file__` 기준 하드코딩(`/app/onbid.db`)이라 이 마운트에선 안 맞음 — 사용 시 수정 필요.
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

## hsrealty.co.kr — NAS 쇼핑몰 (WooCommerce, 2026-07-04 라이브)
- **경로**: `/opt/hsrealty/` (docker-compose.yml·.env·README.md·data/). `/opt`라 ABB 백업 포함. onbid와 별개 스택.
- **스택**: WordPress 7.0(ko_KR) + WooCommerce 10.9.3 + MariaDB 11.4. compose project `hsrealty`.
  - 컨테이너: `hsrealty-wp`(wordpress:php8.3-apache, `127.0.0.1:8083` 검증용만 노출), `hsrealty-db`(mariadb:11.4, 내부), `wpcli`(profile=cli 일회성).
  - 네트워크: 자체 `hsrealty_default` + 외부 `onbid-auction-finder_default` 합류 → onbid-nginx가 `hsrealty-wp:80` 프록시.
  - 데이터: `./data/db`(MariaDB)·`./data/wp`(WP코어·플러그인·업로드). 설정 KRW·KR·소수점0·Asia/Seoul.
- **공개**: `https://hsrealty.co.kr`(+www 정규리다이렉트). onbid-nginx `wonrealty.conf`에 80/443 블록 추가(443→`proxy_pass http://hsrealty-wp:80`, X-Forwarded-Proto https). 백업 `wonrealty.conf.bak.20260704`.
  - SSL 독립 lineage `hsrealty.co.kr`+www(만료 2026-09-26 아님 → **2026-10-02**), 기존 `certbot-renew.timer`가 전 lineage 자동갱신(webroot).
- **명령**: `cd /opt/hsrealty && sudo docker compose ps | logs -f wordpress | restart wordpress`. wp-cli: `sudo docker compose --profile cli run --rm wpcli <cmd>`.
- **시크릿·WP관리자**: `.env`(chmod600, git금지). 확인 `sudo grep WP_ADMIN /opt/hsrealty/.env`. 로그인 `https://hsrealty.co.kr/wp-admin/`.
- **주의**: docker는 ausqueen sudo 필요(docker그룹 아님). WP코어는 wp-cli로 관리(이미지태그 6.7.2보다 앞선 7.0). nginx conf는 단일파일 마운트 → **⚠️ 편집기(inode 교체 방식: Edit/sed -i 등)로 수정하면 `nginx -s reload`로 반영 안 됨**(컨테이너는 시작 시점 바인딩된 옛 inode를 계속 봄. 2026-07-08 확인). 확실한 반영은 `docker restart onbid-nginx`(순단 1~2초, 전 vhost). 반영 검증: `md5sum 호스트파일` == `docker exec onbid-nginx md5sum /etc/nginx/conf.d/default.conf`. (in-place 편집만 `nginx -s reload`로 반영. nginx compose에 새 볼륨 추가 시에만 재생성 순단.)
- **상품**: 79종 임포트 완료(카테고리·가격·이미지29). 멱등 임포터 `/opt/hsrealty/data/wp/hsrealty-import/import_products.php`(`wp eval-file`).
- **테마**: Storefront **자식 테마 `hsrealty`**(목업 디자인 이식 — 화이트헤더+실드로고, 네이비/골드/그린, 프론트 히어로). NAS 백업 `/mnt/nas/hyunsung/temp/hsrealty_theme_backup`. 프론트=page122(전체폭)+히어로, 주메뉴 id38.
  - ⚠️ **신규 스토어는 `woocommerce_coming_soon=yes`(store_pages_only) 기본 ON** → /shop·단일상품이 "준비중"으로 가려짐. 해제: `wp option update woocommerce_coming_soon no` (+`woocommerce_store_pages_only no`). 현재 해제됨=상점 라이브.
  - **로그인/회원가입 화면 분리(2026-07-05)**: 기본 WooCommerce는 /my-account/에 로그인+회원가입을 2단 동시표시 → 자식 테마 오버라이드 `woocommerce/myaccount/form-login.php`로 분리(기본=로그인만, "회원가입" 버튼 `?register=true`로 전환). style.css `.hsrealty-auth*` 추가, child style ver 1.0.2. 백업 `style.css.bak.20260705`·`functions.php.bak.20260705`.
  - **회원가입 정보 강화(2026-07-05)**: 가입폼에 이름·핸드폰 + 동의체크박스(이용약관·개인정보 필수, 마케팅 선택) + **주소(다음 우편번호 검색)** 추가. 핸드폰 형식검증(`/^01[0-9]-?\d{3,4}-?\d{4}$/`). 저장메타 billing_*·동의이력(타임스탬프)·마케팅여부. functions.php에 로직, 관리자 프로필에 가입정보 표시.
  - **클래식 체크아웃 전환(2026-07-05)**: 체크아웃(id7)·장바구니(id6) 블록형→숏코드(`[woocommerce_checkout]`/`[woocommerce_cart]`). 블록(React)은 다음 주소검색 자동입력 불안정 → 클래식 채택. 원본 블록 백업 로컬+NAS `/mnt/nas/hyunsung/temp/hsrealty_checkout_block_backup_20260705/`.
  - **다음(카카오) 주소검색(2026-07-05)**: 회원가입·주소편집·클래식 체크아웃 3곳. `assets/hs-address.js`(`.hs-addr-search` 클릭→`daum.Postcode` 팝업, 체크아웃/주소편집은 `#billing_postcode` 옆 버튼 JS주입). enqueue는 `is_account_page()||is_checkout()`. child style ver 1.0.4. 백업 `functions.php.bak.20260705c`.
  - **⏳ 보류: 핸드폰 본인인증(Solapi OTP)** — 사용자가 다음에 진행. 필요: Solapi API Key+Secret+**발신번호 등록**(SMS OTP는 채널·템플릿 불필요) + 충전. → 인증번호 전송/확인+3분만료+인증 전 가입차단 구현 예정.
  - **✅ 통신판매업 신고번호 표기(2026-07-08)**: 신고번호 **제2026-경기안산-1395호** 확정 → 푸터 사업자정보 위젯(`footer-1`의 Custom HTML `custom_html-3`, DB옵션 `widget_custom_html` i:3)에 "통신판매업 신고번호 제2026-경기안산-1395호" 추가(사업자등록번호 아래). 라이브 반영 확인. 옵션 백업=세션 스크래치패드. ⏭️ (선택) 체크아웃 페이지 하단 표기는 미적용.
  - **✅ 고액 상품 문의 전환(2026-07-09)**: KCP 신용카드 **건당 승인 한도 500만원** 대응 → **단가 500만원 초과** 상품은 온라인 결제 대신 전화/이메일 문의로 유도. 자식테마 `functions.php`에 블록 추가(백업 `functions.php.bak.20260709b`): `hs_is_inquiry_product()`(변형상품은 최고가 변형 기준) + ①`woocommerce_is_purchasable=false`(담기버튼 자동제거·URL직접담기/결제 차단) ②단일상품 CTA(`woocommerce_single_product_summary` 우선순위31: 📞tel `031-520-5552`+✉mailto `hs@hsrealty.co.kr` 제목에 상품명 자동) ③상점 루프버튼 `woocommerce_loop_add_to_cart_link`→'구매 문의'(상세로 이동) ④안전망 `woocommerce_add_to_cart_validation`. `style.css` `.hs-inquiry-*` 추가·자식테마 ver 1.1.4→**1.1.5**(백업 `style.css.bak.20260709`). **자동 판별**(코드수정 없이 신규 고액상품에 적용). 현재 대상 2종=APM-5NODES-1Y-VIRTUAL(693만)·D4ER01-64G(543.4만). 조정=`HS_INQUIRY_THRESHOLD`(0이면 끔). 라이브 경계검증 완료(427만·7.2만은 담기 유지). **기준=상품 단가만**(사용자 선택) → ⚠️ 저가 다수 합산으로 장바구니 합계>500만 시 KCP 카드승인 실패 가능(미방어). 필요 시 `woocommerce_available_payment_gateways`/`add_to_cart_validation`로 합계 가드 추가.
  - **✅ 고액 상품 완전 비공개(2026-07-09)**: 500만원 초과 2종을 상점/검색 숨김에서 더 나아가 **완전 비공개** 전환(사용자 요청). ①카탈로그 숨김 `catalog_visibility=hidden`(product_visibility 택소노미 `exclude-from-catalog`+`exclude-from-search`) ②`post_status=private`로 전환 → **비로그인 방문자는 직접 URL 접속도 HTTP 404 차단**(라이브 검증 완료), 관리자(ausqueen)만 열람·편집. 대상: **ID 24** APM-5NODES-1Y-VIRTUAL(693만)·**ID 80** D4ER01-64G(543.4만). 적용: `wp post update <id> --post_status=private` (+ 앞서 `wc product update <id> --catalog_visibility=hidden`) + `wp cache flush` + `wp wc tool run clear_transients`. 되돌리기=`--post_status=publish`. (문의전환 hook은 그대로 남아있으나 비공개라 노출 안 됨.)
- **미완**: 결제(무통장→PG, 코스모스팜페이+KCP 승인대기)·상품 상세설명 실제 스펙 보강·대리점 데이터(D4ES/D4ESO) 정정·Solapi 핸드폰 본인인증.

## Antigravity CLI (agy)
- hyunsung(구 wonrealty) 서버에 v1.0.13 설치 — `~/.local/bin/agy` (ausqueen 계정)
- 설치: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
- 사용 전 Google 로그인 필요(SSH 세션은 인증 URL 출력 → 로컬 브라우저 로그인)

## Synology Active Backup for Business (ABB) 에이전트
- wonrealty에 설치(2026-06-28). 드라이버 `synosnap`(dkms) + 서비스 3.2.0-5053
- 서비스: `synology-active-backup-business-linux-service` (systemd, enabled)
- NAS 연결: `ausqueen.synology.me`, 계정 `hyunsung567`
- 명령: `sudo abb-cli -s`(상태) / `sudo abb-cli -c`(연결) / `sudo abb-cli -h`(도움말)
- 호스트 볼륨 블록 백업 → `/opt/.../data`(DB·PDF) 포함.
- **백업 스케줄**: NAS(DSM) 제어. 작업 `hyunsung567-linux`(task id 21) = **매주 월·수·금 03:00 KST**. pre/post 스크립트 훅은 지원하나 현재 **비활성**(활성화는 DSM UI에서만 가능).
- **✅ WAL DB 사전 정합 스냅샷(2026-07-08 구축)**: WAL DB는 블록 백업 시 crash-consistent 로만 담기므로, sqlite3 온라인 백업 API로 "단일파일 정합 사본"을 만들어 백업 세트에 포함시킴.
  - 스크립트: `scripts/snapshot-db.sh` (호스트 python3 `sqlite3.Connection.backup()` + `PRAGMA integrity_check` 검증 + 최신 7개 회전). 산출물 `data/db_snapshots/onbid-<TS>.db`(+`onbid-latest.db` 심링크), git ignore·ABB 백업범위(/opt) 안.
  - 스케줄: systemd `onbid-db-snapshot.timer` → **매일 02:50 KST**(ABB 03:00 백업 10분 전). 서비스 `onbid-db-snapshot.service`(oneshot). 유닛=`/etc/systemd/system/onbid-db-snapshot.{service,timer}`.
  - 수동 실행/확인: `sudo /opt/onbid-auction-finder/scripts/snapshot-db.sh` · `systemctl list-timers onbid-db-snapshot.timer` · 로그 `/var/log/onbid-db-snapshot.log` + `journalctl -u onbid-db-snapshot`.
  - ⏭️ (선택) 더 타이트한 결합 원하면 DSM ABB 작업 → Pre/post script 에 이 스크립트를 pre-script 로 지정(현재는 타이머 방식이라 불필요).

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

> 🔧 **realty99 fstab `nofail` 추가 (2026-07-05)**: `/etc/fstab`의 NAS 라인 `defaults,_netdev` → **`defaults,_netdev,nofail`**. NAS가 부팅 시 응답 없어도 부팅이 막히지 않도록(hyunsung과 동일 정책). 백업 `/etc/fstab.bak.20260705`. `_netdev`만으로는 부족 — nofail 없으면 systemd가 마운트 대기하다 emergency mode 가능.

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

## 2026-07-12 작업 이력 — 온비드 공매 추천 서비스 재개(429 원인 제거 + 증분 동기화)
2026-06-29에 data.go.kr OnBid **상세 API 429(호출 쿼터 초과)**로 비활성했던 온비드 일일 동기화를, **근본 원인(매 실행 전건 상세 재조회)을 제거**하고 재개함.

- **근본 원인**: `sync_properties`가 매 실행마다 현재 목록 전건(`max_pages=50`×100=최대 5000행)에 `fetch_property_detail`을 무조건 호출 → 개발키 일일 쿼터 초과. (진단: DB 3538건 전부 이미 `description` 보유 → 전건 상세 재조회는 순수 낭비였음.)
- **수정(4가지, 백업 `.bak.20260712*`)**:
  1. **증분 상세 조회** — `sync_service._needs_detail`: 상세(설명/지목/이미지)는 공고당 1회면 충분하므로 **신규이거나 설명 결측일 때만** 호출. 결과: 정기 실행 상세 호출 **≈0건**(검증됨) → 429 구조적 소멸.
  2. **처리/스킵 분리** — `_needs_process`: 신규·분석없음·설명결측·가격/회차변동일 때만 upsert+시세+분석. **변경 없는 물건은 molit·분석 전체 스킵**.
  3. **목록 중복 결정론적 dedup** — 온비드 목록은 동일 물건(`cltrMngNo`)의 **회차별 예정가를 여러 행(내림차순)**으로 반환(예: 1물건 7행). `fetch_all_properties`가 `notice_no`별 **최저가(최종 회차) 행을 선택**(순서 무관·실행 간 안정 — 두 번 fetch 시 불일치 0건 검증). 5000행→**unique 1904건**. (기존 last-write-wins가 사실상 최저가를 저장하던 동작과 일치 → 분석 의미 보존.)
  4. **안전망** — 상세 호출 일일 상한 `onbid_detail_daily_limit=800` + `fetch_property_detail` **429 감지 시 이번 실행 상세 중단**(목록 데이터로 계속, 나머지는 다음 실행 픽업). 시세 **실행내 캐시**(동일 지역·면적 중복조회 제거). molit **토지 API 미구독(403) 스킵**(`molit_land_enabled=False`, 403 로그 홍수 제거).
- **재개 스위치**:
  - 백엔드: `backend/.env`에 `ONBID_SYNC_ENABLED=true` 추가 → `docker compose build backend && up -d backend`. 스케줄러 로그 `Added job "온비드 일일 동기화"` 확인(매일 **09:00 KST**).
  - 프론트: `frontend/src/pages/Dashboard.tsx` `COLLECTION_DISABLED = false` → `cd frontend && npm install --legacy-peer-deps && npm run build`(dist 즉시 서빙).
- **검증**: 수동 실행 다회 — 429 **0건**, errors **0**, 상세호출 0, dedup 안정성 100%. 재개 직후 내 테스트로 오염된 가격값을 정합 복구하는 **1회성 full 동기화** 실행(이후 정기 실행은 대부분 스킵되어 수 분 내 완료).
- **전남광주통합특별시 처리(2026-07-12)**: 온비드가 `sido="전남광주통합특별시"`(**2026-07-01 실제 출범**한 광주·전남 통합 정식 행정구역, 5시 5구 17군) 반환 → 로그에 `LAWD_CD 매핑 실패` 경고 도배 + 시세 스킵되던 것.
  - **✅ 매핑 경고 제거**: `lawd_codes.normalize_sido`가 조회 시점에 sigungu로 환원(광주 자치구 동/서/남/북/광산구→광주광역시, 그 외→전라남도)해 옛 LAWD_CD 매칭 → "매핑 실패" 경고 사라짐. stored sido는 정식명 유지(덮어쓰지 않음). 영향 199건 재분석 완료.
  - **✅ 신규 법정동코드 확보·추가로 시세 복구**: 통합으로 옛 광주(29)/전남(46) 코드는 molit에서 폐지(전월 0건)되고 **시도 프리픽스 `12`로 재편**됨. molit 실거래 동네이름(umdNm)으로 전 시군구를 실증 매핑(2026-07-12) → `lawd_codes._MERGED_LAWD`(표준 시도명 키, resolve에서 우선 적용) 추가. 매핑(시·구·군 순):
    - 시: 목포12110·여수12130·순천12150·나주12170·광양12190
    - 구: 동구12210·서구12240·남구12270·북구12300·광산구12330
    - 군: 담양12710·곡성12720·구례12730·고흥12740·보성12750·화순12760·장흥12770·강진12780·해남12790·영암12800·무안12810·함평12820·영광12830·장성12840·완도12850·진도12860·신안12870
    - **검증**: 목포 아파트→12110→시세 1.85억, 광주 서구→12240→3.45억 등 정상. 199건 재backfill → **49건 실거래 시세 부여**(나머지 150건은 토지/임야/전답이라 토지 API 미구독으로 제외). ⚠️ 신규 시군구 추가(향후 통합시 발표)나 신안 등 코드는 필요 시 `_MERGED_LAWD` 보강.
- 관련 파일: `sync_service.py`(재작성)·`onbid_client.py`(dedup·429감지)·`molit_client.py`(토지 스킵)·`config.py`(신규 설정). ⚠️ **로컬 수정, GitHub 미push** 상태(2026-06-29 비활성 변경과 동일).

### 종료 물건 정리(활성상태 검증) — 상세 API 검증 방식
"온비드에서 사라진(낙찰/취소) 물건이 추천에 남는가?" 점검 결과 **정리 로직이 아예 없었음**(추천/목록 API는 `is_active==True`만 노출하는데, `is_active`가 upsert마다 True로만 세팅되고 False로 내려가는 코드가 없음 → 전건 4085 True).
- **왜 단순 판정이 불가**: ① 목록이 5만+행(500+페이지)인데 `max_pages=50`으로 앞 window만 수집 → "목록에 없음=종료" 불가. ② 목록의 `cltrBidEndDt`는 미scheduled 회차가 sentinel `29991230…`이고 12자리라 `_parse_datetime`이 **전건 None**으로 버림(파싱 버그였음). 공매는 다회 유찰로 수개월 지속 → updated_at 노후도 종료 아님(오래된 표본 다수가 여전히 활성).
- **채택**: 절대 신호인 **상세 API 존재 여부**만 사용. `verify_stale_active`(신규 `services/maintenance.py`)가 오래(updated_at) 미갱신 `is_active` 물건을 상세 조회 → **not-found(resultCode≠00/item 없음)일 때만 `is_active=False`**(활성 오판 0). 존재하면 `bid_end_dt` 갱신 + updated_at 갱신(재검증 유예). 429 감지 시 즉시 중단, `onbid_verify_max_checks`(기본 500)로 1회 호출량 제한.
- **스케줄**: `scheduler.py` 잡 `verify_stale_active` = **매일 10:30 KST**(09:00 동기화가 상세 ≈0건이라 상세 쿼터 여유). 설정 `onbid_verify_enabled/stale_days(21)/max_checks(500)`.
- **버그 수정**: `onbid_client._parse_datetime` 12자리(YYYYMMDDHHMM) 미처리 + 9999 sentinel → 수정. 이제 bid_end_dt 채워짐.
- **1회 실측(2026-07-12)**: 후보 300 중 170 검증(이후 상세 429=당일 내 테스트로 쿼터 소진) → **만료 26건 정리**, 활성확인 144(bid_end 복구). 후보 총 ~2181건이라 **스케줄 잡이 며칠에 걸쳐 점진 정리**(하루 500 상한). ⚠️ data.go.kr 상세 개발키 **일일 쿼터 ≈1000** 확인됨.

## 미완료 항목
- [x] ~~PDF 파일 동기화~~ — 완료 (498/498)
- [x] ~~certbot 자동 갱신 설정~~ — 완료 (systemd timer)
- [ ] VWorld API 도메인 인증 (wonrealty.kr 등록 필요 — map.vworld.kr 개발자 콘솔)
- [~] (권장) SSH 하드닝 — **fail2ban 완료(2026-07-08)**, `PasswordAuthentication no`는 **보류**(사용자 PC 공개키 등록·검증 후 진행. 현재 ausqueen 등록키는 realty99→hyunsung 1개뿐이라 지금 끄면 락아웃 위험)
  - **fail2ban 1.0.2** 설치·enable. jail=sshd(mode aggressive, maxretry 4, findtime 10m, bantime 1h→재범 점증 최대 1w), backend=systemd, banaction=nftables(전용 `table inet f2b-table`, Docker 규칙과 분리).
    - 화이트리스트(`ignoreip`, `/etc/fail2ban/jail.local`): `127.0.0.1/8 ::1 5.104.87.20`(realty99) `5.104.87.178`(자기) `172.16.0.0/12`(docker). 확인: `sudo fail2ban-client status sshd`. 설치 직후 공격 IP 자동밴 검증됨(무차별 로그인 시도 하루 ~1.2만건 관측).
    - **WordPress 로그인 잼 `hsrealty-wp-auth` 추가(2026-07-08)**: WooCommerce/WP 로그인 브루트포스 방어. 자식테마 `functions.php`가 로그인 실패를 `wp-content/hs-auth-fail.log`에 실제 클라이언트IP(X-Forwarded-For)로 기록 → fail2ban(filter `hsrealty-wp-auth`, backend polling)이 5회/10분 초과 시 밴. **핵심**: hsrealty는 Docker 공개포트(443)라 DNAT→FORWARD 경로로 INPUT hook 밴이 무효 → `banaction=iptables-multiport chain=DOCKER-USER`로 컨테이너 전달 지점(DOCKER-USER 체인)에 밴 삽입(엔드투엔드 검증됨). 필터 `/etc/fail2ban/filter.d/hsrealty-wp-auth.conf`.
- [x] ~~(권장) rpcbind(포트111) 노출 제거~~ — 완료(2026-07-08). NAS가 **NFSv4.1**(rpcbind 불필요)인데 111이 공인IP 노출(DDoS 반사 벡터)이던 것 → `systemctl disable --now + mask rpcbind.socket rpcbind.service`. 포트 닫힘·NAS 마운트 정상 유지 검증.
- **웹 보안 하드닝(2026-07-08, nginx `nginx/wonrealty.conf`, 백업 `.bak.20260708`)**: ①**Portainer(portainer.wonrealty.kr) IP 허용목록** — `allow 116.41.161.23; allow 58.225.109.232; deny all;`(9443/9000/8000은 원래 호스트 미공개, 외부통로는 이 vhost 443뿐). ②**hsrealty**: `location = /xmlrpc.php {deny all}`(403), readme/license/wp-config 차단, 보안헤더(X-Frame-Options SAMEORIGIN·X-Content-Type-Options·Referrer-Policy) 추가, `proxy_hide_header X-Powered-By`. ③전역 `server_tokens off`(nginx 버전 숨김). 반영=`docker exec onbid-nginx nginx -t && nginx -s reload`.
  - **WP 레벨 하드닝(자식테마 `functions.php`, 백업 `.bak.20260708`)**: xmlrpc_enabled=false, 버전 generator 제거, REST `/wp/v2/users` 비로그인 차단(404), `?author=N`·작성자아카이브 → 홈 301(관리자 계정 slug 노출 차단). php -l·라이브 검증 완료.
  - **관리자 로그인 아이디 변경(2026-07-08)**: hsrealty WP 관리자 `hsadmin` → **`ausqueen`**(realty99 blog과 통일). ID 1·비밀번호·데이터 유지, 이메일은 `hs@hsrealty.co.kr` 그대로. `wp_users.user_login`+`user_nicename` DB변경, `.env` `WP_ADMIN_USER`도 동기화. 로그인 `https://hsrealty.co.kr/wp-admin/`(IP 제한 적용된 상태).
  - **WP 관리자 IP 제한(2026-07-08b, nginx `wonrealty.conf`, 백업 `.bak.20260708b`)**: `wp-login.php`·`/wp-admin/`을 신뢰 고정 IP `116.41.161.23`·`58.225.109.232`(SSH 성공 IP=Portainer 허용목록과 동일)만 허용, 그 외 403. **예외 공개**: `admin-ajax.php`(스토어프론트 AJAX, 정확일치 우선), `wp-cron.php`(내부크론, /wp-admin 밖). **고객 로그인 영향 없음**(고객은 `/my-account/`). 동적 모바일 IP(118.235.x)는 제외. 서버 자신은 열 필요 없음(wp-cron·admin-ajax·wp-cli로 충분, wp-cli는 nginx 우회). 다른 장소 접속 필요 시 SSH로 `allow <IP>;` 추가 후 `docker restart onbid-nginx`. 검증: 403/200 매트릭스 확인 완료.
- [x] ~~(권장) ABB 백업 전 WAL DB 사전 스냅샷(`sqlite3 .backup`) 훅~~ — 완료 (2026-07-08, `snapshot-db.sh` + systemd 타이머 02:50 KST, ABB 섹션 참조)
- [x] ~~**온비드 일일 동기화 성능 개선 + 429 원인 제거**~~ — **완료·재개(2026-07-12, 아래 작업이력 참조)**. 증분 동기화로 상세 API 호출을 신규·결측 물건에만 한정(전건 재조회 폐지) → 429 구조적 소멸. 목록 중복(회차별 예정가 다행) 결정론적 dedup + 시세 실행내 캐시 + 상세 일일 상한/429 백오프 추가.
  로그의 `지원하지 않는 시도: …`는 에러 아님 — `molit_client.py`, 미지원 시·도 시세 조회 스킵 경고.
  `전남광주통합특별시`(2026-07-01 출범 광주·전남 통합) — `normalize_sido`로 매핑 경고 제거 + 신규 법정동코드(프리픽스 12) 실증·매핑(`_MERGED_LAWD`)으로 시세 복구 완료. 위 2026-07-12 이력의 전남광주 항목 참조.
