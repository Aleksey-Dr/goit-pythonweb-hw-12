# tests/integration/test_email_registration.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import unittest
from unittest.mock import patch
from fastapi import FastAPI, Depends, HTTPException
from fastapi.routing import APIRoute
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import crud
from database import Base, UserDB
import email_utils

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

app = FastAPI()

# Add middleware to ensure single-threaded access
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

@app.post("/register")
async def register_user(user: dict, db: Session = Depends(get_test_db)):
    db_user = crud.get_user_by_email(db, email=user["email"])
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db, user)
    token = email_utils.generate_verification_token(new_user.email)
    await email_utils.send_verification_email(new_user.email, token, app)
    return {"message": "Registration successful, please check your email"}

@app.get("/verify-email")
async def verify_email_endpoint(token: str, db: Session = Depends(get_test_db)):
    if email_utils.verify_email(token, db):
        return {"message": "Email verified successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# Update the test client to use the same thread for SQLite in-memory database
client = TestClient(app, raise_server_exceptions=True)

class TestEmailRegistrationIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_user_registration_sends_verification_email(self):
        with patch("email_utils.FastMail.send_message") as mock_send:
            response = client.post("/register", json={"email": "newuser@example.com", "password": "securepassword", "username": "newbie"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["message"], "Registration successful, please check your email")
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            message = args[0]
            self.assertEqual(message.recipients, ["newuser@example.com"])
            self.assertIn("http://localhost:8000/verify-email?token=", message.body)

    async def test_verification_endpoint_updates_user_status(self):
        user_data = {"email": "verifytest@example.com", "password": "testpass", "username": "verifyuser"}
        db_generator = get_test_db()
        db = next(db_generator)
        user = crud.create_user(db, user_data)
        token = email_utils.generate_verification_token(user.email)
        try:
            response = client.get(f"/verify-email?token={token}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["message"], "Email verified successfully")
            updated_user = crud.get_user_by_email(db, user.email)
            self.assertTrue(updated_user.is_verified)
        finally:
            try:
                next(db_generator)
            except StopIteration:
                pass

    async def test_verification_endpoint_with_invalid_token(self):
        response = client.get("/verify-email?token=invalid_token")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid or expired token")