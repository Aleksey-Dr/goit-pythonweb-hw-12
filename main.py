# main.py

from typing import List

from fastapi import Depends, FastAPI, HTTPException, status, Request, Response, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.middleware import Middleware

from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mail import FastMail, MessageSchema

from datetime import timedelta, timezone, datetime
from redis_utils import get_redis, redis_client

import os
import redis
import crud, models, database, auth, email_utils, rate_limit, cors, cloudinary_utils

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
cors.enable_cors(app)
rate_limit.init_rate_limit(app)

mail = FastMail(email_utils.conf)


# Dependency for getting a database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Endpoint for new user registration
@app.post("/register", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: models.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return crud.create_user(db=db, user=user)


# Endpoint for user login and obtaining JWT token
@app.post("/login", response_model=models.Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db),
        redis: redis.Redis = Depends(get_redis), # Redis dependency
    ):
    user_db = crud.get_user_by_email(db, email=form_data.username)
    if not user_db or not crud.verify_password(form_data.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user_db.email, "id": user_db.id}, expires_delta=access_token_expires
    )

    # Convert database.UserDB to models.CachedUser
    cached_user = models.CachedUser.model_validate(user_db)

    # Cache the user after a successful login
    redis.setex(f"user:{cached_user.id}", auth.USER_CACHE_EXPIRE_SECONDS, cached_user.model_dump_json())

    return {"access_token": access_token, "token_type": "bearer"}


# Endpoint for obtaining information about the current user
@app.get("/users/me", response_model=models.UserResponse, dependencies=[Depends(auth.get_current_active_user), Depends(rate_limit.limit_user_me)])
async def get_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user


# Endpoint for sending email verification email
@app.post("/send-verification-email", status_code=status.HTTP_202_ACCEPTED)
async def send_verification(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    token = email_utils.generate_verification_token(current_user.email)
    await email_utils.send_verification_email(current_user.email, token, app)
    return {"message": "Verification email sent"}


# Token-based email verification endpoint
@app.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: Session = Depends(get_db)):
    if await email_utils.verify_email(token, db):
        return {"message": "Email verified successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")


# Endpoints for contacts (requires authentication)
@app.post("/contacts", response_model=models.Contact, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth.get_current_active_user)])
async def create_contact(contact: models.ContactCreate, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_contact(db=db, contact=contact, user_id=current_user.id)


@app.get("/contacts", response_model=List[models.Contact], dependencies=[Depends(auth.get_current_active_user)])
async def read_contacts(skip: int = 0, limit: int = 100, first_name: str = None, last_name: str = None, email: str = None, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    contacts = crud.get_contacts(db, user_id=current_user.id, skip=skip, limit=limit, first_name=first_name, last_name=last_name, email=email)
    return contacts


@app.get("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def read_contact(contact_id: int, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    db_contact = crud.get_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return db_contact


@app.put("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def update_contact(contact_id: int, contact: models.ContactUpdate, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    db_contact = crud.update_contact(db=db, contact_id=contact_id, user_id=current_user.id, contact=contact)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return db_contact


@app.delete("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def delete_contact(contact_id: int, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    db_contact = crud.get_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    if crud.delete_contact(db=db, contact_id=contact_id, user_id=current_user.id):
        return db_contact
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")


@app.get("/birthdays", response_model=List[models.Contact], dependencies=[Depends(auth.get_current_active_user)])
async def get_upcoming_birthdays(current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_upcoming_birthdays(db, user_id=current_user.id)


# Endpoint for updating user avatar
@app.post("/users/me/avatar", response_model=models.User, dependencies=[Depends(auth.get_current_active_user)])
async def update_user_avatar(file: str = Form(...), current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    avatar_url = await cloudinary_utils.upload_avatar(file)
    if avatar_url:
        updated_user = crud.update_user_avatar(db=db, user_id=current_user.id, avatar_url=avatar_url)
        if updated_user:
            return updated_user
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update avatar in database")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar to Cloudinary")
    

# Endpoint for password reset request
@app.post("/password-reset-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(body: models.PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=body.email)
    if user:
        token_db = crud.create_password_reset_token(db, email=body.email)
        reset_link = f"{request.base_url}password-reset/verify/{token_db.token}"
        message = MessageSchema(
            subject="Password reset request",
            recipients=[body.email],
            body=f"Follow this link to reset your password: {reset_link}",
            subtype="html" # Или "plain"
        )
        await mail.send_message(message)
    # Important: Do not explicitly report whether an email was found. Avoid information leakage
    return {"message": "If this email address is registered, a password reset link will be sent to it."}


# Password reset endpoint
@app.post("/password-reset", status_code=status.HTTP_200_OK)
async def reset_password(body: models.PasswordReset, db: Session = Depends(get_db)):
    if body.new_password != body.confirm_new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The new passwords do not match")

    token_db = crud.get_password_reset_token(db, token=body.token)
    if not token_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

    if token_db.expires_at.tzinfo is None or token_db.expires_at.tzinfo.utcoffset(token_db.expires_at) is None:
        expires_at_utc = token_db.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at_utc = token_db.expires_at

    if expires_at_utc < datetime.now(timezone.utc):
        crud.delete_password_reset_token(db, token=body.token)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The password reset token has expired")

    user = crud.get_user_by_email(db, email=token_db.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    hashed_password = auth.pwd_context.hash(body.new_password)
    user.hashed_password = hashed_password
    db.commit()
    crud.delete_password_reset_token(db, token=body.token)
    return JSONResponse(content={"message": "Password successfully reset"}, status_code=status.HTTP_200_OK)


# Endpoint for checking the validity of the token (can be used by the client)
@app.get("/password-reset/verify/{token}", response_model=models.PasswordResetToken)
async def verify_password_reset_token(token: str, db: Session = Depends(get_db)):
    token_db = crud.get_password_reset_token(db, token=token)
    if not token_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or obsolete token")

    if token_db.expires_at.tzinfo is None or token_db.expires_at.tzinfo.utcoffset(token_db.expires_at) is None:
        expires_at_utc = token_db.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at_utc = token_db.expires_at

    if expires_at_utc < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or obsolete token")
    return models.PasswordResetToken(token=token_db.token, email=token_db.email, expires_at=token_db.expires_at)
