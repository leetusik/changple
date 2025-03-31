from .settings import *

# Security settings
DEBUG = os.environ.get("DEBUG", False) == "1"
SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Ensure CSRF and session cookies are secure
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Set the static root for collectstatic
STATIC_ROOT = os.environ.get("STATIC_ROOT", os.path.join(BASE_DIR, "static_root"))

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
SOCIAL_AUTH_NAVER_CALLBACK_URL = (
    f"https://{ALLOWED_HOSTS[0]}/naver/callback/"
    if ALLOWED_HOSTS
    else "https://134.185.116.242/naver/callback/"
)

# Database - using SQLite for now
# In a production environment, you might want to use a more robust database like PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        "OPTIONS": {
            "timeout": 30,  # in seconds
            "pragmas": {
                "journal_mode": "wal",  # Use Write-Ahead Logging
                "synchronous": "normal",  # Synchronous setting for better performance with reasonable safety
                "cache_size": -1024 * 32,  # 32MB cache
                "foreign_keys": 1,  # Enforce foreign keys
            },
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
