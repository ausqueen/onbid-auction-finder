import sqlite3
import os

db_path = 'backend/onbid.db'
if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if users table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
table_exists = cur.fetchone()

if not table_exists:
    print("Table 'users' does not exist in the database.")
else:
    print("--- Users in database ---")
    rows = cur.execute("SELECT id, username, name, email, phone, is_approved, is_superuser, hashed_password FROM users").fetchall()
    for r in rows:
        print(f"ID: {r[0]}")
        print(f"  Username: {r[1]}")
        print(f"  Name: {r[2]}")
        print(f"  Email: {r[3]}")
        print(f"  Phone: {r[4]}")
        print(f"  Is Approved: {r[5]}")
        print(f"  Is Superuser: {r[6]}")
        print(f"  Password Hash: {r[7]}")
        print("-" * 30)

conn.close()
