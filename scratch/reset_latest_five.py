import sqlite3

db_path = 'backend/onbid.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# We reset properties with IDs 1, 2, 3, 4, 5 to be analyzed again.
target_ids = [1, 2, 3, 4, 5]

print("Resetting latest 5 properties in database...")
cur.execute(f"""
    UPDATE bankruptcy_properties 
    SET is_analyzed = 0, 
        ai_summary = NULL, 
        asset_type = NULL, 
        target_property = NULL, 
        address = NULL, 
        min_price = NULL, 
        manager_contact = NULL, 
        sale_deadline = NULL,
        is_recommended = 0
    WHERE id IN ({','.join(map(str, target_ids))})
""")
conn.commit()

# Double check
rows = cur.execute(f"SELECT id, title, is_analyzed FROM bankruptcy_properties WHERE id IN ({','.join(map(str, target_ids))})").fetchall()
for r in rows:
    print(f"ID: {r[0]} | Title: {r[1]} | Analyzed: {r[2]}")

conn.close()
print("Reset complete!")
