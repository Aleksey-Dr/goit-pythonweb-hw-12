# tests/integration/test_crud_db.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

import crud
import models
from database import Base, UserDB, ContactDB
from models import UserCreate, ContactCreate

TEST_DATABASE_URL = os.environ.get("DATABASE_URL")
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

class TestCRUDIntegration(unittest.TestCase):
    def setUp(self):
        self.db_generator = get_test_db()
        self.db = next(self.db_generator)
        self.user = crud.create_user(self.db, UserCreate(email="test@example.com", password="password123", username="testuser"))

    def tearDown(self):
        try:
            next(self.db_generator) # Close and drop tables
        except StopIteration:
            pass

    def test_get_users(self):
        user2 = crud.create_user(self.db, UserCreate(email="test2@example.com", password="password456", username="testuser2"))
        users = crud.get_users(self.db, skip=0, limit=100)
        self.assertEqual(len(users), 2)
        self.assertIn(self.user.email, [u.email for u in users])
        self.assertIn(user2.email, [u.email for u in users])

    def test_get_user_by_id(self):
        retrieved_user = crud.get_user(self.db, self.user.id)
        self.assertEqual(self.user.email, retrieved_user.email)

    def test_update_user_avatar(self):
        avatar_url = "http://example.com/avatar.png"
        updated_user = crud.update_user_avatar(self.db, self.user.id, avatar_url)
        self.assertEqual(updated_user.avatar_url, avatar_url)
        retrieved_user = crud.get_user(self.db, self.user.id)
        self.assertEqual(retrieved_user.avatar_url, avatar_url)

    def test_create_contact_and_get_contact(self):
        contact_data = ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="123-456-7890", birthday=date(1990, 1, 15))
        contact = crud.create_contact(self.db, contact_data, self.user.id)
        self.assertIsNotNone(contact.id)
        retrieved_contact = crud.get_contact(self.db, contact.id, self.user.id)
        self.assertEqual(contact.email, retrieved_contact.email)
        self.assertEqual(retrieved_contact.owner, self.user)

    def test_get_contacts_for_user(self):
        contact1_data = ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="123-456-7890", birthday=date(1990, 1, 15))
        crud.create_contact(self.db, contact1_data, self.user.id)
        contact2_data = ContactCreate(first_name="Jane", last_name="Smith", email="jane.smith@example.com", phone_number="987-654-3210", birthday=date(1985, 5, 20))
        crud.create_contact(self.db, contact2_data, self.user.id)
        contacts = crud.get_contacts(self.db, self.user.id, skip=0, limit=100)
        self.assertEqual(len(contacts), 2)
        self.assertIn(contact1_data.email, [c.email for c in contacts])
        self.assertIn(contact2_data.email, [c.email for c in contacts])

    def test_get_contacts_with_filters(self):
        contact1_data = ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="123-456-7890", birthday=date(1990, 1, 15))
        crud.create_contact(self.db, contact1_data, self.user.id)
        contact2_data = ContactCreate(first_name="Jane", last_name="Smith", email="jane.smith@example.com", phone_number="987-654-3210", birthday=date(1985, 5, 20))
        crud.create_contact(self.db, contact2_data, self.user.id)
        contacts = crud.get_contacts(self.db, self.user.id, first_name="John")
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].first_name, "John")

    def test_update_contact(self):
        contact_data = ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="123-456-7890", birthday=date(1990, 1, 15))
        contact = crud.create_contact(self.db, contact_data, self.user.id)
        updated_data = models.ContactUpdate(first_name="Johnny", email="johnny.doe@example.com")
        updated_contact = crud.update_contact(self.db, contact.id, self.user.id, updated_data)
        self.assertEqual(updated_contact.first_name, "Johnny")
        self.assertEqual(updated_contact.email, "johnny.doe@example.com")
        retrieved_contact = crud.get_contact(self.db, contact.id, self.user.id)
        self.assertEqual(retrieved_contact.first_name, "Johnny")
        self.assertEqual(retrieved_contact.email, "johnny.doe@example.com")

    def test_delete_contact(self):
        contact_data = ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="123-456-7890", birthday=date(1990, 1, 15))
        contact = crud.create_contact(self.db, contact_data, self.user.id)
        crud.delete_contact(self.db, contact.id, self.user.id)
        retrieved_contact = crud.get_contact(self.db, contact.id, self.user.id)
        self.assertIsNone(retrieved_contact)