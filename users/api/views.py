import logging

from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.auth_service import AuthService
from ..services.social_auth_service import SocialAuthService
from .serializers import SocialAuthSerializer, UserProfileSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    API viewset for User model.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == "profile":
            return UserProfileSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["profile", "update_profile"]:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def profile(self, request):
        """Get the current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["put", "patch"])
    def update_profile(self, request):
        """Update the current user's profile."""
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SocialAuthView(APIView):
    """
    API view for social authentication.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Process social authentication request.

        Expected payload:
        {
            "provider": "naver",
            "code": "authorization_code",
            "redirect_uri": "optional_redirect_uri"
        }
        """
        serializer = SocialAuthSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        provider = serializer.validated_data["provider"]
        code = serializer.validated_data["code"]
        redirect_uri = serializer.validated_data.get("redirect_uri")

        # Here you would call your social auth service to process the authorization code
        # For now, just return an error since this would require additional implementation
        return Response(
            {"detail": "Social authentication API not fully implemented yet"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
