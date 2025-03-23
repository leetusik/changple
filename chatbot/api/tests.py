from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class HomeViewTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )
        self.client = Client()

    def test_home_view_not_authenticated(self):
        """
        Test that the home view works when user is not authenticated
        """
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check that locked content indicators are in the response
        self.assertContains(response, "로그인 후 이용해 주세요")

    def test_home_view_authenticated(self):
        """
        Test that the home view works when user is authenticated
        """
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check that authenticated content indicators are in the response
        self.assertContains(response, "마이 페이지")
        self.assertContains(response, "input-container-unlocked")
