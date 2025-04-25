# models.py

from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    """
    Base Pydantic model for contact information.
    """
    first_name: str = Field(..., description="The first name of the contact")
    last_name: str = Field(..., description="The last name of the contact")
    email: EmailStr = Field(..., description="The email address of the contact")
    phone_number: str = Field(..., description="The phone number of the contact")
    birthday: date = Field(..., description="The birthday of the contact")
    additional_data: Optional[str] = Field(None, description="Additional information about the contact")


class ContactCreate(ContactBase):
    """
    Pydantic model for creating a new contact.
    Inherits fields from ContactBase.
    """
    pass


class ContactUpdate(BaseModel):
    """
    Pydantic model for updating an existing contact.
    All fields are optional.
    """
    first_name: Optional[str] = Field(None, description="The updated first name of the contact")
    last_name: Optional[str] = Field(None, description="The updated last name of the contact")
    email: Optional[EmailStr] = Field(None, description="The updated email address of the contact")
    phone_number: Optional[str] = Field(None, description="The updated phone number of the contact")
    birthday: Optional[date] = Field(None, description="The updated birthday of the contact")
    additional_data: Optional[str] = Field(None, description="The updated additional information about the contact")


class Contact(ContactBase):
    """
    Pydantic model representing a contact stored in the database.
    Inherits fields from ContactBase and includes database-specific fields.
    """
    id: int = Field(..., description="The unique identifier of the contact")
    user_id: int = Field(..., description="The ID of the user who owns this contact")

    model_config = {
        "from_attributes": True
    }


# User
class UserBase(BaseModel):
    """
    Base Pydantic model for user information.
    """
    email: EmailStr = Field(..., description="The email address of the user")
    password: str = Field(..., description="The password of the user (write-only during creation)")


class UserCreate(UserBase):
    """
    Pydantic model for creating a new user.
    Inherits fields from UserBase and includes fields required for creation.
    """
    username: str = Field(..., description="The username of the user")


class User(UserBase):
    """
    Pydantic model representing a user stored in the database.
    Inherits fields from UserBase and includes database-specific fields and status.
    """
    id: int = Field(..., description="The unique identifier of the user")
    username: str = Field(..., description="The username of the user")
    is_active: bool = Field(True, description="Indicates if the user account is active")
    is_verified: bool = Field(False, description="Indicates if the user's email has been verified")
    created_at: datetime = Field(..., description="The timestamp when the user account was created")
    avatar_url: Optional[str] = Field(None, description="The URL of the user's avatar image")
    role: str = Field("user", description="The role of the user in the system")
    refresh_token: Optional[str] = Field(None, description="The current refresh token for the user")

    model_config = {
        "from_attributes": True
    }


class UserResponse(BaseModel):
    """
    Pydantic model for the user response, exposing safe user information.
    Excludes sensitive information like password and refresh token.
    """
    id: int = Field(..., description="The unique identifier of the user")
    username: str = Field(..., description="The username of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    is_active: bool = Field(True, description="Indicates if the user account is active")
    is_verified: bool = Field(False, description="Indicates if the user's email has been verified")
    created_at: datetime = Field(..., description="The timestamp when the user account was created")
    avatar_url: Optional[str] = Field(None, description="The URL of the user's avatar image")
    role: str = Field("user", description="The role of the user in the system")

    model_config = {
        "from_attributes": True
    }


class CachedUser(BaseModel):
    """
    Pydantic model representing a user stored in the Redis cache.
    Contains a subset of user information for faster retrieval.
    """
    id: int = Field(..., description="The unique identifier of the user")
    username: str = Field(..., description="The username of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    is_active: bool = Field(True, description="Indicates if the user account is active")
    is_verified: bool = Field(False, description="Indicates if the user's email has been verified")
    avatar_url: Optional[str] = Field(None, description="The URL of the user's avatar image")

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    """
    Pydantic model representing an authentication token.
    """
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field("bearer", description="The type of the token")


class TokenData(BaseModel):
    """
    Pydantic model representing the data extracted from a JWT token payload.
    """
    email: Optional[str] = Field(None, description="The email address of the user extracted from the token")
    id: Optional[int] = Field(None, description="The ID of the user extracted from the token")


class TokenPair(BaseModel):
    """
    Pydantic model representing a pair of access and refresh tokens.
    """
    access_token: str = Field(..., description="The JWT access token")
    refresh_token: str = Field(..., description="The JWT refresh token")
    token_type: str = Field("bearer", description="The type of the tokens")


class Email(BaseModel):
    """
    Pydantic model for representing an email address.
    """
    email: EmailStr = Field(..., description="The email address")


class AvatarUpdate(BaseModel):
    """
    Pydantic model for updating a user's avatar.
    Expects the image to be base64 encoded.
    """
    file: str = Field(..., description="Base64 encoded image data for the avatar")


# Pydantic password reset models
class PasswordResetRequest(BaseModel):
    """
    Pydantic model for requesting a password reset.
    Requires the user's email address.
    """
    email: EmailStr = Field(..., description="The email address for which to request a password reset")


class PasswordReset(BaseModel):
    """
    Pydantic model for submitting a password reset.
    Requires the reset token and the new passwords.
    """
    token: str = Field(..., description="The password reset token")
    new_password: str = Field(..., description="The new password to set")
    confirm_new_password: str = Field(..., description="Confirmation of the new password")


class PasswordResetToken(BaseModel):
    """
    Pydantic model representing a password reset token.
    """
    token: str = Field(..., description="The password reset token string")
    email: EmailStr = Field(..., description="The email address associated with the token")
    expires_at: datetime = Field(..., description="The expiration timestamp of the token")
