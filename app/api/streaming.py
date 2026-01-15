from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import mimetypes
from datetime import datetime
import threading
import time

# Import DB & Config
from app.db.session import get_db
from app.core.config import settings
from app.api.deps import get_current_user, get_current_admin_user

# Import Models & Schemas
from app.models.user import User
from app.models.media import Media           
from app.schemas.media import MediaOut       
from app.schemas.common import StandardResponse

router = APIRouter()

# ============================================================================
# GLOBAL STATE (Lưu trạng thái Stream trong RAM)
# ============================================================================
streaming_state = {
    "is_streaming": False,
    "current_media_id": None,
    "current_filename": None,
    "start_time": None,
    "listeners_count": 0,
    "stop_signal": False
}

# Biến global thread để quản lý tiến trình stream nền
stream_thread = None

# ============================================================================
# HELPERS
# ============================================================================
def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """Hàm phụ trợ lưu file vật lý"""
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return destination
    finally:
        upload_file.file.close()

# Giả lập hàm phát Multicast (Bạn thay code FFMPEG/Socket thực của bạn vào đây)
def run_multicast_sender(file_path: str):
    print(f"--- BẮT ĐẦU STREAM MULTICAST: {file_path} ---")
    print(f"--- Gửi đến: {settings.MULTICAST_GROUP}:{settings.MULTICAST_PORT} ---")
    
    # Giả lập stream đang chạy
    while not streaming_state["stop_signal"]:
        time.sleep(1) 
        # Tại đây bạn sẽ gọi code socket gửi UDP packets
        # hoặc gọi subprocess.run(['ffmpeg', ...])
    
    print("--- ĐÃ DỪNG STREAM ---")
    streaming_state["is_streaming"] = False
    streaming_state["current_media_id"] = None

# ============================================================================
# API ENDPOINTS
# ============================================================================

# 1. API UPLOAD MEDIA (Lưu ổ cứng + Lưu DB)
@router.post("/upload-media", response_model=MediaOut)
async def upload_media_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Kiểm tra đuôi file
    valid_types = [".mp3", ".wav", ".mp4", ".mkv", ".avi"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in valid_types:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file Audio/Video (.mp3, .mp4...)")

    # Tạo thư mục lưu trữ
    upload_folder = "static/media_store"
    os.makedirs(upload_folder, exist_ok=True)

    # Đổi tên file để tránh trùng (Timestamp + Ext)
    new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join(upload_folder, new_filename)

    # 1. Lưu file vật lý
    save_upload_file(file, file_path)

    # 2. Lưu thông tin vào Database
    new_media = Media(
        title=title,
        description=description,
        filename=new_filename,
        file_path=file_path,
        media_type=file.content_type or "application/octet-stream"
    )
    
    db.add(new_media)
    db.commit()
    db.refresh(new_media)
    
    return new_media

# 2. API LẤY DANH SÁCH MEDIA (Cho Admin chọn bài)
@router.get("/media-list", response_model=List[MediaOut])
def get_media_list(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    media_files = db.query(Media).order_by(Media.uploaded_at.desc()).offset(skip).limit(limit).all()
    return media_files

# 3. API BẮT ĐẦU STREAM (Admin chọn ID bài hát để phát)
@router.post("/start-stream/{media_id}")
def start_stream(
    media_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    global stream_thread
    
    # Nếu đang stream thì không cho stream đè
    if streaming_state["is_streaming"]:
        raise HTTPException(status_code=400, detail="Đang có một luồng stream khác đang chạy. Hãy tắt nó trước.")

    # Tìm bài hát trong DB
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Không tìm thấy file Media này")
    
    if not os.path.exists(media.file_path):
        raise HTTPException(status_code=404, detail="File vật lý đã bị xóa khỏi server")

    # Cập nhật trạng thái
    streaming_state["is_streaming"] = True
    streaming_state["current_media_id"] = media.id
    streaming_state["current_filename"] = media.title
    streaming_state["start_time"] = datetime.now()
    streaming_state["stop_signal"] = False

    # Chạy thread stream (Non-blocking)
    stream_thread = threading.Thread(target=run_multicast_sender, args=(media.file_path,))
    stream_thread.daemon = True # Tự tắt khi app tắt
    stream_thread.start()

    return {"message": f"Bắt đầu phát sóng: {media.title}", "state": streaming_state}

# 4. API DỪNG STREAM
@router.post("/stop-stream")
def stop_stream(current_user: User = Depends(get_current_admin_user)):
    if not streaming_state["is_streaming"]:
        return {"message": "Hiện tại không có stream nào đang chạy"}

    # Gửi tín hiệu dừng
    streaming_state["stop_signal"] = True
    
    # Chờ thread dừng hẳn (optional)
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=2.0)

    # Reset trạng thái
    streaming_state["is_streaming"] = False
    streaming_state["current_media_id"] = None
    
    return {"message": "Đã dừng phát sóng"}

# 5. API LẤY TRẠNG THÁI STREAM (User kiểm tra xem có gì đang phát không)
@router.get("/stream-info")
def get_stream_info(current_user: User = Depends(get_current_user)):
    return {
        "status": "live" if streaming_state["is_streaming"] else "offline",
        "info": streaming_state,
        "multicast_config": {
            "group": settings.MULTICAST_GROUP,
            "port": settings.MULTICAST_PORT
        }
    }

# 6. API STREAM HTTP (Nghe trực tiếp trên web - Alternative)
@router.get("/stream-http/{media_id}")
async def stream_file_http(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Tìm trong DB
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    file_path = media.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File vật lý không tồn tại")
    
    # Đoán mime type nếu trong DB không có
    mime_type = media.media_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    # Generator đọc file từng chút một (Streaming)
    def iterfile():
        with open(file_path, mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(iterfile(), media_type=mime_type)