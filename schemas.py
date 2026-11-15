from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)


class UserRead(UserBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=0, le=2100)
    genre: Optional[str] = Field(None, max_length=50)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=0, le=2100)
    genre: Optional[str] = Field(None, max_length=50)


class BookRead(BookBase):
    id: str
    owner_id: str

    model_config = ConfigDict(from_attributes=True)
