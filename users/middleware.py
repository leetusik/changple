import logging
import urllib.parse
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class NaverAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle Naver OAuth state management.

    Naver OAuth requires a state parameter for security.
    This middleware extracts the state parameter from the social-auth library
    instead of generating its own.
    """

    def process_request(self, request):
        """Process the request to handle Naver authentication state."""
        if request.path == "/naver/login/":
            # Instead of generating our own state, we'll let social-auth handle it
            # We'll just log this for debugging
            logger.debug("Naver login requested - letting social-auth handle state")

        elif request.path == "/naver/callback/":
            # Process the callback
            logger.debug(f"Naver callback received: {request.GET}")

            # Naver returns state parameter - we'll capture this for debugging only
            state = request.GET.get("state")
            logger.debug(f"Received state: {state}")

            # We'll disable state validation in middleware - let social-auth handle it
            # To avoid the conflict, we won't set state_error anymore
            pass
