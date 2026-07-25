# hyunsung 서버 컨텍스트 (구 wonrealty, Contabo — 5.104.87.178)

> ⭐ **서비스 위상(2026-07-05)**: 이 서버의 **메인 서비스 = hsrealty(WooCommerce 쇼핑몰, `/opt/hsrealty`)**.
> **onbid-auction-finder = 서브 서비스**. 우선순위·리소스·장애대응 판단 시 **hsrealty 우선**.
> (이 CLAUDE.md 파일은 `/opt/onbid-auction-finder/`에 위치하지만 서버 전체 컨텍스트 문서임.)

## 서버 정보
- **호스트명**: hyunsung (구 wonrealty, 2026-07-03 변경 — 도메인 wonrealty.kr과 무관)
- **IP**: 5.104.87.178
- **도메인**: wonrealty.kr, blog.wonrealty.kr, hsrealty.co.kr (HTTPS 운영 중). ~~portainer.wonrealty.kr~~ = **2026-07-25 Portainer 삭제로 404**(인증서 SAN·acme 검증용 80 블록만 유지)
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
| onbid-nginx | **nginx:stable-alpine** (1.30.4, 2026-07-25 태그 변경) | 80, 443 |
| ~~portainer~~ | ~~portainer/portainer-ce:latest~~ | **삭제됨(2026-07-25)** — 아래 Portainer 항목 참조 |
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
- **SAN 도메인**(lineage `wonrealty.kr`, 2026-07-25 재발급): wonrealty.kr, www.wonrealty.kr, **blog.wonrealty.kr** — 3도메인. ~~portainer.wonrealty.kr~~ 제외됨(Portainer 삭제).
  - 별도 lineage `hsrealty.co.kr` = hsrealty.co.kr + www (만료 2026-10-02).
- **만료**: **2026-10-23** (wonrealty.kr lineage)
- **자동 갱신**: systemd timer `certbot-renew.timer` (매일 00·12시 + 랜덤지연 1h)
  → `scripts/renew-cert.sh` 실행(certbot renew → nginx reload). 로그: `/var/log/certbot-renew.log`
  ```bash
  systemctl list-timers certbot-renew.timer
  systemctl start certbot-renew.service   # 수동 1회 실행(미도래 시 skip)
  ```

## ~~Portainer (Docker 관리 UI)~~ — **삭제됨(2026-07-25)**
- **삭제 사유**: ①미사용(화이트리스트 IP 마지막 정상 접속 **2026-07-04**, 누적 164req) ②`/var/run/docker.sock` 마운트 = 침해 시 **호스트 root 동등 권한** ③`portainer.wonrealty.kr` vhost가 봇 스캔 표적(누적 3,182req, 403 차단 중이었음) ④`:latest`인데 2026-06-25 이미지로 고정돼 갱신 안 됨(Portainer는 인증우회 CVE 이력 제품) ⑤compose가 아닌 `docker run --restart always` 독립 컨테이너라 관리 사각. 대체=SSH + `docker compose` CLI.
- **조치**: `docker stop portainer && docker rm portainer`. **이미지·볼륨 `portainer_data`(292K)는 보존** → 되돌리려면 같은 볼륨으로 재기동하면 계정·설정 그대로 복구.
- **nginx**(`nginx/wonrealty.conf`, 백업 `wonrealty.conf.bak.20260725portainer`): portainer vhost **80·443 블록 전부 삭제**(주석만 남김).
- **인증서 재발급**: lineage `wonrealty.kr`을 **3도메인(wonrealty.kr·www·blog)으로 재발급** → SAN에서 portainer 제거, 만료 **2026-10-23**. 명령=`docker compose --profile certbot run --rm certbot certonly --webroot -w /var/www/certbot --cert-name wonrealty.kr -d wonrealty.kr -d www.wonrealty.kr -d blog.wonrealty.kr`. renewal conf 백업 `certbot/conf/renewal/wonrealty.kr.conf.bak.20260725`.
- **DNS**: `portainer.wonrealty.kr` A 레코드 **가비아에서 삭제 완료**(2026-07-25, 사용자). 권위 NS 조회 NXDOMAIN 확인.
  - ⚠️ **순서 주의(교훈)**: DNS를 먼저 지우면 certbot webroot 검증 실패 → LE는 **인증서 단위 all-or-nothing**이라 wonrealty.kr·blog 갱신까지 통째로 실패하고, 갱신은 만료 30일 전에야 시도되므로 **몇 달 뒤 조용히 터짐**. 반드시 **①SAN에서 도메인 제외 재발급 → ②vhost 제거 → ③DNS 삭제** 순서.
- **검증**: `certbot renew --dry-run` **양 lineage 성공**, 회귀 없음(wonrealty·www·blog·hsrealty·shop 전부 200), docker.sock 마운트 컨테이너 **0개**.
- **재설치가 필요해지면**: `docker run -d --name portainer --restart always -v portainer_data:/data -v /var/run/docker.sock:/var/run/docker.sock --network onbid-auction-finder_default portainer/portainer-ce:latest` + nginx 443 블록 복원(백업 파일 참조). setup token은 `docker logs portainer | grep setup_token`.

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
  - **✅ DS225+ NAS 제안서 콘텐츠 이식(2026-07-12)**: 소규모 사무실용 Synology DS225+ 제안서(15p PDF)를 성격에 따라 두 곳에 배치(A안). ①**신규 랜딩 페이지** "소규모 사무실 NAS 도입 가이드"(**page ID 209**, slug `nas-guide`, 전체폭 `template-fullwidth.php`, publish) — 왜NAS·제품스펙·성능·DSM기능·활용시나리오·**추천 구성안 3종**·**도입사례 금강다온부동산(3-2-1)**·Hyper/Active Backup·문의CTA. 제안서 도형(구성도·베이·3-2-1 배지)을 자식테마 브랜드색(네이비/골드/그린) scoped 스타일HTML로 재현, 구성안 HDD는 실제 상품(HAT3300-4T=107·HAT3320-8T=111)과 링크. **주 메뉴(id38) position3 "도입 가이드" 삽입**(홈·회사소개·도입가이드·전체상품·장바구니·내계정). ②**DS225+ 상품(ID 40) 상세설명 보강**(1,017→6,514B): 스펙표·성능타일·2.5GbE·DSM6종 + 하단 가이드 배너링크(상품↔가이드 상호연결). → 미완항목 "상품 상세설명 실제 스펙 보강" 부분 해소. **콘텐츠는 모두 `<!-- wp:html -->` 블록으로 감싸 wpautop 오염 차단**(검증됨). 소스·백업: `data/wp/hsrealty-import/{create_nas_guide,update_ds225_desc}.php`·`{guide_page,product_desc}.html`(멱등 재실행 가능)·`ds225_desc.bak.html`(상품 원본). 라이브 검증: 두 페이지+교차링크 3종 전부 HTTP 200. 되돌리기=`wp post delete 209 --force`(메뉴항목 별도정리)·상품은 백업본 복원.
  - **✅ 검색 노출(SEO) 서버 준비(2026-07-12)**: hsrealty 검색엔진 색인 준비. 진단결과 이미 정상인 것=`blog_public=1`(색인허용)·`robots.txt`(크롤링허용+`Sitemap:` 명시)·WP코어 사이트맵 `/wp-sitemap.xml`(페이지·상품·카테고리 포함, HTTP200). 보강한 것: ①**태그라인**(`blogdescription`) 설정="시놀로지 NAS 정품 전문몰 · 소규모 사무실 데이터 백업 솔루션". ②**자식테마 `functions.php`에 SEO 메타 훅 추가**(백업 `functions.php.bak.20260712seo`, php -l 통과)=`wp_head` priority2로 **meta description + Open Graph(og:type/site_name/title/description/url/image) + twitter:card** 출력(SEO플러그인 미설치 대체). 홈=태그라인, 단일페이지/상품=발췌 또는 본문 트림(155자), 상품 og:image=대표이미지 자동. 라이브 검증=홈·가이드·상품 메타 정상 출력. **og:image 기본 폴백**(`HS_OG_IMAGE`=로고 hsrealty-logo-trimmed.png) 추가로 홈·썸네일없는 페이지도 공유 이미지 출력(백업 `functions.php.bak.20260712seo2`). 참고 점검결과 canonical(홈·상품)·상품 Product JSON-LD·파비콘은 코어/우커머스가 이미 정상 출력 중. **방문분석 설치(2026-07-12)**: 자식테마 `functions.php`에 GA4+네이버애널리틱스 훅 추가(백업 `functions.php.bak.20260712analytics`)=`HS_GA4_ID`(wp_head gtag)·`HS_NAVER_WA`(wp_footer wcslog) define에 ID 채우면 출력. **관리자(로그인+edit_posts) 접속은 집계 제외**(`hs_analytics_should_track`) → 실시간 테스트는 시크릿창 필요. **✅ GA4 `G-KN1MXMH74M`·네이버애널리틱스 `HS_NAVER_WA='24d8291b3271480'` 둘 다 삽입·라이브 검증 완료**(네이버 wcslog CDN은 `wcs.pstatic.net`으로 정렬, 백업 `functions.php.bak.20260712naveranalytics`). ③**검색엔진 소유확인 훅**: 같은 블록에 `HS_NAVER_VERIFY`·`HS_GOOGLE_VERIFY` define → 값 채우면 `naver-site-verification`·`google-site-verification` 메타 자동출력. **✅ 구글·네이버 코드 둘 다 삽입됨**(`HS_GOOGLE_VERIFY='wrLqcuG3foohp-uxpjZl4aP3wyGeimc-EegBm7AV66Q'`·`HS_NAVER_VERIFY='cd65a5b967adf32098467ee0fc1b77ac96a80512'`, 홈 head 라이브 출력 검증 완료). 구글 서치콘솔·네이버 서치어드바이저 소유확인+사이트맵(`wp-sitemap.xml`) 제출 완료(사용자). 소유확인 이후 색인은 며칠~2주.
  - **✅ 다음(Daum) 웹마스터도구 추가(2026-07-12)**: 다음은 메타태그가 아닌 **robots.txt PIN 방식**. WP robots.txt는 정적파일 없이 코어 가상생성이라 자식테마 `functions.php`에 `robots_txt` 필터(priority1) 추가(백업 `functions.php.bak.20260712daum`)로 PIN을 **최상단**에 주입: `HS_DAUM_ROBOTS_PIN='#DaumWebMasterTool:975de40ab3df852948abf18a38524c420a96984b7d290b881d67502e76d46548:NLkqp3sqCgF0b7m1VxgDAA=='`. 라이브 robots.txt 1행 출력 검증 완료. **✅ 다음 웹마스터도구 소유확인+수집요청 완료(사용자, 2026-07-12)**. → 검색엔진 커버리지=**구글·네이버·다음(+네이트) 3대 전부 등록 완료**. 색인 반영은 며칠~2주 소요.
  - **✅ KCP 카드결제(코스모스팜 페이) 라이브 세팅(2026-07-13)**: 무통장→PG 개통 진행. **코스모스팜 페이 for 우커머스 v6.7** 설치·활성화(`plugins/cosmosfarm-pay-for-woocommerce`). NHN KCP 게이트웨이 **카드·가상계좌·계좌이체 3종 운영(LIVE) 활성화**(휴대폰 제외), 무통장(bacs) 병행. 상점코드 **ALVGH**(입력 시 `is_test()` 자동 false → 운영 `spl.kcp.co.kr`; 비우면 테스트 `stg-spl` + 내장 테스트키) + 상점키·개인키(암호화PKCS8)·서비스인증서(발급자 spl.kcp.co.kr, ~2031-07-12)·개인키비밀번호 입력·검증(openssl 복호화 성공). ⚠️ **자격증명은 DB(`woocommerce_nhnkcp_{card,vbank,transfer}_settings`)에만 저장 — 이 문서·NAS에 평문 미기재**(NAS 업로드 원본은 세팅 후 삭제). 자격증명은 게이트웨이별 개별저장(공유 아님, get_option 오버라이드 없음)이라 3곳 입력. 결제수단 노출순서 카드>가상계좌>계좌이체>무통장(`woocommerce_gateway_order`). ⚠️ **카드사 개통(심사) 진행 중** → 개통 완료 전엔 실승인 실패 가능(결제창은 정상), 개통 후 100원 실결제→즉시취소로 실승인 검증 예정. 비밀값은 명령줄 노출 없이 파일읽기 PHP(`wp eval-file`)로 입력, 컨테이너 임시(`data/wp/_kcptmp`) 삭제.
    - **심사 대비 필수표기 정비**: 환불/반품(id9)이 WooCommerce 영문샘플+draft였던 것 → 한글 「교환·환불·배송 정책」 재작성·공개(`/refund-returns/`, 표준값 청약철회7일·단순변심 반품비 고객부담·하자/오배송 판매자부담, 개봉/설치/라이선스/NAS설치 청약철회 예외). 멱등 스크립트 `data/wp/hsrealty-import/create_refund_policy.php`(`<!-- wp:html -->` 래핑). 푸터 위젯 `widget_custom_html[3]`에 링크 추가.
    - **에스크로(구매안전서비스)**: KCP 가입완료(이용확인증 등록번호 **제A11-260709-1162호**, 제공자 NHN KCP, 2026-07-09~2027-07-09 1년자동갱신) → PDF `wp-content/uploads/hsrealty-docs/hsrealty-escrow-certificate.pdf` 게시(공개200)+푸터 링크(표시의무 충족). **푸터 링크 현황**: 이용약관 | 개인정보처리방침 | 교환·환불·배송 | 구매안전서비스 이용확인증.
      - **✅ KCP 에스크로 실거래 적용 완료(2026-07-25)**: 기존 v6.7은 KCP 결제에 `escw_used=N` 하드코딩(KCP 전용 에스크로 게이트웨이 없음)이던 것 → 코스모스팜에 문의(2026-07-22 발신) → **에스크로 게이트웨이 추가된 v6.8 배포받아 적용**. 조치: 플러그인 **v6.7→v6.8 교체**(신규 클래스 `NhnKcp_VBank_Escrow`·`NhnKcp_Transfer_Escrow`, `escw_used=is_escrow()?'Y':'N'`. 카드·휴대폰은 에스크로 대상 아니라 'N' 유지=정상). 롤백본 `/opt/hsrealty/_plugin_bak/cosmosfarm-pay-for-woocommerce-v6.7`. **가상계좌·계좌이체를 에스크로판으로 전환**(사용자 결정): 에스크로 게이트웨이(`woocommerce_nhnkcp_{vbank,transfer}_escrow_settings`)에 자격증명 5필드(kcp_cd=ALVGH·kcp_site_key·kcp_sign_data·kcp_sign_data_pw·**kcp_cert_info=개행제거된 1268B본**) 복사 + `enabled=yes`, 일반 가상계좌/계좌이체는 `enabled=no`. 노출순서 카드>가상계좌(에스크로)>계좌이체(에스크로)>무통장. 전자상거래법상 5만원↑ 현금성결제(가상계좌·계좌이체) 에스크로 의무 충족. ⚠️ **에스크로는 웹훅 URL이 다름** — 두 에스크로 게이트웨이 공용 엔드포인트 `https://hsrealty.co.kr/?wc-api=cosmosfarm_pay_wc_nhnkcp_escrow_notification`(내부 라우터가 결제수단별 분기). **✅ 웹훅 URL 등록 완료(2026-07-25, 사용자가 KCP 상점관리자→기술관리센터→웹훅관리에 등록)**(일반 가상계좌 웹훅 `...noti_vbank`과 별개, 미등록 시 입금 자동전환 안 됨).
        - **등록 후 서버측 재검증(2026-07-25)**: 같은 날 nginx 규칙 5종 추가·WooCommerce 10.9.4 업데이트·컨테이너 전면 재생성을 거쳤기에 경로 재확인함 → 에스크로 엔드포인트 **HTTP 404 + `Content-Type: application/json`**(= WP의 HTML 404가 아니라 **플러그인 핸들러가 받아서 order_no 없음으로 거절** = 정상 도달), 일반 가상계좌 엔드포인트 200. 웹훅 URL은 루트 경로+쿼리스트링(`/?wc-api=...`)이라 신규 nginx deny 규칙(uploads php·bak/log·hsrealty-import)과 **무관**함을 설정으로 확인. KCP 통지 IP 3개(210.122.176.144·103.215.144.173/174) **fail2ban 밴 아님**. 에스크로 게이트웨이 2종 `enabled=yes`·`kcp_cert_info` 1268B 유지, 플러그인 v6.8 유지.
        - ⚠️ **에스크로 운영흐름**: 입금 후 판매자 **배송등록→구매확정** 거쳐야 정산(주문마다).
        - ⏳ **여전히 미검증(실거래 필요)**: 100원 에스크로 가상계좌 실거래로 ①`escw_used=Y` 전송 ②입금 시 **웹훅 실수신→주문 자동전환** 확인. 등록 시점 이후 KCP 통지 IP 접속 이력 **0건**(아직 에스크로 주문이 없어 당연) → 첫 실주문 또는 100원 테스트 때 `docker logs onbid-nginx | grep -E '210\.122\.176\.144|103\.215\.144\.17[34]'`로 수신 확인할 것.
    - **⏳ 카드사 개통 후 실결제 검증 — S032 오류로 KCP 문의 중(2026-07-21)**: 카드사 전체 개통 완료 통보받고 100원 실결제 테스트 진행 → 결제창·앱카드 QR 인증은 성공(res_cd=0000)하나 **승인 API(`spl.kcp.co.kr/gw/enc/v1/payment`)가 `S032 접근권한이 없습니다` 반환**(카드 청구 안 됨). 서버측 자격증명(ALVGH·상점키·개인키·인증서 CN=2026071310016369, 7/13발급~2031유효)은 전부 정상 확인 → 원인은 KCP측: ①인증서 재발급으로 기존 무효화 또는 ②API 권한 전산 미반영으로 추정했으나 → **✅ KCP 답변 수신·원인 확정·수정 완료(2026-07-22)**: 승인 요청의 `kcp_cert_info`(서비스인증서)에 **`\r\n` 개행문자가 포함**돼 인증서 검증 실패가 원인(플러그인 내장 테스트 인증서는 개행 없는 한 줄 형식인데, 운영 인증서를 여러 줄 PEM 그대로 입력했던 것). 조치: 3개 게이트웨이 설정(`woocommerce_nhnkcp_{card,vbank,transfer}_settings`)의 `kcp_cert_info`에서 `\r\n` 전부 제거(1310→1268B, wp eval·플러그인 코드 무수정). 개행 제거 후에도 X.509 정합 확인(CN=2026071310016369, ~2031-07-12). **✅ 100원 실결제 재테스트 성공(2026-07-22 17:15)**: 하나카드 100원 승인(res_cd=0000, 승인번호 23126010) → wp-cli `wc shop_order_refund create --api_refund=true`로 즉시취소(KCP `/gw/mod/v1/cancel` STSC res_cd=0000, 주문 refunded 확인). **→ KCP 카드결제 라이브 검증 완전 완료.** 임시 리소스(테스트 상품 213·주문 215/216/217·디버그 mu-plugin+로그·kcp-settings 백업 json) 전부 삭제 정리 완료.
      - **✅ 결제창 "진행중" 멈춤(약 2분) 해결(2026-07-22)**: 승인 성공 후 결제창이 안 닫히던 증상 → 원인은 KCP 아님. 결제완료 콜백이 주문 메일 2통(관리자+고객)을 **동기 발송**하는데 wp-mail-smtp(smtp.daum.net:465)가 **간헐적으로 통당 ~60초 지연**(실측: 같은 메일이 62.5초/2.4초 오락가락 — 다음 서버측 타핏, 연결·인증·전송 각 단계는 0.1초 미만 정상). 조치: 자식테마 `functions.php`에 `add_filter('woocommerce_defer_transactional_emails', '__return_true')` 추가(백업 `functions.php.bak.20260722`) → 주문 메일이 크론 비동기 발송으로 전환, 콜백 응답 즉시 반환. ⚠️ 우커머스 외 일반 wp_mail(비번재설정 등)은 여전히 동기 — 다음 SMTP 지연이 잦아지면 발송 서비스 교체 검토.
      - ~~검증 임시 리소스~~ → **전부 정리 완료(2026-07-22)**: 테스트 상품 213·주문 215/216/217·디버그 mu-plugin(hs-kcp-debug.php)+로그·kcp-settings 백업 json 삭제. 환불은 wp-cli `wc shop_order_refund create <주문id> --amount=<금액> --api_refund=true --user=ausqueen`로도 가능(플러그인 process_refund가 KCP STSC 취소 API 직접 호출 — KCP 관리자 불필요).
    - **✅ 가상계좌 실거래 검증 완료(2026-07-22 저녁)**: 테스트 상품 재생성(ID 219, 100원, `/product/payment-test-100/`)로 가상계좌 주문 220 → **발급 성공**(res_cd=0000, 국민은행 40249085811064, 예금주 현성리얼티, 기한 3일 — 가상계좌 KCP 개통 확정) → 주문 `awaiting-vbank`(입금대기) 전환·고객화면 계좌안내 표시 정상. 계좌정보 메타는 플러그인이 postmeta(구형)에 저장하나 자체 HPOS 호환계층(`Cosmosfarm_Pay_WC_HPOS::get_meta`)이 읽기+백필 — 표시코드 전부 이 경로라 실사용 문제없음. **실입금(100원) 후 자동전환 실패** → 원인: **KCP 입금통지(웹훅)가 아예 미발송**(KCP 통지 IP 210.122.176.144·103.215.144.173/174 접속 0건) = KCP 파트너관리자에 웹훅 URL 미등록이었음. → **사용자가 웹훅 URL 등록 완료(UTF-8)**: `https://hsrealty.co.kr/?wc-api=cosmosfarm_pay_wc_nhnkcp_noti_vbank` (플러그인 핸들러가 KCP IP 화이트리스트+tx_cd=TX00 처리, 입금 시 payment_complete+재고차감+새주문메일). 등록 전 입금건이라 웹훅 발송이력 없음 → **주문 220 수동 결제완료 처리 후 환불**(STSC res_cd=0000, 18:40) 완료. ⚠️ **미검증 잔여**: 웹훅 실수신(등록 이후 첫 가상계좌 입금 시 자동전환 확인 필요) · 환불금 100원이 환불계좌(주문 시 수집: 하나은행, 예금주 원유호)로 실제 반환되는지(수일 소요, 미도착 시 KCP 관리자에서 환불계좌 입력 확인). **계좌이체는 결제창 노출 확인까지만 하고 실결제 테스트 생략(사용자 결정)** — 카드·가상계좌와 동일 자격증명/승인 경로(STSC 취소 포함)라 리스크 낮음, 첫 실주문에서 자연 검증. 테스트 상품 219·디버그 로거는 삭제 완료. **주문 220(환불됨)은 보존 중** — 환불금 100원 하나은행 도착 확인 후 삭제 예정(거래번호 26833404346625·환불계좌 기록 보전 목적).
- **미완**: ~~결제~~(✅ 2026-07-22 KCP 카드결제 라이브 검증 완료)·~~KCP 에스크로 실거래 적용(escw_used=N)~~(✅ 2026-07-25 v6.8 에스크로 게이트웨이 적용, 웹훅등록·100원 실거래 검증만 잔여 — 위 에스크로 항목 참조)·상품 상세설명 실제 스펙 보강(DS225+ 외 나머지 제품)·대리점 데이터(D4ES/D4ESO) 정정·Solapi 핸드폰 본인인증.
- **⏳ 판매채널 확장(2026-07-12 계획, 사용자 요청 = 나중에 진행)**: 검색 등록·방문분석 완료 후 다음 단계로 **①네이버 쇼핑 노출 + ③구글 머천트 센터**(②지역검색·스마트플레이스는 이번엔 제외). 두 채널 공통 선결과제 = **WooCommerce 79상품 → 상품피드(feed) 생성**(제목·가격KRW·이미지·재고·상품URL·카테고리, 가급적 GTIN/브랜드). 생성방식 후보: 피드 플러그인(CTX Feed / Product Feed PRO 등) 또는 커스텀 엔드포인트(WP REST/eval-file로 XML·TSV 출력). **비공개 상품(ID24·80)은 피드서 제외** 필수.
  - **① 네이버 쇼핑**: 경로A=**네이버 스마트스토어 입점**(별도 판매자 가입·정산, 상품 재등록 필요) / 경로B=**쇼핑파트너센터 가격비교 EP 연동**(자체몰 유지한 채 상품DB EP 등록). 선결=네이버 커머스ID/판매자 가입, 사업자·**통신판매업 신고(제2026-경기안산-1395호 보유)**, EP 포맷(네이버 전용 필드). 어느 경로로 갈지 사용자 결정 필요.
  - **③ 구글 머천트 센터**: Merchant Center 계정 생성 → **구글 상품 피드**(Google Shopping 스펙: id·title·price·availability·image_link·link·brand·gtin/mpn) 제출 → 무료 리스팅(Shopping 탭 무료노출)+선택적 유료광고. **GA4(G-KN1MXMH74M) 이미 연동돼 전환추적 가능**. 선결=구글계정·피드 생성·정책검토(배송/반품 정보 필요).
  - 착수 시 참고: SEO/애널리틱스 훅은 자식테마 `functions.php`에 있음. 피드는 별도 `hsrealty-import/` 스크립트나 플러그인으로. 재개하려면 위 "선결과제(상품피드)"부터.

## blog.wonrealty.kr — 워드프레스 블로그 (2026-07-23 신설)
- **경로**: `/opt/blog-wonrealty/` (docker-compose.yml·.env·data/). compose project **blogwr**. hsrealty와 동일 패턴, ABB 백업 포함(/opt).
- **스택**: WordPress php8.3-apache(ko_KR) + MariaDB 11.4. 컨테이너 `blogwr-wp`(검증용 `127.0.0.1:8084`)·`blogwr-db`·`wpcli`(profile=cli).
  - 네트워크: 자체 `blogwr_default` + 외부 `onbid-auction-finder_default` 합류 → onbid-nginx가 `blogwr-wp:80` 프록시.
- **공개**: `https://blog.wonrealty.kr`. nginx `wonrealty.conf` 말미에 80/443 블록 append(백업 `wonrealty.conf.bak.20260723`).
  - SSL: 기존 `wonrealty.kr` lineage **SAN 확장**(blog 추가, 총 4도메인, 만료 **2026-10-21**) — `certbot-renew.timer`가 그대로 자동갱신.
- **WP 설정**: 제목 "원리얼티 블로그", 관리자 `ausqueen`(비번 `.env` WP_ADMIN_PASSWORD, chmod600), 타임존 Asia/Seoul, 고유주소 `/%postname%/`.
- **하드닝**: nginx=hsrealty 세트 동일(xmlrpc 403·readme/wp-config 차단·보안헤더·**wp-login/wp-admin IP 제한** 116.41.161.23·58.225.109.232, admin-ajax 공개). WP=**mu-plugin** `data/wp/wp-content/mu-plugins/blogwr-hardening.php`(xmlrpc off·generator 제거·REST users 404·author 열거→홈 301, template_redirect priority 0). 검증 매트릭스 전부 통과.
- **명령**: `cd /opt/blog-wonrealty && sudo docker compose ps | logs -f wordpress`. wp-cli: `sudo docker compose --profile cli run --rm wpcli <cmd>`.
- **테마(2026-07-23)**: **GeneratePress 3.6.1** + 브랜드 커스텀 CSS(네이비 #16284a/골드 #c9a84c, WP 커스터마이저 custom_css post 14).
- **SEO(2026-07-23)**: mu-plugin `blogwr-seo.php` = meta description+OG+twitter:card(대표이미지 자동, 폴백 BLOGWR_OG_IMAGE)·robots.txt에 Sitemap 명시·소유확인 상수 **`BLOGWR_GOOGLE_VERIFY`·`BLOGWR_NAVER_VERIFY`·`BLOGWR_DAUM_ROBOTS_PIN`(현재 빈값 — 사용자가 서치콘솔/서치어드바이저/다음도구에서 코드 받아오면 채움)**. 사이트맵 `/wp-sitemap.xml` 정상.
- **✅ 매일 자동 발행 파이프라인(2026-07-23 가동)**: `/opt/blog-wonrealty/autopost/autopost.py`(python3 stdlib only, root 실행).
  - 흐름: 구글뉴스 RSS(부동산 검색, ko) 헤드라인 20건 → **Gemini API**(`gemini-2.5-flash`, 키=onbid와 동일 키 복사)가 화두 1개 선정+Gutenberg 블록 글 생성(JSON) → **이미지 풀 30장**(`pool.json`, WP 미디어 ID 5~10·16~21·26~43, 힉스필드 soul_2 생성. 2026-07-23 12→30장 확장)에서 LLM이 2장 선택 → **WP REST API**(Application Password `autopost`, `autopost.env` chmod600)로 발행(카테고리 부동산=2, 태그 find-or-create, 대표이미지).
  - 스케줄: systemd `blogwr-autopost.timer` = **매일 08:00·20:00 KST 2회**(+랜덤 5분, Persistent. 2026-07-23 저녁 2회로 확대). 로그 `/var/log/blogwr-autopost.log`. 상태 `state.json`(최근제목 40개 중복방지 + **회차(AM/PM) 단위 멱등**(14시 기준), 재실행은 `--force`).
  - 안전장치: 헤드라인에 없는 수치 날조 금지·투자권유 금지 고지문 강제(프롬프트), Gemini 3회 재시도, 발행상태 `autopost.env` `POST_STATUS`(draft로 바꾸면 검수모드). 검증: draft 테스트 후 발행 확인 완료(post 22).
  - **분량·중복 개선(2026-07-23 저녁)**: 분량 피드백 두 차례(짧다→2,000자↑로 상향→너무 길다) 거쳐 **최종 공백 포함 1,400~1,700자(1,500자 안팎, 2,000자 초과 금지)**·h2 3~4개로 확정(draft 검증 1,687자 확인). 같은 날 헤드라인 도배로 전일과 같은 주제를 또 고르는 문제 → "표현만 바꾼 같은 주제 절대 금지, 겹치는 헤드라인 건너뛰기" 지시 강화(검증 런에서 다른 주제 '양극화' 선택 확인).
  - 수동 실행: `sudo systemctl start blogwr-autopost.service` 또는 `sudo python3 /opt/blog-wonrealty/autopost/autopost.py --force`.
  - **✅ 네이버 블로그 복사용 메일(2026-07-23)**: 발행 직후 `ausqueen@hanmail.net`으로 **글 1건당 메일 1통** 자동 발송(`send_copy_mail` — 제목·태그·원문링크+블록주석 제거된 본문, 이미지는 블로그 절대URL **+ 본문 이미지 파일 첨부**(붙여넣기 누락 대비, 로컬 uploads에서 읽고 없으면 URL 다운로드)). SMTP=**다음 smtp.daum.net:465 hyunsung567@daum.net**(hsrealty wp-mail-smtp와 동일 계정, 설정은 autopost.env). 메일 실패해도 발행은 성공 처리. 기존 4건(post 11·12·13·22) 소급 발송 완료.
- **✅ 검색 노출 작업(2026-07-23)**: ①**구글 소유확인 메타 삽입 완료** — 구글 토큰은 계정 단위 재사용 가능이라 hsrealty 토큰(`wrLqcuG3...`)을 `BLOGWR_GOOGLE_VERIFY`에 삽입, 라이브 출력 확인(서치콘솔에서 속성 추가만 하면 즉시 인증). ②**IndexNow 구축** — 키 `44d9145e90e244dba06c075ff1caa4fd`(웹루트 `<키>.txt` 200), autopost.py가 발행 직후 api.indexnow.org+네이버 서치어드바이저 엔드포인트에 자동 핑(`INDEXNOW_KEY` in autopost.env). 초기 제출 5 URL 완료(빙 202·네이버 200). ③**hsrealty 푸터 백링크** — 패밀리 사이트 링크 추가(위젯 백업=세션 스크래치패드 `hsrealty_widget_custom_html.bak.json`).
- **✅ 구글 애드센스 코드 설치(2026-07-23)**: `blogwr-seo.php` `BLOGWR_ADSENSE_CLIENT='ca-pub-6535750585778559'` → 전 페이지 head에 adsbygoogle.js 출력 + 웹루트 `ads.txt`(`google.com, pub-..., DIRECT, f08c47fec0942fa0`) 200. 심사 신청·승인 후 자동광고는 애드센스 대시보드에서 설정(코드 수정 불필요). ⚠️ 신규 사이트라 콘텐츠 부족 거절 가능 — 글 15건+ 쌓인 뒤 신청 권장함.
  - **루트 도메인 확인 대응**: 애드센스가 상위도메인(wonrealty.kr) 단위 등록만 허용 → onbid 프론트 `frontend/index.html`에 스크립트 임시 삽입+`frontend/public/ads.txt`(재빌드에도 유지, vite가 dist로 복사) 배치 → **코드 스니펫 방식으로 소유확인 통과(2026-07-23)**. 확인 직후 사용자 요청으로 **루트 스크립트는 제거·재빌드**(공매 서비스엔 광고 미표시 — 스크립트 없으면 자동광고 원천 차단). **ads.txt는 루트·blog 양쪽 유지**(구글 상시 크롤링 파일). 최종 상태: 광고 코드=blog만, ads.txt=양쪽. 재확인 요구 시 index.html에 스크립트 재삽입+빌드.
- **✅ GA4 방문분석(2026-07-23)**: `blogwr-seo.php`에 gtag 훅 — **`BLOGWR_GA4_ID='G-K1FLJMXL7L'`**(블로그 전용 속성, hsrealty G-KN1MXMH74M과 별개). 관리자(로그인+edit_posts) 집계 제외(`blogwr_analytics_should_track`) → 실시간 테스트는 시크릿창. 홈·글 페이지 라이브 출력 검증 완료.
- **✅ 3대 검색엔진 소유확인 코드 전부 삽입 완료(2026-07-23)**: 구글 `BLOGWR_GOOGLE_VERIFY='grahwvd9gEJ8ZUedh7rycOIr6spW1_uqM2fRhXmFymc'`(당초 hsrealty 토큰 재사용 시도 → 사용자 발급 신규 코드로 교체)·네이버 `BLOGWR_NAVER_VERIFY='902e7bdfc78df885558e3adf12ada5dc1eafaddd'`·다음 robots PIN(`#DaumWebMasterTool:6ffb21af...`, robots_txt 필터 priority 99 — 코어 Sitemap 중복 방지 포함). 홈 head·robots.txt 라이브 출력 검증 완료. 소유확인 버튼 클릭+사이트맵(`wp-sitemap.xml`)·RSS(`/feed/`) 제출은 사용자 진행.
- **✅ realty99 상담 유도 배너(2026-07-23)**: 단일 글 본문 하단(애드핏 위, the_content priority 20)에 realty99.co.kr 홈페이지 유도 배너. 버튼 표시문구는 URL 대신 **"금강다온부동산"**(전 배너 5곳 공통, 링크는 realty99.co.kr 유지). **+우측 사이드바 미니 배너**(Recent Comments 아래, 블록위젯 `block-7` in sidebar-1, utm_medium=sidebar). **+wonrealty.kr(공매 서비스)**: 처음 우하단 고정(floating)으로 넣었다가 사용자 요청으로 **파산 매각 페이지 상단 버튼줄(파일 동기화 등) 바로 아래 우측 정렬 배너로 이동**(`frontend/src/pages/BankruptcyList.tsx`, utm_medium=header. index.html의 고정 배너는 제거) 후 npm 재빌드. ⚠️ frontend 파일 수정 시 CRLF 보존 + 재빌드 필요. — 문구 "부동산 매매·전세·월세 상담" + "**경매 대리입찰이 필요하신가요?**" + 바로가기 버튼(네이비/골드). 이 서버 `blogwr-realty99-banner.php`(utm_source=blog_wonrealty) + realty99 서버 `r99-consult-banner.php`(utm_source=blog_realty99). 양쪽 라이브 검증.
  - **blog.realty99 구 하단 배너 비활성화(2026-07-23)**: 새 상담 배너와 중복되던 기존 `realty99-link.php`("공식 홈페이지" 초록 박스, the_content append) → `data/wordpress/realty99-link.php.bak.20260723`로 이동해 비활성. 글 하단 배너는 새 것 1개만 노출.
  - **blog.realty99 좌측 사이드바 미니 배너(2026-07-23)**: 방문자 집계 하단에 "🏠 부동산 상담/⚖️ 경매 대리입찰 → realty99.co.kr" 소형 배너(utm_medium=sidebar). `realty99-category-sidebar.php`에 삽입(백업 `.bak.20260723`).
  - **blog.realty99 상단 홈페이지 링크 제거(사용자 요청)**: TT5 블록테마 내비게이션(`wp_navigation` post 4)의 "금강다온공인중개사사무소 공식홈페이지" 항목 삭제(백업 `data/wordpress/nav4.bak.20260723.txt`) + 그 버튼 전용 mu-plugin `realty99-home-link-button.php`도 제거(백업 `data/wordpress/*.bak.20260723`). realty99 서버 wp-cli는 `docker run --rm -e WORDPRESS_DB_* --volumes-from realty99_wordpress --network container:realty99_wordpress wordpress:cli-php8.3` 방식(전용 wpcli 서비스 없음, env 전달 필수).
- **✅ 카카오 애드핏 활성화(2026-07-23)**: mu-plugin — 이 서버 `blogwr-adfit.php`(PC `DAN-AUJQR3DTzOYrKyFg`·모바일 `DAN-ncXEIssn6sp1oJze`) + **realty99 서버** `/opt/realty99/data/wordpress/wp-content/mu-plugins/r99-adfit.php`(mu-plugins 폴더 신설. PC `DAN-l6FBDTISo2rH4uW1`·모바일 `DAN-0FWTOCvF1Peqof5u`). 단일 글 본문 하단 자동 삽입, PC(728x90)/모바일(320x100) 미디어쿼리 반응형, ba.min.js는 footer 1회. **1차 심사 보류(2026-07-23)**: 광고가 글 페이지에만 있어 심사 크롤러가 홈에서 미발견 → **홈·목록 등 비단일글 페이지 하단(wp_footer)에도 광고 출력 추가**(양쪽, `if (!is_singular('post')) echo adfit_units_html()`) + **스크립트를 공식 SDK 가이드 스펙으로 정렬**(구 `t1.daumcdn.net` → `https://t1.kakaocdn.net/kas/static/ba.min.js`, charset=utf-8, ins `width:100%`) 후 재심사 요청. 홈·글 페이지 출력/중복없음 검증 완료. **2차 보류(원리얼티만, 콘텐츠 부족)** → 상록 가이드 글 6건 일괄 생성·발행(`bulk_evergreen.py` 1회성, 전세체크리스트·DSR/LTV/DTI·청약가점·등기부등본·경매vs공매·재개발vs재건축)으로 총 10건 확보. 자동발행 누적 후 며칠 뒤(15건+) 재심사 권장.
- ⏭️ 미진행: fail2ban WP 잼(wp-login IP 제한이라 우선순위 낮음), 이미지 풀 보충(추가 시 pool.json에 항목 추가).

## MCP 커넥터 — PlayMCP (카카오 공식) ⭐ 네이버 검색 기본 경로
- **연결 확인**: 2026-07-24 실호출 검증 완료(`get_current_korean_time` 응답 정상, `KakaotalkChat-MemoChat` 테스트 발송 성공).
- ⭐ **규칙: 네이버 검색이 필요하면 PlayMCP 커넥터의 NaverSearch 도구를 사용한다**(일반 웹검색·스크래핑보다 우선).
  - 검색: `search_blog`·`search_news`·`search_shop`·`search_image`·`search_local`·`search_cafearticle`·`search_kin`·`search_book`·`search_encyc`·`search_academic`·`search_webkr`
  - 데이터랩(트렌드): `datalab_search`(검색어 트렌드), `datalab_shopping_category`·`datalab_shopping_keywords` + 성별/연령/기기별 변형, `find_category`
  - 유틸: `get_current_korean_time`(한국 현재시각)
  - 도구는 지연 로딩(deferred) — 호출 전 `ToolSearch`로 `select:mcp__claude_ai_PlayMCP__NaverSearch-<도구명>` 스키마를 먼저 로드해야 함.
- **카카오톡**: `KakaotalkChat-MemoChat` = **"나에게 보내기"만 가능**(타인·단톡방 불가), 메시지 **최대 200자**.
- ⚠️ **적용 범위**: 이 커넥터는 Claude 세션 안에서만 동작 → 서버 크론/스크립트(blog autopost 등)에서 직접 쓰려면 별도 네이버·카카오 REST API 키·토큰 발급 필요.

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

### 대법원 파산 Phase1 수집 캡·삭제 정합 수정(2026-07-12)
- **① 500 캡 제거**: `scourt_scraper.collect_all_notices`가 `max_pages=50`(=500건)에서 잘리던 것 → 게시판 실제 505건(51.5페이지)이라 51페이지 5건 누락. `debug.py`·`bankruptcy.py:phase1_collect` 호출을 **max_pages=200**으로 상향(빈 페이지에서 자동 종료하므로 실행시간 영향 없음). 검증: 505건 전량 수집(누락 0), DB 500→505.
- **② 삭제 오작동 방지**: 기존 삭제 정합(스크랩 목록에 없는 DB공고 삭제)이 `len(notices)>50/100`만 확인 → 캡/부분수집 시 **아직 활성인데 창 밖 공고를 대량 오삭제** 위험. `collect_all_notices_ex`가 **reached_end(마지막 빈 페이지 도달=전체 수집)** 반환 → 삭제는 `reached_end and len>N`일 때만 실행, 부분 수집이면 스킵(로그 경고). 하위호환: `collect_all_notices`(리스트 반환)는 래퍼로 유지(1페이지 프리뷰 등 무영향).
- 별도 `delete_expired_notices`(sale_deadline 기일 경과 삭제, bankruptcy.py)는 정상 로직이라 유지. 백업 `.bak.20260712`.

## 2026-07-12 작업 이력 — DNS 리졸버 교체(realty99.co.kr apex 조회 실패 해결)
- **증상**: 이 서버(hyunsung)에서 realty99.co.kr을 **IP(5.104.87.20)로는 접속되는데 도메인(URL)으로는 실패**(`Could not resolve host`). www는 간헐 성공, apex(`realty99.co.kr`)는 계속 실패.
- **원인**: realty99 DNS 존(등록업체 **dothome.co.kr** ns1~3)에는 apex A레코드 **정상 존재**(1.1.1.1 경유 확인). 문제는 **이 서버가 쓰던 Contabo 기본 DNS(209.126.15.53 / 195.179.224.53)가 apex에 간헐 SERVFAIL** 반환. IP는 DNS 미경유라 항상 됐던 것. → realty99·nginx·방화벽 문제 아님, **이 서버 업스트림 리졸버 불안정**이 원인.
- **조치(A안: 신뢰 리졸버로 교체)**:
  1. `/etc/systemd/resolved.conf.d/dns.conf` 신규 — `DNS=1.1.1.1 8.8.8.8`, `FallbackDNS=209.126.15.53 195.179.224.53`.
  2. **netplan 링크 DNS 교체(진짜 원인)** — `/etc/netplan/50-cloud-init.yaml`의 eth0 `nameservers.addresses`를 Contabo 고정 → **`1.1.1.1, 8.8.8.8`**(+Contabo 2개는 뒤에 백업으로 유지). eth0가 default-route라 이게 실제 주 경로였음. 백업 `50-cloud-init.yaml.bak.20260712`. `netplan generate`(문법검증)→`netplan apply`.
  3. **cloud-init 네트워크 재생성 차단** — `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg`(`network: {config: disabled}`)로 재부팅 시 netplan nameservers 원복 방지.
- **검증**: apex 3회 연속 조회 성공(5.104.87.20), `https://realty99.co.kr` 200·www 301(정규리다), 회귀 없음(hsrealty 200·github 조회 정상). `resolvectl status eth0` Current DNS=1.1.1.1.
- ⚠️ 되돌리기: netplan 백업 복원 + `99-disable-network-config.cfg`·`resolved.conf.d/dns.conf` 삭제 후 `netplan apply` & `systemctl restart systemd-resolved`.
- **realty99(5.104.87.20)도 예방 적용(2026-07-12)**: 동일하게 Contabo DNS 사용 중이라 예방 차원에서 같은 3조치 적용(resolved.conf.d/dns.conf·netplan nameservers 1.1.1.1·8.8.8.8 우선·cloud-init 네트워크 disable, 백업 `50-cloud-init.yaml.bak.20260712`). realty99↔hyunsung 양방향 도메인 조회·접속 전부 정상 검증(realty99→wonrealty.kr·hsrealty.co.kr 200, portainer는 IP화이트리스트로 403=정상). ※ realty99에선 실제 장애는 없었음(hyunsung 도메인은 dothome NS가 아니라 SERVFAIL 대상 아니었음).

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
  - **✅ 웹 취약점 점검·수정 5건(2026-07-25, 재부팅 점검 중 발견)** — nginx 백업 `wonrealty.conf.bak.20260725web`, 반영은 전부 **inode 보존 편집 + `nginx -s reload`(순단 0)**. **각 항목을 nginx + Apache `.htaccess` 2중으로 차단**(nginx 규칙이 유일한 방어선이 되지 않도록).
    - **① uploads 디렉터리 PHP 실행 가능(hsrealty·blog 양쪽)** — 실증됨(테스트 파일이 실제 실행). "업로드 취약점 → RCE" 체인이 성립하는 상태였음(WP 코어의 `.php` 업로드 금지가 유일 방어선). 조치=nginx `location ~* ^/wp-content/uploads/.*\.(php|phtml|phps|php[0-9])$ {deny all;}` + `uploads/.htaccess`(FilesMatch Require all denied). 검증: nginx 경유·컨테이너 직접(8083/8084) 모두 403, 본문 미실행.
    - **② 테마 백업파일 21개(440K) 소스 원문 노출** — `functions.php.bak.20260722` 등은 최종 확장자가 `.php`가 아니라 PHP로 파싱되지 않고 **정적 파일로 소스 전송**(전부 200이었음). 하드코딩 시크릿은 없었으나(KCP·SMTP는 DB/.env에만) 커스텀 로직 전문 + **auth 로그 경로**가 노출돼 ③으로 체인. 조치=nginx `\.(bak|old|orig|save|swp|swo|sql|log)($|\.)` deny + `~$` deny + **파일 21개를 `/opt/hsrealty/_theme_bak/`(웹루트 밖)로 이동**. ⚠️ **이후 테마 백업은 반드시 `_theme_bak/`에 둘 것**(테마 폴더에 두면 재발).
    - **③ 로그인 실패 로그 `wp-content/hs-auth-fail.log` 공개** — 유효 관리자 ID `ausqueen` + **신뢰 IP `58.225.109.232`** 노출. REST users 404·author 열거 차단으로 숨긴 관리자 계정명이 이 파일로 새고 있었음. 조치=②의 `.log` 규칙으로 차단(nginx+.htaccess 403).
    - **④ X-Forwarded-For 위조 → fail2ban 임의 밴(실증 완료)** — `functions.php`의 `hs_client_ip()`가 XFF **첫 값**을 무조건 신뢰했는데, nginx는 `$proxy_add_x_forwarded_for`로 "클라이언트 값 + 실제 IP" 순으로 덧붙이므로 **첫 값 = 공격자 지정값**. 공개 경로 `/my-account/`(WooCommerce 고객 로그인)에서 nonce 취득 후 위조 POST → 로그에 `203.0.113.99`(존재하지 않는 IP)가 기록되는 것 확인. 이 로그가 fail2ban 입력원이라 **③이 알려준 관리자 신뢰 IP를 밴시켜 차단(DoS)** + **공격자 자신은 매번 다른 위조 IP로 밴 회피**가 가능했음. 조치=nginx가 매 요청 덮어쓰는 **`X-Real-IP` 사용**으로 변경(`filter_var` 검증 포함, 없으면 REMOTE_ADDR). 백업 `_theme_bak/functions.php.bak.20260725xff`, php -l 통과. 재검증: 위조 `198.51.100.77` 무시하고 실제 IP 기록.
    - **⑤ `hsrealty-import/` 스크립트 폴더가 웹루트 안에서 실행 가능** — `wp eval-file` 전용 스크립트인데 누구나 HTTP로 실행 요청 가능(`create_nas_guide.php` 200). 7개 중 4개(`create_refund_policy`·`enrich_rs826`·`import_products`·`setup_payments`)에 `ABSPATH` 가드가 없었음(WP 미부트스트랩이라 즉시 fatal→500, 실제 피해는 없었음). 조치=nginx `location ^~ /hsrealty-import/ {deny all;}` + **4개 스크립트에 `if (!defined('ABSPATH')) exit;` 가드 추가**(php -l 통과, 백업 `/opt/hsrealty/_import_bak_*.20260725`). wp-cli는 nginx를 거치지 않으므로 **운영 사용에 영향 없음**.
    - **체인 구조**: ②가 로그 경로 노출 → ③이 관리자 ID·신뢰 IP 노출 → ④로 그 IP를 밴/회피 → ①로 RCE 마무리. 개별로는 중간 등급이나 연결 시 정찰~실행 완결 경로였음.
    - **회귀 검증**: 홈·shop·상품상세·cart·checkout(302=빈 장바구니 정상)·my-account·nas-guide·refund-returns·blog·feed·ads.txt·IndexNow키·admin-ajax·uploads 이미지·테마 CSS·에스크로 PDF **전부 정상**. fail2ban `hsrealty-wp-auth` logpath 변경 없음(경로 유지, 웹 노출만 차단)이라 재설정 불필요.
  - **✅ 유지보수 3건(2026-07-25) — WooCommerce 업데이트·이미지 갱신·볼륨 정리**. 사전 백업 전부 `/opt/_maint_backup_20260725/`(DB덤프 hsrealty 5.1M·blogwr 3.3M, woocommerce-10.9.3 플러그인 폴더 76M, portainer_data tar 43K) + onbid DB 스냅샷 1회.
    - **① WooCommerce 10.9.3 → 10.9.4**(`wp plugin update woocommerce`). `wp wc update`=DB 마이그레이션 불필요(이미 10.9.4). 검증: 결제수단 4종 노출순서 유지(신용카드>가상계좌(에스크로)>계좌이체(에스크로)>무통장), KCP 자격증명 `kcp_cert_info` **1268B**(개행 제거본) 3게이트웨이 모두 보존, 상품 77 publish/2 private, PHP fatal 0건.
    - **② 컨테이너 베이스 이미지 갱신** — ⚠️ **`nginx:1.27-alpine`은 `docker pull` 해도 "up to date"**. 1.27은 상류에서 유지보수가 끝난 브랜치라 **태그 자체가 2025-04-16(1.27.5) 이후 갱신되지 않음** = pull로는 절대 최신화 안 됨. → `docker-compose.yml`의 태그를 **`nginx:stable-alpine`(1.30.4, 2026-07-15 빌드)**으로 변경(백업 `docker-compose.yml.bak.20260725`). 교체 전 **일회용 컨테이너로 현재 conf를 `nginx -t` 검증**(compose 네트워크에 붙여야 upstream 이름 해석됨)해 호환 확인 후 적용. wordpress 이미지도 갱신(PHP 8.3.32, 2026-07-14 빌드) — 이미지 내장 WP가 7.0.2로 설치본과 동일해 **코어 덮어쓰기 없음**(확인 후 진행). mariadb·certbot도 최신 확인.
      - ⚠️ **함정: WP 컨테이너 재생성 시 nginx가 502** — `docker compose up -d`로 컨테이너가 재생성되면 **컨테이너 IP가 바뀌는데**, nginx는 `proxy_pass http://hsrealty-wp:80` 같은 리터럴 호스트명을 **기동 시점에 1회만 DNS 해석**해 캐시함 → 옛 IP로 계속 붙어 502. **해결=`docker exec onbid-nginx nginx -s reload`**(재해석). blog에서 먼저 겪음. **hsrealty(결제 사이트)는 `docker compose up -d && docker exec onbid-nginx nginx -s reload`로 한 번에 연결해 순단 최소화**할 것.
      - 검증: nginx 1.30.4 기동, 전 사이트 200, 보안 규칙 전부 유지(uploads PHP·auth로그·임포트폴더·xmlrpc·wp-admin 403), 보안헤더·HSTS 정상, `server_tokens off` 유지.
    - **③ `portainer_data` 볼륨 삭제**(tar 백업 후). **남은 도커 볼륨 0개**. 미사용 이미지 정리(portainer-ce 187M 등). ※ 남겨둔 것=`nginx:1.27-alpine`(롤백용), dangling wordpress/certbot 구버전(롤백용), 빌드캐시 3.9G — 디스크는 145G 중 14% 사용이라 여유.
    - **④ onbid 백엔드 이미지 재빌드(2026-07-25, 검토 후 진행)** — 백업: 롤백 이미지 태그 **`onbid-backend-rollback:20260725`**, `backend/{Dockerfile,requirements.txt}.bak.20260725`, `/opt/_maint_backup_20260725/backend-pip-freeze-before.txt`, DB 스냅샷.
      - **검토 결과 ①: 베이스는 pull 해도 안 올라감** — `mcr.microsoft.com/playwright/python:v1.60.0-noble`은 **상류 마지막 빌드 2026-05-18**이고 MS는 구 태그를 재빌드하지 않음(새 태그 v1.61…로 나감). 실측 결과 이 베이스에 **OS 보안 업데이트 74건 누적**. → Dockerfile에 **`apt-get update && apt-get -y upgrade` 레이어 추가**(Playwright 버전은 그대로 두어 브라우저 번들 정합 유지). 결과 **잔여 보안 업데이트 74 → 0**.
      - **검토 결과 ②: `playwright` 미고정 = 지뢰** — `requirements.txt`에 `google-genai`·`pymupdf`·**`playwright`**·`pyhwp`·`lxml`이 **버전 미고정**이었음. 재빌드 시 playwright 최신판이 설치되면 베이스 내장 브라우저(**v1.60.0 / chromium-1223**)와 불일치해 **스크래핑 전면 실패**. → 5종 모두 운영 중 실제 버전으로 고정(`playwright==1.60.0` 등).
      - **검토 결과 ③: 전이 의존성 드리프트** — 위 5종만 고정하고 빌드했더니 전이 의존성이 제멋대로 올라감. 특히 **`pydantic` 2.13.4 → 2.14.0a1(알파)** — FastAPI 검증 경로 핵심이라 허용 불가. → **`backend/constraints.txt` 신설**(2026-07-12 운영 이미지의 `pip freeze` 전량 56줄)하고 `pip install -r requirements.txt -c constraints.txt`로 빌드. **결과: 파이썬 패키지 56개 전부 이전과 동일(드리프트 0)**. ⚠️ **의도적으로 패키지를 올릴 때는 constraints.txt의 해당 줄을 수정할 것.**
      - **빌드 함정: PEP 668** — apt upgrade가 python3 패키지를 갱신하면서 `EXTERNALLY-MANAGED` 표시가 생겨 `pip install`이 거부됨(`externally-managed-environment`). 이 이미지는 원래 venv 없이 시스템 파이썬에 설치하고 CMD(uvicorn)도 그 경로를 쓰므로 **`--break-system-packages`로 기존 동작 유지**.
      - **코드 드리프트 없음 확인**: 이미지 빌드일(2026-07-12) 이후 `backend/` 코드 변경 0건 → 재빌드해도 코드는 동일. (⚠️ 로컬 수정이 GitHub 미push 상태라 재빌드는 항상 "현재 로컬 코드"를 굽는다는 점 주의.)
      - **검증(교체 전 격리 테스트 → 교체 후)**: pip freeze 완전 일치 · OS 보안 0건 · **Playwright 실구동**(chromium 148.0.7778.96로 courtauction.go.kr 로드) · `app.main`·`scheduler` 임포트 · 워커 3종 구문 · DB `integrity ok`/properties 5475/WAL 유실 없음 · 스케줄러 **5개 잡 재등록** · `/health` 200 · API 401(인증 정상 동작) · **대법원 스크래퍼 실행으로 실제 공고 10건 수집 성공**.
      - ⚠️ **여기서도 nginx DNS 캐시 함정 동일** — 백엔드 재생성 시 IP가 바뀌므로 `docker compose up -d backend && docker exec onbid-nginx nginx -s reload`로 묶어서 실행할 것.
      - **롤백**: `docker tag onbid-backend-rollback:20260725 onbid-auction-finder-backend:latest && docker compose up -d backend && docker exec onbid-nginx nginx -s reload` (+ 필요 시 Dockerfile·requirements 백업 복원).
- [x] ~~(권장) ABB 백업 전 WAL DB 사전 스냅샷(`sqlite3 .backup`) 훅~~ — 완료 (2026-07-08, `snapshot-db.sh` + systemd 타이머 02:50 KST, ABB 섹션 참조)
- [x] ~~**온비드 일일 동기화 성능 개선 + 429 원인 제거**~~ — **완료·재개(2026-07-12, 아래 작업이력 참조)**. 증분 동기화로 상세 API 호출을 신규·결측 물건에만 한정(전건 재조회 폐지) → 429 구조적 소멸. 목록 중복(회차별 예정가 다행) 결정론적 dedup + 시세 실행내 캐시 + 상세 일일 상한/429 백오프 추가.
  로그의 `지원하지 않는 시도: …`는 에러 아님 — `molit_client.py`, 미지원 시·도 시세 조회 스킵 경고.
  `전남광주통합특별시`(2026-07-01 출범 광주·전남 통합) — `normalize_sido`로 매핑 경고 제거 + 신규 법정동코드(프리픽스 12) 실증·매핑(`_MERGED_LAWD`)으로 시세 복구 완료. 위 2026-07-12 이력의 전남광주 항목 참조.
