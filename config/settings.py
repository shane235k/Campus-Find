"""Django settings for Campus Lost & Found Hub project.

Phase 0.1 Foundation Architecture (Neon PostgreSQL & Custom User Model).
"""

from pathlib import Path
import sys
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure the 'apps' directory is included in Python search path
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    DATABASE_URL=(str, None),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "0.0.0.0"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:8000", "http://127.0.0.1:8000"]),
    TIME_ZONE=(str, "Asia/Kolkata"),
    LANGUAGE_CODE=(str, "en-us"),
    CONN_MAX_AGE=(int, 600),
)

# Read .env file if available
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "CRITICAL ERROR: SECRET_KEY environment variable is not set. "
        "Define SECRET_KEY in your .env file or host environment variables."
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "pgvector",
]

LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.items.apps.ItemsConfig",
    "apps.matching.apps.MatchingConfig",
    "apps.claims.apps.ClaimsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.dashboard.apps.DashboardConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database Configuration (Neon PostgreSQL via DATABASE_URL)
# Strictly environment-driven, never hardcoded.
DATABASE_URL = env("DATABASE_URL", default=None)
if not DATABASE_URL:
    raise ValueError(
        "CRITICAL ERROR: DATABASE_URL environment variable is not set. "
        "Define DATABASE_URL in your .env file with your Neon PostgreSQL connection string."
    )

DATABASES = {
    "default": env.db("DATABASE_URL")
}

# SSL and connection pooling configuration for Neon
db_host = DATABASES["default"].get("HOST", "")
if "neon.tech" in db_host:
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("sslmode", "require")

DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=600)

# If running Django test runner against Neon, route through the direct endpoint
# because PgBouncer pooler endpoints reject administrative CREATE DATABASE queries
if "test" in sys.argv and "-pooler" in DATABASES["default"].get("HOST", ""):
    DATABASES["default"]["HOST"] = DATABASES["default"]["HOST"].replace("-pooler", "")

# Custom User Model (Configured in Phase 0.1 before dependent model migrations)
AUTH_USER_MODEL = "accounts.CampusUser"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (Item uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework Settings (Phase 0 Foundation)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
