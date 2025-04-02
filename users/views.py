import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
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

    def get(self, request: HttpRequest) -> HttpResponse:
        """Redirect to Naver OAuth login page."""
        strategy = load_strategy(request)
        try:
            # Construct the redirect_uri dynamically using the named URL
            # This ensures it works correctly in both development and production
            callback_url_name = (
                "social:complete"  # Standard name for python-social-auth callback
            )
            redirect_uri = request.build_absolute_uri(
                reverse(callback_url_name, args=("naver",))
            )

            # Log what we're about to do
            logger.info(
                f"Setting up Naver OAuth with dynamic redirect_uri: {redirect_uri}"
            )

            # Create the backend, passing the dynamic redirect_uri
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)

            # Ensure the backend uses the correct redirect_uri
            # (This might be redundant if load_backend handles it, but doesn't hurt)
            backend.redirect_uri = redirect_uri

            # Generate auth URL and let the backend handle state
            auth_url = backend.auth_url()
            logger.info(f"Generated Naver auth URL: {auth_url}")

            return redirect(auth_url)
        except Exception as e:
            logger.error(f"Error in NaverLoginView: {str(e)}", exc_info=True)
            # Avoid showing detailed traceback in production if possible
            # Consider redirecting to an error page or logging less detail
            return redirect(reverse("home"))


class NaverCallbackView(View):
    """View for handling Naver OAuth callback."""

    # CSRF exempt because Naver sends a POST/GET request externally
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request: HttpRequest) -> HttpResponse:
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

        logger.info(f"Callback received - code: {bool(code)}, state: {bool(state)}")

        if error:
            logger.error(f"Error from Naver callback: {error}")
            return redirect(reverse("home"))

        if not code or not state:
            logger.error("Missing code or state parameter from Naver callback")
            return redirect(reverse("home"))

        strategy = load_strategy(request)
        try:
            # Construct the redirect_uri dynamically AGAIN to match the login view
            callback_url_name = "social:complete"
            redirect_uri = request.build_absolute_uri(
                reverse(callback_url_name, args=("naver",))
            )
            logger.info(f"Using dynamic redirect_uri for callback: {redirect_uri}")

            # Load the backend with the same dynamic redirect_uri
            backend = load_backend(strategy, "naver", redirect_uri=redirect_uri)
            backend.redirect_uri = redirect_uri  # Ensure it matches

            logger.info(f"Backend for callback: {backend.__class__.__name__}")

            # Complete the authentication process using the backend's complete method
            # The backend should handle code/state validation internally
            logger.info("Starting backend.complete")
            user = backend.complete(
                request=request
            )  # Pass request for state/session handling
            logger.info(f"backend.complete finished. User: {user}")

            if user and user.is_active:
                login(request, user)
                logger.info(f"User logged in successfully via Naver: {user.id}")
                return redirect(reverse("home"))
            else:
                logger.error(
                    "Authentication failed: User not active or not returned by backend.complete"
                )
                return redirect(reverse("home"))  # Or redirect to a login failure page

        except Exception as e:
            logger.error(
                f"Error during Naver authentication callback: {str(e)}", exc_info=True
            )
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
