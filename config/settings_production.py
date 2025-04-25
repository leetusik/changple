from .settings import *

# Security settings
DEBUG = os.environ.get("DEBUG", False) == "1"
SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "changple.ai,134.185.116.242").split(
    ","
)

# Ensure CSRF and session cookies are secure
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Add these settings for SameSite cookie behavior
CSRF_COOKIE_SAMESITE = "None"  # Allow cross-site requests when secure
SESSION_COOKIE_SAMESITE = "None"

# Add trusted origins for CSRF
CSRF_TRUSTED_ORIGINS = ["https://changple.ai", "https://www.changple.ai"]

# Static files configuration
STATIC_ROOT = os.environ.get("STATIC_ROOT", os.path.join(BASE_DIR, "static_root"))
STATIC_URL = "/static/"  # Ensure leading slash to match Nginx config

# Redis configuration for RQ
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 360,
    },
    "high": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 500,
    },
    "low": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 1200,
    },
}

# Social Auth callback URL for production
SOCIAL_AUTH_NAVER_CALLBACK_URL = os.environ.get(
    "SOCIAL_AUTH_NAVER_CALLBACK_URL",
    (
        f"https://{ALLOWED_HOSTS[0]}/naver/callback/"
        if ALLOWED_HOSTS
        else "https://changple.ai/naver/callback/"
    ),
)

# Publication path for production - use environment variable if available
PUBLICATION_PATH = os.environ.get(
    "PUBLICATION_PATH",
    os.path.join(BASE_DIR, "chatbot", "data", "창플 출판 서적 요약.txt"),
)

# Database - using SQLite for now
# In a production environment, you might want to use a more robust database like PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        "OPTIONS": {
            "timeout": 30,  # in seconds
        },
    }
}

# Logging settings
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "django.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "users": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "social_core": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "social_django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "scraper": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
