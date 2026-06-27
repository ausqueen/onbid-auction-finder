import sqlite3
import json

db_path = 'backend/onbid.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

rows = cur.execute("SELECT id, title, attachments FROM bankruptcy_properties WHERE id <= 5").fetchall()
for r in rows:
    print(f"ID: {r[0]} | Title: {r[1]}")
    print(f"  Attachments: {r[2]}")
    print("-" * 50)

conn.close()
