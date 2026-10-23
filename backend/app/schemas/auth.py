from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    roles: List[str] = []


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    keycloak_sub: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keycloak_sub: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class AuthURLResponse(BaseModel):
    auth_url: str
    state: str
    code_verifier: str


class CallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str


class LogoutResponse(BaseModel):
    message: str
    logout_url: Optional[str] = None


class MessageResponse(BaseModel):
    message: str