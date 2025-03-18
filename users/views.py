import json
import logging
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import NaverUserProfile
from .services.naver_auth_service import NaverAuthService

logger = logging.getLogger(__name__)


def home_view(request):
    """
    Home page view that always shows the login page
    regardless of authentication status
    """
    return login_view(request)


def login_view(request):
    """
    Render the login page with Naver login button
    """
    # Generate state parameter for CSRF protection
    state = str(uuid.uuid4())
    request.session["naver_auth_state"] = state
    logger.info(f"Generated new state for login: {state[:5]}...")

    # Get the authorization URL
    naver_login_url = NaverAuthService.get_authorize_url(state)

    return render(request, "users/login.html", {"naver_login_url": naver_login_url})


def naver_login_callback(request):
    """
    Handle the callback from Naver OAuth
    """
    # Get query parameters
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    # Check for errors
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        logger.error(f"Naver login error: {error} - {error_description}")
        return render(request, "users/login_error.html", {"error": error_description})

    # Verify state parameter to prevent CSRF
    session_state = request.session.get("naver_auth_state")
    if not session_state or session_state != state:
        logger.error("State parameter mismatch")
        return render(
            request,
            "users/login_error.html",
            {"error": "Security validation failed. Please try again."},
        )

    # Exchange authorization code for access token
    token_data = NaverAuthService.get_access_token(code, state)
    if not token_data or "access_token" not in token_data:
        logger.error("Failed to obtain access token")
        return render(
            request,
            "users/login_error.html",
            {"error": "Failed to authenticate with Naver. Please try again."},
        )

    # Authenticate or create user
    user = NaverAuthService.authenticate_or_create_user(token_data["access_token"])
    if not user:
        logger.error("Failed to authenticate or create user")
        return render(
            request,
            "users/login_error.html",
            {"error": "Failed to process login. Please try again."},
        )

    # Log in the user
    login(request, user)

    # Clear the state from session
    if "naver_auth_state" in request.session:
        del request.session["naver_auth_state"]

    # Redirect to home or next URL
    next_url = request.GET.get("next", "home")
    return redirect(next_url)


def logout_view(request):
    """
    Log out the user
    """
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    """
    Display user profile page
    """
    profile_data = {
        "username": request.user.username,
        "email": request.user.email,
        "is_admin": request.user.is_staff,
        "is_superuser": request.user.is_superuser,
        "date_joined": request.user.date_joined,
    }

    # Try to get Naver profile if it exists
    try:
        naver_profile = NaverUserProfile.objects.get(user=request.user)
        profile_data.update(
            {
                "nickname": naver_profile.nickname,
                "profile_image": naver_profile.profile_image,
                "gender": naver_profile.gender,
                "age": naver_profile.age,
                "birthday": naver_profile.birthday,
                "name": naver_profile.name,
                "birthyear": naver_profile.birthyear,
                "mobile": naver_profile.mobile,
                "has_naver_profile": True,
            }
        )
    except NaverUserProfile.DoesNotExist:
        # For users without a profile (like superusers)
        profile_data.update(
            {
                "nickname": request.user.username,
                "has_naver_profile": False,
            }
        )

    return render(request, "users/profile.html", {"profile": profile_data})


def naver_login_api(request):
    """
    Initiate Naver OAuth login flow for API clients
    """
    # Generate state parameter for CSRF protection
    state = str(uuid.uuid4())
    request.session["naver_auth_state"] = state
    logger.info(f"Generated new state for API login: {state[:5]}...")

    # Get the authorization URL
    naver_login_url = NaverAuthService.get_authorize_url(state)

    # Redirect to Naver login page
    return redirect(naver_login_url)


def naver_login_callback_api(request):
    """
    Handle the callback from Naver OAuth for API clients
    Returns JWT tokens for authenticated users
    """
    # Get query parameters
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    # Check for errors
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        logger.error(f"Naver login error: {error} - {error_description}")
        return JsonResponse({"error": error_description}, status=400)

    # Verify state parameter to prevent CSRF
    session_state = request.session.get("naver_auth_state")
    if not session_state or session_state != state:
        logger.error("State parameter mismatch")
        return JsonResponse({"error": "Security validation failed"}, status=400)

    # Exchange authorization code for access token
    token_data = NaverAuthService.get_access_token(code, state)
    if not token_data or "access_token" not in token_data:
        logger.error("Failed to obtain access token")
        return JsonResponse({"error": "Failed to authenticate with Naver"}, status=400)

    # Authenticate or create user
    user = NaverAuthService.authenticate_or_create_user(token_data["access_token"])
    if not user:
        logger.error("Failed to authenticate or create user")
        return JsonResponse({"error": "Failed to process login"}, status=400)

    # Log in the user with session-based authentication too
    login(request, user)
    logger.info(f"User {user.username} logged in via Naver API with session")

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # Clear the state from session
    if "naver_auth_state" in request.session:
        del request.session["naver_auth_state"]

    # For local testing, redirect to our own login success page
    return redirect(
        f"/users/login/success/?token={access_token}&refresh={refresh_token}"
    )


def login_success_view(request):
    """
    Render the login success page that handles JWT token storage
    """
    return render(request, "users/login_success.html")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info_api(request):
    """
    Simple API endpoint that returns user info
    Requires JWT authentication
    """
    try:
        # Get Naver profile if it exists
        naver_profile = NaverUserProfile.objects.get(user=request.user)
        user_data = {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "nickname": naver_profile.nickname,
            "profile_image": naver_profile.profile_image,
            "is_premium": naver_profile.is_premium,
            "daily_query_limit": naver_profile.daily_query_limit,
            "daily_queries_used": naver_profile.daily_queries_used,
        }
    except NaverUserProfile.DoesNotExist:
        user_data = {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
        }

    return JsonResponse(user_data)
