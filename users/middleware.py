import logging
import urllib.parse
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class NaverAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle Naver OAuth state management.

    Naver OAuth requires a state parameter for security.
    This middleware ensures proper state handling between Naver and social-auth.
    """

    def process_request(self, request):
        """Process the request to handle Naver authentication state."""
        if request.path == "/naver/login/":
            # Let social-auth handle state
            logger.debug("Naver login requested - letting social-auth handle state")

        elif request.path == "/naver/callback/":
            # Process the callback
            logger.debug(f"Naver callback received: {request.GET}")

            # Save state for debugging
            state = request.GET.get("state")
            logger.debug(f"Received state: {state}")

            # The issue is that Naver adds redirect_state to the callback URL which confuses social-auth
            # We need to:
            # 1. Fix the redirect_uri that's stored in the session to match what Naver sends
            # 2. Or clean up the request parameters so they match what social-auth expects

            # We'll go with approach #2 - clean the request
            if "redirect_state" in request.GET:
                # Create a mutable copy of QueryDict
                query_dict = request.GET.copy()

                # Remove redirect_state parameter
                redirect_state = query_dict.pop("redirect_state")
                logger.debug(f"Removed redirect_state: {redirect_state}")

                # Update request.GET
                request.GET = query_dict
                logger.debug(f"Updated request parameters: {request.GET}")

            # Let social-auth validate the state parameter
