# email_utils.py

import os
from typing import Dict
from sqlalchemy.orm import Session

from fastapi import FastAPI
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jose import JWTError, jwt

import crud

conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT")),
    MAIL_FROM=os.environ.get("MAIL_FROM"),
    MAIL_FROM_NAME="FastAPI Mailer",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


async def send_verification_email(email: str, token: str, app: FastAPI):
    """
    Sends a verification email to the specified email address.

    Args:
        email (str): The recipient's email address.
        token (str): The verification token to include in the email link.
        app (FastAPI): The FastAPI application instance.
    """
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"""
        Please click the following link to verify your email:
        http://localhost:8000/verify-email?token={token}
        """,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)


def generate_verification_token(email: str):
    """
    Generates a JWT verification token for the given email address.

    Args:
        email (str): The email address to generate the token for.
    Returns:
        str: The generated JWT verification token.
    """
    return jwt.encode({"sub": email}, os.environ.get("SECRET_KEY"), algorithm="HS256")


async def verify_email(token: str, db: Session):
    """
    Verifies the email address associated with the given token.

    Args:
        token (str): The verification token received via email.
        db (Session): The database session.

    Returns:
        bool: True if the token is valid and the email was successfully verified, False otherwise.
    """
    try:
        payload = jwt.decode(token, os.environ.get("SECRET_KEY"), algorithms=["HS256"])
        email = payload.get("sub")
        if email is None:
            return False
    except JWTError:
        return False
    user = crud.get_user_by_email(db, email=email)
    if user and not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return True
    return False
