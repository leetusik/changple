"""
Pytest configuration for Changple Core service tests.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
        user_type="social",
        provider="naver",
        social_id="test123",
        name="테스트 사용자",
        nickname="tester",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpassword123",
        user_type="admin",
        name="관리자",
    )


@pytest.fixture
def api_client():
    """Create an API client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Create an admin authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client
