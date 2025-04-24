# models.py

from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_data: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    birthday: Optional[date] = None
    additional_data: Optional[str] = None


class Contact(ContactBase):
    id: int
    user_id: int

    model_config = {
        "from_attributes": True
    }


class UserBase(BaseModel):
    email: EmailStr
    password: str


class UserCreate(UserBase):
    username: str


class User(UserBase):
    id: int
    username: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    avatar_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    avatar_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class CachedUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    id: Optional[int] = None


class Email(BaseModel):
    email: EmailStr


class AvatarUpdate(BaseModel):
    file: str = Field(..., description="Base64 encoded image")
