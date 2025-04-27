# crud.py

import os
import secrets
from typing import List, Optional
from datetime import date, timedelta, timezone, datetime
from calendar import isleap

from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from passlib.context import CryptContext

import models, database

PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get("PASSWORD_RESET_TOKEN_EXPIRY_MINUTES", 15))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# password
def get_password_hash(password):
    """
    Hashes the given password using bcrypt.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """
    Verifies a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the plain password matches the hashed password, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_password_reset_token(db: Session, email: str) -> database.PasswordResetTokenDB:
    """
    Creates a new password reset token for the given email address.

    Args:
        db (Session): The database session.
        email (str): The email address for which to create the reset token.

    Returns:
        database.PasswordResetTokenDB: The newly created password reset token database object.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRY_MINUTES)
    db_token = database.PasswordResetTokenDB(email=email, token=token, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_password_reset_token(db: Session, token: str) -> Optional[database.PasswordResetTokenDB]:
    """
     Retrieves a password reset token from the database by its token value.

    Args:
        db (Session): The database session.
        token (str): The password reset token string to search for.

    Returns:
        Optional[database.PasswordResetTokenDB]: The password reset token database object if found, otherwise None.
    """
    return db.query(database.PasswordResetTokenDB).filter(database.PasswordResetTokenDB.token == token).first()


def delete_password_reset_token(db: Session, token: str):
    """
    Deletes a password reset token from the database by its token value.

    Args:
        db (Session): The database session.
        token (str): The password reset token string to delete.
    """
    db_token = get_password_reset_token(db, token)
    if db_token:
        db.delete(db_token)
        db.commit()


def get_password_reset_token_by_email(db: Session, email: str) -> Optional[database.PasswordResetTokenDB]:
    """
    Retrieves the most recent password reset token for a given email address.

    Args:
        db (Session): The database session.
        email (str): The email address to search for.

    Returns:
        Optional[database.PasswordResetTokenDB]: The password reset token database object if found, otherwise None.
    """
    return db.query(database.PasswordResetTokenDB).filter(database.PasswordResetTokenDB.email == email).first()


# user
def get_user_by_email(db: Session, email: str):
    """
    Retrieves a user from the database by their email address.

    Args:
        db (Session): The database session.
        email (str): The email address to search for.

    Returns:
        Optional[database.UserDB]: The user database object if found, otherwise None.
    """
    return db.query(database.UserDB).filter(database.UserDB.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(database.UserDB).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    """
    Retrieves a user from the database by their ID.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to retrieve.

    Returns:
        Optional[database.UserDB]: The user database object if found, otherwise None.
    """
    return db.query(database.UserDB).filter(database.UserDB.id == user_id).first()


def create_user(db: Session, user: models.UserCreate):
    """
    Creates a new user in the database.

    Args:
        db (Session): The database session.
        user (models.UserCreate): The user data to create.

    Returns:
        database.UserDB: The newly created user database object.
    """
    db_user = database.UserDB(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        username=user.username,
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_avatar(db: Session, user_id: int, avatar_url: str):
    """
    Updates the avatar URL of an existing user.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to update.
        avatar_url (str): The new avatar URL.

    Returns:
        Optional[database.UserDB]: The updated user database object if found, otherwise None.
    """
    db_user = db.query(database.UserDB).filter(database.UserDB.id == user_id).first()
    if db_user:
        db_user.avatar_url = avatar_url
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


def update_user_refresh_token(db: Session, user_id: int, refresh_token: str):
    """
    Updates the refresh token of an existing user.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to update.
        refresh_token (str): The new refresh token.

    Returns:
        Optional[database.UserDB]: The updated user database object if found, otherwise None.
    """
    db_user = db.query(database.UserDB).filter(database.UserDB.id == user_id).first()
    if db_user:
        db_user.refresh_token = refresh_token
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


def get_user_by_refresh_token(db: Session, refresh_token: str):
    """
    Retrieves a user from the database by their refresh token.

    Args:
        db (Session): The database session.
        refresh_token (str): The refresh token to search for.

    Returns:
        Optional[database.UserDB]: The user database object if found, otherwise None.
    """
    return db.query(database.UserDB).filter(database.UserDB.refresh_token == refresh_token).first()


# contact
def get_contact(db: Session, contact_id: int, user_id: int):
    """
    Retrieves a specific contact by its ID for a given user.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to retrieve.
        user_id (int): The ID of the user who owns the contact.

    Returns:
        Optional[database.ContactDB]: The contact database object if found, otherwise None.
    """
    return db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()


def get_contacts(db: Session, user_id: int, skip: int = 0, limit: int = 100, first_name: str = None,
                 last_name: str = None, email: str = None):
    """
    Retrieves a list of contacts for a specific user with optional filtering.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user whose contacts to retrieve.
        skip (int, optional): The number of contacts to skip. Defaults to 0.
        limit (int, optional): The maximum number of contacts to return. Defaults to 100.
        first_name (Optional[str], optional): Filter contacts by first name (case-insensitive). Defaults to None.
        last_name (Optional[str], optional): Filter contacts by last name (case-insensitive). Defaults to None.
        email (Optional[str], optional): Filter contacts by email address (case-insensitive). Defaults to None.

    Returns:
        List[database.ContactDB]: A list of contact database objects matching the criteria.
    """
    query = db.query(database.ContactDB).filter(database.ContactDB.user_id == user_id)
    if first_name:
        query = query.filter(database.ContactDB.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(database.ContactDB.last_name.ilike(f"%{last_name}%"))
    if email:
        query = query.filter(database.ContactDB.email.ilike(f"%{email}%"))
    return query.offset(skip).limit(limit).all()


def create_contact(db: Session, contact: models.ContactCreate, user_id: int):
    """
    Creates a new contact for a specific user.

    Args:
        db (Session): The database session.
        contact (models.ContactCreate): The contact data to create.
        user_id (int): The ID of the user who owns the contact.

    Returns:
        database.ContactDB: The newly created contact database object.
    """
    db_contact = database.ContactDB(**contact.model_dump(), user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def update_contact(db: Session, contact_id: int, user_id: int, contact: models.ContactUpdate):
    """
    Updates an existing contact for a specific user.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to update.
        user_id (int): The ID of the user who owns the contact.
        contact (models.ContactUpdate): The updated contact data.

    Returns:
        Optional[database.ContactDB]: The updated contact database object if found, otherwise None.
    """
    db_contact = db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()
    if db_contact:
        for key, value in contact.model_dump(exclude_unset=True).items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact


def delete_contact(db: Session, contact_id: int, user_id: int):
    """
    Deletes a specific contact by its ID for a given user.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to delete.
        user_id (int): The ID of the user who owns the contact.

    Returns:
        bool: True if the contact was successfully deleted, False otherwise.
    """
    db_contact = db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()
    if db_contact:
        db.delete(db_contact)
        db.commit()
        return True
    return False


def get_upcoming_birthdays(db: Session, user_id: int):
    """
    Retrieves a list of contacts with birthdays in the next 7 days for a specific user.

    This function handles the edge case of February 29th in non-leap years by considering it as February 28th.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user whose contacts to check.

    Returns:
        List[database.ContactDB]: A list of contact database objects with upcoming birthdays.
    """
    today = date.today()
    next_week = today + timedelta(days=7)
    upcoming_birthdays = []
    contacts = db.query(database.ContactDB).filter(database.ContactDB.user_id == user_id).all()
    for contact in contacts:
        birthday_month = contact.birthday.month
        birthday_day = contact.birthday.day

        # Processing February 29 in a non-leap year
        if birthday_month == 2 and birthday_day == 29 and not isleap(today.year):
            birthday_this_year = date(today.year, 2, 28)
        else:
            try:
                birthday_this_year = date(today.year, birthday_month, birthday_day)
            except ValueError:
                continue

        if today <= birthday_this_year <= next_week:
            upcoming_birthdays.append(contact)
        else:
            next_year = today.year + 1
            if birthday_month == 2 and birthday_day == 29 and not isleap(next_year):
                birthday_next_year = date(next_year, 2, 28)
            else:
                try:
                    birthday_next_year = date(next_year, birthday_month, birthday_day)
                except ValueError:
                    continue

            if today <= birthday_next_year <= next_week:
                upcoming_birthdays.append(contact)
    return upcoming_birthdays
