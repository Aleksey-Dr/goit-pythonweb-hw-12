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
    """
    Creates and returns a SQLAlchemy database session.

    Yields:
        Session: Active database session.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# registration
# Endpoint for new user registration
@app.post("/register", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: models.UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user in the system.

    Args:
        user (models.UserCreate): New user data.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.UserResponse: Information about the created user.

    Raises:
        HTTPException: If the email is already registered (status code 409).
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return crud.create_user(db=db, user=user)


# login
# Endpoint for user login and obtaining JWT token
@app.post("/login", response_model=models.TokenPair)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis: redis.Redis = Depends(get_redis), # Redis dependency
):
    """
    Authenticates the user and returns a pair of JWT tokens (access and refresh).

    Args:
        form_data (OAuth2PasswordRequestForm): User credentials (username and password).
        db (Session, optional): Database session. Defaults to Depends(get_db).
        redis (redis.Redis, optional): Redis client. Defaults to Depends(get_redis).

    Returns:
        models.TokenPair: An object containing access_token, refresh_token, and token_type.

    Raises:
        HTTPException: If the username or password entered is invalid (status code 401).
    """
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
    refresh_token = auth.create_refresh_token(user_db.id)
    crud.update_user_refresh_token(db, user_db.id, refresh_token)

    # Convert database.UserDB to models.CachedUser
    cached_user = models.CachedUser.model_validate(user_db)

    # Cache the user after a successful login
    redis.setex(f"user:{cached_user.id}", auth.USER_CACHE_EXPIRE_SECONDS, cached_user.model_dump_json())

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# Endpoint for refreshing access token
@app.post("/refresh-token", response_model=models.Token)
async def refresh_access_token(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Refreshes the access token using the provided refresh token.

    Args:
        refresh_token (str): Refresh token obtained during login.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.Token: An object containing the new access_token and token_type.

    Raises:
        HTTPException: If the provided refresh token is invalid (status code 401).
    """
    user = crud.get_user_by_refresh_token(db, refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email, "id": user.id}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


# admin
# Endpoint for creating a new administrator (accessible only to other administrators)
@app.post(
        "/admin/create-admin",
        response_model=models.UserResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(auth.get_current_active_admin)]
    )
async def create_admin(
    admin_create: models.UserCreate,
    current_admin: models.User = Depends(auth.get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Creates a new administrator in the system (available only to administrators).

    Args:
        admin_create (models.UserCreate): Data to create a new administrator.
        current_admin (models.User): The current administrator executing the request.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.UserResponse: Information about the created administrator.

    Raises:
        HTTPException: If the email is already registered (status code 409).
    """
    db_user = crud.get_user_by_email(db, email=admin_create.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return crud.create_user(db=db, user=admin_create)


# Endpoint for updating user avatar (available only to administrators)
@app.post("/users/me/avatar", response_model=models.UserResponse, dependencies=[Depends(auth.get_current_active_user), Depends(auth.get_current_active_admin)])
async def update_user_avatar(file: str = Form(...), current_admin: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)): # Зверніть увагу на зміну current_admin на current_user
    """
    Updates the current admin avatar (only available to admins).

    Args:
        file (str): Base64 encoded avatar image.
        current_admin (models.User): The current admin executing the request.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.UserResponse: Updated admin information.

    Raises:
        HTTPException: In case of an error uploading to Cloudinary or updating the database (status code 500).
    """
    avatar_url = await cloudinary_utils.upload_avatar(file)
    if avatar_url:
        updated_user_db = crud.update_user_avatar(db=db, user_id=current_admin.id, avatar_url=avatar_url)
        if updated_user_db:
            # Convert database.UserDB to schemas.UserResponse before returning
            return models.UserResponse.model_validate(updated_user_db)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update avatar in database")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar to Cloudinary")


# Endpoint for updating user roles (available only to administrators)
class UserRoleUpdate(models.BaseModel):
    """Model for updating user role."""
    role: str

@app.put("/users/{user_id}/role", response_model=models.UserResponse, dependencies=[Depends(auth.get_current_active_admin)])
async def update_user_role(user_id: int, role_update: UserRoleUpdate, db: Session = Depends(get_db)):
    """
    Updates the role of the specified user (only available to administrators).

    Args:
        user_id (int): The ID of the user whose role is to be updated.
        role_update (UserRoleUpdate): An object with the new role.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.UserResponse: The updated user information.

    Raises:
        HTTPException: If the user is not found (status code 404).
    """
    db_user = crud.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db_user.role = role_update.role
    db.commit()
    db.refresh(db_user)
    return db_user


# Endpoint for getting a list of all users (available only to administrators)
@app.get("/users", response_model=List[models.UserResponse], dependencies=[Depends(auth.get_current_active_admin)])
async def get_all_users(db: Session = Depends(get_db)):
    """
    Returns a list of all registered users (only available to administrators).

    Args:
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        List[models.UserResponse]: List of information about all users.
    """
    users = crud.get_users(db)
    return users


# user
# Endpoint for obtaining information about the current user
@app.get("/users/me", response_model=models.UserResponse, dependencies=[Depends(auth.get_current_active_user), Depends(rate_limit.limit_user_me)])
async def get_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    """
    Returns information about the currently authenticated user.

    Args:
        current_user (models.User): The currently authenticated user.

    Returns:
        models.UserResponse: Information about the current user.
    """
    return current_user


# verification email
# Endpoint for sending email verification email
@app.post("/send-verification-email", status_code=status.HTTP_202_ACCEPTED)
async def send_verification(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Sends an email with a verification link to the current user's email address.

    Args:
        request (Request): FastAPI request object.
        db (Session, optional): Database session. Defaults to Depends(get_db).
        current_user (models.User): The current authenticated user.

    Returns:
        dict: The message that the email was sent.
    """
    token = email_utils.generate_verification_token(current_user.email)
    await email_utils.send_verification_email(current_user.email, token, app)
    return {"message": "Verification email sent"}


# Token-based email verification endpoint
@app.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify the user's email using the provided token.

    Args:
        token (str): Verification token from the email.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        dict: Message about successful verification or error.

    Raises:
        HTTPException: If the token is invalid or expired (status code 400).
    """
    if await email_utils.verify_email(token, db):
        return {"message": "Email verified successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")


# contacts
# Endpoints for contacts (requires authentication)
@app.post("/contacts", response_model=models.Contact, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth.get_current_active_user)])
async def create_contact(contact: models.ContactCreate, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Creates a new contact for the current user.

    Args:
        contact (models.ContactCreate): Data for the new contact.
        current_user (models.User): The current authenticated user.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        models.Contact: Information about the created contact.
    """
    return crud.create_contact(db=db, contact=contact, user_id=current_user.id)


@app.get("/contacts", response_model=List[models.Contact], dependencies=[Depends(auth.get_current_active_user)])
async def read_contacts(skip: int = 0, limit: int = 100, first_name: str = None, last_name: str = None, email: str = None, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Returns a list of contacts for the current user with optional filtering and pagination.

    Args:
        skip (int, optional): The number of contacts to skip. Defaults to 0.
        limit (int, optional): The maximum number of contacts to return. Defaults to 100.
        first_name (str, optional): Filter by first name. Defaults to None.
        last_name (str, optional): Filter by last name. Defaults to None.
        email (str, optional): Filter by email. Defaults to None.
        current_user (models.User): The currently authenticated user.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        List[models.Contact]: A list of the user's contacts.
    """
    contacts = crud.get_contacts(db, user_id=current_user.id, skip=skip, limit=limit, first_name=first_name, last_name=last_name, email=email)
    return contacts


@app.get("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def read_contact(contact_id: int, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Returns a specific contact by its ID for the current user.

    Args:
        contact_id (int): The ID of the contact to retrieve.
        current_user (models.User): The currently authenticated user.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        models.Contact: The requested contact information.

    Raises:
        HTTPException: If the contact with the given ID is not found for the current user (status code 404).
    """
    db_contact = crud.get_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return db_contact


@app.put("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def update_contact(contact_id: int, contact: models.ContactUpdate, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Updates an existing contact with the provided data for the current user.

    Args:
        contact_id (int): The ID of the contact to update.
        contact (models.ContactUpdate): The updated contact data.
        current_user (models.User): The currently authenticated user.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        models.Contact: The updated contact information.

    Raises:
        HTTPException: If the contact with the given ID is not found for the current user (status code 404).
    """
    db_contact = crud.update_contact(db=db, contact_id=contact_id, user_id=current_user.id, contact=contact)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return db_contact


@app.delete("/contacts/{contact_id}", response_model=models.Contact, dependencies=[Depends(auth.get_current_active_user)])
async def delete_contact(contact_id: int, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Deletes a specific contact by its ID for the current user.

    Args:
        contact_id (int): The ID of the contact to delete.
        current_user (models.User): The currently authenticated user.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        models.Contact: The deleted contact information.

    Raises:
        HTTPException: If the contact with the given ID is not found for the current user (status code 404).
    """
    db_contact = crud.get_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    if crud.delete_contact(db=db, contact_id=contact_id, user_id=current_user.id):
        return db_contact
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")


@app.get("/birthdays", response_model=List[models.Contact], dependencies=[Depends(auth.get_current_active_user)])
async def get_upcoming_birthdays(current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Returns a list of contacts with upcoming birthdays for the current user.

    Args:
        current_user (models.User): The currently authenticated user.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        List[models.Contact]: A list of contacts with upcoming birthdays.
    """
    return crud.get_upcoming_birthdays(db, user_id=current_user.id)


# password
# Endpoint for password reset request
@app.post("/password-reset-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(body: models.PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    """
    Initiates a password reset request for the user with the provided email.

    Args:
        body (models.PasswordResetRequest): An object containing the user's email.
        request (Request): The FastAPI request object.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A message indicating that a password reset link will be sent if the email is registered.
    """
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
    """
    Resets the user's password using the provided token and new password.

    Args:
        body (models.PasswordReset): An object containing the token, new password, and confirmation.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        JSONResponse: A message indicating that the password was successfully reset.

    Raises:
        HTTPException: If the new passwords do not match (status code 400),
                       if the password reset token is invalid (status code 400),
                       if the password reset token has expired (status code 400),
                       or if the user is not found (status code 404).
    """
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
    """
    Verifies the validity of a password reset token.

    Args:
        token (str): The password reset token to verify.
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        models.PasswordResetToken: Information about the valid password reset token.

    Raises:
        HTTPException: If the token is invalid or obsolete (status code 400).
    """
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
