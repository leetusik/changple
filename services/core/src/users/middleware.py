"""
Authentication middleware for Changple Core service.
"""

import logging

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
        if request.path.endswith("/naver/login/"):
            logger.debug("Naver login requested - letting social-auth handle state")

        elif request.path.endswith("/naver/callback/"):
            logger.debug(f"Naver callback received: {request.GET}")

            state = request.GET.get("state")
            logger.debug(f"Received state: {state}")

            # Clean up the redirect_state parameter if present
            if "redirect_state" in request.GET:
                query_dict = request.GET.copy()
                redirect_state = query_dict.pop("redirect_state")
                logger.debug(f"Removed redirect_state: {redirect_state}")
                request.GET = query_dict
                logger.debug(f"Updated request parameters: {request.GET}")
