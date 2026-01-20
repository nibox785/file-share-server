from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Xác định connect_args dựa trên loại database
db_url = settings.DATABASE_URL

if db_url.startswith("sqlite"):
    # SQLite settings
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        echo=settings.DB_ECHO,
        connect_args=connect_args
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-64000")  # ~64MB cache
        cursor.close()
else:
    # MySQL/PostgreSQL settings
    connect_args = {
        "charset": "utf8mb4",
        "use_unicode": True
    }
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Kiểm tra connection trước khi sử dụng
        pool_recycle=3600,   # Recycle connection sau 1 giờ
        echo=settings.DB_ECHO,
        connect_args=connect_args
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho models
Base = declarative_base()

def ensure_sqlite_indexes():
    """Create indexes for SQLite to speed up common queries."""
    if not db_url.startswith("sqlite"):
        return
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_files_owner_id ON files (owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_files_is_public ON files (is_public)",
        "CREATE INDEX IF NOT EXISTS idx_files_uploaded_at ON files (uploaded_at)",
        "CREATE INDEX IF NOT EXISTS idx_files_file_type ON files (file_type)",
        "CREATE INDEX IF NOT EXISTS idx_files_download_count ON files (download_count)",
        "CREATE INDEX IF NOT EXISTS idx_files_original_filename ON files (original_filename)",
    ]
    with engine.begin() as conn:
        for stmt in index_statements:
            conn.execute(text(stmt))

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()