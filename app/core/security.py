from datetime import datetime, timedelta, timezone
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
        expire_dt = datetime.now(timezone.utc) + expires_delta
    else:
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Normalize subject and expiration
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    to_encode.update({"exp": int(expire_dt.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Giải mã JWT token - non-verbose: returns payload or None on any failure"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True, "leeway": 60},
        )
        return payload
    except ExpiredSignatureError:
        # Debug hint for server logs
        try:
            claims = jwt.get_unverified_claims(token)
            exp = claims.get("exp")
            now_utc = datetime.now(timezone.utc).timestamp()
            print(f"[Auth] Token expired. exp={exp}, now={int(now_utc)}")
        except Exception:
            print("[Auth] Token expired (unable to read claims)")
        return None
    except JWTError:
        print("[Auth] Token invalid or signature mismatch")
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