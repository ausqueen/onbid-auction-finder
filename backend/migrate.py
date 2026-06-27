import os
import sys

from app.database import engine, Base
from app.models.bankruptcy import BankruptcyProperty # 강제 임포트

def migrate():
    print("Dropping all tables to reset schema...")
    Base.metadata.drop_all(bind=engine)
    print("Re-creating all tables with updated schema (is_recommended added)...")
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
