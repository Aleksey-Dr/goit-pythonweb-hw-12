# tests/test_database.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

import unittest
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, ContactDB, UserDB, PasswordResetTokenDB, get_db


# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Overrides the get_db dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestDatabaseModels(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_create_contact(self):
        user = UserDB(username="testuser", email="test@example.com", hashed_password="hashed")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        contact = ContactDB(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="123-456-7890",
            birthday=date(1990, 1, 15),
            user_id=user.id,
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)

        retrieved_contact = self.db.query(ContactDB).filter(ContactDB.id == contact.id).first()
        self.assertEqual(retrieved_contact.first_name, "John")
        self.assertEqual(retrieved_contact.owner, user)

    def test_create_user(self):
        user = UserDB(username="testuser", email="test@example.com", hashed_password="hashed")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        retrieved_user = self.db.query(UserDB).filter(UserDB.id == user.id).first()
        self.assertEqual(retrieved_user.username, "testuser")
        self.assertTrue(retrieved_user.is_active)
        self.assertFalse(retrieved_user.is_verified)
        self.assertIsNotNone(retrieved_user.created_at)
        self.assertEqual(retrieved_user.role, "user")
        self.assertIsNone(retrieved_user.avatar_url)
        self.assertIsNone(retrieved_user.refresh_token)

    def test_create_password_reset_token(self):
        token = PasswordResetTokenDB(email="test@example.com", token="test_token", expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)

        retrieved_token = self.db.query(PasswordResetTokenDB).filter(PasswordResetTokenDB.token == token.token).first()
        self.assertEqual(retrieved_token.email, "test@example.com")
        self.assertEqual(retrieved_token.token, "test_token")
        self.assertIsNotNone(retrieved_token.expires_at)
        self.assertIsNotNone(retrieved_token.created_at)

    def test_contact_user_relationship(self):
        user = UserDB(username="owner", email="owner@example.com", hashed_password="hashed")
        contact1 = ContactDB(first_name="Alice", last_name="Smith", email="alice.smith@example.com", phone_number="111-222-3333", birthday=date(1988, 7, 22), owner=user)
        contact2 = ContactDB(first_name="Bob", last_name="Johnson", email="bob.johnson@example.com", phone_number="444-555-6666", birthday=date(1992, 3, 10), owner=user)

        self.db.add_all([user, contact1, contact2])
        self.db.commit()
        self.db.refresh(user)

        retrieved_user = self.db.query(UserDB).filter(UserDB.id == user.id).first()
        self.assertEqual(len(retrieved_user.contacts), 2)
        self.assertEqual(retrieved_user.contacts[0].first_name, "Alice")
        self.assertEqual(retrieved_user.contacts[1].first_name, "Bob")
        self.assertEqual(retrieved_user.contacts[0].owner, user)
        self.assertEqual(retrieved_user.contacts[1].owner, user)

    def test_get_db_dependency(self):
        """Tests the get_db dependency function."""
        db_generator = get_db()
        db_session = next(db_generator)
        self.assertIsNotNone(db_session)
        db_session.close() # Simulate the 'finally' block

if __name__ == "__main__":
    unittest.main()