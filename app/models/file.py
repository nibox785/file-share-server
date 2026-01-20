from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False, index=True)  # Size in bytes
    file_type = Column(String(50), nullable=False, index=True)  # Extension: .pdf, .jpg, etc
    mime_type = Column(String(100), nullable=True)
    
    # Metadata
    description = Column(String(500), nullable=True)
    is_public = Column(Boolean, default=False, index=True)  # Public or private file
    download_count = Column(Integer, default=0, index=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Foreign key
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationship
    owner = relationship("User", back_populates="files")