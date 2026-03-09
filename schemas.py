from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class URLBase(BaseModel):
    original_url: str

class URLCreate(URLBase):
    max_clicks: Optional[int] = None

class URLEdit(BaseModel):
    original_url: str
    max_clicks: Optional[int] = None
    is_enabled: bool

class URLInfo(URLBase):
    id: int
    short_code: str
    clicks: int
    max_clicks: Optional[int] = None
    is_enabled: bool
    created_at: datetime
    last_accessed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True
