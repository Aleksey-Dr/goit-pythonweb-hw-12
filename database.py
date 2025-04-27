# database.py

import os

from datetime import timezone, datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ContactDB(Base):
    """
    SQLAlchemy model representing a contact in the database.

    Attributes:
        id (int): The primary key and unique identifier for the contact.
        first_name (str): The first name of the contact.
        last_name (str): The last name of the contact.
        email (str): The unique email address of the contact.
        phone_number (str): The phone number of the contact.
        birthday (date): The birthday of the contact.
        additional_data (Optional[str]): Additional information about the contact (nullable).
        user_id (int): Foreign key linking this contact to the user who owns it.
        owner (UserDB): Relationship to the UserDB model representing the owner of the contact.
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    birthday = Column(Date, nullable=False)
    additional_data = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("UserDB", back_populates="contacts")

class UserDB(Base):
    """
    SQLAlchemy model representing a user in the database.

    Attributes:
        id (int): The primary key and unique identifier for the user.
        username (str): The unique username of the user.
        email (str): The unique email address of the user.
        hashed_password (str): The hashed password of the user.
        is_active (bool): Indicates if the user account is active (default: True).
        is_verified (bool): Indicates if the user's email has been verified (default: False).
        created_at (datetime): The timestamp when the user account was created (default: current UTC time).
        avatar_url (Optional[str]): The URL of the user's avatar image (nullable).
        role (str): The role of the user in the system (default: "user").
       contacts (List[ContactDB]): Relationship to the ContactDB model representing the contacts owned by this user.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    avatar_url = Column(String, nullable=True)
    role = Column(String(50), default="user")
    refresh_token = Column(String, nullable=True)

    contacts = relationship("ContactDB", back_populates="owner")

def get_db():
    """
    Dependency function to get a database session.

    Yields:
        Session: A SQLAlchemy database session. The session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLAlchemy password reset model
class PasswordResetTokenDB(Base):
    """
    SQLAlchemy model representing a password reset token in the database.

    Attributes:
        id (int): The primary key and unique identifier for the token.
        email (str): The email address associated with the password reset request.
        token (str): The unique password reset token string.
        expires_at (datetime): The timestamp when the token expires.
       created_at (datetime): The timestamp when the token was created (default: current database time).
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
