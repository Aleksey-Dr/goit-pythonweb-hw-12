# tests/test_crud.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

import crud
from models import UserCreate, ContactCreate, ContactUpdate
from database import UserDB, ContactDB, PasswordResetTokenDB


class TestPasswordFunctions(unittest.TestCase):
    def test_get_password_hash(self):
        password = "test_password"
        hashed_password = crud.get_password_hash(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(hashed_password.startswith("$2b$"))   # bcrypt hash

    def test_verify_password_valid(self):
        password = "test_password"
        hashed_password = crud.get_password_hash(password)
        self.assertTrue(crud.verify_password(password, hashed_password))

    def test_verify_password_invalid(self):
        password = "test_password"
        wrong_password = "wrong_password"
        hashed_password = crud.get_password_hash(password)
        self.assertFalse(crud.verify_password(wrong_password, hashed_password))

    def test_create_password_reset_token(self):
        mock_db = MagicMock(spec=Session)
        email = "test@example.com"
        token_db = crud.create_password_reset_token(mock_db, email)
        self.assertIsNotNone(token_db)
        self.assertEqual(token_db.email, email)
        self.assertIsNotNone(token_db.token)
        self.assertIsInstance(token_db.expires_at, datetime)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_get_password_reset_token_invalid(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        token_db = crud.get_password_reset_token(mock_db, "invalid_token")
        self.assertIsNone(token_db)

    def test_delete_password_reset_token_exists(self):
        mock_db = MagicMock(spec=Session)
        token_value = "test_token"
        existing_token_db = PasswordResetTokenDB(email="test@example.com", token=token_value, expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))
        mock_db.query().filter().first.return_value = existing_token_db
        crud.delete_password_reset_token(mock_db, token_value)
        mock_db.delete.assert_called_once_with(existing_token_db)
        mock_db.commit.assert_called_once()

    def test_delete_password_reset_token_not_exists(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        crud.delete_password_reset_token(mock_db, "nonexistent_token")
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_get_password_reset_token_by_email_invalid(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        token_db = crud.get_password_reset_token_by_email(mock_db, "nonexistent@example.com")
        self.assertIsNone(token_db)


class TestUserFunctions(unittest.TestCase):
    def test_get_user_by_email_valid(self):
        mock_db = MagicMock(spec=Session)
        email = "test@example.com"
        expected_user_db = UserDB(id=1, email=email, hashed_password="hashed", username="test")
        mock_db.query().filter().first.return_value = expected_user_db
        user_db = crud.get_user_by_email(mock_db, email)
        self.assertEqual(user_db, expected_user_db)

    def test_get_user_by_email_invalid(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        user_db = crud.get_user_by_email(mock_db, "nonexistent@example.com")
        self.assertIsNone(user_db)

    def test_get_user_by_id_valid(self):
        mock_db = MagicMock(spec=Session)
        user_id = 1
        expected_user_db = UserDB(id=user_id, email="test@example.com", hashed_password="hashed", username="test")
        mock_db.query().filter().first.return_value = expected_user_db
        user_db = crud.get_user(mock_db, user_id)
        self.assertEqual(user_db, expected_user_db)

    def test_get_user_by_id_invalid(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        user_db = crud.get_user(mock_db, 99)
        self.assertIsNone(user_db)

    def test_create_user(self):
        mock_db = MagicMock(spec=Session)
        user_create = UserCreate(email="new@example.com", password="new_password", username="new_user")
        expected_user_db = UserDB(id=1, email=user_create.email, hashed_password=crud.get_password_hash(user_create.password), username=user_create.username, role="user")
        mock_db.add.return_value = None
        mock_db.query().filter().first.return_value = None  # Simulate no existing user
        mock_db.refresh.return_value = expected_user_db
        crud.create_user(mock_db, user_create)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_user_avatar_exists(self):
        mock_db = MagicMock(spec=Session)
        user_id = 1
        avatar_url = "http://example.com/avatar.png"
        existing_user_db = UserDB(id=user_id, email="test@example.com", hashed_password="hashed", username="test")
        mock_db.query().filter().first.return_value = existing_user_db
        updated_user = crud.update_user_avatar(mock_db, user_id, avatar_url)
        self.assertEqual(updated_user.avatar_url, avatar_url)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_user_avatar_not_exists(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        updated_user = crud.update_user_avatar(mock_db, 99, "http://example.com/avatar.png")
        self.assertIsNone(updated_user)
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

    def test_update_user_refresh_token_exists(self):
        mock_db = MagicMock(spec=Session)
        user_id = 1
        refresh_token = "new_refresh_token"
        existing_user_db = UserDB(id=user_id, email="test@example.com", hashed_password="hashed", username="test")
        mock_db.query().filter().first.return_value = existing_user_db
        updated_user = crud.update_user_refresh_token(mock_db, user_id, refresh_token)
        self.assertEqual(updated_user.refresh_token, refresh_token)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_user_refresh_token_not_exists(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        updated_user = crud.update_user_refresh_token(mock_db, 99, "new_refresh_token")
        self.assertIsNone(updated_user)
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

    def test_get_user_by_refresh_token_valid(self):
        mock_db = MagicMock(spec=Session)
        refresh_token = "test_refresh_token"
        expected_user_db = UserDB(id=1, email="test@example.com", hashed_password="hashed", username="test", refresh_token=refresh_token)
        mock_db.query().filter().first.return_value = expected_user_db
        user_db = crud.get_user_by_refresh_token(mock_db, refresh_token)
        self.assertEqual(user_db, expected_user_db)

    def test_get_user_by_refresh_token_invalid(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query().filter().first.return_value = None
        user_db = crud.get_user_by_refresh_token(mock_db, "invalid_refresh_token")
        self.assertIsNone(user_db)


class TestContactFunctions(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock(spec=Session)
        self.user_id = 1
        self.contact_id = 10
        self.contact_data = ContactCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="123-456-7890",
            birthday=date(1990, 1, 15),
            additional_data="Some info"
        )
        self.contact_update_data = ContactUpdate(
            first_name="Updated John",
            email="updated.john@example.com"
        )
        self.existing_contact = ContactDB(id=self.contact_id, user_id=self.user_id, **self.contact_data.model_dump())

    def test_get_contact_not_exists(self):
        self.mock_db.query().filter().first.return_value = None
        contact = crud.get_contact(self.mock_db, self.contact_id, self.user_id)
        self.assertIsNone(contact)

    def test_create_contact(self):
        self.mock_db.add.return_value = None
        self.mock_db.refresh.return_value = ContactDB(id=self.contact_id, user_id=self.user_id, **self.contact_data.model_dump())
        contact = crud.create_contact(self.mock_db, self.contact_data, self.user_id)
        self.assertIsNotNone(contact)
        self.assertEqual(contact.user_id, self.user_id)
        self.assertEqual(contact.first_name, self.contact_data.first_name)
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_update_contact_exists(self):
        self.mock_db.query().filter().first.return_value = self.existing_contact
        updated_contact = crud.update_contact(self.mock_db, self.contact_id, self.user_id, self.contact_update_data)
        self.assertIsNotNone(updated_contact)