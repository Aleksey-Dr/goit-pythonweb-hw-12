# tests/test_models.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from datetime import date, datetime, timedelta

from pydantic import ValidationError

from models import (
    ContactBase,
    ContactCreate,
    ContactUpdate,
    Contact,
    UserBase,
    UserCreate,
    User,
    UserResponse,
    CachedUser,
    Token,
    TokenData,
    TokenPair,
    Email,
    AvatarUpdate,
    PasswordResetRequest,
    PasswordReset,
    PasswordResetToken,
)


class TestContactModels(unittest.TestCase):
    def test_contact_base_valid(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "123-456-7890",
            "birthday": date(1990, 1, 15),
        }
        contact = ContactBase(**data)
        self.assertEqual(contact.first_name, "John")
        self.assertEqual(contact.email, "john.doe@example.com")
        self.assertIsInstance(contact.birthday, date)

    def test_contact_base_invalid_email(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid-email",
            "phone_number": "123-456-7890",
            "birthday": date(1990, 1, 15),
        }
        with self.assertRaises(ValidationError):
            ContactBase(**data)

    def test_contact_create_valid(self):
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "phone_number": "987-654-3210",
            "birthday": date(1985, 5, 20),
            "additional_data": "Loves hiking",
        }
        contact_create = ContactCreate(**data)
        self.assertEqual(contact_create.first_name, "Jane")
        self.assertEqual(contact_create.additional_data, "Loves hiking")

    def test_contact_update_valid(self):
        data = {
            "first_name": "Updated Jane",
            "email": "updated.jane@example.com",
        }
        contact_update = ContactUpdate(**data)
        self.assertEqual(contact_update.first_name, "Updated Jane")
        self.assertEqual(contact_update.email, "updated.jane@example.com")
        self.assertIsNone(contact_update.last_name)

    def test_contact_valid(self):
        data = {
            "id": 1,
            "user_id": 10,
            "first_name": "Peter",
            "last_name": "Jones",
            "email": "peter.jones@example.com",
            "phone_number": "555-123-4567",
            "birthday": date(2000, 12, 1),
        }
        contact = Contact(**data)
        self.assertEqual(contact.id, 1)
        self.assertEqual(contact.user_id, 10)
        self.assertEqual(contact.email, "peter.jones@example.com")


class TestUserModels(unittest.TestCase):
    def test_user_base_valid(self):
        data = {"email": "test@user.com", "password": "securepassword"}
        user_base = UserBase(**data)
        self.assertEqual(user_base.email, "test@user.com")
        self.assertEqual(user_base.password, "securepassword")

    def test_user_base_invalid_email(self):
        data = {"email": "invalid", "password": "securepassword"}
        with self.assertRaises(ValidationError):
            UserBase(**data)

    def test_user_create_valid(self):
        data = {"email": "new@user.com", "password": "newpassword", "username": "newuser"}
        user_create = UserCreate(**data)
        self.assertEqual(user_create.email, "new@user.com")
        self.assertEqual(user_create.username, "newuser")

    def test_user_response_valid(self):
        now = datetime.now()
        data = {
            "id": 4,
            "username": "responser",
            "email": "response@user.com",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "avatar_url": "http://example.com/avatar.png",
            "role": "admin",
        }
        user_response = UserResponse(**data)
        self.assertEqual(user_response.id, 4)
        self.assertEqual(user_response.email, "response@user.com")
        self.assertEqual(user_response.avatar_url, "http://example.com/avatar.png")
        self.assertEqual(user_response.role, "admin")

    def test_cached_user_valid(self):
        data = {
            "id": 5,
            "username": "cached",
            "email": "cached@user.com",
            "is_active": True,
            "is_verified": False,
            "avatar_url": "http://example.com/cached_avatar.png",
        }
        cached_user = CachedUser(**data)
        self.assertEqual(cached_user.id, 5)
        self.assertEqual(cached_user.avatar_url, "http://example.com/cached_avatar.png")

    def test_token_valid(self):
        data = {"access_token": "some_token", "token_type": "bearer"}
        token = Token(**data)
        self.assertEqual(token.access_token, "some_token")
        self.assertEqual(token.token_type, "bearer")

    def test_token_data_valid(self):
        data = {"email": "token@data.com", "id": 6}
        token_data = TokenData(**data)
        self.assertEqual(token_data.email, "token@data.com")
        self.assertEqual(token_data.id, 6)

    def test_token_pair_valid(self):
        data = {"access_token": "access", "refresh_token": "refresh", "token_type": "bearer"}
        token_pair = TokenPair(**data)
        self.assertEqual(token_pair.access_token, "access")
        self.assertEqual(token_pair.refresh_token, "refresh")
        self.assertEqual(token_pair.token_type, "bearer")

    def test_email_valid(self):
        data = {"email": "valid@email.com"}
        email = Email(**data)
        self.assertEqual(email.email, "valid@email.com")

    def test_avatar_update_valid(self):
        data = {"file": "base64_encoded_image"}
        avatar_update = AvatarUpdate(**data)
        self.assertEqual(avatar_update.file, "base64_encoded_image")

    def test_password_reset_request_valid(self):
        data = {"email": "reset@request.com"}
        reset_request = PasswordResetRequest(**data)
        self.assertEqual(reset_request.email, "reset@request.com")

    def test_password_reset_valid(self):
        data = {"token": "reset_token", "new_password": "new_pass", "confirm_new_password": "new_pass"}
        password_reset = PasswordReset(**data)
        self.assertEqual(password_reset.token, "reset_token")
        self.assertEqual(password_reset.new_password, "new_pass")
        self.assertEqual(password_reset.confirm_new_password, "new_pass")

    def test_password_reset_token_valid(self):
        now = datetime.now()
        expiry = now + timedelta(hours=1)
        data = {"token": "auth_token", "email": "token@email.com", "expires_at": expiry}
        reset_token = PasswordResetToken(**data)
        self.assertEqual(reset_token.token, "auth_token")
        self.assertEqual(reset_token.email, "token@email.com")
        self.assertEqual(reset_token.expires_at, expiry)


if __name__ == "__main__":
    unittest.main()