# Settings module - import development or production based on environment
import os

environment = os.environ.get("DJANGO_ENV", "development")

if environment == "production":
    from .production import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
