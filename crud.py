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
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_password_reset_token(db: Session, email: str) -> database.PasswordResetTokenDB:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRY_MINUTES)
    db_token = database.PasswordResetTokenDB(email=email, token=token, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_password_reset_token(db: Session, token: str) -> Optional[database.PasswordResetTokenDB]:
    return db.query(database.PasswordResetTokenDB).filter(database.PasswordResetTokenDB.token == token).first()


def delete_password_reset_token(db: Session, token: str):
    db_token = get_password_reset_token(db, token)
    if db_token:
        db.delete(db_token)
        db.commit()


def get_password_reset_token_by_email(db: Session, email: str) -> Optional[database.PasswordResetTokenDB]:
    return db.query(database.PasswordResetTokenDB).filter(database.PasswordResetTokenDB.email == email).first()


# user
def get_user_by_email(db: Session, email: str):
    return db.query(database.UserDB).filter(database.UserDB.email == email).first()


def get_user(db: Session, user_id: int):
    return db.query(database.UserDB).filter(database.UserDB.id == user_id).first()


def create_user(db: Session, user: models.UserCreate):
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
    db_user = db.query(database.UserDB).filter(database.UserDB.id == user_id).first()
    if db_user:
        db_user.avatar_url = avatar_url
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


# contact
def get_contact(db: Session, contact_id: int, user_id: int):
    return db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()


def get_contacts(db: Session, user_id: int, skip: int = 0, limit: int = 100, first_name: str = None,
                 last_name: str = None, email: str = None):
    query = db.query(database.ContactDB).filter(database.ContactDB.user_id == user_id)
    if first_name:
        query = query.filter(database.ContactDB.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(database.ContactDB.last_name.ilike(f"%{last_name}%"))
    if email:
        query = query.filter(database.ContactDB.email.ilike(f"%{email}%"))
    return query.offset(skip).limit(limit).all()


def create_contact(db: Session, contact: models.ContactCreate, user_id: int):
    db_contact = database.ContactDB(**contact.model_dump(), user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def update_contact(db: Session, contact_id: int, user_id: int, contact: models.ContactUpdate):
    db_contact = db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()
    if db_contact:
        for key, value in contact.model_dump(exclude_unset=True).items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact


def delete_contact(db: Session, contact_id: int, user_id: int):
    db_contact = db.query(database.ContactDB).filter(database.ContactDB.id == contact_id, database.ContactDB.user_id == user_id).first()
    if db_contact:
        db.delete(db_contact)
        db.commit()
        return True
    return False


def get_upcoming_birthdays(db: Session, user_id: int):
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
