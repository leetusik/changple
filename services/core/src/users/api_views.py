"""
API views for users app.
"""

import logging

import requests
from django.conf import settings
from django.contrib.auth import logout
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.users.models import User
from src.users.serializers import UserProfileUpdateSerializer, UserSerializer

logger = logging.getLogger(__name__)


class CurrentUserView(APIView):
    """
    Get current authenticated user's profile.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return current user's profile data."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserProfileUpdateView(APIView):
    """
    Update current user's profile.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Update user profile."""
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserWithdrawView(APIView):
    """
    Delete user account and disconnect from Naver.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """Delete user account and disconnect from Naver OAuth."""
        user = request.user

        # Disconnect from Naver if social user
        if user.is_social_user() and user.provider == "naver":
            if user.naver_access_token:
                try:
                    self._disconnect_naver(user.naver_access_token)
                except Exception as e:
                    logger.error(f"Failed to disconnect from Naver: {e}")
                    # Continue with deletion even if Naver disconnect fails

        # Logout and delete user
        logout(request)
        user.delete()

        return Response(
            {"message": "계정이 성공적으로 삭제되었습니다."},
            status=status.HTTP_200_OK,
        )

    def _disconnect_naver(self, access_token: str):
        """Disconnect user from Naver OAuth."""
        url = "https://nid.naver.com/oauth2.0/token"
        params = {
            "grant_type": "delete",
            "client_id": settings.SOCIAL_AUTH_NAVER_KEY,
            "client_secret": settings.SOCIAL_AUTH_NAVER_SECRET,
            "access_token": access_token,
            "service_provider": "NAVER",
        }

        response = requests.post(url, data=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Naver disconnect failed: {response.text}")
            raise Exception("Failed to disconnect from Naver")

        logger.info("Successfully disconnected from Naver")
