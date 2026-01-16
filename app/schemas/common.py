from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Thao tác thành công"
    data: Optional[T] = None

def success_response(data=None, message="Thao tác thành công"):
    """Helper function tạo success response"""
    return StandardResponse(success=True, message=message, data=data)

def error_response(message: str, data=None):
    """Helper function tạo error response"""
    return StandardResponse(success=False, message=message, data=data)