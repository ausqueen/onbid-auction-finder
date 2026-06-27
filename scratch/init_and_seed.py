import sys
import os

# Add backend directory to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.database import init_db, SessionLocal
from app.models.user import User
from app.api.endpoints.auth import get_password_hash

print("Initializing database (creating tables)...")
init_db()
print("Database initialized successfully.")

print("Checking and seeding root administrator account...")
db = SessionLocal()
try:
    root_user = db.query(User).filter(User.username == "root").first()
    if not root_user:
        print("Root user not found. Creating root user...")
        new_root = User(
            username="root",
            hashed_password=get_password_hash("Realty!@34"),
            name="최고관리자",
            email="root@local.com",
            phone="010-0000-0000",
            is_approved=True,
            is_superuser=True
        )
        db.add(new_root)
        db.commit()
        print("Root user created successfully!")
        print("Name: 최고관리자")
        print("Email: root@local.com")
        print("Phone: 010-0000-0000")
        print("Password: Realty!@34")
    else:
        print("Root user already exists.")
        print(f"Name: {root_user.name}")
        print(f"Email: {root_user.email}")
        print(f"Phone: {root_user.phone}")
        # Let's reset the password to Realty!@34 to be absolutely sure
        root_user.hashed_password = get_password_hash("Realty!@34")
        db.commit()
        print("Password reset to: Realty!@34")
finally:
    db.close()
