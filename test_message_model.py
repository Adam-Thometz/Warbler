"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import app

db.create_all()

class MessageModelTestCase(TestCase):
    """Test message model"""

    def setUp(self):
        db.drop_all()
        db.create_all()

        u1 = User.signup('Spongebob', 'sponge@bikini-bottom.com', 'password', None)
        db.session.commit()

        u1 = User.query.get(1)

        self.u1 = u1
        self.uid = u1.id

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does message model work?"""
        m1 = Message(text="I'm ready. I'm ready. I'm ready.", user_id = self.uid)
        db.session.add(m1)
        db.session.commit()

        self.assertEqual(len(self.u1.messages), 1)
        self.assertEqual(self.u1.messages[0].text, "I'm ready. I'm ready. I'm ready.")
    
    def test_likes(self):
        """Testing the like feature"""
        m1 = Message(text="I'm ready. I'm ready. I'm ready.", user_id = self.uid)
        u2 = User.signup('Patrick', 'patrick@bikini-bottom.com', 'password2', None)
        db.session.add_all([m1, u2])
        db.session.commit()

        u2.likes.append(m1)
        db.session.commit()

        l = Likes.query.filter(Likes.user_id == u2.id).all()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].message_id, m1.id)