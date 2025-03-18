import json
import logging
import urllib.parse

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import NaverUserProfile

logger = logging.getLogger(__name__)


class NaverAuthService:
    """
    Service for handling Naver OAuth authentication
    """

    # Naver OAuth URLs
    AUTHORIZE_URL = "https://nid.naver.com/oauth2.0/authorize"
    TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
    PROFILE_URL = "https://openapi.naver.com/v1/nid/me"

    @classmethod
    def get_authorize_url(cls, state):
        """
        Generate the authorization URL for Naver login with expanded scope

        Args:
            state: Random state string for CSRF protection

        Returns:
            URL to redirect the user to for Naver login
        """
        # URL encode the redirect URI and scope
        params = {
            "response_type": "code",
            "client_id": settings.NAVER_CLIENT_ID,
            "redirect_uri": settings.NAVER_REDIRECT_URI,
            "state": state,
            "scope": "name,email,profile_image,gender,age,birthday,birthyear,mobile",
        }

        # Build the full URL with properly encoded parameters
        auth_url = f"{cls.AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

        # Log the generated URL for debugging
        logger.info(f"Generated Naver authorization URL: {auth_url}")

        return auth_url

    @classmethod
    def get_access_token(cls, code, state):
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code received from Naver
            state: State parameter for verification

        Returns:
            dict with access_token and related data or None if failed
        """
        try:
            params = {
                "grant_type": "authorization_code",
                "client_id": settings.NAVER_CLIENT_ID,
                "client_secret": settings.NAVER_CLIENT_SECRET,
                "code": code,
                "state": state,
            }

            logger.info(f"Requesting access token with params: {params}")

            response = requests.post(cls.TOKEN_URL, data=params)
            logger.info(f"Token response status: {response.status_code}")

            response.raise_for_status()
            token_data = response.json()

            # Log token data (without the actual tokens for security)
            safe_log_data = {
                k: v
                for k, v in token_data.items()
                if k not in ("access_token", "refresh_token")
            }
            logger.info(f"Received token data: {safe_log_data}")

            return token_data
        except Exception as e:
            logger.error(f"Error getting Naver access token: {str(e)}")
            return None

    @classmethod
    def get_user_profile(cls, access_token):
        """
        Get user profile information from Naver

        Args:
            access_token: OAuth access token from Naver

        Returns:
            User profile information or None if failed
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}

            logger.info("Requesting user profile from Naver")
            response = requests.get(cls.PROFILE_URL, headers=headers)
            logger.info(f"Profile response status: {response.status_code}")

            response.raise_for_status()

            profile_data = response.json()

            # Check if the response contains the necessary data
            if "response" not in profile_data:
                logger.error("Invalid profile data from Naver")
                logger.error(f"Profile data received: {profile_data}")
                return None

            # Log the full profile data for debugging (without sensitive info)
            safe_profile = profile_data["response"].copy()
            if "id" in safe_profile:
                safe_profile["id"] = (
                    safe_profile["id"][:5] + "..." if safe_profile["id"] else None
                )
            if "email" in safe_profile:
                safe_profile["email"] = "***" + (
                    safe_profile["email"].split("@")[1]
                    if "@" in safe_profile["email"]
                    else ""
                )

            logger.info(f"Received Naver profile data: {safe_profile}")

            return profile_data["response"]
        except Exception as e:
            logger.error(f"Error getting Naver user profile: {str(e)}")
            return None

    @classmethod
    def authenticate_or_create_user(cls, access_token):
        """
        Authenticate an existing user or create a new one using Naver profile

        Args:
            access_token: OAuth access token from Naver

        Returns:
            User instance or None if failed
        """
        profile = cls.get_user_profile(access_token)

        if not profile or "id" not in profile:
            logger.error("Failed to get valid profile data")
            return None

        # Try to find existing user profile
        try:
            naver_profile = NaverUserProfile.objects.get(naver_id=profile["id"])
            logger.info(f"Found existing user with Naver ID: {profile['id'][:5]}...")

            # Update all profile information
            if "nickname" in profile:
                naver_profile.nickname = profile["nickname"]
            if "profile_image" in profile:
                naver_profile.profile_image = profile["profile_image"]
            if "gender" in profile:
                naver_profile.gender = profile["gender"]
            if "age" in profile:
                naver_profile.age = profile["age"]
            if "birthday" in profile:
                naver_profile.birthday = profile["birthday"]
            # Add new fields
            if "name" in profile:
                naver_profile.name = profile["name"]
            if "birthyear" in profile:
                naver_profile.birthyear = profile["birthyear"]
            if "mobile" in profile:
                naver_profile.mobile = profile["mobile"]

            naver_profile.save()
            logger.info("Updated user profile information")

            # Update user information if email is provided
            user = naver_profile.user
            if "email" in profile and profile["email"]:
                user.email = profile["email"]
                # Update user's first name if name is provided
                if "name" in profile:
                    user.first_name = profile["name"]
                user.save()
                logger.info("Updated user email and name")

            user.last_login = timezone.now()
            user.save()
            logger.info(f"User {user.username} authenticated successfully")
            return user
        except NaverUserProfile.DoesNotExist:
            # Create new user and profile
            # Generate a unique username based on Naver ID
            logger.info(f"Creating new user for Naver ID: {profile['id'][:5]}...")
            username = f"naver_{profile['id'][:10]}"
            email = profile.get("email", f"{username}@example.com")

            # Create User with name if available
            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,  # No password for social logins
                first_name=profile.get("name", ""),  # Add name to Django User
            )
            logger.info(f"Created new Django user: {username}")

            # Create NaverUserProfile with all available fields
            naver_profile = NaverUserProfile.objects.create(
                user=user,
                naver_id=profile["id"],
                nickname=profile.get("nickname", username),
                profile_image=profile.get("profile_image", ""),
                gender=profile.get("gender", ""),
                age=profile.get("age", ""),
                birthday=profile.get("birthday", ""),
                name=profile.get("name", ""),
                birthyear=profile.get("birthyear", ""),
                mobile=profile.get("mobile", ""),
            )
            logger.info(f"Created new Naver profile for user: {username}")

            return user
