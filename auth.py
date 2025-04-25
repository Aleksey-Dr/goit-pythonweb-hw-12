# auth.py

import os
from datetime import timedelta, timezone, datetime
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis_utils import get_redis, redis_client
from pydantic import ValidationError

import redis
import json
import database, models, crud

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
USER_CACHE_EXPIRE_SECONDS = 3600 # User cache lifetime (1 hour)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Generates a new access token.

    Args:
        data (dict): Dictionary containing the data to encode in the token.
        expires_delta (Optional[timedelta]): Optional timedelta object specifying the expiration time.
                                             If None, the default ACCESS_TOKEN_EXPIRE_MINUTES is used.

    Returns:
        str: The encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int):
    """
    Generates a new refresh token for a given user ID.

    Args:
        user_id (int): The ID of the user for whom to create the refresh token.

    Returns:
        str: The encoded JWT refresh token.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(database.get_db),
        redis: redis.Redis = Depends(get_redis),
    ):
    """
     Retrieves the current user based on the provided JWT access token.

     This function performs the following steps:
     1. Decodes the JWT token.
     2. Extracts the user's email and ID from the token's payload.
     3. Checks if the user data exists in the Redis cache.
     4. If found in the cache and valid, returns the cached user.
     5. If not found or invalid in the cache, queries the database for the user.
     6. If the user exists in the database, caches the user data in Redis.
     7. If the token is invalid or the user does not exist, raises an HTTPException.

     Args:
         token (str, optional): The JWT access token obtained from the Authorization header. Defaults to Depends(oauth2_scheme).
         db (Session, optional): The database session. Defaults to Depends(database.get_db).
         redis (redis.Redis, optional): The Redis client. Defaults to Depends(get_redis).

     Raises:
         HTTPException: If the token is invalid (401 Unauthorized) or the user does not exist.

     Returns:
         models.User: The authenticated user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("id")
        if email is None or user_id is None:
            raise credentials_exception
        token_data = models.TokenData(email=email, id=user_id)
    except JWTError:
        raise credentials_exception
    
    # Checking Redis cache
    cached_user_data = redis.get(f"user:{user_id}")
    if cached_user_data:
        try:
            cached_user = models.CachedUser.model_validate_json(cached_user_data)
            user = crud.get_user(db, user_id=cached_user.id)
            if user:
                return user
            else:
                await redis.delete(f"user:{user_id}") # Removing outdated cache
                pass
            return models.User.model_validate_json(cached_user_data)
        except ValidationError:
            # If the data in the cache is corrupted or does not match the User schema,
            # you can handle this situation (for example, remove the key from the cache and request it from the DB)
            await redis.delete(f"user:{user_id}")
            pass  # Go to query from database
    
    # If not in cache or validation error occurred, we access the database
    user = crud.get_user(db, user_id=token_data.id)
    if user is None:
        raise credentials_exception

    # Cache the user in Redis (use CachedUser for saving)
    cached_user = models.CachedUser.model_validate(user)
    redis.setex(f"user:{cached_user.id}", USER_CACHE_EXPIRE_SECONDS, cached_user.model_dump_json())
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    """
     Retrieves the currently active user.

     Args:
         current_user (models.User, optional): The current authenticated user object.
                                               Defaults to Depends(get_current_user).

     Raises:
         HTTPException: If the current user is inactive (400 Bad Request).

     Returns:
         models.User: The currently active user object.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user
