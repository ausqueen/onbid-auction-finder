#!/bin/bash
# Let's Encrypt 인증서 자동 갱신 (Docker certbot webroot 방식)
# wonrealty.kr / www.wonrealty.kr — nginx webroot: /var/www/certbot
set -euo pipefail
PROJECT_DIR=/opt/onbid-auction-finder
LOG=/var/log/certbot-renew.log
cd "$PROJECT_DIR"

echo "===== $(date '+%F %T %Z') 인증서 갱신 시도 =====" >> "$LOG"
# 30일 이내 만료 시에만 실제 갱신됨 (certbot 기본 동작)
if docker compose run --rm certbot renew >> "$LOG" 2>&1; then
    # 갱신 성공 시 nginx 리로드로 새 인증서 반영
    docker compose exec -T nginx nginx -s reload >> "$LOG" 2>&1 || \
        docker compose restart nginx >> "$LOG" 2>&1
    echo "$(date '+%F %T %Z') 갱신 절차 완료 + nginx 리로드" >> "$LOG"
else
    echo "$(date '+%F %T %Z') [ERROR] 갱신 실패 — 로그 확인 필요" >> "$LOG"
    exit 1
fi
