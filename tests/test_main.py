# test_main.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from datetime import timedelta, timezone, datetime
from fastapi import HTTPException, status
from auth import pwd_context

from unittest.mock import MagicMock
from main import app, get_db, get_redis

import models
import crud
import auth
import email_utils
import cloudinary_utils
import database

ADMINTOKEN = os.environ.get("ADMINTOKEN")
USERTOKEN = os.environ.get("USERTOKEN")

# A fixture for creating a mock administrator
@pytest.fixture
def mock_admin():
    return MagicMock(
        spec=models.User,
        id=2,
        email="admin@example.com",
        username="adminuser",
        hashed_password="hashed_admin",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        avatar_url=None,
        role="admin",  # Ensure role is set to "admin"
        refresh_token=None
    )

# Fixture for creating a FastAPI test client with a mocked get_db dependency
@pytest.fixture
def test_app(mock_db, mock_redis, mock_user, mock_admin):
    def override_get_db():
        yield mock_db
    def override_get_redis():
        yield mock_redis
    def override_get_current_user():
        yield mock_user
    def override_get_current_admin():
        yield mock_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[auth.get_current_active_user] = override_get_current_user
    app.dependency_overrides[auth.get_current_active_admin] = override_get_current_admin
    
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = None
    mock.delete.return_value = None
    return mock

# Fixture for creating a mock user
@pytest.fixture
def mock_user():
    return MagicMock(
        spec=models.User,
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        avatar_url=None,
        role="user",
        refresh_token="valid_refresh_token"
    )

# Endpoint tests /register
def test_register_user_success(test_app, mock_db, mock_redis):
    user_data = {"email": "newuser@example.com", "password": "password", "username": "newuser"}
    mock_user_db = MagicMock(
        id=1,
        email="newuser@example.com",
        username="newuser",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(),
        avatar_url=None,
        role="user"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = mock_user_db
    crud.create_user = MagicMock(return_value=mock_user_db)
    test_app.app.dependency_overrides[get_db] = lambda: mock_db
    test_app.app.dependency_overrides[get_redis] = lambda: mock_redis
    response = test_app.post("/register", json=user_data)

    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["username"] == "newuser"
    assert response.json()["id"] == 1
    assert response.json()["is_active"] is True
    assert response.json()["is_verified"] is False
    assert isinstance(response.json()["created_at"], str)
    assert response.json()["role"] == "user"
    test_app.app.dependency_overrides.clear()

def test_register_user_email_exists(test_app, mock_db, mock_redis):
    user_data = {"email": "test@example.com", "password": "password", "username": "existinguser"}
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=database.UserDB, email="test@example.com")
    test_app.app.dependency_overrides[get_db] = lambda: mock_db
    test_app.app.dependency_overrides[get_redis] = lambda: mock_redis
    response = test_app.post("/register", json=user_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Email already registered"
    test_app.app.dependency_overrides = {}

# Endpoint tests /login
def test_login_success(test_app):
    form_data = {"username": "test@example.com", "password": "password"}
    mock_db = MagicMock()
    hashed_password = pwd_context.hash("password")
    mock_user = MagicMock(
        spec=models.User,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        id=1,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    auth.create_access_token = MagicMock(return_value="mock_token")
    
    test_app.app.dependency_overrides[get_db] = lambda: mock_db
    response = test_app.post("/login", data=form_data)
    assert response.status_code == 200
    assert response.json()["access_token"] == "mock_token"
    assert response.json()["token_type"] == "bearer"
    test_app.app.dependency_overrides = {}

def test_login_incorrect_password(test_app, mock_user):
    form_data = {"username": "test@example.com", "password": "wrong_password"}
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    test_app.app.dependency_overrides[get_db] = lambda: mock_db
    crud.verify_password = MagicMock(return_value=False)
    response = test_app.post("/login", data=form_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    test_app.app.dependency_overrides = {}

def test_login_user_not_found(test_app):
    form_data = {"username": "nonexistent@example.com", "password": "password"}
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    test_app.app.dependency_overrides[get_db] = lambda: mock_db
    response = test_app.post("/login", data=form_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    test_app.app.dependency_overrides = {}

# Endpoint tests /refresh-token
def test_refresh_access_token_success(test_app, mock_user):
    form_data = {"refresh_token": "valid_refresh_token"}
    mock_db = test_app.app.dependency_overrides[get_db]()
    crud.get_user_by_refresh_token.return_value = mock_user
    auth.create_access_token = MagicMock(return_value="new_mock_access_token")
    response = test_app.post("/refresh-token", data=form_data)
    assert response.status_code == 200
    assert response.json()["access_token"] == "new_mock_access_token"
    assert response.json()["token_type"] == "bearer"
    test_app.app.dependency_overrides.clear()

def test_refresh_access_token_invalid_token(test_app):
    form_data = {"refresh_token": "invalid_refresh_token"}
    mock_db = next(test_app.app.dependency_overrides[get_db]())
    crud.get_user_by_refresh_token = MagicMock(return_value=None)
    response = test_app.post("/refresh-token", data=form_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid refresh token"
    test_app.app.dependency_overrides.clear()

# Endpoint tests /admin/create-admin
def test_create_admin_success(test_app, mock_admin):
    admin_data = {
        "email": "newadmin@example.com",
        "password": "adminpass",
        "username": "newadmin"
    }
    
    # Mock the database response
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Create a mock of the created user
    created_admin = MagicMock(
        email="newadmin@example.com",
        username="newadmin",
        role="admin",
        id=3,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc)
    )
    
    crud.create_user = MagicMock(return_value=created_admin)
    
    response = test_app.post(
        "/admin/create-admin",
        json=admin_data,
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "newadmin@example.com"

def test_create_admin_not_admin(test_app, mock_user):
    admin_create_data = {"email": "newadmin@example.com", "password": "adminpassword", "username": "newadmin"}
    auth.get_current_active_user = MagicMock(return_value=mock_user)
    response = test_app.post("/admin/create-admin", json=admin_create_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough privileges"

def test_create_admin_email_exists(test_app, mock_admin):
    admin_create_data = {"email": "admin@example.com", "password": "adminpassword", "username": "existingadmin"}
    mock_db = next(test_app.app.dependency_overrides[get_db]())
    mock_db.query.return_value.filter.return_value.first.return_value = mock_admin
    response = test_app.post(
        "/admin/create-admin",
        json=admin_create_data,
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Email already registered"
    test_app.app.dependency_overrides.clear()

# Endpoint tests /users/me/avatar
def test_update_user_avatar_success(test_app, mock_admin):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_admin] = MagicMock(return_value=mock_admin)
    cloudinary_utils.upload_avatar = MagicMock(return_value="http://example.com/avatar.jpg")
    crud.update_user_avatar = MagicMock(return_value=mock_admin)
    response = test_app.post(
        "/users/me/avatar",
        data={"file": "base64_encoded_image"},
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["avatar_url"] == "http://example.com/avatar.jpg"
    test_app.app.dependency_overrides.clear()

def test_update_user_avatar_upload_fails(test_app, mock_admin):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_admin] = MagicMock(return_value=mock_admin)
    cloudinary_utils.upload_avatar = MagicMock(return_value=None)
    response = test_app.post(
        "/users/me/avatar",
        data={"file": "base64_encoded_image"},
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to upload avatar to Cloudinary"
    test_app.app.dependency_overrides.clear()

def test_update_user_avatar_db_fails(test_app, mock_admin):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_admin] = MagicMock(return_value=mock_admin)
    cloudinary_utils.upload_avatar = MagicMock(return_value="http://example.com/avatar.jpg")
    crud.update_user_avatar = MagicMock(return_value=None)
    response = test_app.post(
        "/users/me/avatar",
        data={"file": "base64_encoded_image"},
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to update avatar in database"
    test_app.app.dependency_overrides.clear()

# Endpoint tests /users/{user_id}/role
def test_update_user_role_success(test_app, mock_admin):
    # Mocking data
    mock_db = MagicMock()
    user_to_update = MagicMock(
        id=2,
        email="user@example.com",
        username="user",
        role="user"
    )
    
    crud.get_user.return_value = user_to_update
    
    response = test_app.put(
        "/users/2/role",
        json={"role": "editor"},
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "editor"

def test_update_user_role_not_admin(test_app, mock_user):
    auth.get_current_active_admin = MagicMock(side_effect=HTTPException(status_code=403, detail="Not enough privileges"))
    response = test_app.put("/users/1/role", json={"role": "editor"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough privileges"

def test_update_user_role_user_not_found(test_app, mock_admin):
    mock_db = test_app.app.dependency_overrides[get_db]()
    auth.get_current_active_admin = MagicMock(return_value=mock_admin)
    crud.get_user.return_value = None
    response = test_app.put(
        "/users/1/role",
        json={"role": "editor"},
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    test_app.app.dependency_overrides.clear()

# Endpoint tests /users
def test_get_all_users_success(test_app, mock_admin, mock_user):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_admin] = MagicMock(return_value=mock_admin)
    crud.get_users.return_value = [mock_user]
    response = test_app.get(
        "/users",
        headers={"Authorization": f"Bearer {ADMINTOKEN}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "test@example.com"
    test_app.app.dependency_overrides.clear()

def test_get_all_users_not_admin(test_app, mock_user):
    auth.get_current_active_admin = MagicMock(side_effect=HTTPException(status_code=403, detail="Not enough privileges"))
    response = test_app.get("/users")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough privileges"

# Endpoint tests /users/me
def test_get_users_me_authenticated(test_app, mock_user):
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    response = test_app.get("/users/me", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    test_app.app.dependency_overrides.clear()

def test_get_users_me_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.get("/users/me")
    assert response.status_code == 401

# Endpoint tests /send-verification-email
def test_send_verification_email_success(test_app, mock_user):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    email_utils.generate_verification_token = MagicMock(return_value="mock_token")
    email_utils.send_verification_email = MagicMock(return_value=None)
    response = test_app.post(
        "/send-verification-email",
        headers={"Authorization": f"Bearer {USERTOKEN}"}
    )
    assert response.status_code == 202
    assert response.json()["message"] == "Verification email sent"
    test_app.app.dependency_overrides.clear()

def test_send_verification_email_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.post("/send-verification-email")
    assert response.status_code == 401 # Or another code for unauthorized users

# Endpoint tests /verify-email
@pytest.mark.asyncio
def test_verify_email_success(test_app):
    mock_db = test_app.app.dependency_overrides[get_db]()
    email_utils.verify_email = AsyncMock(return_value=True)
    response = test_app.get("/verify-email?token=valid_token")
    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully"
    test_app.app.dependency_overrides.clear()

@pytest.mark.asyncio
def test_verify_email_invalid_token(test_app):
    mock_db = test_app.app.dependency_overrides[get_db]()
    email_utils.verify_email = AsyncMock(return_value=False)
    response = test_app.get("/verify-email?token=invalid_token")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"
    test_app.app.dependency_overrides.clear()

# Fixture for creating a mock contact
@pytest.fixture
def mock_contact():
    return models.Contact(
        id=1,
        first_name="Test",
        last_name="Contact",
        email="test.contact@example.com",
        phone_number="111-222-3333",
        birthday="2023-01-01",
        user_id=1
    )

# Endpoint tests POST /contacts (creating a contact)
def test_create_contact_success(test_app, mock_user, mock_contact):
    contact_data = {
        "first_name": "New",
        "last_name": "Contact",
        "email": "new.contact@example.com",
        "phone_number": "444-555-6666",
        "birthday": "2024-02-02"
    }
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    mock_contact.id = 1
    crud.create_contact = MagicMock(return_value=mock_contact)
    response = test_app.post(
        "/contacts",
        headers={"Authorization": f"Bearer {USERTOKEN}"},
        json=contact_data
    )
    assert response.status_code == 201

def test_create_contact_unauthenticated(test_app):
    contact_data = {
        "first_name": "New",
        "last_name": "Contact",
        "email": "new.contact@example.com",
        "phone_number": "444-555-6666",
        "birthday": "2024-02-02"
    }
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.post("/contacts", json=contact_data)
    assert response.status_code == 401

# Endpoint tests GET /contacts (getting all contacts)
# add usertoken
def test_read_contacts_success(test_app, mock_user, mock_contact):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_contacts = MagicMock(return_value=[mock_contact])
    response = test_app.get("/contacts", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["first_name"] == "Test"
    assert response.json()[0]["user_id"] == 1
    test_app.app.dependency_overrides.clear()

def test_read_contacts_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.get("/contacts")
    assert response.status_code == 401

def test_read_contacts_with_filters(test_app, mock_user, mock_contact):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_contacts = MagicMock(return_value=[mock_contact])
    response = test_app.get("/contacts?first_name=Test&email=test.contact@example.com", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["first_name"] == "Test"
    crud.get_contacts.assert_called_once_with(
        mock_db,
        user_id=mock_user.id,
        skip=0,
        limit=100,
        first_name="Test",
        last_name=None,
        email="test.contact@example.com"
    )
    test_app.app.dependency_overrides.clear()

# Endpoint tests GET /contacts/{contact_id} (receiving one contact)
def test_read_contact_success(test_app, mock_user, mock_contact):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_contact = MagicMock(return_value=mock_contact)
    response = test_app.get("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["first_name"] == "Test"
    crud.get_contact.assert_called_once_with(mock_db, contact_id=1, user_id=mock_user.id)
    test_app.app.dependency_overrides.clear()

# add usertoken
def test_read_contact_not_found(test_app, mock_user):
    mock_db = test_app.app.dependency_overrides[get_db]()
    auth.get_current_active_user = MagicMock(return_value=mock_user)
    crud.get_contact = MagicMock(return_value=None)
    response = test_app.get("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"
    test_app.app.dependency_overrides.clear()

def test_read_contact_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.get("/contacts/1")
    assert response.status_code == 401

# Endpoint tests PUT /contacts/{contact_id} (contact update)
def test_update_contact_success(test_app, mock_user, mock_contact):
    contact_update_data = {"first_name": "Updated"}
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.update_contact = MagicMock(return_value=mock_contact)
    response = test_app.put("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"}, json=contact_update_data)
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["first_name"] == "Updated"
    crud.update_contact.assert_called_once_with(
        mock_db,
        contact_id=1,
        user_id=mock_user.id,
        contact=models.ContactUpdate(**contact_update_data)
    )
    test_app.app.dependency_overrides.clear()

# add usertoken
def test_update_contact_not_found(test_app, mock_user):
    contact_update_data = {"first_name": "Updated"}
    mock_db = test_app.app.dependency_overrides[get_db]()
    auth.get_current_active_user = MagicMock(return_value=mock_user)
    crud.update_contact = MagicMock(return_value=None)
    response = test_app.put("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"}, json=contact_update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"
    test_app.app.dependency_overrides.clear()

def test_update_contact_unauthenticated(test_app):
    contact_update_data = {"first_name": "Updated"}
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.put("/contacts/1", json=contact_update_data)
    assert response.status_code == 401

# Endpoint tests DELETE /contacts/{contact_id} (delete contact)
def test_delete_contact_success(test_app, mock_user, mock_contact):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_contact = MagicMock(return_value=mock_contact)
    crud.delete_contact = MagicMock(return_value=True)
    response = test_app.delete("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert response.json()["id"] == 1
    crud.get_contact.assert_called_once_with(mock_db, contact_id=1, user_id=mock_user.id)
    crud.delete_contact.assert_called_once_with(mock_db, contact_id=1, user_id=mock_user.id)
    test_app.app.dependency_overrides.clear()

# add usertoken
def test_delete_contact_not_found(test_app, mock_user):
    mock_db = test_app.app.dependency_overrides[get_db]()
    auth.get_current_active_user = MagicMock(return_value=mock_user)
    crud.get_contact = MagicMock(return_value=None)
    response = test_app.delete("/contacts/1", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"
    test_app.app.dependency_overrides.clear()

def test_delete_contact_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.delete("/contacts/1")
    assert response.status_code == 401

# Endpoint tests GET /birthdays (getting future birthdays)
def test_get_upcoming_birthdays_success(test_app, mock_user, mock_contact):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_upcoming_birthdays = MagicMock(return_value=[mock_contact])
    response = test_app.get("/birthdays", headers={"Authorization": f"Bearer {USERTOKEN}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["first_name"] == "Test"
    crud.get_upcoming_birthdays.assert_called_once_with(mock_db, user_id=mock_user.id)
    test_app.app.dependency_overrides.clear()

# add usertoken
def test_get_upcoming_birthdays_empty(test_app, mock_user):
    mock_db = test_app.app.dependency_overrides[get_db]()
    test_app.app.dependency_overrides[auth.get_current_active_user] = MagicMock(return_value=mock_user)
    crud.get_upcoming_birthdays = MagicMock(return_value=[])
    response = test_app.get(
        "/birthdays",
        headers={"Authorization": f"Bearer {USERTOKEN}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0
    test_app.app.dependency_overrides.clear()

def test_get_upcoming_birthdays_unauthenticated(test_app):
    auth.get_current_active_user = MagicMock(return_value=None)
    response = test_app.get("/birthdays")
    assert response.status_code == 401