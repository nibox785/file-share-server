from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# =================================================================
# 1. Base Schema
# =================================================================
class FileBase(BaseModel):
    description: Optional[str] = None
    is_public: bool = False

class FileBase(BaseModel):
    description: Optional[str] = Field(None, max_length=500) 
    is_public: bool = False
# =================================================================
# 2. Input Schemas (Dữ liệu Client gửi lên)
# =================================================================

# Khi update thông tin file (ví dụ sửa mô tả, đổi trạng thái public)
class FileUpdate(FileBase):
    pass

# =================================================================
# 3. Output Schemas (Dữ liệu Server trả về cho Client)
# =================================================================

# Đây là Class quan trọng nhất để map từ SQLAlchemy Model ra JSON
class FileOut(FileBase):
    id: int
    filename: str           # Tên file trên hệ thống (có timestamp)
    original_filename: str  # Tên gốc user upload
    file_path: str          # Đường dẫn lưu file
    file_size: int          # Kích thước (bytes)
    file_type: str          # Đuôi file (.jpg, .pdf)
    mime_type: Optional[str] = None
    download_count: int
    uploaded_at: datetime
    owner_id: int

    # Cấu hình để Pydantic đọc được dữ liệu từ SQLAlchemy Object
    class Config:
        from_attributes = True 

# Schema trả về khi upload thành công
class FileUploadResponse(BaseModel):
    message: str
    file_info: FileOut

# Schema trả về cho chức năng tìm kiếm (Search)
class FileSearchResult(BaseModel):
    total: int
    results: List[FileOut]