import json
import logging

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
            # Set up the backend with the correct params - no query string
            redirect_uri = "http://localhost:8000/naver/callback/"

            # Log what we're about to do
            logger.info(f"Setting up Naver OAuth with redirect_uri: {redirect_uri}")

            # Create the backend
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)

            # Configure the backend for correct redirect
            backend.redirect_uri = redirect_uri

            # Generate auth URL and let the backend handle state
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

            # Use the exact same redirect_uri as in the login view
            redirect_uri = "http://localhost:8000/naver/callback/"
            logger.info(f"Using redirect_uri: {redirect_uri}")

            # Load the backend with our redirect_uri
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)

            # Configure the backend
            backend.redirect_uri = redirect_uri
            logger.info(f"Backend redirect_uri: {backend.redirect_uri}")

            # Log the backend configuration
            logger.info(f"Backend: {backend.__class__.__name__}")

            # Complete the authentication process
            try:
                logger.info("Starting backend.complete")
                # Make request.backend available for the pipeline
                request.backend = backend

                # Use the backend to complete the authentication with minimal parameters
                # Pass the code and state to the backend
                user = backend.complete(
                    request=request,
                    redirect_uri=redirect_uri,  # Ensure this matches what was used in auth_url
                )
                logger.info(f"User authenticated: {user}")

                if user and user.is_active:
                    login(request, user)
                    logger.info(f"User logged in: {user.id}")
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
