from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import shutil
import os
from datetime import datetime
import mimetypes

from app.db.session import get_db
from app.models.file import File as FileModel
from app.models.user import User
from app.schemas.file import FileOut, FileUploadResponse, FileSearchResult
from app.schemas.common import StandardResponse
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter()

# ============================================================================
# NGHIỆP VỤ 0: REGISTER FILE METADATA (sau khi upload TCP)
# ============================================================================

class FileRegisterRequest(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    description: Optional[str] = None
    is_public: bool = False


@router.post("/register", response_model=StandardResponse[FileOut])
def register_file_metadata(
    payload: FileRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Đăng ký metadata file sau khi upload qua TCP
    - File đã tồn tại trong static/uploads
    - Lưu metadata vào database để hiển thị ở danh sách
    """

    file_path = os.path.join(settings.UPLOAD_DIR, payload.filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại trên hệ thống"
        )

    # Tránh duplicate cho cùng owner + filename
    existing = db.query(FileModel).filter(
        FileModel.filename == payload.filename,
        FileModel.owner_id == current_user.id
    ).first()
    if existing:
        return StandardResponse(
            success=True,
            message="File đã được đăng ký trước đó",
            data=existing
        )

    file_ext = os.path.splitext(payload.original_filename)[1].lower()
    if not file_ext:
        file_ext = os.path.splitext(payload.filename)[1].lower()

    mime_type, _ = mimetypes.guess_type(payload.original_filename)

    new_file = FileModel(
        filename=payload.filename,
        original_filename=payload.original_filename,
        file_path=file_path,
        file_size=payload.file_size,
        file_type=file_ext or ".bin",
        mime_type=mime_type,
        description=payload.description,
        is_public=payload.is_public,
        owner_id=current_user.id
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return StandardResponse(
        success=True,
        message="Đăng ký metadata thành công",
        data=new_file
    )

# ============================================================================
# NGHIỆP VỤ 1: UPLOAD FILE (HTTP)
# ============================================================================

@router.post("/upload", response_model=StandardResponse[FileUploadResponse])
async def upload_file_http(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Upload file qua HTTP
    
    - User phải đăng nhập
    - File size tối đa 50MB
    - Chỉ cho phép các file extension hợp lệ
    - Lưu metadata vào database
    - Lưu file vào storage
    """
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File quá lớn. Tối đa {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = settings.get_allowed_extensions_list()
    
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type không được phép. Chỉ cho phép: {', '.join(allowed_exts)}"
        )
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{current_user.id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu file: {str(e)}"
        )
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(file.filename)
    
    # Save metadata to database
    new_file = FileModel(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_ext,
        mime_type=mime_type,
        description=description,
        is_public=is_public,
        owner_id=current_user.id
    )
    
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    
    return FileUploadResponse(
        message=f"File {file.filename} đã được upload thành công",
        file_info=new_file  # Quan trọng: Phải gán object file vừa tạo vào biến file_info
    )

# ============================================================================
# NGHIỆP VỤ 2: DOWNLOAD FILE (HTTP)
# ============================================================================

@router.get("/download/{file_id}")
async def download_file_http(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Download file qua HTTP
    
    - Kiểm tra quyền truy cập (public hoặc owner)
    - Tăng download count
    - Stream file về client
    """
    
    # Get file from database
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại"
        )
    
    # Check permission
    if not file_record.is_public and file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền tải file này"
        )
    
    # Check file exists on disk
    if not os.path.exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại trên hệ thống"
        )
    
    # Increment download count
    file_record.download_count += 1
    db.commit()
    
    # Return file
    return FileResponse(
        path=file_record.file_path,
        filename=file_record.original_filename,
        media_type=file_record.mime_type or 'application/octet-stream'
    )

# ============================================================================
# NGHIỆP VỤ 3: LIST FILES (Xem danh sách file)
# ============================================================================

@router.get("/", response_model=StandardResponse[List[FileOut]])
def list_files(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên file"),
    file_type: Optional[str] = Query(None, description="Lọc theo loại file (.pdf, .jpg, ...)"),
    only_mine: bool = Query(False, description="Chỉ xem file của mình"),
    only_public: bool = Query(False, description="Chỉ xem file public"),
    sort_by: str = Query("newest", enum=["newest", "oldest", "largest", "smallest", "most_downloaded"]),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_total: bool = Query(False, description="Có tính tổng số file hay không"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Xem danh sách file
    
    - Có thể search theo tên
    - Lọc theo loại file
    - Chỉ xem file của mình hoặc file public
    - Sắp xếp theo nhiều tiêu chí
    """
    
    query = db.query(FileModel)
    
    # Filter by permission
    if only_mine:
        query = query.filter(FileModel.owner_id == current_user.id)
    elif only_public:
        query = query.filter(FileModel.is_public == True)
    else:
        # Show: own files + public files
        query = query.filter(
            (FileModel.owner_id == current_user.id) | (FileModel.is_public == True)
        )
    
    # Search by filename
    if search:
        query = query.filter(
            (FileModel.original_filename.contains(search)) |
            (FileModel.description.contains(search))
        )
    
    # Filter by file type
    if file_type:
        query = query.filter(FileModel.file_type == file_type)
    
    # Sort
    if sort_by == "newest":
        query = query.order_by(FileModel.uploaded_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(FileModel.uploaded_at.asc())
    elif sort_by == "largest":
        query = query.order_by(FileModel.file_size.desc())
    elif sort_by == "smallest":
        query = query.order_by(FileModel.file_size.asc())
    elif sort_by == "most_downloaded":
        query = query.order_by(FileModel.download_count.desc())
    
    # Pagination
    files = query.offset(skip).limit(limit).all()
    total = query.count() if include_total else len(files)
    
    return StandardResponse(
        success=True,
        message=f"Tìm thấy {total} file",
        data=files
    )

# ============================================================================
# NGHIỆP VỤ 4: GET FILE INFO (Xem chi tiết file)
# ============================================================================

@router.get("/{file_id}", response_model=StandardResponse[FileOut])
def get_file_info(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Xem thông tin chi tiết file
    """
    
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại"
        )
    
    # Check permission
    if not file_record.is_public and file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem file này"
        )
    
    return StandardResponse(
        success=True,
        message="Lấy thông tin file thành công",
        data=file_record
    )

# ============================================================================
# NGHIỆP VỤ 5: DELETE FILE (Xóa file)
# ============================================================================

@router.delete("/{file_id}", response_model=StandardResponse)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Xóa file
    
    - Chỉ owner mới được xóa
    - Xóa cả file trên disk và database
    """
    
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại"
        )
    
    # Check ownership
    if file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa file này"
        )
    
    # Delete file from disk
    if os.path.exists(file_record.file_path):
        try:
            os.remove(file_record.file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
    
    # Delete from database
    db.delete(file_record)
    db.commit()
    
    return StandardResponse(
        success=True,
        message=f"Đã xóa file '{file_record.original_filename}'",
        data=None
    )

# ============================================================================
# NGHIỆP VỤ 6: SHARE FILE (Chia sẻ file qua email)
# ============================================================================

@router.post("/{file_id}/share", response_model=StandardResponse)
async def share_file(
    file_id: int,
    recipient_email: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Chia sẻ file qua email
    
    - Gửi link download cho người nhận
    - Chỉ owner hoặc file public mới share được
    """
    
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại"
        )
    
    # Check permission
    if not file_record.is_public and file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chia sẻ file này"
        )
    
    # Generate download link (giả sử server IP là 192.168.1.10)
    download_url = f"http://192.168.1.10:8000/api/v1/files/download/{file_id}"
    
    # Send email
    try:
        from app.network.email_service import EmailService
        await EmailService.send_download_link(
            to_email=recipient_email,
            filename=file_record.original_filename,
            download_url=download_url,
            sender_name=current_user.username
        )
        
        return StandardResponse(
            success=True,
            message=f"Đã gửi link download đến {recipient_email}",
            data={"download_url": download_url}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi email: {str(e)}"
        )

# ============================================================================
# NGHIỆP VỤ 7: UPDATE FILE METADATA (Cập nhật thông tin file)
# ============================================================================

@router.put("/{file_id}", response_model=StandardResponse[FileOut])
def update_file_metadata(
    file_id: int,
    description: Optional[str] = Form(None),
    is_public: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Cập nhật thông tin file (không thay đổi file gốc)
    
    - Chỉ owner mới được update
    - Có thể đổi description, public/private
    """
    
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File không tồn tại"
        )
    
    # Check ownership
    if file_record.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền sửa file này"
        )
    
    # Update fields
    if description is not None:
        file_record.description = description
    
    if is_public is not None:
        file_record.is_public = is_public
    
    db.commit()
    db.refresh(file_record)
    
    return StandardResponse(
        success=True,
        message="Cập nhật thông tin file thành công",
        data=file_record
    )

# ============================================================================
# NGHIỆP VỤ 8: GET MY STATISTICS (Thống kê của user)
# ============================================================================

@router.get("/stats/me", response_model=StandardResponse)
def get_my_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NGHIỆP VỤ: Xem thống kê của bản thân
    
    - Tổng số file đã upload
    - Tổng dung lượng
    - Tổng lượt download
    """
    
    files = db.query(FileModel).filter(FileModel.owner_id == current_user.id).all()
    
    total_files = len(files)
    total_size = sum(f.file_size for f in files)
    total_downloads = sum(f.download_count for f in files)
    
    stats = {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "total_downloads": total_downloads,
        "files_by_type": {}
    }
    
    # Count by file type
    for file in files:
        file_type = file.file_type
        if file_type not in stats["files_by_type"]:
            stats["files_by_type"][file_type] = 0
        stats["files_by_type"][file_type] += 1
    
    return StandardResponse(
        success=True,
        message="Lấy thống kê thành công",
        data=stats
    )