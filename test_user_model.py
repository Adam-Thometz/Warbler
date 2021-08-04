"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import app

db.create_all()


class UserModelTestCase(TestCase):
    """Test user model."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        u1 = User.signup('Spongebob', 'sponge@bikini-bottom.com', 'password', None)
        u2 = User.signup('Patrick', 'pat@bikini-bottom.com', 'password2', None)

        db.session.commit()

        u1 = User.query.get(1)
        u2 = User.query.get(2)

        self.u1 = u1
        self.u2 = u2

        self.client = app.test_client()
    
    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
    
    def test_repr(self):
        """Does repr work?"""
        self.assertEqual(repr(self.u1), '<User #1: Spongebob, sponge@bikini-bottom.com>')

    #########
    # Follow Tests
    #########

    def test_user_follows(self):
        """Tests user-follow relationship"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u1.following), 1)
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u2.followers), 1)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)
    
    def test_is_followed_by(self):
        """Tests is_followed_by function"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u2.is_followed_by(self.u1))
        self.assertFalse(self.u1.is_followed_by(self.u2))

    def test_is_following(self):
        """Tests is_following function"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))
    
    #########
    # Create User Tests
    #########

    def test_signup(self):
        """Test user sign up"""
        u_test = User.signup('Squidward', 'squidward@bikini-bottom.com', 'clarinet', None)
        db.session.commit()

        u_test = User.query.get(3)

        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.username, 'Squidward')
        self.assertEqual(u_test.email, 'squidward@bikini-bottom.com')
        self.assertNotEqual(u_test.password, 'clarinet')
        self.assertTrue(u_test.password.startswith('$2b$'))

    def test_invalid_username(self):
        """Test invalid username"""
        u_test = User.signup(None, 'squidward@bikini-bottom.com', 'clarinet', None)
        uid = u_test.id
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_email(self):
        """Test invalid email"""
        u_test = User.signup('Squidward', None, 'clarinet', None)
        uid = u_test.id
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
    
    def test_invalid_password(self):
        """Test invalid password"""
        with self.assertRaises(ValueError) as context:
            User.signup('Squidward', 'squidward@bikini-bottom.com', None, None)


    #########
    # Authenticate User Tests
    #########

    def test_authenticate(self):
        """Test successful authentication"""
        u_test = User.authenticate(self.u1.username, 'password')
        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.id, self.u1.id)
    
    def test_invalid_username(self):
        """Test invalid username"""
        self.assertFalse(User.authenticate('fiuhebfiv', 'password'))

    def test_invalid_password(self):
        """Test invalid password"""
        self.assertFalse(User.authenticate(self.u1.username, 'eurhger'))