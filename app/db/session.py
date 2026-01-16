from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Tạo engine kết nối MySQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Kiểm tra connection trước khi sử dụng
    pool_recycle=3600,   # Recycle connection sau 1 giờ
    echo=True,           # Log SQL queries (tắt khi deploy)
    # MySQL specific settings
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True
    }
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