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
  - **✅ SK네트웍스 추가자료 반영 + 상세설명 일괄 보강(2026-07-28)**: 자료 원본 `/mnt/nas/temp/`(`20260727_SK네트웍스추가자료/`·`ExcelSaveTemplate_260601_hsrealty.xlsx`(네이버 일괄등록)·`260601_시놀로지 단가표_SS.xlsx`·`이미지/`).
    - **신규 상품 6종 등록**: BC510(id273)·TC510(id274) IP카메라 각 **328,000** / MSD01-256G(275) **194,000**·MSD01-512G(276) **387,000**·MSD01-1T(277) **581,000** 감시용 microSD / TC500(279) **419,000**. microSD용 **`메모리 카드` 카테고리 신설(term 40)** — 기존 `메모리`(33)는 NAS RAM이라 분리. 카메라는 `IP 카메라`(21). 상품 **77→83종**.
    - 이미지 45장 업로드. **GIF는 원본 애니메이션 유지**(사용자 요청. BC510/TC510 각 19MB — `loading=lazy` 적용). ⚠️ **함정**: 세로로 긴 상세이미지는 WP `big_image_size_threshold`(2560px)가 자동 축소해 **860px→268~383px**가 되어 사양표 글자가 뭉갬 → 임포터에서 **`wp_get_original_image_url()`로 원본 URL 사용**해 해결.
    - **기존 상품 30건 상세 보강**: 네이버 일괄등록 엑셀 **Y열의 공급사 CDN 상세이미지**(`gi.esmplus.com/sgoffice39/Synology/...`)를 **외부 링크 그대로**(사용자 결정) 삽입 + 제품정보표(브랜드·제조사·모델명·수입사 SK네트웍스서비스·A/S **031-520-5552**) + A/S·반품 안내문(BF열). 본문 평균 **870→2,300자**. 29 URL 전수 200 확인 후 삽입. ⚠️ **외부 CDN 의존** — 공급사가 파일을 옮기면 30개 상품 상세가 한꺼번에 깨짐(자체호스팅 전환은 다운로드 스크립트만 추가하면 됨).
    - **가격 체계 확정**: 단가표는 `노출가(VAT포함)/공급가(포함)/공급가(별도)` 3단. 쇼핑몰 **76건이 노출가와 정확히 일치** → 쇼핑몰 = **노출가 체계**. 노출가÷공급가(별도) 중앙값 **1.372배**. 예외 2건은 사용자 확인 결과 **현행 유지 확정** — DS1825+ **2,522,000원**(단가표 2,134,000과 다르나 쇼핑몰이 맞음), BC510·TC510 **328,000원**(노출가 맞음. BC500 419,000보다 싼 것이 정상).
    - 스크립트(전부 멱등, `data/wp/hsrealty-import/`): `import_sk.php`+`sk_products.json`(신규 5종) / `enrich_xl.php`+`xl_enrich.json`(상세보강 30건, `SK_XL_START`~`SK_XL_END` 마커 구간만 교체) / `create_tc500.php`. ⚠️ **`wc_get_product_id_by_sku()`는 조회테이블 기반이라 draft를 못 찾아 중복 생성함** → postmeta 직접 조회로 교체(1차 등록분 5건 삭제함).
  - **✅ 리드 마그넷(자료 신청 폼) 구축(2026-07-28)**: NAS 소개자료 발송용 이메일을 **옵트인으로 직접 수집**하는 폼. 시작 시점 회원 0명·주문 0건이라 보유 리스트가 전무했음. ⚠️ 한국은 **자동수집(크롤링)·구매 리스트가 불법**(정보통신망법 §50조의2, 1년 이하 징역/1천만원 벌금), 동의 없는 광고 발송은 과태료 3천만원(§50) → 옵트인 외 선택지 없음.
    - **mu-plugin** `data/wp/wp-content/mu-plugins/hs-lead-magnet.php` — 숏코드 `[hs_lead_form]`, CPT `hs_lead`, 관리자 메뉴 "자료 신청" + **CSV 내보내기**(BOM 포함).
    - **설치 위치**: hsrealty `nas-guide`(page 209) 하단에 폼 본체 / blog.wonrealty.kr **post 104·105**(NAS 글 2편)에 CTA 배너 → 폼으로 유도(`utm_campaign=nas_lead`).
    - **수집**: 필수=이메일·회사명·동의 / 선택=담당자·연락처·사용인원·용도·문의. **동의 이력(시각·IP·동의문구 전문)을 함께 저장** — 분쟁 시 입증용.
    - **발송**: 신청자에게 제안서 PDF 자동 첨부 + 가이드 링크, 관리자(`hs@hsrealty.co.kr`)에게 즉시 알림. 기존 WP Mail SMTP(다음) 사용.
    - **PDF**: `uploads/hsrealty-docs/nas-proposal.pdf` (DS225+ 제안서 12버전, 16p·727KB). **파일이 있으면 첨부, 없으면 링크만** 안내하는 구조라 **같은 경로에 덮어쓰기만 하면 코드 수정 없이 갱신**됨. 원본은 `/mnt/nas/temp/`. ※ 10p 도입사례에 금강다온부동산 실명·자택 원격지 구성이 노출되나 **사용자가 그대로 가기로 확정(2026-07-28)**.
    - ⚠️ **함정: `admin-post.php`가 403** — nginx가 `/wp-admin/` 전체를 신뢰 IP로 제한(2026-07-08 하드닝)하므로 워드프레스 폼의 표준 제출 경로를 쓸 수 없음. **nginx를 푸는 대신 폼 페이지 자체로 POST 받아 `template_redirect`에서 처리**하도록 구현. 같은 이유로 앞으로 이 사이트에 폼을 만들 때 `admin-post.php`/`admin_post_*` 훅을 쓰면 안 됨(`admin-ajax.php`는 예외적으로 허용돼 있음).
    - 스팸 방지: 허니팟 필드 · nonce · **동일 이메일 5분 내 재제출 차단**. 실제 신청 2회로 저장·동의이력·PDF 첨부 발송 전 경로 검증 후 테스트 데이터 삭제(현재 0건).
- **미완**: ~~결제~~(✅ 2026-07-22 KCP 카드결제 라이브 검증 완료)·~~KCP 에스크로 실거래 적용(escw_used=N)~~(✅ 2026-07-25 v6.8 에스크로 게이트웨이 적용, 웹훅등록·100원 실거래 검증만 잔여 — 위 에스크로 항목 참조)·~~상품 상세설명 실제 스펙 보강~~(✅ 2026-07-28 30건 보강. 단가표에 없는 잔여 53종은 미적용)·대리점 데이터(D4ES/D4ESO) 정정·Solapi 핸드폰 본인인증.
- **⏳ 판매채널 확장(2026-07-12 계획, 사용자 요청 = 나중에 진행)**: 검색 등록·방문분석 완료 후 다음 단계로 **①네이버 쇼핑 노출 + ③구글 머천트 센터**(②지역검색·스마트플레이스는 이번엔 제외). 두 채널 공통 선결과제 = **WooCommerce 79상품 → 상품피드(feed) 생성**(제목·가격KRW·이미지·재고·상품URL·카테고리, 가급적 GTIN/브랜드). 생성방식 후보: 피드 플러그인(CTX Feed / Product Feed PRO 등) 또는 커스텀 엔드포인트(WP REST/eval-file로 XML·TSV 출력). **비공개 상품(ID24·80)은 피드서 제외** 필수.
  - **⚠️ 이 계획은 낡음(2026-07-29 정정)** — ①은 이미 별도 경로로 진행되어 있었음: 네이버 스마트스토어에 시놀로지 30종이 **WooCommerce 피드 연동이 아니라 수동/독립적으로 이미 등록**돼 판매 중(아래 2026-07-29 이력 참조). WooCommerce 피드 자동연동은 여전히 미착수.
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

## Tailscale — hyunsung·realty99·NAS 2대 통합 tailnet (2026-08-02~03)
사용자가 기존에 집 NAS·회사 NAS를 Tailscale로 연결해 쓰던 tailnet에, **hyunsung·realty99 서버 2대를 추가**. 목적=NAS 접근(NFS·ABB)을 공인 인터넷(DDNS) 대신 암호화된 tailnet 경유로 전환해 노출면 축소.
- **tailnet 구성원(4대)**: hyunsung `100.95.122.4` · realty99 `100.65.176.46` · **ds725-main**(구 homenas) `100.99.184.84` = `ausqueen.synology.me`(공인 DDNS)와 동일 기기, `/volume2/vpsshr/linux` 제공 · **ds224-backup**(구 dasung000) `100.84.141.124`.
- 두 서버에 공식 설치스크립트(`curl -fsSL https://tailscale.com/install.sh | sudo sh`)로 설치 후 `tailscale up --hostname=<hyunsung|realty99>`(최초 1회 브라우저 로그인 필요). 전 노드 간 **직접 P2P 연결 확인**(DERP 릴레이 아님, NAS 공인IP 116.41.161.23·58.225.109.232 경유 UDP hole-punch 성공).
- **NFS(NAS→서버) 전환**: ds725-main DSM의 NFS 권한 규칙에 두 서버 tailscale IP를 **/32 단위로**(광역 `100.64.0.0/10` 대신 최소권한 채택) 추가 → 포트(2049) 자체는 이미 전 인터페이스에 열려있었으나 기존 권한규칙(공인 IP 2개 한정)에 막혀 `access denied by server`였던 걸 해소. "비특권 포트 허용"은 **불필요**(root fstab 마운트는 기본 특권포트 사용, 지금과 동일 조건).
  - 양쪽 `/etc/fstab`을 `ausqueen.synology.me:/volume2/vpsshr/linux` → **`100.99.184.84:/volume2/vpsshr/linux`**로 교체(백업 `/etc/fstab.bak.20260802`), 사용 중 프로세스 0건 확인 후 라이브 리마운트(`umount && mount -a`)로 즉시 전환·검증(디렉터리 목록 이전과 동일 = 회귀 없음).
  - **부팅 순서 보장**: `/etc/systemd/system/mnt-nas.mount.d/tailscale.conf`(양쪽) 추가 — `After=tailscaled.service`+`Requires=tailscaled.service`로, tailscale 연결 전에 마운트 시도해 실패하는 경쟁상태 방지(기존 `nofail`이라 실패해도 부팅은 안 막혔지만, 이제 아예 순서를 보장).
- **ABB(Active Backup for Business, 서버→NAS) 전환**: `abb-cli -c -a <addr> -u <user> -p <pw>`는 **이미 연결된 상태에서 재실행 불가**(exit 6 "Already connected") → 먼저 `abb-cli -l`(로그아웃, **NAS DSM 관리자 계정 인증 필요** — hyunsung567과 별개 계정, 대화형 프롬프트라 사용자가 직접 터미널에서 실행) 후 `abb-cli -c -a 100.99.184.84 -u hyunsung567 -p ***`로 재연결. **인증서 경고 발생**(cert CN=`ausqueen.synology.me`인데 IP로 접속 → "Proceed anyway?" 프롬프트, 비대화형 실행이라 default(y)로 자동 진행 — tailnet 자체가 WireGuard로 암호화·인증되므로 허용 가능한 트레이드오프로 판단). **device_id 그대로 유지**(hyunsung=20, realty99=19) → 신규기기 중복등록 없이 동일 백업이력·정책 유지 확인.
  - ⏳ **다음 자동 백업(2026-08-03 03:00 KST)이 tailscale 경로의 첫 실전 검증**(abb-cli엔 수동 트리거 명령이 없어 CLI로 미리 테스트 불가, DSM 콘솔 "지금 백업"으로만 강제 가능).
- ⚠️ **비밀번호 노출 주의**: 이 작업 중 hyunsung567 계정 비밀번호가 대화 세션에 평문으로 노출됨(bash `!` 히스토리 확장 문제로 재입력하다 발생) → **사용자에게 교체 권장 안내함**(비필수·사용자 판단에 맡김).
- **✅ 마무리 완료(2026-08-03, 사용자가 "지금 바로 끝내자"고 결정 — 애초 권고는 며칠 안정성 확인 후였음)**: ① NAS(ds725-main) NFS 권한 규칙에서 **기존 공인 IP 2개(5.104.87.178·5.104.87.20) 규칙을 삭제**(사용자가 DSM에서 직접 실행), tailscale IP 규칙만 남김. 검증: 공인 경로(`ausqueen.synology.me`)로 마운트 시도 → **`access denied by server`로 정상 차단** 확인, tailscale 경로(`100.99.184.84`) 마운트는 문제없이 유지. → **NFS가 공인 인터넷에서 완전히 걷어내짐.**
  ② 양쪽 Uptime Kuma의 "NAS NFS(synology)" 모니터(id=4, PORT 타입) hostname을 `ausqueen.synology.me` → **`100.99.184.84`**로 갱신(임시 `python:3.12-alpine`+`uptime-kuma-api<2.0` 컨테이너로 API 호출, host에 패키지 설치 안 함 — 기존 패턴 재사용). 오탐(다운 알림) 없이 정상 반영 확인.
  - ⚠️ **참고**: realty99↔hyunsung 상호 사이트 모니터(`*.co.kr`·`*.kr` 공인 도메인 체크)는 **의도적으로 tailscale로 안 바꿈** — 그건 실제 방문자가 겪는 공인 경로(DNS·nginx vhost·TLS) 자체를 검증하는 게 목적이라 tailscale IP로 바꾸면 오히려 장애를 놓치게 됨. NAS NFS·ABB만 tailscale 대상(관리자·데이터 전용 채널이라 공개될 이유가 없었음).
  - **롤백이 필요해지면**: NAS DSM에서 NFS 권한 규칙에 공인 IP(5.104.87.178·5.104.87.20) 재추가 + 양쪽 fstab을 `/etc/fstab.bak.20260802`로 복원 + Kuma 모니터 hostname을 `ausqueen.synology.me`로 되돌리기.
- **롤백**: `/etc/fstab.bak.20260802` 복원 + `mnt-nas.mount.d/tailscale.conf` 삭제 + `mount -a` (+ ABB는 `abb-cli -l`(admin인증) 후 `-c -a ausqueen.synology.me ...`로 재연결).

## GitHub — 저장소 3개 (2026-08-09 hsrealty·blog-wonrealty 추가)
이 서버의 서비스 3개가 각각 별도 private 저장소를 쓴다. **저장소마다 전용 배포키**를 두어,
키 하나가 유출돼도 그 저장소 하나만 영향을 받게 했다.

| 저장소 | 경로 | SSH 별칭 / 배포키 |
|--------|------|-------------------|
| `ausqueen/onbid-auction-finder` | `/opt/onbid-auction-finder` | `github-onbid` / `~/.ssh/onbid_deploy_key` |
| `ausqueen/hsrealty` | `/opt/hsrealty` | `github-hsrealty` / `~/.ssh/hsrealty_deploy_key` |
| `ausqueen/blog-wonrealty` | `/opt/blog-wonrealty` | `github-blogwr` / `~/.ssh/blogwr_deploy_key` |

- 별칭 정의는 `~/.ssh/config`(각 `Host` 블록 + `IdentitiesOnly yes`). remote 는 `git@<별칭>:ausqueen/<repo>.git` 형식.
- ⚠️ **배포키는 저장소 단위 권한**이다. `github-onbid` 키로 hsrealty 에 push 하면 `Repository not found` 가 난다
  (계정 키가 아니라 onbid 전용 키. `ssh -T git@github-onbid` 하면 `Hi ausqueen/onbid-auction-finder!` 로 확인됨).
  **새 저장소를 추가할 때는 키도 새로 만들어 `gh repo deploy-key add --allow-write` 로 등록**할 것.
- ⚠️ **git 명령은 `sudo` 없이 `ausqueen` 계정으로 실행할 것** — sudo 는 root 의 SSH 키를 쓰므로 origin 접근이 실패함(2026-07-25 확인).
  - `/opt/blog-wonrealty` 는 원래 root 소유라 **최상위 디렉터리만 ausqueen 으로 chown** 했다(하위 소유권은 유지). `/opt/hsrealty` 는 원래 ausqueen 소유.
- **gh CLI 2.97.0 설치됨**(2026-08-09, 공식 apt 저장소). 저장소 생성·배포키 등록용.
  인증은 디바이스 플로우로 완료(scopes `repo`/`read:org`/`gist`), 토큰은 `~/.config/gh/hosts.yml` 에 **평문 저장**(권한 600).
  일상 push/pull 은 배포키로 동작하므로 **`gh auth logout` 해도 무방**하다.

### 추적 범위 — "직접 작성한 것"만
워드프레스 코어·서드파티 플러그인/테마·업로드·DB 는 컨테이너 이미지와 백업(ABB·db_predump)이 관리하므로 제외한다.

- **hsrealty**(58 파일 / 808K): 자식테마 `hsrealty`(functions.php·style.css·WooCommerce 오버라이드·assets), mu-plugins(`hs-lead-magnet`·`hs-product-feed`), `hsrealty-import/` 스크립트·콘텐츠 원본, docker-compose.yml, `.env.example`.
- **blog-wonrealty**(608 파일 / 3.9M): `autopost/`(autopost.py·pool.json), mu-plugins 6종, `naver_archive/`(스크립트·원문 555건·진행상태 JSON·운영 문서), **`deploy/`(systemd 유닛 사본)**, docker-compose.yml, env 예시 2종.
  - `deploy/` 를 둔 이유: systemd 유닛은 `/etc/systemd/system/` 에 있어 저장소 밖이라, 서버 재구축 시 **자동발행 스케줄(08·20시)을 기억으로 복원**해야 했음. 사본을 함께 보관한다.
- ⛔ **제외**: `.env`(WP 관리자·DB 비번), `autopost/autopost.env`(Gemini API 키·WP 앱 비번·SMTP 비번·IndexNow 키), 인증 실패 로그(`hs-auth-fail.log` — 관리자 계정명·신뢰 IP 노출), `naver_archive/images`(248M), 각종 `*_bak`.
  값 없는 **`.env.example`** 을 대신 추적해 어떤 키가 필요한지는 남겼다.
- ⚠️ **`.gitignore` 함정**: `data/` 처럼 **디렉터리를 통째로 제외하면 git 이 그 안으로 내려가지 않아** `!data/.../mu-plugins` 재포함이 동작하지 않는다.
  blogwr 에서 실제로 mu-plugin 6개가 통째로 빠졌었다. **하위 경로를 개별 제외**할 것.

### 커밋 기록
- 최신은 `git log -1` 로 확인할 것(아래 줄은 항상 뒤처짐).
- 2026-08-09: `9c7d138`(onbid, robots.txt 추적) / `9ad3f35`(hsrealty 최초) / `7694440`(blog-wonrealty 최초).

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

## 2026-07-26 작업 이력 — 상호 감시 모니터링(Uptime Kuma) 구축
- **구조**: realty99 ↔ hyunsung 두 서버가 **서로의 사이트를 감시**(자기 서버가 죽으면 자기 Kuma도 같이 죽으므로 교차 배치). 각 서버 `/opt/monitoring/docker-compose.yml`, 이미지 **`louislam/uptime-kuma:1` 고정**(⚠️ 설정 자동화에 쓴 python `uptime-kuma-api`가 2.x 미지원 — 임의로 2.x 올리지 말 것), **127.0.0.1:3001에만 바인딩**(ufw inactive라 공개 바인딩 금지). 대시보드 접속: `ssh -L 3001:127.0.0.1:3001 <서버>` 후 http://localhost:3001.
- **이 서버(hyunsung) Kuma 감시 대상**: realty99.co.kr, blog.realty99.co.kr, ~~NAS 미포함~~→**NAS NFS(2049) 추가(2026-07-29)**. / **realty99 Kuma 감시 대상**: hsrealty.co.kr, wonrealty.kr, blog.wonrealty.kr, NAS NFS(ausqueen.synology.me:2049 포트체크).
- **⚠️ 2026-07-29 발견·수정: NAS 다운 알림 편측 문제** — NAS가 펌웨어 업데이트로 5분+ 다운됐을 때 **realty99 Kuma는 알림(다운·복구) 정상 발송, hyunsung/hsrealty 쪽은 무응답** → 원인은 장애가 아니라 **설계상 hyunsung Kuma에 NAS 모니터가 애초에 없었음**(구축 시 NAS 감시를 realty99 쪽 하나만 두기로 함). 실측: NAS 다운 11:35:31~11:38:38(EHOSTUNREACH→ECONNREFUSED, 약 3분), 같은 시간 hsrealty.co.kr·wonrealty.kr·blog.wonrealty.kr은 200 OK 유지(둘 다 `/mnt/nas` 실시간 미사용이라 서비스 자체엔 영향 없음). **realty99 서버 자체가 죽으면 NAS 감시도 함께 죽는 단일장애점**이라 판단 → hyunsung Kuma에도 동일 `NAS NFS(synology)` 포트체크(hostname=ausqueen.synology.me, port=2049, interval 60s, retry 60s×2) monitor id=4 추가 + email-daum·kakao 알림 연결(`notificationIDList=[1,2]`) 완료. 이제 **NAS 다운 시 두 서버 모두에서 이중 알림**. 추가는 `uptime-kuma-api<2.0`을 임시 `python:3.12-alpine` 컨테이너(`--network host`, 설치 즉시 폐기)로 API 호출해 처리 — 호스트에 패키지 설치 안 함(PEP668 externally-managed라 회피).
- **알림**: smtp.daum.net:465(ceo@realty99.co.kr, 비번은 realty99 `/opt/daon/.env`의 `MAIL_SMTP_PASSWORD` 재사용) → **ausqueen@hanmail.net**. 발신자명 `hsrealty-monitor`/`realty99-monitor`로 어느 쪽 감시자가 보냈는지 구분됨. 모니터 60초 간격·재시도 2회 → 다운 후 약 2~3분 내 메일.
- **검증 완료**: 전 모니터 UP, 양쪽 모두 SMTP 테스트 발송 성공("Sent Successfully"), realty99 쪽은 모의 DOWN(죽은 주소 임시 모니터)으로 상태 전이까지 확인.
- **계정**: admin `ausqueen`, 비밀번호는 realty99 `/opt/monitoring/admin_password.txt`(600) — 양쪽 Kuma 동일.
- ⚠️ 재부팅 점검 시 `sudo docker ps`에 `uptime-kuma` 기동 여부 확인 항목 추가할 것(restart: unless-stopped라 자동 기동 예상).
- **카카오톡 알림 추가(같은 날)**: 각 서버에 `kakao-relay` 컨테이너(같은 compose) — Kuma 웹훅 → 카카오 나에게 보내기 API → 사용자 카톡. 스크립트·토큰은 `/opt/monitoring/kakao/`(tokens.json 600, 서버별 독립 토큰·3일 주기 자동갱신으로 재동의 불필요). 카카오디벨로퍼스 앱은 기존 "파산공매" 앱 재사용, Redirect URI `https://realty99.co.kr/kakao-auth`. 이메일(다음 SMTP)과 카톡(카카오 API)이 경로 분리라 이중화됨. 재부팅 점검 시 `kakao-relay` 컨테이너도 확인할 것.
- **DB 사전 정합 덤프 추가(같은 날)**: `db-predump.timer`(매일 02:40 KST, ABB 03:00 직전) → `/opt/monitoring/db_predump.sh`가 hsrealty-db·blogwr-db MariaDB 전체를 `/opt/backup/db_predump/`에 덤프(3일 보존, ABB에 포함됨). 온비드 SQLite는 기존 02:50 스냅샷이 계속 담당. 성공 시 로컬 Kuma 푸시 모니터에 하트비트 → 26시간 무신호면 이메일+카톡 경보. realty99에도 동일 구성(그쪽은 pg_dumpall+blog MariaDB).

## 2026-07-29 작업 이력 — hsrealty 네이버 스마트스토어 존재 확인 + SK 8/1 가격변동 반영
- **⭐ 문서 정정**: 2026-07-12 "판매채널 확장" 계획에는 네이버 쇼핑 미입점으로 기록돼 있었으나, **실제로는 네이버 스마트스토어에 시놀로지 상품 30종이 이미 등록·판매 중**이었음(등록 시점 미상 — 이 CLAUDE.md에 기록되지 않은 채 진행됨). **관리 방식은 API 연동이 아니라 스마트스토어센터 "상품 일괄수정" 엑셀 다운로드/업로드 수동 방식**(이 서버에 네이버 커머스API 키 없음).
- **SK네트웍스 8/1자 가격변동 반영**: SK가 보낸 `260803_시놀로지 단가표_SS_신구비교.xlsx`(0601→0801 전체 189개 품목 신구비교, 신규36·단종33·가격변동79·견적문의41)와 스마트스토어 상품 다운로드 엑셀(30개, 상품번호 `136667844xx`대)을 모델코드로 매칭 → 29개 가격변경 + TC500 1개(단가표상 상태 모순: "견적/문의"인데 0801란엔 "단종" 텍스트 → 사용자 판단으로 **단종 처리, 재고 0으로 설정해 품절/판매중지**) = 총 30개 전량 매칭 성공(미매칭 0).
  - 눈에 띄는 인상 3종(단가표 원본 그대로 반영, 특이사항이라 기록): **DS1525+** 1,746,000→2,058,000(+312,000) · **DS925+** 1,164,000→1,402,000(+238,000) · **DS725+** 1,066,000→1,309,000(+243,000). 나머지는 대부분 소폭 인하.
  - 산출 파일 `네이버가격변경_20260803.xlsx`(원본 일괄수정 양식 그대로 유지, F열 판매가만 수정 + TC500은 M열 재고수량만 0으로) → `/mnt/nas/temp/`에 생성, 사용자가 3~5행(작성가이드) 삭제 후 스마트스토어센터에 업로드 → **반영 완료 확인(사용자, 2026-07-29)**.
  - 매칭 스크립트는 세션 스크래치패드 1회성(저장 안 됨) — 재사용 필요 시 이 항목 참고해 재작성.
- ✅ **hsrealty 자체몰(WooCommerce) SK 8/1 단가표 반영 완료(같은 날 후속)**: hsrealty 실제 85종을 SK 189개 전체와 SKU 매칭해 3종 분류 후 1~3단계 실행 완료.
  - **① 가격변경 83건 — 완료(2026-08-02)**: 78건 정상매칭 + 5건(7/28 신규등록한 BC510·TC510·MSD01-256G/512G/1T, SK표에선 "신규"분류지만 hsrealty엔 이미 있어 사실상 가격변경)을 스크립트 `data/wp/hsrealty-import/sk0801_price_update.php`+`sk0801_price_updates.json`(멱등, `wc_get_product`→`set_regular_price/set_price`)로 반영·라이브 검증까지 했으나 **사용자가 실행계획 변경을 이유로 즉시 전량 원복 지시** → `sk0801_price_revert.php`로 old값 복원. 이후 **사용자가 인상 3종만 우선 반영 요청** → `sk0801_price_update_inc3.php`+`sk0801_price_updates_increase3.json`로 DS725+(1,066,000→1,309,000)·DS925+(1,164,000→1,402,000)·DS1525+(1,746,000→2,058,000) 3건만 재반영·라이브 확인 완료(2026-07-29). **✅ 나머지 80건도 2026-08-02에 반영 완료** — 사전 `db_predump.sh` 수동백업 후 `sk0801_price_update.php` 재실행(멱등이라 인상 3종은 자동 스킵) → 80건 신가 반영, 라이브 확인(BC500·DS225+·D4ER01-64G·HAT3320-20T 등) 정상. **→ SK 8/1 단가표 83건 전량 반영 완료.** 신규등록 15건(자료 도착 시)만 잔여.
  - **② 단종 2건 완료 — 유지**(가격변경 원복과 별개로 사용자가 유지 확정) — E10G18-T1(id96)·TC500(id279, 네이버 스마트스토어와 동일 판단) → `catalog_visibility=hidden`+`post_status=private`(기존 ID24·80 패턴). 비로그인 404 확인 완료.
  - **③ 사전 백업**: 실행 직전 `sudo /opt/monitoring/db_predump.sh` 수동 1회 실행(`hsrealty_mariadb_20260729.sql.gz`, 매일 자동덤프와 별개).
  - **④ 신규등록 15건 — 미착수, 자료 대기 중**: SK 8/1 단가표에 있으나 hsrealty엔 없는 31개 중 오프라인견적(가격없음) 15건과 상태모순 1건(RT2600ac, "신규"인데 0801란=단종 텍스트)은 **등록 제외 확정**(사용자 결정), 나머지 **가격 확정 15건이 등록 대상**으로 확정됐으나 **이미지·상세설명·카테고리 자료가 없어 보류 중**(7/28 SK등록 때와 달리 이번 단가표엔 가격만 있고 이미지 CDN 링크 등 상세자료 없음). SK에 자료 요청 필요. 500만원 초과인 D4ER02-64G(6,737,000)는 기존 `hs_is_inquiry_product()` 단가기준 자동판별 로직이 이미 있어 등록만 하면 문의CTA 자동적용(코드 수정 불필요, 확정).
    - **등록 대상 15건**(모델 | 노출가0801 | 분류): Surveillance365 Business 1License-1Y \| 95,000 \| 라이선스 · BST170-4T \| 882,000 \| BeeStation 4TB · DS725neo+ \| 935,000 · DS925neo+ \| 1,028,000 · DS1525neo+ \| 1,496,000 · DS1825neo+ \| 1,870,000 (DiskStation Neo plus 4종) · RS1226+ \| 3,563,000 · RS1226RP+ \| 4,231,000 (RackStation 8bay 2종) · FS200T \| 1,684,000 (RackStation Enterprise 6bay) · RX426 \| 1,224,000 (확장베이 4bay) · D4ER02-16G \| 2,621,000 · D4ER02-64G \| 6,737,000(500만초과→문의CTA) · D4ER03-32G \| 4,118,000 (Memory 3종) · E10G30-T1 \| 242,000 (PCI카드)
    - **제외 확정 16건**(오프라인견적 15 + RT2600ac): RS11626xs+·FS200T… 아 FS200T는 위 포함이니 제외목록엔 없음. 제외=PAS7700·PAX224·SPU7200D-1920G/3840G/7680G·P2100G·PAS7700 SW유지보수·HAT5320-4T/8T·HAT5310-16T·HAT5320-20T·HAS5310-12T/20T·HAS5320-24T·RS11626xs+(SA시리즈 후속)·RT2600ac(상태모순)
    - **재개 방법**: SK에서 위 15건 이미지·상세스펙 받으면 → 카테고리 매핑(신규 카테고리 필요할 수 있음: DiskStation Neo plus, BeeStation, RackStation Enterprise) → `import_sk.php` 패턴으로 신규 등록 스크립트 작성.

## 2026-08-05 작업 이력 — NAS tailscale TUN 인터페이스 버그 수정 + hyunsung·realty99 SSH 22번 포트 화이트리스트 전환

### ✅ NAS 2대(ds725-main·ds224-backup) tailscale TUN 인터페이스 미생성 버그 수정
- **증상**: ds725-main → ds224-backup Hyper Backup/ABB 설정 중 "인터넷 오류" 발생. 두 NAS를 spk 1.58.2→1.102.2로 업데이트하고 재부팅했는데도 재현.
- **진단**: `tailscale status`엔 정상 표시되고 `tailscale ping`(자체 프로토콜)도 성공했지만, **`ip addr show tailscale0`이 "Device does not exist"** — 즉 커널 TUN 인터페이스가 아예 안 만들어져 있어서 OS 레벨 라우팅(일반 ping·실제 백업 트래픽)이 전부 실패하고 있었음. tailscaled 로그(`/volume{1,2}/@appdata/Tailscale/tailscaled.stdout.log`)에서 원인 확인.
- **원인 2가지(둘 다 필요)**:
  1. **`CAP_NET_ADMIN` 캐퍼빌리티 유실** — spk 업데이트로 `tailscaled` 바이너리가 교체되면서 파일에 걸려있던 캐퍼빌리티(setcap) xattr가 날아감. 로그: `tstun.New("tailscale0"): permission denied`(ds725, 캐퍼빌리티 문제). `sudo getpcaps <pid>`로 빈 값(`=`) 확인.
  2. **`/dev/net/tun` 장치 파일 권한 600(root 전용)** — tailscaled는 `tailscale`이라는 비root 계정으로 도는데 장치를 열 권한이 없음. 로그: `tstun.New("tailscale0"): operation not permitted`(ds224, 캐퍼빌리티는 있는데 장치 권한 문제 — 원인이 서로 다름에 주의).
  - 캐퍼빌리티가 없거나 장치를 못 열면 tailscaled는 **`netstack`(유저스페이스 폴백) 모드로 조용히 전환**됨 — 이 모드는 tailscale 자체 프로토콜(status/ping)엔 응답하지만 일반 OS 라우팅은 안 됨(공식 문서상 아웃바운드는 SOCKS5/HTTP 프록시로 별도 설정해야 함). `ip addr show`/`/proc/net/dev`로 인터페이스 부재를 확인하는 게 확실한 진단법 — netstack 폴백이어도 우연히 ping이 통과되는 것처럼 보이는 애매한 상태가 나올 수 있어(정확한 메커니즘 불명), **tailscaled 자체 로그의 `tstun.New(...)` 라인이 최종 판단 근거**임.
- **수정**: 두 NAS 다 동일 조치(경로만 다름: ds725-main=`/volume2/@appstore/Tailscale/`, ds224-backup=`/volume1/@appstore/Tailscale/`).
  ```
  sudo chmod 0666 /dev/net/tun
  sudo setcap cap_net_admin,cap_net_raw+eip /volume{1,2}/@appstore/Tailscale/bin/tailscaled
  ```
  적용 후 Package Center에서 Tailscale 중지→실행(재시작해야 새 캐퍼빌리티가 새 프로세스에 반영됨, setcap은 이미 뜬 프로세스엔 소급 적용 안 됨).
- **재부팅해도 유지되도록 부팅 스크립트(Task Scheduler, 트리거=부팅 시, 실행계정=root) 갱신** — 기존에 `/dev/net/tun` mknod+chmod만 하던 스크립트가 있었으나 **`tun` 커널 모듈 로드보다 chmod가 먼저 실행되는 경쟁상태**로 인해 이후 Tailscale 자체가 부르는 `modprobe tun`이 실제 모듈 최초 로드를 트리거하면서 devtmpfs가 장치를 기본권한(600)으로 재생성 → 무력화되는 버그가 있었음. **`modprobe tun`을 스크립트 맨 앞에 명시적으로 추가**해서 해결(모듈을 먼저 확실히 로드시켜두면, 이후 Tailscale이 부르는 `modprobe tun`은 no-op이 되어 권한이 유지됨). 최종 스크립트(volume 번호만 서버별로 다름):
  ```bash
  modprobe tun
  mkdir -p /dev/net
  [ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200
  chmod 0666 /dev/net/tun
  setcap cap_net_admin,cap_net_raw+eip /volume{1,2}/@appstore/Tailscale/bin/tailscaled
  sleep 5
  synopkg restart Tailscale
  ```
  ds725-main·ds224-backup 양쪽 실제 재부팅으로 `tailscale0` 인터페이스 생성 + `ping` 실제 왕복 성공까지 검증 완료.
- **⚠️ MagicDNS는 DSM에서 구조적으로 작동 안 함**(tailscale GitHub Issue #4017, 미해결) — DSM이 tailscaled에게 `/etc/resolv.conf` 수정 권한을 안 줘서(`rename ... permission denied`), 관리자 콘솔에서 MagicDNS를 켜놔도 NAS 자체 OS는 `.ts.net` 이름을 못 풂. **NAS 위에서 도는 앱(Hyper Backup·ABB 등)에 tailscale 대상을 입력할 때는 반드시 MagicDNS 이름이 아니라 tailscale IP(`100.x.x.x`)를 직접 입력할 것.**
- **참고(완료는 아님, 방법만 확인)**: DSM 인증서 저장소에 tailscale 발급 HTTPS 인증서를 넣으려면 `tailscale configure synology-cert`(1.64.0+ 필요, Task Scheduler로 root 실행 가능) 또는 수동 `tailscale cert <이름>` 후 제어판→보안→인증서에서 가져오기. 기존 DDNS 인증서와는 SNI로 공존 가능(서비스별로 "구성"에서 명시 지정 안 해도 호스트명에 따라 자동 분기됨).

### ✅ hyunsung·realty99 SSH(22번) 공인 IP 화이트리스트 전환
- **배경 점검 결과**: 그동안 두 서버 다 22번 포트가 **전체 인터넷에 완전히 열려있었음**(ufw 비활성, iptables INPUT 정책 ACCEPT에 22번 관련 규칙 전무). 방어는 fail2ban(사후 차단)뿐 — 누적 실패 로그인 hyunsung 3,072건/realty99 4,519건.
- **적용한 규칙**(양쪽 서버 동일 구조, `iptables`=IPv4 + `ip6tables`=IPv6 둘 다):
  - 허용: 관리자 자택/사무실 공인 IP 2곳(`116.41.161.23`=ausqueen.synology.me, `58.225.109.232`=dasung000.synology.me) · **상대 서버 공인 IP**(hyunsung↔realty99 상호 SSH 자동화 유지용, `5.104.87.178`/`5.104.87.20`) · **tailscale0 인터페이스 경유**(이름이 아니라 인터페이스 매칭이라 tailnet 어느 피어에서 접속해도 통과)
  - 그 외 전부 DROP. IPv6는 위 관리자 2개 IP가 IPv4 전용(A레코드만 있음)이라 **tailscale 경로만 허용 + DROP**.
  - 순서 중요: 기존 tailscale 자체 `ts-input` 점프 규칙(1번) 뒤에 위 규칙들을 **append**(`-A INPUT`)해야 tailscale의 자체 필터링(스푸핑 방지용 DROP 등)과 안 꼬임.
- `iptables-persistent` 설치 + `netfilter-persistent save`로 **재부팅해도 유지**되도록 저장(`/etc/iptables/rules.v4`·`rules.v6`).
- **⚠️ 겪은 함정 1 — 서버 간 SSH가 tailscale이 아니라 공인 IP로 나가고 있었음**: hyunsung→realty99 자동화가 `ssh ausqueen@5.104.87.20`(공인 IP 직접)를 쓰고 있었는데, DROP 규칙 적용 직후 이 경로가 즉시 막혀 타임아웃 발생. tailscale IP(`100.65.176.46`)로 우회 접속해 복구 후, **상대 서버 공인 IP를 화이트리스트에 추가**해 원래 방식도 계속 되게 조치.
- **⚠️ 겪은 함정 2(=운영상 인지 필요) — 화이트리스트는 DDNS 이름이 아니라 그 순간 resolve된 고정 IP값**: `ausqueen.synology.me`/`dasung000.synology.me`가 나중에 실제로 다른 IP로 바뀌면(회선 재계약 등), 이 iptables 규칙은 **자동으로 안 따라감** — 옛 IP는 계속 열려있고 새 IP는 막힘. 관리자 PC(daonpc)는 이미 tailnet 멤버라 **평소 SSH 접속은 tailscale IP를 주력으로 쓰고, 공인 IP 화이트리스트 경로는 백업으로만 두는 걸 권장**함(사용자에게 안내 완료). DDNS IP가 바뀌면 이 iptables 규칙(`-s <IP>`)을 수동으로 갱신해야 함 — 자동 동기화 스크립트는 미구축.
- fail2ban은 그대로 유지(화이트리스트 IP発 비밀번호 대입 등에 대한 이중 방어, sshd `PasswordAuthentication`은 여전히 `yes`라 완전 무의미하지 않음).
- **되돌리기**(각 서버에서 실행): `sudo iptables -F INPUT && sudo ip6tables -F INPUT && sudo netfilter-persistent save` (tailscale의 `ts-input` 점프 규칙은 tailscaled가 재시작 시 자동 재삽입하므로 별도 복구 불필요).
- **사용자 판단**: 구글 계정(`ausqueen@gmail.com`, tailnet 로그인 ID)에 2FA가 걸려있어 "현재 수준으로 충분히 안전"하다고 판단 → tailscale ACL 세분화·Tailscale SSH 전환 등 추가 강화는 보류.

### ✅ fail2ban이 tailscale 경유 접속을 밴하지 않도록 화이트리스트 추가(같은 날 후속)
- iptables는 tailscale0 인터페이스를 통째로 허용하지만, **fail2ban은 별도 로직**(sshd 로그의 실패 횟수만 보고 밴)이라 tailscale IP(`100.x.x.x`)로 접속해도 비밀번호를 여러 번 틀리면 그대로 밴될 수 있는 상태였음(`/etc/fail2ban/jail.local`의 `ignoreip`에 tailscale 대역 누락).
- 조치: `ignoreip`에 **tailscale CGNAT 전체 대역 `100.64.0.0/10`** 추가(백업 `jail.local.bak.20260805`) → `fail2ban-client reload sshd`로 무중단 반영. `fail2ban-client get sshd ignoreip`로 반영 확인.
- 개별 피어 IP 나열 대신 **대역 전체를 허용**해서 향후 tailnet에 새 기기(daonpc·galaxy-z-fold7 등)가 추가돼도 별도 수정 불필요.

## 2026-08-09 작업 이력 — hsrealty 구축 지원 서비스 신설 + 노출 확대(플레이스·머천트·블로그)

### ✅ 구축 지원(방문 설치) 서비스 신설
가격·범위는 사용자 결정: **경기 시흥·안산 1일 방문 설치 165,000원(VAT 포함), 그 외 지역 협의**.
- **상품** `NAS 방문 설치 지원 (1일)` id=**286**, SKU `SETUP-VISIT-1D`, **virtual**(배송 없음), 신규 카테고리 `구축 지원`(term **41**, slug `setup-service`).
- **랜딩** `/setup-service/`(page **287**, 전체폭) — 지원 범위 4단계(자가설치/원격지원/공식카페/방문설치)·포함·불포함·진행절차·FAQ. **주 메뉴(id38) position 4** 삽입.
- **결제 실동작 검증**: 장바구니 담기 → 결제 진입까지 확인. virtual 이라 **배송비·배송지 미노출**, 결제수단 4종(카드·가상계좌에스크로·계좌이체에스크로·무통장) 정상. 165,000원이라 `hs_is_inquiry_product`(500만 초과 문의전환) 대상 아님.
- 스크립트(멱등): `data/wp/hsrealty-import/create_setup_service.php` + `setup_service_page.html`.
- **포함 범위 단서 명시**(사용자 요청): 원격 접속 설정은 **사내 네트워크 및 방화벽 담당자 협조 필수**, 협조 불가 시 해당 항목 제외하고 진행하되 **금액은 변동 없음**. NAS 기본 보안 설정은 **DSM 자체 보안**이며 사내 네트워크 장비 보안은 불포함임을 명시.

### ✅ "무상 방문 설치" 오인 문구 정정
홈 히어로·회사소개·도입가이드·SEO 메타가 **설치를 무료 제공하는 것처럼** 읽혔음 → **자가 설치 기본 / 원격 지원 무료 / 방문 설치 유료** 원칙으로 통일(백업 `_theme_bak/functions.php.bak.20260809setup`, `_copyfix_backup_20260809.json`).
- 히어로 본문·지표(`1:1 무료 원격지원`)·신뢰 배지(`무료 원격 설정 지원` + `방문 설치 서비스(유료)`), 회사소개(page 180), 도입가이드(page 209), `hs_seo` 기본 설명.

### ✅ SK네트웍스 시놀로지 공식 네이버 카페 안내 (https://cafe.naver.com/synologyskns)
- 자식테마 `functions.php`에 **상품 상세 지원·A/S 안내 박스**(`woocommerce_single_product_summary` priority 45). `구축 지원` 카테고리 상품에는 미출력. 상수 `HS_SKNS_CAFE_URL`.
- `/setup-service/` 지원범위 4번째 카드 + 문의 CTA + **푸터 위젯**(`widget_custom_html[3]`)에 링크 추가.

### ✅ 교환·환불 정책 개정 — "개봉 시 환불 불가"의 법적 검토와 대안
사용자 요청(HDD는 개봉 시 중고 취급)에 대해 **현행법 검토 후 진행**.
- **결론**: 「전자상거래법」 제17조 제2항 제1호 단서가 **"내용을 확인하기 위한 포장 훼손은 제외"**라고 명시 → **개봉만으로 청약철회를 막는 조항은 제35조에 의해 무효**(공정위 시정조치·과태료 리스크).
- **대안 채택**: 기준을 개봉이 아니라 **제2호(사용으로 인한 가치의 현저한 감소)** = **"NAS·PC에 장착하여 전원을 인가한 경우"**로 전환. HDD 는 **SMART(전원 인가 시간·켜짐 횟수)로 객관 입증 가능**하고, 제17조 제5항상 입증책임이 판매자에게 있어 이 품목은 방어 가능.
- **제17조 제6항 필수 요건 충족**: 제한 사유는 **사전에 명확히 표시**하지 않으면 무효 → 정책 페이지뿐 아니라 **HDD·SSD·메모리카드 상품의 구매 버튼 바로 위**에 고지 박스 출력(`functions.php`, priority 29, 상수 `HS_STORAGE_CATS='hdd,ssd,memory-card'` — 카테고리 기준 자동 판별이라 신규 상품도 코드 수정 없이 적용).
- 정책 페이지(page 9) 수정: ~~"미사용·미개봉 상태"~~ → **"사용하지 않은 상태" + 개봉만으로는 제한되지 않음 명시**, 제한사유 목록에서 **'개봉' 단독 항목 제거**, 라이선스 키 확인·등록은 제4호로 적법 명시, **하자·오배송은 A/S가 아닌 교환·환불**임을 추가(제17조 제3항은 배제 불가). 백업 `_theme_bak/_page9_backup_20260809.html`.
- ⏭️ 사용자 후속 권고: 출고 시 **HDD 일련번호+SMART 초기값 기록**(분쟁 시 입증), 공정위 전자거래 상담(1670-0007) 1회 확인.

### ✅ 제안서 PDF(nas-proposal.pdf) 도입사례 구성 변경 — 실측 반영
금강다온부동산 구성 변경(메인 DS224+→**DS725+**, 원격지 DS220J→**DS224+ 4TB+4TB SHR**) 및 **ABB 실측 대수** 반영. 11페이지만 수정, 나머지 14p 텍스트 무변경 대조 확인.
- **PC 대수는 DS725+에 SSH 접속해 실측**: `/volume2/@ActiveBackup/config.db`(device_table)+`activity.db`(device_result_table) 조회 → 등록 13대 중 **매일 백업되는 Windows PC 7대**(최근 7일 7/7 성공) + **리눅스 서버 2대**(realty99·hyunsung). 나머지 4대는 중단 상태(마지막 성공 7/5·6/14·이력없음)라 제외. 다이어그램 박스를 `직원 PC 7대`(Windows) / `서버 2대`(Ubuntu Linux)로 교체.
- ⚠️ **함정 1 — Calibri-Bold 서브셋에 숫자 '7' 글리프가 없음**: 문서 전체 폰트를 훑어도 '7' 보유 Calibri-Bold 없음 → `DS725+`를 쓸 수 없어 **Calibri 메트릭 호환 폰트 Carlito-Bold**로 그 span 만 대체(폭 오차 0.0pt). 일회용 `python:3.12-slim` 컨테이너에 `fonts-crosextra-carlito`+`pymupdf` 설치해 작업(운영 컨테이너 미오염).
- ⚠️ **함정 2 — 리댁션이 폰트 등록을 초기화**: `page.insert_font()`는 반드시 `apply_redactions()` **이후**에 호출해야 함.
- ⚠️ **함정 3 — 한글 자간**: 원본이 폰트 기본폭보다 넓게 조판돼 있어, 새 텍스트를 그대로 넣으면 뒤 글자와 간격이 벌어짐 → 원본 span 폭에 맞춰 **글자 균등 분배**(align='S')로 재현. 한글 서브셋엔 **공백 글리프가 없어** 공백 포함 span 은 우측 정렬로 위치 계산.
- **용량**: 폰트 임베드로 727KB→1.74MB 로 늘어난 것을 `subset_fonts()`로 **847KB**까지 축소. 원본 백업 `_theme_bak/nas-proposal.bak.20260809.pdf`.

### ✅ 노출 확대 — 현황 진단(실측)
- **GA4**: 하루 방문자 2~10명, 유입 대부분 direct, **검색 유입 1세션**. 페이지뷰≈방문자수(홈만 보고 이탈).
- **GSC 서비스계정 연결**(사용자가 `ga4-reaport@ga4-report-503309.iam.gserviceaccount.com` 추가) 후 실측: 3개월 **57페이지 노출 / 426회 / 6클릭(CTR 1.4%)**. 노출 검색어가 **전부 영문 모델번호**(hat3320-20t, e10g30-t2 등)이고 **평균 순위 3~10위(1페이지)**. 기기별 **데스크톱 242 vs 모바일 27**.
- **해석**: 색인·순위 문제가 아니라 ①파이가 작고 ②클릭을 못 먹는 것. 한글 키워드 노출은 0.
- **네이버 데이터랩 실측**(1년): `시놀로지` 35~58 / `나스 설치·구축` 1.1~3.4 / `나스 추천` 0.7~6.5 / **`사무실 나스`·`기업용 나스` 0.03~0.06(사실상 검색 없음)**. → **"사무실 NAS" 키워드 전략은 폐기**, `나스 설치/구축`으로 전환. `나스 설치 대행` 네이버 블로그 상위는 전부 무관 문서 = **경쟁 콘텐츠 공백**.
- **사용자 전략 확정**: 네이버쇼핑·쿠팡은 가격경쟁이라 승산 없음 → **자사몰 홍보로 집중**(자사몰에만 방문설치·원격지원·구축사례를 표현할 수 있음). 스마트스토어 30종은 **1번 유지**(관리 부담 낮음, 정리하지 않음).

### ✅ 1단계 — 네이버 스마트플레이스 + 지역 랜딩
- **플레이스 등록 신청 완료(사용자, 심사 중)**. 대표자(김미화)와 계정 명의가 달라도 등록 가능 — 네이버는 **ARS 또는 서류(OCR) 인증**으로 주인 권한을 주고, **직원에게 위임하는 기능도 공식 지원**(고객센터 20470/20521). 사진은 **필수 항목 아님**(반려 사유 아님)이나 순위·전환에 영향.
- **지역 랜딩 신설** `/ansan-siheung-nas/`(page **303**) — 방문 가능 지역을 동 단위까지 명시, 금강다온 지역 사례, 사업장 정보, 지역 FAQ. 푸터·`/setup-service/` 배지에서 내부 링크.
- **LocalBusiness JSON-LD** 추가(`functions.php`, wp_head priority 3) — 주소·좌표(37.3164, 126.8309)·영업시간·`areaServed`(안산·시흥·광명·부천·안양)·`makesOffer`(방문 설치 165,000원). **홈·지역·구축지원·회사소개 4곳만** 출력(중복 방지).

### ✅ 2단계 — 구글 머천트 센터 상품 피드
- **mu-plugin** `data/wp/wp-content/mu-plugins/hs-product-feed.php` — 피드 URL **`https://hsrealty.co.kr/google-merchant.xml`**(rewrite) / `?hs_feed=google`(대체). **81종**(공개 82종 중 서비스 상품 제외), 6시간 캐시 + 상품 수정 시 자동 무효화, 응답 0.15초.
  - 자동 제외: 비공개·카탈로그 숨김(단종 포함), `구축 지원` 카테고리, **구매 불가**(500만 초과 문의전환 = 정책 위반 방지), 대표이미지 없는 상품.
  - ⚠️ **`identifier_exists: no` 를 넣으면 안 됨** — 그 값은 '식별자가 하나도 없다'는 선언이라 `brand`+`mpn`을 함께 보내면 **모순으로 반려**됨. GTIN 확보 전까지는 brand+mpn 만 전송.
  - ⚠️ 설명은 짧은설명/상세설명 중 **긴 쪽** 사용 — 상품 절반이 짧은설명 한 줄이라 그대로 쓰면 피드 품질이 전부 그 수준으로 떨어짐(중앙값 266자 확보).
  - **GTIN 대응**: `HS_FEED_GTIN_MAP`(`wp-content/hs-feed-gtin.json`, SKU=>GTIN)만 채우면 `g:gtin` 자동 출력. **코드 수정 불필요.**
- **구글 수집 확인**: `google-xrawler`가 13:36 KST 에 200 응답 수신(로그상 10,614B 는 **gzip 압축 크기**, 원본 132,011B — 실측 대조 완료). 직후 **Googlebot-Image 68건** 크롤 = 머천트가 상품을 실제로 처리 중이라는 신호.
- **EAN(GTIN) 확보**: 시놀로지 공식 사이트·SK 단가표(260601/260803)·네이버 일괄등록 양식·스마트스토어 등록본·공급사 CDN 상세 HTML·**상세 이미지 OCR**까지 전수 확인했으나 **전부 없음** → SK네트웍스 담당자(max239@sk.com)에게 **요청 메일 발송**(참조 ceo@realty99.co.kr, 발신 hs@hsrealty.co.kr, wp_mail 경유).

### ✅ 검색 결과 클릭률(CTR) 개선
- 상품 meta description 을 **가격·무료배송·세금계산서·안산/시흥 방문설치·전화번호**가 앞에 오도록 자동 생성(`hs_seo_desc_for()`). 예: `정품 1,313,000원(VAT 포함) · 전국 무료배송 · 세금계산서 발행. … 안산·시흥 NAS 방문 설치 지원 · 031-520-5552`(101자).
- 상품 페이지 **제목 단축** — 사이트명이 길어 모델명이 잘리던 것을 `– 현성리얼티`로(`document_title_parts`, 상품에만 적용). 백업 `_theme_bak/functions.php.bak.20260809meta`.

### ✅ 3단계 — hsrealty 자체 블로그 개설 + 콘텐츠 11편
- **블로그 신설**: `/blog/`(page **305** `NAS 기술 블로그`, `page_for_posts` 지정), 카테고리 `NAS 가이드`(term **42**, 기본 카테고리), 주 메뉴 `블로그`(position 5). 글 공용 CSS 는 자식테마 `style.css` 로 이동(ver **1.2.0**, `.hs-post`) — 글마다 `<style>` 중복 방지.
- **blog.wonrealty.kr → hsrealty 글 3편 이전(복사 아님)**: 테일스케일 통합망 가이드·시놀로지 NAS 3년 실사용기·부동산 사무실 NAS 도입기. **동일 slug 유지 + 301 리다이렉트**(blogwr mu-plugin `blogwr-moved-redirects.php`), 이미지는 hsrealty 미디어로 복제 후 본문 URL 교체, 원본은 휴지통(복구 가능).
  - 판단 근거: 이전 전 GSC 확인 결과 3편 모두 **노출 상위 15위 밖(3회 이하)** = 잃을 SEO 자산이 거의 없어 지금이 최적 시점.
  - 리드 마그넷 CTA 의 `utm_source=blog_wonrealty` → **`hsrealty_blog`로 정정**(같은 도메인 안에서 발생한 신청이 타 사이트發로 집계되는 것 방지).
- **신규 1편 발행**: `/nas-install-diy-or-outsource/` 「사무실 NAS 설치, 직접 할까 맡길까 — 판단 기준 5가지」(3,762자).
- **7편 예약 발행 등록** — 매일 **09:00 KST** 1편씩(8/10~8/16): 설치비용·5인 견적·속도 문제·이전 방법·외부접속·헤놀로지 비교·Active Backup. 스크립트 `hsrealty-import/schedule_posts.php` + `hsrealty-import/posts/p2~p8.html`.
- ⚠️ **WP 예약 발행은 방문이 있어야 실행됨** — 하루 방문자 2~10명이라 정시 발행 불가 → **호스트 크론 등록**: `*/15 * * * * curl -sS -o /dev/null -m 30 "https://hsrealty.co.kr/wp-cron.php?doing_wp_cron"` (ausqueen crontab). 예약 발행뿐 아니라 **WooCommerce 주문 처리·메일 발송 예약 작업도 함께 정상화**됨.

### ⚠️ 이번에 겪은 함정 (재발 방지)
- **CSS 이스케이프 금지** — 본문에 `content:"\2713"` 같은 CSS 이스케이프를 쓰면 `wp_update_post()`의 `wp_unslash()`가 백슬래시를 제거해 **숫자 "2713"이 그대로 출력**됨. 반드시 실제 문자(`✓`, `–`)를 쓸 것.
- **클래스명 충돌** — 자식테마가 홈 히어로용으로 `.hs-hero`를 이미 쓰고 있어(2열 grid), 페이지 본문에서 같은 이름을 쓰면 레이아웃이 깨짐 → `.hs-vhero`로 개명. 본문용 클래스는 테마 CSS와 겹치는지 먼저 확인할 것.
- **어두운 섹션의 색 상속** — `/nas-guide/`의 `.bg-nv{color:#dbe4ee}`가 그 안의 **흰색 카드까지 상속**돼 체크리스트가 흰 바탕에 연회색으로 보이던 것 수정(`.hs-guide .checks li`, `.bg-nv .card`에 `color:var(--ink)` 지정).

### ⏳ 대기·후속
- 네이버 플레이스 **심사 결과** / ~~구글 머천트 첫 처리 결과~~(✅ 8/10 확인) / SK **EAN 회신**.
- 8/16 예약분 소진 후 다음 콘텐츠 주제 선정 필요(자동 생성 파이프라인은 기술 콘텐츠 정확도 문제로 보류 권고).
- ~~상품 상세설명 44종이 300자 미만~~ — ✅ **2026-08-10 43종 보강 완료**(아래 참조).

## 2026-08-10 작업 이력 — hsrealty 상품 상세 보강 + IndexNow + 머천트 피드 정비
커밋 `2b3288d`(hsrealty, push 완료). 사전 백업: DB `db_predump/hsrealty_mariadb_20260810.sql.gz`, 테마 `_theme_bak/{style.css,functions.php}.bak.20260810*`, 피드 `_mu_bak/hs-product-feed.php.bak.20260810gpc`.

### ✅ 상품 상세설명 43종 보강 — 공개 88종 전부 300자 이상
- **왜 이 43종이 우선이었나**: GSC 실측상 **노출을 만드는 검색어가 전부 영문 모델번호**(`d4es03-16g`·`e10g30-t2`·`d4es02-4g` 등)인데, 그 상품들이 정확히 **본문 250자짜리 템플릿**이었고 순위도 6~11위(1페이지 하단~2페이지)라 끌어올릴 여지가 컸음. 한글 키워드 노출은 여전히 0.
- 대상: 메모리 13 · 소프트웨어 라이선스 13 · 네트워크/어댑터 카드 7 · 레일킷 5 · SSD 3 · 보증 연장 2. **250자대 → 754~1,243자**.
- **내용은 시놀로지 공식 페이지에서 2026-08-10 확인한 것만 사용**. 메모리는 모델별 **호환 NAS 전체 목록**(DS925+·DS725+·RS826+ 등 — 검색 유입에 이게 핵심), 네트워크 카드는 포트·PCIe 세대·요구 DSM 버전, 레일킷은 **랙 마운팅 깊이**(RKS-01/04 553~834 · RKS-02 610~890 · RKS-03 670~940 · RKM114 고정형 570~720/810), 라이선스는 영구/기간 구분·계정 계산법·활성화 절차. ⚠️ **확인 안 된 수치는 적지 않음**(SNV5420 용량별 TBW, D4ES03 계열 동작 속도 등).
- 스크립트: `hsrealty-import/spec_enrich.php` + `spec_enrich.json`(멱등, `<!--HS_SPEC_START/END-->` 마커 구간 교체). **되돌리기 `spec_revert.php`** — json 에 원본 43종 전문 보관.
- 스타일은 본문마다 `<style>` 을 박던 기존 `sk-xl` 방식과 달리 **자식테마 `.hs-spec` 으로 분리**(43개 페이지 CSS 중복 방지).
- ⚠️ **자식테마 버전 정합 문제 발견·수정**: `style.css` 헤더는 1.2.0인데 `functions.php` enqueue 는 **1.1.5로 방치**돼 있었음 → 08-09에 추가한 블로그 글 CSS(`.hs-post`)가 재방문자 브라우저에서 갱신 안 됐을 가능성. **양쪽 1.3.0으로 동기화**. 앞으로 style.css 수정 시 enqueue 버전도 같이 올릴 것.

### ✅ IndexNow 도입 (mu-plugin `hs-indexnow.php`)
- 키 **`8002411989c12cdb09b350a046a35b8c`** (hsrealty 전용, blogwr 키와 별개). 키 파일 = 웹루트 `data/wp/<키>.txt`(내용은 키 문자열 자체) — **gitignore 대상이라 서버 재구축 시 mu-plugin 의 `HS_INDEXNOW_KEY` 값으로 같은 이름 파일을 다시 만들어야 함**.
- 엔드포인트 2개(`api.indexnow.org`=빙 연합 · `searchadvisor.naver.com`=네이버). **초기 106 URL 제출 완료**(빙 202 / 네이버 200). 이후 상품·글·페이지 발행/수정 시 자동 통지, URL당 10분 쿨다운.
- ⚠️ **통지는 요청 경로가 아니라 크론에서 보낸다**(`wp_schedule_single_event`, 60초 뒤). 주문 처리 중에도 상품 저장이 일어나는데 거기서 외부 HTTP 를 동기 호출하면 **07-22 주문 메일 동기 발송으로 결제창이 2분 멈췄던 것과 같은 사고**가 남. 15분 크론(`wp-cron.php` curl)이 이미 있어 정상 실행됨.
- 수동 일괄 재제출: `sudo docker compose --profile cli run --rm wpcli eval 'hs_indexnow_submit_all();'`
- ※ **구글은 IndexNow 미참여** — 실효는 네이버·빙. 네이버 유입 0인 현 상황에 맞춘 선택.

### ✅ 구글 머천트 피드 정비 — 87 → **85종**
- **`google_product_category` 추가(85종 전부)**. 없으면 구글이 상품명으로 자동 분류하는데 "Synology D4ES03-16G" 류는 오분류되기 쉬움. 매핑(term_id→구글ID): IP카메라21→362 · 메모리카드40→3387 · 메모리33→1733 · 네트워크카드35→290 · 라우터31→5497 · 레일킷34→293 · 소프트웨어16→313 · HDD37/SSD36/외장SSD23→380 · DiskStation26/RackStation27/올인원25/확장유닛29→**5269**(Network Storage Systems). **M2D18·M2D20 은 SKU 예외 → 505299**(쇼핑몰 분류상 네트워크 카드지만 실제로는 M.2 어댑터). 분류표 출처 = Google Product Taxonomy 2021-09-21(`taxonomy-with-ids.en-US.txt`, **ko-KR with-ids 는 404** — ID는 언어 무관이라 숫자로 전송).
- **보증 연장(EW201·EW202) 피드 제외**(사용자 결정) — 하드웨어가 아니라 **서비스 플랜이라 구글 분류표에 대응 항목 자체가 없고** 쇼핑 정책 취급 대상이 아님(계정 리스크). `HS_FEED_EXCLUDE_CATS` 에 추가. ⚠️ 한글 카테고리 슬러그는 **URL 인코딩된 형태**로 저장되므로 `%eb%b3%b4%ec%a6%9d-%ec%97%b0%ec%9e%a5` 를 그대로 넣어야 매칭됨. **쇼핑몰에서는 그대로 판매됨**(publish·구매가능 확인).
- 결과: 설명 **중앙값 266자 → 932자**, 300자 미만 0종. 배송(`g:shipping` KR·0원)·brand·mpn·product_type 은 전 상품 유지. **GTIN 0종**(SK 회신 대기 — 받으면 `wp-content/hs-feed-gtin.json` 에 `{"SKU":"바코드"}` 넣기만 하면 코드 수정 없이 반영).

### 📊 머천트 센터 실측(2026-08-10, 사용자 확인)
- 판매자 센터 ID **5837599712** / 계정명 "시놀로지 NAS 판매 전문". **"확인 필요" 탭 비어 있음 = 오류·거부 0건.**
- 대부분 상태가 **"제한적(Limited)"** — 오류가 없는 상태의 "제한적"은 사실상 **GTIN 누락**이 원인. 거부가 아니라 일부 쇼핑 기능 제한이며 무료 리스팅 노출은 됨. **SK EAN 받기 전엔 서버에서 해소 불가.**
- **✅ 사용자가 배송·반품 정책 등록 완료**: 배송=대한민국 전체·**0원**(피드 값과 일치해야 함, 다르면 불일치로 거부)·처리 1~2일·배송 1~3일 / 반품=**7일**·단순변심 고객부담·정책 URL `https://hsrealty.co.kr/refund-returns/`.
- 마지막 가져오기 8/10 00:00 기준 **81종** — 오늘 작업(보강·분류·제외) 반영 전 숫자. **다음 크롤 후 85종이 되면 정상**. 84 이하면 재점검 필요.

### 📊 GSC 추이(hsrealty, 2026-08-09까지)
- 최근 28일 노출 275·클릭 6(CTR 2.18%·평균순위 9.6). **최근 7일 104 vs 직전 7일 79**(+32%), 클릭 0→2.
- 기기별 **데스크톱 246 : 모바일 28** — 검색어가 전부 모델번호(B2B 성격)라 자연스러운 편중.
- 조회 스크립트는 realty99 의 `~/scripts/.ga4_service_account.json` 재사용(서비스계정이 hsrealty 속성에 **siteFullUser**). 1회성 조회 스크립트는 세션 스크래치패드.
- ✅ **예약 발행 정상 작동 확인** — 8/10 09:00 글(id 314) 자동 발행됨(08-09 등록한 15분 wp-cron 크론이 실효). 8/16까지 6편 대기(id 315~320).

### ✅ 검색광고 준비 — 선결과제 2건 처리(커밋 `715baee`)
사용자가 검색광고 집행을 원해 검토. **실행 계획 문서(아티팩트)**: https://claude.ai/code/artifact/3811ce78-c84f-4209-92a6-0929375e6c67
- **⚠️ 검색량 실측 결론(네이버 데이터랩 1년)**: "나스 일반" 최고점 100 기준 → 나스 47~60 · 시놀로지 15~16 · 모델명 8~10 · 백업/파일서버 5 · **나스 설치/구축 0.35(시놀로지의 1/45)** · **사무실/기업용 나스 0.006(사실상 0)** · **안산·시흥 전산 데이터 없음**. → **우리 차별점인 방문설치·지역 키워드는 광고를 걸어도 노출될 검색이 없음.** 물량은 상품 키워드뿐이고 그 자리는 가격비교와 경쟁. 이 판단은 07-12·08-09 진단과 일치(재검토 불필요).
- **채널 권고 = 구글 쇼핑 우선**(피드 재활용·모델번호 검색에 직접 붙음·무료 리스팅과 동일 피드). 네이버 파워링크는 구글 결과 본 뒤. 예산 월 30만원(사용자 결정)을 둘로 쪼개면 양쪽 다 데이터 부족.
- **손익분기 CPC**(노출가÷1.372=공급가별도, 전환율 0.5% 가정): DS925+ 약 1,200원 · DS725+ 약 1,100원 · D4ES03-16G 약 1,600원 · **D4ES02-4G 약 350원**. → 평균 CPC 1,000원 초과 시 저가 상품군은 역마진.
- **✅ ① 상품 이미지 500×500 규격 보정(42종 → 85종 전부 충족)**: ⚠️ **구글이 2026-04부터 최소 해상도를 500×500으로 상향** — 700×420(25) · 316×316(13) · 568×220(4)이 미달이라 쇼핑 광고 시 거부될 상태였음. **원본 자체가 그 크기**(축소본 아님, `original_image` 0건)라 더 큰 파일이 없음 → **긴 변 기준 정사각 캔버스 + 흰 배경 패딩**(업스케일 없음=화질 손실 없음, 원본이 전부 흰 배경 제품컷이라 이질감 없음). 316×316 아이콘류만 500으로 Lanczos 확대. **새 파일 `uploads/hsrealty-sq/`로 만들고 대표이미지 교체**(덮어쓰기 아님 → URL이 바뀌어 구글이 확실히 재크롤, 원본 첨부는 보존). 스크립트 `img_sq_apply.php`(멱등, 파일당 첨부 1개만 생성)·`img_sq_revert.php`·`img_sq.json`. 생성은 일회용 `python:3.12-slim`+Pillow 컨테이너(`make_square.py`). ⚠️ **42종인데 고유 파일 33개** = 라이선스 아이콘을 여러 상품이 공유하기 때문(정상).
- **✅ ② GA4 전환 추적 설치**(자식테마 `functions.php`, 백업 `_theme_bak/functions.php.bak.20260810conv`): 그동안 **GA4가 방문자 수만 세고 전환 이벤트가 0개**여서 무엇이 매출로 이어졌는지 알 수 없었음. 추가 이벤트 = `purchase`(주문완료, 매출액·품목·SKU 포함) · `generate_lead`(리드폼 `?hs_lead=ok` 감지) · `click_to_call`(tel: 클릭 — 고액상품 문의CTA·구축지원이 전부 이 경로) · `add_to_cart`. **임시 주문(id 418)으로 실검증 후 삭제** — 1차 호출에 purchase 정상 출력(value 1,872,000·item_id D4ES03-16G), 2차 호출은 0건(주문 메타 `_hs_ga4_purchase_sent`로 새로고침 중복 차단). ⚠️ **주문 생성 시점 기준**이라 가상계좌 미입금 건도 포함 — 입금 시점 기준으로 바꾸려면 브라우저가 없어 Measurement Protocol 필요. 광고 최적화는 '주문 발생'을 학습해야 해 현 기준 채택.
- **✅ 구글 쇼핑 광고 가동(2026-08-10, 사용자 실행)**: Ads 계정 개설(전문가 모드) → GA4(속성 `545181462` = GA계정 **현성리얼티** `400868430`) 연결 → 머천트 연결 → **캠페인 `NAS shopping 캠페인`** 생성. **표준 쇼핑**(제품 그룹 탭이 있는 것으로 확인 — 실적 최대화면 '애셋 그룹'), 광고그룹 `NAS1` / 제품그룹 `모든 제품`, 일 예산 10,000원, **최대 CPC 300 → 800원으로 수정**(300은 경매에서 밀려 노출 자체가 안 나옴 = 3주 기다려도 데이터 0), 네트워크 검색만(YouTube·디스플레이 해제). **승인 상품 81개 전부 "운영가능/문제 없음"**(거부 0). 81 vs 피드 85 차이는 크롤 시점차 — 8/10 00:00 크롤분이라 EW201/EW202가 아직 남아있고 이미지도 정사각 이전 것. 다음 크롤에 정합.
  - **⏳ 2026-08-31경 판단**: 평균 CPC 1,000원 이하 · 클릭 300회↑ · 주문 2건↑ · 전환당 비용 10만원 이하면 계속. **3주간 입찰가 손대지 말 것**(학습 초기화). 단 **1~2일 내 노출수 0이면 CPC 추가 인상 필요**.
  - ⚠️ **GA4 UI 함정**: 전환 등록은 "이벤트 만들기"(파생 이벤트 생성 기능)가 아니라 **이벤트 목록의 별표 토글**. `purchase`는 GA4가 표준 전자상거래 이벤트로 **자동 등록하며 별표를 켤 수 없는 게 정상**(목록에 있으면 등록된 것). **수집된 이벤트가 관리화면 목록에 뜨기까지 최대 24시간** — 실시간 API로는 즉시 보임(`click_to_call` 1건 실측 확인 = 브라우저 전송 경로 검증 완료). 전환 0건이어도 "클릭수 최대화/수동 CPC"는 정상 작동하므로 캠페인 시작에 지장 없음.
  - 네이버는 계정만 미리 개설(광고 미집행 시 비용 없음). 구글 결과 본 뒤 판단.
- 랜딩: 네이버 파워링크는 **홈**(사용자 결정), 구글 쇼핑은 성격상 **상품 페이지 직행**(정상·전환 유리).

## 2026-08-11 작업 이력 — 구글 광고 첫 성과 + 네이버 파워링크 준비
커밋 `f3823cc`(hsrealty). 실행 계획 문서: https://claude.ai/code/artifact/3811ce78-c84f-4209-92a6-0929375e6c67 (7번 = 네이버)

### 📊 구글 쇼핑 광고 첫 실적(가동 익일)
- **노출 973 · 클릭 15 · CTR 1.54% · 평균 CPC 237원**(비용 약 3,555원). 쇼핑 광고 평균 CTR(0.5~1%)보다 높고, **손익분기 CPC(DS925+ 1,200원 / 최저가 메모리 350원) 대비 크게 여유**. 최대 CPC 800원을 걸었는데 실제 237원 = 경쟁이 예상보다 약함.
- **GA4 실측 유입**: `google/cpc` 세션 4 + `(data not available)` 9(연결 직후 매칭 지연분) ≈ Ads 클릭 15와 근접. 도착 페이지가 **전부 NAS 본체**(DS1825+·DS425+·RS1221+·DiskStation 카테고리) = 마진 큰 쪽으로 유입 중. 전날 세션 3 → 당일 15.
- ⚠️ **일 예산 10,000원 중 3,555원만 소진** — 예산이 모자란 게 아니라 **노출 기회 자체가 그만큼**. "이 시장은 검색량이 작다"는 07-12·08-09 진단이 실측으로 재확인됨. 이 여유가 네이버 병행 결정의 근거가 됨.
- `purchase` 0건은 정상(클릭 15회). **전환율 0.5% 가정 시 200클릭에 1건** — 최소 100클릭 이상 쌓여야 판단 가능.

### ✅ 네이버 파워링크 결정 + 전환 추적 설치
- **채널 판단(2026 검색 점유율 실측)**: 네이버 **60~65%** · 구글 20~30%대 · **다음 3%대** · 빙 3%대. → 네이버는 구글의 2배 이상이라 집행 가치 충분.
- **⛔ 카카오 보류(권고)**: ①**키워드광고(다음)**는 점유율 3%로 네이버에서도 부족한 물량의 1/20 ②**카카오모먼트(비즈보드·디스플레이)**는 검색 의도 없는 노출이라 100만원대 B2B 고관여 상품에 부적합, 이를 살리는 **리타게팅은 방문자 하루 15명이라 모수 미달**(보통 수천 명 필요). → **방문자 하루 수백 명대가 되면 재검토**(카카오 상품 카탈로그 광고가 있어 기존 피드 재활용 가능).
- **⚠️ `wcs.inflow()` 누락 발견·수정** — 기존 네이버 스크립트는 `wcs_add['wa']`+`wcs_do()`만 있어 **방문 수만 세고 광고 클릭(NaPm)이 세션에 연결되지 않던 상태**. 파워링크를 켰어도 "어느 광고로 들어와 무엇을 샀는지"가 안 이어짐.
- **`wcs.trans()` 전환 3종 추가**(purchase / lead / add_to_cart), GA4 전환과 같은 지점. **임시 주문(id 420)으로 실검증 후 삭제**(금액·SKU·수량 정상, 재호출 시 미발송 — 주문 메타 `_hs_naver_conv_sent`).
  - ⚠️ **우선순위 함정**: wcslog.js가 `wp_footer` priority 20에서 로드되므로 전환 호출은 **23**에 둔다. `woocommerce_thankyou` 시점에 바로 부르면 **wcs 객체가 아직 없어 조용히 아무 일도 안 일어남** → thankyou 에서는 주문번호만 담고 출력은 푸터에서.
  - ⚠️ 상품명의 **따옴표 제거 필수**(네이버 스크립트가 깨짐). 전환가치 10억 초과는 자동 치환(2026-01 정책).
- ⏳ **자가설치만으로는 수집 안 됨 — 검수 통과 필요.** 검색광고 계정 공통키가 현재 `HS_NAVER_WA='24d8291b3271480'`과 다르면 교체해야 함(미확인).

### ⚠️ 사업자 분리 확인 (광고 계정 개설 시 중요)
사이트 푸터 실측으로 **두 사업체가 완전히 별개**임을 확인:
- **hsrealty.co.kr** = 현성리얼티, 대표 **김미화**, 사업자 **830-88-03629**(법인), 통신판매업 제2026-경기안산-1395호
- **realty99.co.kr** = 금강다온공인중개사사무소, 대표 **원유호**, 사업자 **781-03-02961**(개인)
- → **광고 계정을 공유하면 안 됨**(세금계산서가 잘못된 사업자로 발행되어 매입세액 공제 불가 + 비즈머니 혼용). 네이버는 **한 네이버 아이디로 광고계정 추가 생성** 가능하므로 로그인은 그대로 두고 계정만 분리.
- ✅ **구글 Ads 결제 프로필 세금정보 = 830-88-03629 확인 완료**(정상). GA4도 이미 별도 계정 "현성리얼티"(400868430)라 분리돼 있음.

### ⏳ 네이버 진행 상태 (2026-08-11 기준)
**네이버는 단계가 순차 종속** — 비즈채널 검수 → 전환 추적 신청 → 전환 검수 → 캠페인 생성. 앞 단계가 끝나야 다음이 열린다.
1. ✅ 광고계정 개설 + 자동충전 등록(사업자 830-88-03629)
2. ⏳ **비즈채널 등록 = "검토중"**(영업일 1일 내외) — 이게 끝나야 전환 추적 신청 가능. 미완 상태에서 신청하면 "신청 가능한 사이트가 없습니다" 팝업.
3. ⏭️ 전환 추적 신청 — ⚠️ **메뉴명이 "프리미엄 로그분석" → 「도구 > 전환 추적 관리」로 바뀜**(표에 "네이버 공통키" 열이 있는 화면). 신청 시 **설치 방식은 반드시 "자가설치"** — 설치대행은 FTP·관리자 접근 정보를 요구하므로 절대 금지(이미 자체 설치 완료).
4. ⏭️ 데이터 검수 요청(안내 메일의 버튼). 담당자 `031-520-5552`, 전환유형 구매·신청·장바구니, 테스트 키워드 `시놀로지 나스`.
5. ⏭️ 파워링크 캠페인 — 일 5,000원(월 약 15만원, 구글 여유분 내), 입찰 100~300원 시작(최소 70원). 키워드는 **모델명 위주**(DS925+·DS725+·DS1825+·DS425+·RS1221+ — 구글에서 실제 유입된 것) + 브랜드(시놀로지 나스) + 용도(나스 설치·사무실 나스). "나스" 단독은 회피(비싸고 무관 검색 섞임).
- 📌 **자동충전 주의**: 실제 상한은 충전액이 아니라 **캠페인 일 예산**. 반드시 일 5,000원 설정할 것. 첫 충전은 10만원 이하 권장.
- 📌 검증 도구: 전환 추적 관리 화면의 **"네이버 전환 스크립트 어시스턴트"**로 설치 상태 자가 점검 가능.

### ✅ realty99(금강다온) 광고 점검 — 전화 클릭 추적 + 파워링크 키워드 전면 재구성
※ 상세는 메모리 `project_realty99_powerlink.md`. 여기엔 서버 작업분만 기록.
- **전화 클릭 추적 배포**(daon 커밋 `74f0e66`, **push 미완**): `frontend/src/components/analytics/PhoneClickTracker.tsx`(client)를 `app/layout.tsx`에 상시 마운트. 부동산의 실제 전환은 전화인데 `kakao_click`·`form_start`는 잡히고 **전화만 빠져 있었음**. 전화번호가 Footer·about·privacy·플로팅버튼에 흩어져 있어 **document 캡처 단계에서 한 번만** 잡음(새 페이지 추가돼도 무수정). `/admin`은 제외(직원이 고객에게 거는 전화). 이벤트 `click_to_call {phone, page_path}` — 번호로 중개(031-404-7600)/경매(031-520-5552) 구분됨. **실시간 API로 1건 실측 검증 완료.**
  - 배포: `docker compose build frontend && up -d frontend` 후 **`docker exec realty99_nginx nginx -s reload`**(컨테이너 재생성 시 nginx가 옛 IP를 봐서 502 — hyunsung과 동일 함정).
  - ⚠️ 검증 시 HTML에서 청크 URL을 정규식으로 긁으면 **`chunks/app/` 하위 경로를 놓침**. 컨테이너 내 `/app/.next/static`에서 grep하는 편이 확실.
- **realty99 광고 실태**: 30일 세션 1,637 중 **direct 89%**, 네이버 광고 유입(`ad.search.naver.com`) **월 1~2세션**, 구글 cpc 5~12. 광고비 70만원→10만원 축소했는데 **사이트 유입은 오히려 증가**(7월 767 → 8월 11일까지 877).
  - ⚠️ **채널별 측정 지점을 섞으면 안 됨**: 네이버 **부동산 매물광고**(`fin.land.naver.com/realtor/hyunsung567`)와 **플레이스**는 사이트로 오지 않으므로 GA4에 안 잡히는 게 정상 — 각각 부동산 파트너센터·스마트플레이스 통계에서 봐야 함. GA4로 판단 가능한 건 **파워링크와 구글 Ads뿐**.
  - **플레이스 광고 요일·시간·지역 확대**(사용자 진행): 일요일·야간을 빼두고 있었는데 GA4 실측상 **일요일 14.1%(평일과 동일)·21시 5.5%**로 오히려 활발. 지역도 서울 49.9%·시흥 8.5%·인천 7.5%라 시흥 인근 한정은 근거가 약함. 설정은 광고그룹 단위(`입찰가/노출설정` 탭=요일·시간, `정보관리`=지역).

- **✅ 파워링크 키워드 635개 등록 완료(2026-08-11 저녁, 사용자)** — 기존 87개 전량 삭제 후 재등록, 입찰가 200원 균일(사용자 결정). 산출물·재생성 스크립트는 `/mnt/nas/temp/파워링크키워드_20260811/`, 상세는 메모리 `project_realty99_powerlink.md`. **2~3주 뒤 클릭이 실제 발생한 키워드만 입찰가 인상**할 것.

### ⏳ realty99 구글 Ads 점검 — 진행 중(PC 클로드 코드로 이어받기)
**인수인계문**: `/mnt/nas/temp/구글Ads_인수인계_20260811.txt` (그대로 붙여넣으면 됨. 판단 근거 수치까지 포함)
- **계정**: 금강 다온 공인중개사사무소 `171-158-0542`, 로그인 `hyunsungrealty@gmail.com`. **hsrealty와 별개 사업자**(금강다온 781-03-02961).
- **30일 실적**: 클릭 412 · 노출 5.37만 · 평균 CPC ₩734 · **비용 ₩30.2만**. ⚠️ 사용자가 앞서 말한 "월 10만원"은 네이버였고 **구글은 별도 30만원**.
- **캠페인 3개**: `금강다온캠페인`(6천원/일·검색·일시중지) / `공인중개사사무소방문`(9천원/일·**PMax**·타겟CPA·**전환 99**·예산제약) / `금강다온홈페이지방문`(2만원/일·검색·타겟CPA·**전환 0**·**광고 효력 나쁨**).
  - ⚠️ **예산 배분이 거꾸로** — 전환 내는 쪽은 예산에 막히고, 전환 0인 쪽이 예산 2/3를 잡음. 계정 일 예산 29,000원인데 **실제 지출은 하루 1만원**(2/3가 안 쓰임).
- **⚠️ 전환 99건의 정체 = 통화 + 길찾기 + 페이지조회.** 홈페이지 문의는 **0건**이었음(같은 기간 GA4 문의 4건과 25배 차이의 원인). 전환 목표 중 **`견적요청`·`다운로드`가 계정-기본인데 둘 다 "잘못된 구성"** → 타겟 CPA가 고장난 기준으로 학습 중이었음. `페이지조회`·`참여`가 전환으로 켜져 있어 숫자가 부풀려짐.
- **계정 설정 실측**: 자동 태그 켜짐(정상) · 통화 보고서 사용 중 · 제외 키워드 없음. ⚠️ **자동 적용은 이미 전부 꺼져 있었음**(체크박스 21개 전부 해제 — 계정 설정 화면의 "디스플레이 네트워크 추가 기능 외 추천 유형 5개 사용"은 *사용 가능한 유형* 표기이지 활성 상태가 아니었다. 8/11 PC 세션에서 개별 확인).
- **GA4 대조**: Ads 클릭 412회(30일) vs GA4 cpc 세션 **17회(90일)**. cpc 랜딩은 **전부 홈(/)**, 이탈 58~80%, 체류 4~29초. 전체 세션의 **1.0%**, direct가 89%.
- **✅ 완료**: GA4에 주요 이벤트 3개 등록(`click_to_call`·`kakao_click`·`proxy_inquiry_submit`). ※ `sell_inquiry_submit`은 코드에 있으나 28일간 발생 0이라 목록에 없음 — 첫 문의 후 별표.
- **⛔ 막힌 지점**: Ads에서 GA4 이벤트를 전환으로 가져오는 마법사가 **"새 전환 액션이 저장되지 않았습니다"** 반복(카테고리·값·횟수 어떻게 바꿔도 동일). GA4 별표를 당일 켜서 **Ads 동기화 미완**으로 추정. → 재시도 전에 `목표 > 전환 > 모든 전환 액션 보기`에서 **이미 생성됐는지 먼저 확인**(구글 마법사가 오류를 뱉고도 만들어 두는 경우 있음).
- **✅ 2026-08-11 저녁 PC 세션(브라우저 조작)에서 처리 완료**:
  - `금강다온홈페이지방문` 입찰 **타겟CPA → 클릭수 최대화 + 최대 CPC ₩1,000**, 예산 **₩20,000 → ₩10,000/일**
  - `공인중개사사무소방문`(PMax) **일시중지**(삭제 아님)
  - 자동 적용 — 확인 결과 이미 전부 꺼져 있어 변경 없음
  - 전환 액션 목록 확인 → GA4 가져오기 액션 **0개**(마법사가 실제로 저장 실패한 것이 맞음)
  - **현재 운영 캠페인은 `금강다온홈페이지방문` 하나뿐**(검색·클릭수최대화·₩10,000/일). 계정 일 예산도 ₩10,000.
- **⛔ 여전히 막힘 — GA4 전환 가져오기**: 3개 일괄도, `click_to_call` 1개만도 저장 실패. **특정 이벤트·카테고리 문제가 아니라 서버측 저장 API 문제**로 확인됨. GA4 주요 이벤트를 당일 켠 탓에 백엔드 동기화가 안 끝난 것으로 추정 → **24시간 후 재시도**. 경로: 목표 → 전환 → 전환 액션 만들기 → "연결된 계정에서 여러 전환 액션 만들기" → realty99_daon. 카테고리 매핑은 `click_to_call`→전화 통화 리드, `kakao_click`→연락처, `proxy_inquiry_submit`→리드 양식 제출.
- **⚠️ 지금 구조의 리스크**: PMax(전환 99건을 내던 유일한 캠페인)를 껐고, 남은 `금강다온홈페이지방문`은 **"광고 효력이 나쁨"** 상태라 노출이 거의 안 나올 수 있음. → **광고 소재(제목·설명) 보강이 다음 우선순위**.
- ⚠️ **Google Ads는 이 서버 세션에서 조작 불가** — 브라우저 제어 수단이 없고 API는 개발자 토큰 심사(수일~수주) 필요. **브라우저 조작이 가능한 PC 세션에 넘길 것**(2026-08-11 실제로 그렇게 처리함). GA4는 서비스계정에 **편집자 권한**을 주면 API로 처리 가능(현재는 읽기 전용).

## 2026-08-12 작업 이력 — realty99 구글 광고 소재 보강 (PC 세션 브라우저 조작)

### ✅ 광고 소재 등록 완료 — "광고 효력이 나쁨" 해소
- **⚠️ 광고그룹 구성이 예상과 달랐음**: 기존 `광고그룹 1`의 키워드 23개가 **전부 경매·대리입찰 계열**(법원경매·대리입찰·부천지원경매 등)이고 **중개 키워드는 0개**였음. 즉 "중개와 경매가 섞인 것"이 아니라 **중개 광고그룹 자체가 없던 것**. → `광고그룹 1`을 대리입찰용으로 두고 **신규 `중개` 광고그룹 생성**.
- **대리입찰 그룹**: RSA 제목 15·설명 4 등록(최종 URL `/auction`, 고정 없음) → **광고 효력 "매우 좋음"**, 정책 검토 통과.
- **중개 그룹**: RSA 제목 15·설명 4 등록(최종 URL `/properties`). 키워드가 없으면 게재가 안 되므로 **중개 키워드 15개**(장현지구 아파트·시흥시청역 아파트·시흥 아파트 매매/전세·금강펜테리움·제일풍경채·트리플포레·서희스타힐스·능곡동/군자동 부동산 등, 확장검색)를 함께 추가. 효력은 저장 전 '나쁨'(미충족 항목이 "제목에 인기 키워드 포함" 1개뿐) → 저장 후 '보류중'. **신규 그룹이라 키워드 데이터가 없어 생기는 현상**이므로 1~2일 뒤 재확인.
- 기존 효력 '나쁨' 광고는 **삭제하지 않고 유지**(성과 비교용).
- 소재·재생성 스크립트: `/mnt/nas/temp/금강다온_구글광고소재_20260812.txt` · `build_rsa.py`

### ⚠️ 글자수 함정 — Google Ads 는 한글을 2자로 센다
- 제목 30자 = **한글 15자**, 설명 90자 = **한글 45자**. `len()` 으로 세면 통과처럼 보이지만 실제 등록에서 거부된다.
- 08-12 에 중개 설명 1·2가 **95·97자로 초과**해 현장에서 축약해야 했음. → `build_rsa.py` 에 CJK 2배 계산(`ad_len`)을 넣어 정정하고 전 문구 재검증(초과 0).

### ✅ 확장소재
- **사이트링크 4개는 이미 캠페인 수준에 등록돼 있었고 URL도 일치**(금강다온부동산 매물 보기 `/properties` · 대리입찰 요금안내 `/auction` · 대리입찰 신청하기 `/auction/apply` · 믿을 수 있는 사무소 `/about`). 텍스트만 조금 다르나 **수정하면 심사가 리셋되므로 그대로 둠**.
- **전화번호는 광고그룹 수준 등록이 가능**했음(앞서 "계정당 1개"로 알았던 것 정정). 대리입찰 그룹에 `031-520-5552`(원유호) 신규 등록(검토중), 중개 그룹은 계정 수준 `031-404-7600`(박선영)이 적용됨.

### ✅ GA4 전환 가져오기 — 원인은 **GA4 권한 누락**이었음 (3일 만에 해결)
- ⚠️ **오진 정정**: 3일간 반복된 "새 전환 액션이 저장되지 않았습니다"를 *구글 서버측 문제*로 결론냈으나 **틀렸음**. 실제 원인은 **Ads 로그인 계정 `hyunsungrealty@gmail.com` 에 GA4 속성 권한이 아예 없던 것**. 그 계정으로 GA4에 접속하니 신규 가입 환영 화면이 떴고, 속성 사용자 목록에도 `ausqueen`(관리자)·서비스계정·Ads 링크 역할뿐이었음.
- **해결**: `ausqueen@gmail.com`(GA4 관리자)으로 속성 액세스 관리에서 `hyunsungrealty@gmail.com` 에 **'마케팅 담당자'** 역할 부여 → 즉시 저장 성공.
- 📌 **교훈**: Ads↔GA4 *연결*이 정상이어도, **Ads 로그인 계정 본인에게 GA4 속성 권한이 없으면 전환 가져오기가 실패**한다. 두 서비스의 로그인 계정이 다를 때 먼저 확인할 것. (연결 상태·본인 인증·카테고리·값 설정은 전부 무관했음)
- **생성 완료**: `realty99_daon (web) click_to_call`(전화 통화 리드) · `kakao_click`(연락처/문의) · `proxy_inquiry_submit`(리드 양식 제출) — 모두 기본 전환 액션.
- **캠페인 전환 목표 변경**: `금강다온홈페이지방문` 을 **리드 양식 제출 + 전화 통화 리드 + 문의**로 지정, 기존 `견적 요청`(통화만 집계·잘못된 구성) 해제.

### 📊 입찰 전략 판단 근거 (전환 축적 속도)
- realty99 GA4 전환 대상 이벤트 **30일 합계 31건**(kakao_click 26 · proxy_inquiry_submit 4 · click_to_call 1[08-11 설치라 하루치] · sell_inquiry_submit 0).
- ⚠️ **그러나 이건 전체 트래픽 기준**이다. Ads 전환은 **광고 클릭에 귀속된 것만** 센다. 광고 유입은 90일 17세션(전체의 1.0%)뿐이라, **Ads 기준 전환 30건은 훨씬 오래 걸린다.**
- → **"전환 30건 쌓이면 전환수 최대화로 전환"은 당분간 적용 불가.** 클릭수 최대화를 유지하고, 먼저 **광고 유입 자체를 늘리는 것**(소재 개선·키워드 정비)이 순서.

### ⏭️ 남은 것
- 중개 광고그룹 **광고 효력 재확인**(신규 그룹이라 '보류중'이었음)
- 캠페인의 **업체명 애셋 "금강다온공인중개사사무소"가 '비승인(관련성 없는 업체 이름)'** 상태 — 재제출 검토
- 전환이 실제로 Ads 에 들어오는지 며칠 뒤 확인(광고 유입 전환이라 숫자는 작을 것)

## 미완료 항목
- [x] ~~PDF 파일 동기화~~ — 완료 (498/498)
- [x] ~~certbot 자동 갱신 설정~~ — 완료 (systemd timer)
- [ ] VWorld API 도메인 인증 (wonrealty.kr 등록 필요 — map.vworld.kr 개발자 콘솔)
- [~] (권장) SSH 하드닝 — **fail2ban 완료(2026-07-08)**, **22번 포트 공인 IP 화이트리스트 전환 완료(2026-08-05, 아래 작업이력 참조)** — 이제 전체 인터넷 노출은 아니지만, `PasswordAuthentication no`는 여전히 **보류**(사용자 PC 공개키 등록·검증 후 진행. 현재 ausqueen 등록키는 realty99→hyunsung 1개뿐이라 지금 끄면 락아웃 위험)
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
