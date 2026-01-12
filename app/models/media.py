from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.db.session import Base

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)       
    description = Column(Text, nullable=True)
    filename = Column(String(255), nullable=False)    
    file_path = Column(String(500), nullable=False)  
    media_type = Column(String(50))                 
    uploaded_at = Column(DateTime, default=datetime.utcnow)