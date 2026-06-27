import sqlite3
import os

db_path = 'backend/onbid.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("--- Latest 10 Bankruptcy Properties ---")
rows = cur.execute("""
    SELECT id, board_no, title, attachment_filename, is_analyzed, ai_summary, min_price, address, asset_type
    FROM bankruptcy_properties 
    ORDER BY board_no DESC 
    LIMIT 10
""").fetchall()

for r in rows:
    print(f"ID: {r[0]} | BoardNo: {r[1]} | Title: {r[2][:30]}")
    print(f"  Attachment: {r[3]}")
    print(f"  Analyzed: {r[4]} | Summary: {r[5]}")
    print(f"  MinPrice: {r[6]} | Address: {r[7]} | AssetType: {r[8]}")
    print("-" * 50)

# Also check how many properties have is_analyzed = 1 but empty/null ai_summary
empty_count = cur.execute("""
    SELECT COUNT(*) 
    FROM bankruptcy_properties 
    WHERE is_analyzed = 1 
      AND ai_summary IS NULL 
      AND (attachment_filename IS NULL OR attachment_filename NOT LIKE '%.hwp')
""").fetchone()[0]
print(f"\nAnalyzed but empty summary (non-HWP): {empty_count}건")

conn.close()
