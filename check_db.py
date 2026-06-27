import sqlite3
conn = sqlite3.connect('backend/onbid.db')
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"{t[0]}: {count}건")

# 온비드 properties 샘플 확인
try:
    rows = cur.execute("SELECT id, cltr_mng_no, nm, low_price, addr FROM properties LIMIT 5").fetchall()
    print("\n[properties 샘플]")
    for r in rows:
        print(r)
except Exception as e:
    print(f"properties 조회 실패: {e}")

conn.close()
