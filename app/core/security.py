from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra password với hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Tạo JWT token

    - Ensure `sub` is a string for portability
    - Use numeric UNIX timestamp for `exp` to avoid datetime encoding issues
    """
    to_encode = data.copy()
    if expires_delta:
        expire_dt = datetime.utcnow() + expires_delta
    else:
        expire_dt = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Normalize subject and expiration
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    to_encode.update({"exp": int(expire_dt.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Giải mã JWT token - non-verbose: returns payload or None on any failure"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token_verbose(token: str) -> dict:
    """Giải mã JWT token với thông tin lỗi chi tiết (dùng cho debug endpoints).

    Returns: {"ok": bool, "payload": dict|None, "error": str|None}
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return {"ok": True, "payload": payload, "error": None}
    except ExpiredSignatureError:
        return {"ok": False, "payload": None, "error": "expired"}
    except JWTError:
        return {"ok": False, "payload": None, "error": "invalid"}