from pydantic import BaseModel, HttpUrl

class URLBase(BaseModel):
    original_url: HttpUrl

class URLCreate(URLBase):
    pass

class URLInfo(URLBase):
    id: str
    short_code: str
    clicks: int

    class Config:
        from_attributes = True
