"""
Basic API tests for Changple Core service.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAuthAPI:
    """Tests for authentication endpoints."""

    def test_auth_status_unauthenticated(self, api_client):
        """Test auth status returns unauthenticated for anonymous users."""
        response = api_client.get("/api/v1/auth/status/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["authenticated"] is False

    def test_auth_status_authenticated(self, authenticated_client, user):
        """Test auth status returns user data for authenticated users."""
        response = authenticated_client.get("/api/v1/auth/status/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["authenticated"] is True
        assert response.data["user"]["email"] == user.email


@pytest.mark.django_db
class TestUserAPI:
    """Tests for user endpoints."""

    def test_get_current_user(self, authenticated_client, user):
        """Test getting current user profile."""
        response = authenticated_client.get("/api/v1/users/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["name"] == user.name

    def test_get_current_user_unauthenticated(self, api_client):
        """Test getting current user returns 401 for unauthenticated."""
        response = api_client.get("/api/v1/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestContentAPI:
    """Tests for content endpoints."""

    def test_list_content(self, api_client):
        """Test listing content."""
        response = api_client.get("/api/v1/content/columns/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_preferred_content(self, api_client):
        """Test listing preferred content."""
        response = api_client.get("/api/v1/content/preferred/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestScraperAPI:
    """Tests for scraper endpoints."""

    def test_scraper_status_authenticated(self, authenticated_client):
        """Test scraper status endpoint."""
        response = authenticated_client.get("/api/v1/scraper/status/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_posts" in response.data

    def test_scraper_run_requires_admin(self, authenticated_client):
        """Test scraper run requires admin permission."""
        response = authenticated_client.post("/api/v1/scraper/run/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_scraper_run_admin(self, admin_client):
        """Test admin can trigger scraper."""
        response = admin_client.post("/api/v1/scraper/run/", {})
        assert response.status_code == status.HTTP_200_OK
        assert "task_id" in response.data
