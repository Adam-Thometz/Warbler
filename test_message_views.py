"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="Spongebob",
                                    email="sponge@test.com",
                                    password="gary1234",
                                    image_url=None)

        db.session.commit()

        self.testmessage = Message(text="I like jellyfishing", user_id=self.testuser.id)

        db.session.commit()
    
    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res
    
    def test_add_message(self):
        """Can user add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_delete_message(self):
        """Can user delete a message?"""
        m2 = Message(text="You'll never get the krabby patty formula!", user_id=self.testuser.id)
        db.session.add(m2)
        db.session.commit()
        mid = m2.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.post(f"/messages/{mid}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('I like jellyfishing', html)
    
    def test_add_message_no_user(self):
        """Can a user add or delete a message when not logged in?"""

        with self.client as c:
            resp = c.post('/messages/new', data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You must be logged in to do that.", html)

    def test_delete_message_no_user(self):
        """Can a user add or delete a message when not logged in?"""
        
        m2 = Message(text='Hello', user_id = self.testuser.id)
        db.session.add(m2)
        db.session.commit()
        mid = m2.id

        with self.client as c:
            resp = c.post(f'/messages/{mid}/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You must be logged in to do that.", html)
    
    def test_add_message_unauthorized(self):
        """Can a user add another user's post"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 3624576436
            
            resp = c.post('/messages/new', data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You must be logged in to do that.", html)
    
    def test_delete_message_unauthorized(self):
        """Can a user delete another user's post"""
        u2 = User(username='Plankton', email='plankton@aol.com', password='formula', image_url=None)
        m2 = Message(text='Hello', user_id = self.testuser.id)
        db.session.add_all([u2, m2])
        db.session.commit()
        mid = m2.id
        uid = u2.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = uid
            
            resp = c.post(f'/messages/{mid}/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You are not authorized to delete that message.", html)

    def test_show_message(self):
        """Can a user view a message?"""
        m2 = Message(text="You'll never get the krabby patty formula!", user_id=self.testuser.id)
        db.session.add(m2)
        db.session.commit()
        mid = m2.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get(f'/messages/{mid}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('You&#39;ll never get the krabby patty formula!', html)
    
    def test_show_message_invalid(self):
        """Will an invalid id lead to a 404?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get('/messages/999999999999')

            self.assertEqual(resp.status_code, 404)