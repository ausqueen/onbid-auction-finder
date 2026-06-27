from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

# Ensure database and WAL/SHM file permissions for standard users
from .permissions import ensure_file_permissions
db_url = settings.db_url
if db_url.startswith("sqlite:///"):
    db_file_path = db_url.replace("sqlite:///", "")
    ensure_file_permissions(db_file_path)
    ensure_file_permissions(db_file_path + "-wal")
    ensure_file_permissions(db_file_path + "-shm")

engine = create_engine(
    settings.db_url,
    connect_args={
        "check_same_thread": False,  # SQLite 전용
        "timeout": 30,               # DB 잠금 대기 최대 30초
    },
)

# SQLite WAL 모드 활성화 — 읽기/쓰기 동시 접근 시 'database is locked' 방지
@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA busy_timeout=10000")  # 락 대기 10초

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from .models import property as _  # noqa: F401 - 모델 등록
    from .models import bankruptcy as _
    from .models import user as _
    from .models import favorite as _
    from .models import read as _
    Base.metadata.create_all(bind=engine)
