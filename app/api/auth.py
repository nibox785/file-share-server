from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, Token, UserOut
from app.schemas.common import StandardResponse
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token, decode_token_verbose
from app.core.config import settings
from datetime import timedelta, datetime
from app.api.deps import get_current_user, oauth2_scheme

router = APIRouter()

@router.post("/register", response_model=StandardResponse[UserOut])
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    API đăng ký tài khoản mới
    """
    # Kiểm tra username đã tồn tại
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã tồn tại"
        )
    
    # Kiểm tra email đã tồn tại
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng"
        )
    
    # Tạo user mới
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return StandardResponse(
        success=True,
        message="Đăng ký thành công",
        data=new_user
    )

@router.post("/login", response_model=StandardResponse[Token])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    API đăng nhập - Trả về JWT token
    """
    # Tìm user theo username
    user = db.query(User).filter(User.username == credentials.username).first()
    
    # Kiểm tra user tồn tại và password đúng
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Kiểm tra user có active không
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa"
        )
    
    # Tạo access token with explicit expiry
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at_dt = datetime.utcnow() + expires_delta
    # ensure subject is string
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=expires_delta)
    expires_in = int(expires_delta.total_seconds())
    expires_at = expires_at_dt.replace(microsecond=0).isoformat() + "Z"
    
    return StandardResponse(
        success=True,
        message="Đăng nhập thành công",
        data=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            expires_at=expires_at,
            user=UserOut.from_orm(user)
        )
    )

@router.get("/me", response_model=StandardResponse[UserOut])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    API lấy thông tin user hiện tại (yêu cầu đăng nhập)
    """
    return StandardResponse(
        success=True,
        message="Lấy thông tin thành công",
        data=current_user
    )

@router.get("/debug/token", response_model=StandardResponse[dict])
def debug_token(token: str = Depends(oauth2_scheme), current_user: User = Depends(get_current_user)):
    """
    Dev-only endpoint to return decoded token claims.
    Accessible only when settings.DEBUG_TOKEN_ENDPOINT is true or the user is admin.
    """
    if not settings.DEBUG_TOKEN_ENDPOINT and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug token endpoint is disabled"
        )
    payload = decode_token(token)
    return StandardResponse(
        success=True,
        message="Token claims decoded",
        data=payload
    )


# Dev: decode a token provided in request body (useful when tokens fail to authenticate)
from pydantic import BaseModel
class TokenRequest(BaseModel):
    token: str

@router.post("/debug/decode", response_model=StandardResponse[dict])
def decode_token_debug(request: TokenRequest):
    """
    Dev-only endpoint to decode a provided token without requiring authentication.
    Only enabled when DEBUG_TOKEN_ENDPOINT is true (set via .env) for safety.
    """
    if not settings.DEBUG_TOKEN_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug token endpoint is disabled"
        )
    result = decode_token_verbose(request.token)
    if not result.get("ok"):
        # Provide clearer reason for debugging
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token error: {result.get('error')}"
        )
    return StandardResponse(
        success=True,
        message="Token decoded",
        data=result.get("payload")
    )

@router.post("/logout", response_model=StandardResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    API logout (client sẽ xóa token)
    """
    return StandardResponse(
        success=True,
        message=f"Đăng xuất thành công. Tạm biệt {current_user.username}!",
        data=None
    )