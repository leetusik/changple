import json
import logging
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from social_core.exceptions import AuthException, MissingBackend
from social_django.utils import load_backend, load_strategy

from .services.social_auth_service import SocialAuthService

# Create a logger
logger = logging.getLogger(__name__)

# Create your views here.


class SocialLoginView(View):
    """Base view for social login integration."""

    provider = None

    def get(self, request):
        """Redirect to social provider login page."""
        # This should be implemented by specific provider views
        pass

    def handle_callback(self, request, social_data):
        """Process social login callback data and log in the user."""
        # Extract user data from social_data
        social_id = social_data.get("id")
        email = social_data.get("email")

        if not social_id or not email:
            # Redirect to login failure page
            return redirect(reverse("login"))

        # Get or create user
        extra_data = {
            "first_name": social_data.get("first_name", ""),
            "last_name": social_data.get("last_name", ""),
            "profile_image": social_data.get("profile_image", ""),
        }

        user, created = SocialAuthService.get_or_create_user(
            provider=self.provider, social_id=social_id, email=email, **extra_data
        )

        # Authenticate and login
        auth_user = authenticate(request, provider=self.provider, social_id=social_id)

        if auth_user:
            login(request, auth_user)
            return redirect(reverse("home"))

        # Authentication failed
        return redirect(reverse("login"))


class NaverLoginView(View):
    """View for initiating Naver login."""

    def get(self, request):
        """Redirect to Naver OAuth login page."""
        strategy = load_strategy(request)
        try:
            # Get the callback URL from settings
            redirect_uri = settings.SOCIAL_AUTH_NAVER_CALLBACK_URL

            # Log what we're about to do
            logger.info(f"Setting up Naver OAuth with redirect_uri: {redirect_uri}")

            # Create the backend with clean redirect_uri
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)

            # Let social-auth handle everything
            auth_url = backend.auth_url()
            logger.info(f"Naver auth URL: {auth_url}")

            return redirect(auth_url)
        except Exception as e:
            logger.error(f"Error in NaverLoginView: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return redirect(reverse("home"))


class NaverCallbackView(View):
    """View for handling Naver OAuth callback."""

    def get(self, request):
        """Process Naver OAuth callback data."""
        # Enhanced logging of all request parameters
        logger.info("====== NAVER CALLBACK RECEIVED ======")
        logger.info(
            f"Request GET params: {json.dumps(dict(request.GET.items()), ensure_ascii=False)}"
        )
        logger.info(f"Request META: {self._get_safe_meta(request)}")
        logger.info("======================================")

        code = request.GET.get("code")
        error = request.GET.get("error")
        state = request.GET.get("state")

        # The middleware should already have removed redirect_state if present
        logger.info(f"Callback received - code: {code}, state: {state}")

        if error:
            logger.error(f"Error from Naver: {error}")
            return redirect(reverse("home"))

        if not code:
            logger.error("No code parameter received from Naver")
            return redirect(reverse("home"))

        strategy = load_strategy(request)
        try:
            # Use the social auth backend to complete the authentication
            logger.info("Loading Naver backend")

            # Get the callback URL from settings
            redirect_uri = settings.SOCIAL_AUTH_NAVER_CALLBACK_URL
            logger.info(f"Using redirect_uri: {redirect_uri}")

            # Load the backend with our redirect_uri
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)
            logger.info(f"Backend: {backend.__class__.__name__}")

            # Complete the authentication process
            try:
                logger.info("Starting backend.complete")
                request.backend = backend

                # Pass the code and state to the backend
                user = backend.complete(request=request, redirect_uri=redirect_uri)
                logger.info(f"User authenticated: {user}")

                if user and user.is_active:
                    login(request, user)
                    logger.info(f"User logged in: {user.id}")

                    # Store the access token for later use (e.g., for disconnection)
                    try:
                        # Check if the response from backend.complete contains the token
                        if hasattr(user, "social_auth") and hasattr(
                            user.social_auth, "extra_data"
                        ):
                            # For python-social-auth storage
                            logger.info("Storing token in social_auth extra_data")
                        else:
                            # Custom storage - need to store the token in our own way
                            # Get token from the pipeline response
                            token = getattr(backend, "access_token", None)
                            if token:
                                logger.info(f"Storing access token for user {user.id}")
                                # Create or update a model to store the token - using a simple attribute for now
                                # In a real implementation, consider encrypting this token
                                user.naver_access_token = token
                                user.save()
                            else:
                                logger.warning(
                                    f"No access token found for user {user.id}"
                                )
                    except Exception as e:
                        logger.error(f"Error storing access token: {str(e)}")

                    return redirect(reverse("home"))
                else:
                    logger.error("User not active or not returned")
            except Exception as e:
                logger.error(f"Error during backend.complete: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                raise

        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error during Naver authentication: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return redirect(reverse("home"))

        logger.error("No user returned from auth process")
        return redirect(reverse("home"))

    def _get_safe_meta(self, request):
        """Get a safe version of request.META for logging."""
        safe_meta = {}
        for key, value in request.META.items():
            # Only log headers and other useful information, skip server details
            if key.startswith("HTTP_") or key in [
                "QUERY_STRING",
                "PATH_INFO",
                "REMOTE_ADDR",
                "REQUEST_METHOD",
            ]:
                safe_meta[key] = str(value)
        return safe_meta


def logout_view(request):
    """
    Custom logout view that handles Django logout properly.
    """
    # Django logout
    logout(request)

    # Redirect to home page
    return redirect("home")


def withdraw_account(request):
    """
    Handle user account deletion.
    For Naver social users, this will also disconnect their Naver account.
    """
    if not request.user.is_authenticated:
        return redirect("home")

    user = request.user

    # Get access token - try different sources
    access_token = None

    # Try to get token from user attribute (where we stored it during login)
    if hasattr(user, "naver_access_token") and user.naver_access_token:
        access_token = user.naver_access_token
        logger.info(f"Using access token stored in user model for user {user.id}")

    # If no token found and this is a Naver user, log a warning
    if not access_token and user.provider == "naver":
        logger.warning(
            f"No access token found for Naver user {user.id}, disconnection may fail"
        )

    # Call the service to disconnect from Naver and delete the user
    success = SocialAuthService.disconnect_naver_and_delete_user(user, access_token)

    # If the deletion wasn't successful, just log the user out
    if not success:
        logout(request)

    # Redirect to home page with a message
    return redirect("home")
