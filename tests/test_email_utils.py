# tests/test_email_utils.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from sqlalchemy.orm import Session
from jose import jwt

import email_utils
import crud
from database import UserDB

# Mock environment variables
os.environ["MAIL_USERNAME"] = "test_username"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["MAIL_SERVER"] = "test_server"
os.environ["MAIL_PORT"] = "587"
os.environ["MAIL_FROM"] = "test@example.com"
os.environ["SECRET_KEY"] = "test_secret_key"

class TestEmailUtils(unittest.IsolatedAsyncioTestCase):

    def test_generate_verification_token(self):
        """
        Tests if the generate_verification_token function generates a valid JWT.
        """
        email = "test@example.com"
        token = email_utils.generate_verification_token(email)
        self.assertIsNotNone(token)

        # Try to decode the token to verify its structure
        try:
            payload = jwt.decode(token, os.environ.get("SECRET_KEY"), algorithms=["HS256"])
            self.assertEqual(payload.get("sub"), email)
        except jwt.JWTError as e:
            self.fail(f"Generated token is invalid: {e}")

    async def test_verify_email_valid_token_user_exists_not_verified(self):
        """
        Tests verify_email with a valid token, existing and not verified user.
        Mocks crud.get_user_by_email and the database session.
        """
        email = "test@example.com"
        token = jwt.encode({"sub": email}, os.environ.get("SECRET_KEY"), algorithm="HS256")
        user_mock = UserDB(id=1, email=email, hashed_password="hashed", username="test", is_verified=False)
        db_mock = AsyncMock(spec=Session)
        db_mock.query().filter().first.return_value = user_mock

        with patch("crud.get_user_by_email", return_value=user_mock):
            result = await email_utils.verify_email(token, db_mock)
            self.assertTrue(result)
            self.assertTrue(user_mock.is_verified)
            db_mock.commit.assert_called_once()
            db_mock.refresh.assert_called_once_with(user_mock)

    async def test_verify_email_invalid_token(self):
        """
        Tests verify_email with an invalid token.
        Mocks the database session.
        """
        invalid_token = "invalid_token"
        db_mock = AsyncMock(spec=Session)

        result = await email_utils.verify_email(invalid_token, db_mock)
        self.assertFalse(result)
        db_mock.query.assert_not_called()
        db_mock.commit.assert_not_called()

    async def test_verify_email_valid_token_user_not_exists(self):
        """
        Tests verify_email with a valid token but user does not exist.
        Mocks crud.get_user_by_email and the database session.
        """
        email = "test@example.com"
        token = jwt.encode({"sub": email}, os.environ.get("SECRET_KEY"), algorithm="HS256")
        db_mock = AsyncMock(spec=Session)
        db_mock.query().filter().first.return_value = None

        with patch("crud.get_user_by_email", return_value=None):
            result = await email_utils.verify_email(token, db_mock)
            self.assertFalse(result)
            db_mock.commit.assert_not_called()

    async def test_verify_email_valid_token_user_already_verified(self):
        """
        Tests verify_email with a valid token but user is already verified.
        Mocks crud.get_user_by_email and the database session.
        """
        email = "test@example.com"
        token = jwt.encode({"sub": email}, os.environ.get("SECRET_KEY"), algorithm="HS256")
        user_mock = UserDB(id=1, email=email, hashed_password="hashed", username="test", is_verified=True)
        db_mock = AsyncMock(spec=Session)
        db_mock.query().filter().first.return_value = user_mock

        with patch("crud.get_user_by_email", return_value=user_mock):
            result = await email_utils.verify_email(token, db_mock)
            self.assertFalse(result)
            db_mock.commit.assert_not_called()

    async def test_verify_email_valid_token_no_sub_in_payload(self):
        """
        Tests verify_email with a valid token but without 'sub' (email) in the payload.
        """
        invalid_payload_token = jwt.encode({"other": "data"}, os.environ.get("SECRET_KEY"), algorithm="HS256")
        db_mock = AsyncMock(spec=Session)

        result = await email_utils.verify_email(invalid_payload_token, db_mock)
        self.assertFalse(result)
        db_mock.query.assert_not_called()

if __name__ == "__main__":
    unittest.main()