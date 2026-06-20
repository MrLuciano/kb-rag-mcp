from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CreateUserRequest(BaseModel):
    username: str
    email: str = ""
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateApiKeyRequest(BaseModel):
    user_id: Optional[str] = None
    description: str = ""


class ApiKeyResponse(BaseModel):
    id: str
    prefix: str
    description: str
    is_revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str


class ErasureRequestResponse(BaseModel):
    id: str
    user_id: str
    status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    id: str
    username: str
    role: str
    token_type: str = "Bearer"
    expires_in: int = 28800


class UserExportResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    api_keys: list[ApiKeyResponse]
