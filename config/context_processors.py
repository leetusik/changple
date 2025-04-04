import os

from django.conf import settings


def settings_context(request):
    """Context processor that provides access to settings variables."""
    return {
        "ALLOWED_HOSTS": request.get_host().split(":")[0],
        "DEBUG": settings.DEBUG,
        "PORT": ":8000" if settings.DEBUG else "",
    }
