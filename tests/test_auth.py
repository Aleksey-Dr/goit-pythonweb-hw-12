# tests/test_auth.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import timedelta, datetime
from unittest.mock import MagicMock

import pytest
from jose import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_active_user,
    get_current_active_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ALGORITHM,
    SECRET_KEY,
    USER_CACHE_EXPIRE_SECONDS,
)
from models import User, TokenData, CachedUser
from database import get_db
import crud
import redis

# Set a test secret key if not already set
if not SECRET_KEY:
    os.environ["SECRET_KEY"] = "test_secret_key"
    SECRET_KEY = os.environ.get("SECRET_KEY")

# Mock database session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Mock Redis client
@pytest.fixture
def mock_redis():
    return MagicMock(spec=redis.Redis)

# Sample user data for testing
now = datetime.now()
test_user = User(id=1, email="test@example.com", username="testuser", password="hashed_password", is_active=True, role="user", created_at=now)
test_admin = User(id=2, email="admin@example.com", username="adminuser", password="hashed_password", is_active=True, role="admin", created_at=now)
test_inactive_user = User(id=3, email="inactive@example.com", username="inactive", password="hashed_password", is_active=False, role="user", created_at=now)

def test_create_access_token():
    data = {"sub": "test@example.com", "id": 1}
    token = create_access_token(data)
    assert isinstance(token, str)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert payload["id"] == 1
    assert "exp" in payload

    expires_delta = timedelta(minutes=60)
    token_with_expiry = create_access_token(data, expires_delta=expires_delta)
    payload_with_expiry = jwt.decode(token_with_expiry, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload_with_expiry["exp"] > payload["exp"]

def test_create_refresh_token():
    user_id = 1
    token = create_refresh_token(user_id)
    assert isinstance(token, str)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "exp" in payload
    # Check if expiration is roughly 7 days from now (cannot be exact due to time differences)
    expected_expiry = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expiry_from_now = datetime.fromtimestamp(payload["exp"]) - datetime.now()
    assert expiry_from_now > expected_expiry - timedelta(seconds=60)
    assert expiry_from_now < expected_expiry + timedelta(seconds=60)

@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db, mock_redis):
    token_data = {"sub": "test@example.com", "id": 1}
    access_token = create_access_token(token_data)

    mock_redis.get.return_value = None  # Simulate no cache hit
    crud.get_user.return_value = test_user

    user = await get_current_user(token=access_token, db=mock_db, redis=mock_redis)
    assert user == test_user
    mock_redis.get.assert_called_once_with("user:1")
    crud.get_user.assert_called_once_with(mock_db, user_id=1)
    mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_get_current_user_valid_token_from_cache(mock_db, mock_redis):
    token_data = {"sub": "test@example.com", "id": 1}
    access_token = create_access_token(token_data)
    cached_user = CachedUser.model_validate(test_user)
    mock_redis.get.return_value = cached_user.model_dump_json()

    user = await get_current_user(token=access_token, db=mock_db, redis=mock_redis)
    assert user.id == test_user.id
    assert user.email == test_user.email
    mock_redis.get.assert_called_once_with("user:1")
    crud.get_user.assert_not_called()
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db, mock_redis):
    invalid_token = "invalid_token"
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=invalid_token, db=mock_db, redis=mock_redis)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in excinfo.value.detail
    mock_redis.get.assert_not_called()
    crud.get_user.assert_not_called()
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_get_current_user_expired_token(mock_db, mock_redis):
    expired_data = {"sub": "test@example.com", "id": 1, "exp": 0}
    expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=expired_token, db=mock_db, redis=mock_redis)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in excinfo.value.detail
    mock_redis.get.assert_not_called()
    crud.get_user.assert_not_called()
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mock_db, mock_redis):
    token_data = {"sub": "test@example.com", "id": 999}
    access_token = create_access_token(token_data)

    mock_redis.get.return_value = None
    crud.get_user.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=access_token, db=mock_db, redis=mock_redis)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in excinfo.value.detail
    mock_redis.get.assert_called_once_with("user:999")
    crud.get_user.assert_called_once_with(mock_db, user_id=999)
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_get_current_user_invalid_cached_data(mock_db, mock_redis):
    token_data = {"sub": "test@example.com", "id": 1}
    access_token = create_access_token(token_data)
    mock_redis.get.return_value = '{"invalid": "data"}' # Simulate corrupted cache

    crud.get_user.return_value = test_user

    user = await get_current_user(token=access_token, db=mock_db, redis=mock_redis)
    assert user == test_user
    mock_redis.get.assert_called_once_with("user:1")
    mock_redis.delete.assert_called_once_with("user:1")
    crud.get_user.assert_called_once_with(mock_db, user_id=1)
    mock_redis.setex.assert_called_once()

def test_get_current_active_user_active(mock_db):
    active_user = get_current_active_user(current_user=test_user)
    assert active_user == test_user

def test_get_current_active_user_inactive():
    with pytest.raises(HTTPException) as excinfo:
        get_current_active_user(current_user=test_inactive_user)
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Inactive user" in excinfo.value.detail

def test_get_current_active_admin_admin(mock_db):
    admin_user = get_current_active_admin(current_user=test_admin)
    assert admin_user == test_admin

def test_get_current_active_admin_not_admin():
    with pytest.raises(HTTPException) as excinfo:
        get_current_active_admin(current_user=test_user)
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Not enough privileges" in excinfo.value.detail

def test_get_current_active_admin_inactive():
    with pytest.raises(HTTPException) as excinfo:
        get_current_active_admin(current_user=test_inactive_user)
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Inactive user" in excinfo.value.detail