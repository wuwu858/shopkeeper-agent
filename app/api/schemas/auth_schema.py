# app/api/schemas/auth_schema.py

from pydantic import BaseModel
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    department: Optional[str] = None
    regions: List[str] = []

class UserInfo(BaseModel):
    user_id: str
    username: str
    role: str
    department: Optional[str] = None
    regions: List[str] = []