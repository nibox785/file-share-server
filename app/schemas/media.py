from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MediaBase(BaseModel):
    title: str
    description: Optional[str] = None

class MediaCreate(MediaBase):
    pass

class MediaOut(MediaBase):
    id: int
    filename: str
    file_path: str
    media_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True