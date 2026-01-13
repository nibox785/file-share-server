from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Base schema
class UserBase(BaseModel):
    username: str
    email: EmailStr

# Schema cho request đăng ký
class UserRegister(UserBase):
    password: str

# Schema cho request đăng nhập
class UserLogin(BaseModel):
    username: str
    password: str

# Schema cho response (không trả password)
class UserOut(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schema cho token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    expires_at: Optional[str] = None 
    user: Optional[UserOut] = None