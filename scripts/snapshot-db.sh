#!/usr/bin/env bash
#
# onbid SQLite(WAL) 애플리케이션 정합 스냅샷 생성 — ABB 블록 백업(월·수·금 03:00 KST) 직전 실행용.
#
# 목적: WAL 모드 DB는 블록 스냅샷 시 main/-wal/-shm 가 crash-consistent 로만 담긴다.
#       sqlite3 온라인 백업 API(=CLI의 '.backup')로 "단일 파일 정합 사본"을 data/ 안에 만들어 두면
#       ABB 백업 세트에 그 정합 사본이 그대로 포함 → 복원 시 무조건 깨끗한 DB 확보.
# 배치: data/db_snapshots/ (컨테이너 미마운트, ABB 백업 범위 /opt/.../data 안, git ignore 됨).
# 실행: systemd timer(onbid-db-snapshot.timer)가 매일 02:50 KST 호출. 수동: sudo /opt/onbid-auction-finder/scripts/snapshot-db.sh
#
set -euo pipefail

DB="/opt/onbid-auction-finder/data/onbid.db"
SNAP_DIR="/opt/onbid-auction-finder/data/db_snapshots"
KEEP=7                                   # 회전: 최신 N개 timestamped 사본 유지 (ABB 자체 버전관리와 별개 안전망)
LOG="/var/log/onbid-db-snapshot.log"

log() { echo "$(date '+%F %T %z') $*" | tee -a "$LOG" >&2; }

mkdir -p "$SNAP_DIR"

if [[ ! -f "$DB" ]]; then
  log "ERROR: source DB not found: $DB"
  exit 1
fi

TS="$(date '+%Y%m%d-%H%M%S')"
DEST="$SNAP_DIR/onbid-$TS.db"
TMP="$DEST.tmp"

# 온라인 백업 API: source 를 read 트랜잭션으로 페이지 복사 → WAL 정합 보장, 컨테이너 동시 접근 안전.
# 완료 후 dest 에 대해 integrity_check 로 검증. 검증 통과분만 최종 파일로 승격.
python3 - "$DB" "$TMP" <<'PY'
import sqlite3, sys
src_path, dst_path = sys.argv[1], sys.argv[2]
# source 는 기본(RW) 로 열어 read-only WAL 함정(-shm 생성 불가) 회피. backup 은 source 를 읽기만 함.
src = sqlite3.connect(src_path, timeout=60)
dst = sqlite3.connect(dst_path)
with dst:
    src.backup(dst)
ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
n  = dst.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
dst.close(); src.close()
if ok != "ok":
    sys.exit(f"integrity_check FAILED: {ok}")
print(f"integrity ok, tables={n}")
PY

chmod 600 "$TMP"
mv -f "$TMP" "$DEST"
ln -sfn "$(basename "$DEST")" "$SNAP_DIR/onbid-latest.db"
log "snapshot OK: $DEST ($(du -h "$DEST" | cut -f1))"

# 회전: 최신 KEEP 개 초과분 삭제
mapfile -t OLD < <(ls -1t "$SNAP_DIR"/onbid-2*.db 2>/dev/null | tail -n +$((KEEP + 1)))
for f in "${OLD[@]:-}"; do
  [[ -n "$f" ]] || continue
  rm -f -- "$f" && log "rotated out: $f"
done

exit 0
