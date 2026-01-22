from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import os

from app.db.session import get_db
from app.models.user import User
from app.models.file import File as FileModel
from app.schemas.common import StandardResponse
from app.schemas.user import UserOut
from app.schemas.file import FileOut
from app.api.deps import get_current_admin_user
from app.network.multicast_server import set_radio_source
from app.core.config import settings

router = APIRouter()


class ToggleActiveRequest(BaseModel):
    is_active: bool


class ToggleAdminRequest(BaseModel):
    is_admin: bool


class TogglePublicRequest(BaseModel):
    is_public: bool


class RadioUploadResponse(BaseModel):
    filename: str
    file_path: str


class RadioStartResponse(BaseModel):
    source: str
    file_path: str


@router.get("/users", response_model=StandardResponse[List[UserOut]])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return StandardResponse(success=True, message="Danh sách users", data=users)


@router.patch("/users/{user_id}/active", response_model=StandardResponse[UserOut])
def set_user_active(
    user_id: int,
    payload: ToggleActiveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return StandardResponse(success=True, message="Cập nhật trạng thái thành công", data=user)


@router.patch("/users/{user_id}/admin", response_model=StandardResponse[UserOut])
def set_user_admin(
    user_id: int,
    payload: ToggleAdminRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại")
    user.is_admin = payload.is_admin
    db.commit()
    db.refresh(user)
    return StandardResponse(success=True, message="Cập nhật quyền admin thành công", data=user)


@router.get("/files", response_model=StandardResponse[List[FileOut]])
def list_files_all(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    files = db.query(FileModel).order_by(FileModel.uploaded_at.desc()).all()
    return StandardResponse(success=True, message="Danh sách files", data=files)


@router.patch("/files/{file_id}/public", response_model=StandardResponse[FileOut])
def set_file_public(
    file_id: int,
    payload: TogglePublicRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File không tồn tại")
    file.is_public = payload.is_public
    db.commit()
    db.refresh(file)
    return StandardResponse(success=True, message="Cập nhật public/private thành công", data=file)


@router.delete("/files/{file_id}", response_model=StandardResponse)
def delete_file_admin(
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File không tồn tại")

    # Delete physical file
    try:
        if file.file_path and os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception:
        pass

    db.delete(file)
    db.commit()
    return StandardResponse(success=True, message="Đã xóa file", data=None)


@router.post("/radio/upload", response_model=StandardResponse[RadioUploadResponse])
async def upload_radio_file(
    file: UploadFile = File(...),
    _: User = Depends(get_current_admin_user),
):
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ file WAV"
        )

    # Validate WAV header (RIFF/WAVE)
    try:
        header = await file.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File không phải WAV chuẩn (RIFF/WAVE). Vui lòng convert sang WAV PCM"
            )
    finally:
        try:
            await file.seek(0)
        except Exception:
            try:
                file.file.seek(0)
            except Exception:
                pass

    audio_dir = os.path.join("static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    base_name = os.path.basename(file.filename)
    target_path = os.path.join(audio_dir, base_name)

    # Avoid overwrite
    if os.path.exists(target_path):
        name, ext = os.path.splitext(base_name)
        target_path = os.path.join(audio_dir, f"{name}_{int(os.path.getmtime(target_path))}{ext}")

    with open(target_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    # Switch radio source to the new WAV
    settings.RADIO_AUDIO_FILE = target_path
    if not set_radio_source("wav", audio_file=target_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Radio server chưa sẵn sàng"
        )

    return StandardResponse(
        success=True,
        message="Đã cập nhật file phát radio",
        data=RadioUploadResponse(filename=os.path.basename(target_path), file_path=target_path)
    )


@router.post("/radio/start", response_model=StandardResponse[RadioStartResponse])
def start_radio_broadcast(
    _: User = Depends(get_current_admin_user),
):
    audio_file = settings.RADIO_AUDIO_FILE
    if not set_radio_source("wav", audio_file=audio_file):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Radio server chưa sẵn sàng"
        )

    return StandardResponse(
        success=True,
        message="Đã phát radio",
        data=RadioStartResponse(source="wav", file_path=audio_file)
    )
