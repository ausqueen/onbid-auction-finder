import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'onbid.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM bankruptcy_properties WHERE notice_url LIKE '%33060%'")
print('Deleted target count:', cursor.rowcount)

cursor.execute("DELETE FROM bankruptcy_properties WHERE asset_type IS NULL OR asset_type = 'None' OR ai_summary IS NULL")
print('Deleted empty count:', cursor.rowcount)
conn.commit()
conn.close()
