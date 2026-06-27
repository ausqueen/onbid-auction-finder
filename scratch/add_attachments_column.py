import sqlite3

db_path = 'backend/onbid.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    print("Adding 'attachments' column to 'bankruptcy_properties' table...")
    cur.execute("ALTER TABLE bankruptcy_properties ADD COLUMN attachments TEXT")
    conn.commit()
    print("Column added successfully!")
except Exception as e:
    print(f"Error adding column (it might already exist): {e}")

conn.close()
