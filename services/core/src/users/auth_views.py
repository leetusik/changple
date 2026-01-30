"""
Authentication views for Naver OAuth.
"""

import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from social_django.utils import load_backend, load_strategy

logger = logging.getLogger(__name__)


class NaverLoginView(APIView):
    """
    Initiate Naver OAuth login flow.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Redirect to Naver OAuth authorization page."""
        strategy = load_strategy(request)
        backend = load_backend(
            strategy, "naver", redirect_uri=settings.SOCIAL_AUTH_NAVER_CALLBACK_URL
        )

        # Generate the authorization URL
        auth_url = backend.auth_url()
        return redirect(auth_url)


class NaverCallbackView(APIView):
    """
    Handle Naver OAuth callback.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Process Naver OAuth callback and authenticate user."""
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code:
            logger.error("No code in Naver callback")
            return Response(
                {"error": "Authentication failed - no code provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            strategy = load_strategy(request)
            backend = load_backend(
                strategy, "naver", redirect_uri=settings.SOCIAL_AUTH_NAVER_CALLBACK_URL
            )

            # Complete the authentication
            user = backend.complete(request=request)

            if user and user.is_authenticated:
                logger.info(f"User {user.id} authenticated successfully via Naver")
                
                # Explicitly log the user in to persist session
                # (backend.complete() authenticates but doesn't call login() in custom views)
                login(request, user, backend="social_core.backends.naver.NaverOAuth2")

                # Redirect to frontend with success
                frontend_url = settings.SOCIAL_AUTH_LOGIN_REDIRECT_URL
                return redirect(frontend_url)
            else:
                logger.error("Authentication completed but no user returned")
                return Response(
                    {"error": "Authentication failed"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as e:
            logger.error(f"Naver authentication error: {str(e)}")
            return Response(
                {"error": f"Authentication failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    """
    Logout the current user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logout the current user."""
        logout(request)
        return Response(
            {"message": "로그아웃되었습니다."},
            status=status.HTTP_200_OK,
        )


class AuthStatusView(APIView):
    """
    Check authentication status.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Return authentication status."""
        if request.user.is_authenticated:
            from src.users.serializers import UserSerializer

            return Response(
                {
                    "is_authenticated": True,
                    "user": UserSerializer(request.user).data,
                }
            )
        return Response({"is_authenticated": False})
