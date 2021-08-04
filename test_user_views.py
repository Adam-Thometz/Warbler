"""Message model tests."""

# run this to conduct test:
#
#    python -m unittest test_user_views.py


import os
from unittest import TestCase
from sqlalchemy import exc
from bs4 import BeautifulSoup
from models import db, User, Message, Follows, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import CURR_USER_KEY, app, do_login

db.create_all()

class UserViewsTestCase(TestCase):
    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="RickSanchez",
                                    email="rick@rick.gov2",
                                    password="morty123",
                                    image_url=None)
        self.u1 = User.signup("MortySmith", 'morty@gmail.com', 'jessica123', None)
        self.u2 = User.signup("SummerSmith", 'summer@gmail.com', 'brad1234', None)
        self.u3 = User.signup("BethSmith", 'beth@gmail.com', 'horses4eva123', None)
        self.u4 = User.signup("JerrySmith", 'jerry@aol.com', 'password123', None)
        db.session.commit()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

######### General user view tests
    def test_users_index(self):
        """Does this page show all users?"""
        with self.client as c:
            resp = c.get('/users')
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)

            self.assertIn('RickSanchez', html)
            self.assertIn('MortySmith', html)
            self.assertIn('SummerSmith', html)
            self.assertIn('BethSmith', html)
            self.assertIn('JerrySmith', html)
    
    def test_user_search(self):
        """Does the search function work as expected?"""
        with self.client as c:
            resp = c.get('/users?q=Smith')
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)

            self.assertIn('MortySmith', html)
            self.assertIn('SummerSmith', html)
            self.assertIn('BethSmith', html)
            self.assertIn('JerrySmith', html)

            self.assertNotIn('RickSanchez', html)

    def test_show_user(self):
        """Does a specific user show up?"""
        with self.client as c:
            resp = c.get(f'/users/{self.testuser.id}')
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('RickSanchez', html)

######### Like view tests
    def setup_likes(self):
        """Likes for likes testing"""
        m1 = Message(text="Aw geez...", user_id=self.u1.id)
        m2 = Message(text="Wubba lubba dub dub!", user_id=self.testuser.id)
        m3 = Message(text="The trick is getting the correct cereal to milk ratio", user_id = self.u4.id)

        db.session.add_all([m1, m2, m3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser.id, message_id = m1.id)

        db.session.add(l1)
        db.session.commit()
    
    def test_show_likes(self):
        """Do the like stats display correctly?"""
        self.setup_likes()
        with self.client as c:
            resp = c.get(f'/users/{self.testuser.id}')
            html = str(resp.data)
            soup = BeautifulSoup(html, 'html.parser')
            found = soup.find_all("li", {"class": "stat"})

            self.assertEqual(resp.status_code, 200)
            self.assertIn('@RickSanchez', html)

            self.assertEqual(len(found), 4)
            # Messages:
            self.assertIn("1", found[0].text)
            # Following:
            self.assertIn("0", found[1].text)
            # Followers:
            self.assertIn("0", found[2].text)
            # Likes:
            self.assertIn("1", found[3].text)
    
    def test_add_like(self):
        """Is a like added to a user's post?"""
        m2 = Message(id=2, text="Wubba lubba dub dub!", user_id=self.testuser.id)
        db.session.add(m2)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id
            resp = c.post('/messages/2/like', follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            likes = Likes.query.filter(Likes.message_id == 2).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.u2.id)
            self.assertNotEqual(2, self.u2.id)
    
    def test_remove_like(self):
        """Is a like removed to a user's post?"""
        self.setup_likes()
        m = Message.query.filter(Message.text == "Aw geez...").one()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            resp = c.post(f'/messages/{m.id}/like', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == m.id).all()
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        """Does an unauthenticated like fail?"""
        self.setup_likes()
        m = Message.query.filter(Message.text == "Aw geez...").one()

        like_count = Likes.query.count()

        with self.client as c:
            resp = c.post(f'/messages/{m.id}/like', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("You must be logged in to do that.", str(resp.data))
            self.assertEqual(like_count, Likes.query.count())

######### Follow view tests
    def setup_follows(self):
        """Follows for follow testing"""
        f1 = Follows(user_being_followed_id=self.u1.id, user_following_id=self.testuser.id)
        f2 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.u1.id)
        f3 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.u2.id)
        f4 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.u3.id)

        db.session.add_all([f1, f2, f3, f4])
        db.session.commit()
    
    def test_user_follow(self):
        """Do the correct follows stats show on the user page?"""
        self.setup_follows()
        with self.client as c:
            resp = c.get(f'/users/{self.testuser.id}')
            html = str(resp.data)
            soup = BeautifulSoup(html, 'html.parser')
            found = soup.find_all("li", {"class": "stat"})

            self.assertEqual(resp.status_code, 200)

            self.assertIn('@RickSanchez', html)

            self.assertEqual(len(found), 4)
            # Messages:
            self.assertIn("0", found[0].text)
            # Following:
            self.assertIn("1", found[1].text)
            # Followers:
            self.assertIn("3", found[2].text)
            # Likes:
            self.assertIn("0", found[3].text)

    def test_show_following(self):
        """Do the correct 'following' users show?"""
        self.setup_follows()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get(f'/users/{self.testuser.id}/following')
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)

            self.assertIn('@MortySmith', html)
            self.assertNotIn('@SummerSmith', html)
            self.assertNotIn('@BethSmith', html)
            self.assertNotIn('@JerrySmith', html)

    def test_show_followers(self):
        """Do the correct 'followers' show?"""
        self.setup_follows()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get(f'/users/{self.testuser.id}/followers')
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)

            self.assertIn('@MortySmith', html)
            self.assertIn('@SummerSmith', html)
            self.assertIn('@BethSmith', html)
            self.assertNotIn('@JerrySmith', html)

    def test_show_followers_unauthorized(self):
        """Can a user access a 'followers' page w/o credentials?"""
        self.setup_follows()
        with self.client as c:
            
            resp = c.get(f'/users/{self.testuser.id}/followers', follow_redirects=True)
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@MortySmith', html)
            self.assertIn('You must be logged in to do that', html)

    def test_show_following_unauthorized(self):
        """Can a user access a 'following' page w/o credentials?"""
        self.setup_follows()
        with self.client as c:
            
            resp = c.get(f'/users/{self.testuser.id}/following', follow_redirects=True)
            html = str(resp.data)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@MortySmith', html)
            self.assertIn('You must be logged in to do that', html)