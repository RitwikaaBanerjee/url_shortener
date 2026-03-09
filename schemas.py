from pydantic import BaseModel

class URLBase(BaseModel):
    original_url: str

class URLCreate(URLBase):
    pass

class URLInfo(URLBase):
    id: int
    short_code: str
    clicks: int

    class Config:
        from_attributes = True
