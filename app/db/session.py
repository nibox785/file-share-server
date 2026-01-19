from sqlalchemy import create_engine
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
        echo=True,  # Log SQL queries (tắt khi deploy)
        connect_args=connect_args
    )
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
        echo=True,           # Log SQL queries (tắt khi deploy)
        connect_args=connect_args
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho models
Base = declarative_base()

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()