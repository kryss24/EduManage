"""
Réglages Django communs à tous les environnements.

Toute valeur sensible ou dépendante de l'environnement (secrets, hôtes,
base de données, CORS...) est lue depuis les variables d'environnement
via django-environ. Aucune valeur par défaut « permissive » n'est fournie
ici pour la production : chaque environnement (dev/prod/test) surcharge
ce qu'il faut.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Lit backend/.env si présent (en local sans Docker). Dans Docker, les
# variables sont injectées directement par docker-compose / .env.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="changeme-override-in-env")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Tiers
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "axes",
    "drf_spectacular",
    # Apps internes du projet École
    "apps.tenants",
    "apps.accounts",
    "apps.academics",
    "apps.grades",
    "apps.reports",
    "apps.core",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/ecole",
    )
}

# ---------------------------------------------------------------------------
# Authentification Django (axes en premier : voir docs/securite.md)
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ---------------------------------------------------------------------------
# Validation des mots de passe
# ---------------------------------------------------------------------------
# Hachage : Argon2 en premier (nouveaux mots de passe), BCryptSHA256 en
# second pour accepter la vérification de hash bcrypt existants. Les
# hashers Django "legacy" (PBKDF2, etc.) sont volontairement absents : ce
# produit n'a jamais eu d'autre hasher en production.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Interface d'administration Django : désactivée en production (prod.py).
ADMIN_ENABLED = True

# ---------------------------------------------------------------------------
# Cache partagé (throttling DRF) — base de données pour être partagé entre
# tous les workers gunicorn sans dépendance supplémentaire (Redis...).
# Nécessite `python manage.py createcachetable` (voir README).
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Échec fermé par défaut : voir apps.accounts.permissions.HasFeatureAccess
    # et apps.core.tenancy.SchoolIsActive. Les seules routes publiques sont
    # health/login/refresh (authentication_classes/permission_classes vides
    # explicitement déclarés sur ces vues).
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "apps.core.tenancy.SchoolIsActive",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "120/min",
        "login": "5/min",
        "refresh": "30/min",
    },
    # Nombre de proxys en amont de l'application (load balancer...) : utilisé
    # pour déterminer la vraie IP cliente depuis X-Forwarded-For.
    "NUM_PROXIES": env.int("NUM_PROXIES", default=0),
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "EduManage API",
    "DESCRIPTION": "API de gestion d'écoles primaires privées (multi-tenant).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
# Durées pilotées par variables d'environnement (cahier des charges : accès
# courte durée, session considérée expirée après 8h d'inactivité — implémenté
# par la rotation du refresh qui redonne `JWT_REFRESH_HOURS` à chaque usage).
JWT_ACCESS_MINUTES = env.int("JWT_ACCESS_MINUTES", default=10)
JWT_REFRESH_HOURS = env.int("JWT_REFRESH_HOURS", default=8)

# Clé de signature DÉDIÉE aux JWT, distincte de SECRET_KEY. En dev, une
# valeur par défaut est fournie pour ne pas bloquer le premier démarrage ;
# `prod.py` refuse de démarrer si elle n'a pas été explicitement définie,
# si elle est trop courte, ou si elle est identique à SECRET_KEY.
JWT_SIGNING_KEY = env(
    "JWT_SIGNING_KEY",
    default="dev-only-jwt-signing-key-change-me-32chars+",
)
JWT_ISSUER = env("JWT_ISSUER", default="edumanage-api")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="edumanage-frontend")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=JWT_REFRESH_HOURS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "ISSUER": JWT_ISSUER,
    "AUDIENCE": JWT_AUDIENCE,
    "AUTH_HEADER_TYPES": ("Bearer",),
    # Identifiants UUID : le claim est systématiquement transmis comme
    # chaîne (voir apps.accounts.tokens) car un UUID n'est pas sérialisable
    # JSON tel quel.
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# Cookie du refresh token (jamais le JSON de réponse)
# ---------------------------------------------------------------------------
AUTH_COOKIE_NAME = "edumanage_refresh"
AUTH_COOKIE_PATH = "/api/auth/"
AUTH_COOKIE_DOMAIN = env("AUTH_COOKIE_DOMAIN", default=None)
# "Lax"/"Strict" en topologie recommandée (même domaine racine que le
# frontend) ; "None" uniquement documenté comme option pour une topologie
# cross-site (voir README « Topologie de déploiement »).
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="Lax")
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=True)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-school-id",
]

# ---------------------------------------------------------------------------
# django-axes : verrouillage par couple (identifiant, IP)
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_HTTP_RESPONSE_CODE = 429
# Le champ "username" transmis aux vérifications d'axes est l'email.
AXES_USERNAME_FORM_FIELD = "email"
NUM_PROXIES = env.int("NUM_PROXIES", default=0)
AXES_IPWARE_PROXY_COUNT = NUM_PROXIES or None

# ---------------------------------------------------------------------------
# Super administrateur de départ (voir apps.accounts.management.commands)
# ---------------------------------------------------------------------------
SUPERADMIN_EMAIL = env("SUPERADMIN_EMAIL", default="")
SUPERADMIN_PASSWORD = env("SUPERADMIN_PASSWORD", default="")
SUPERADMIN_NOM = env("SUPERADMIN_NOM", default="Administrateur")
SUPERADMIN_PRENOM = env("SUPERADMIN_PRENOM", default="Super")

# ---------------------------------------------------------------------------
# Journalisation
# ---------------------------------------------------------------------------
# "security" : évènements d'authentification/autorisation (jamais de secret,
# token ou mot de passe — voir apps.core.audit). JSON uniquement en
# production (surchargé dans prod.py) ; format lisible ailleurs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
        "json": {"()": "apps.core.logging.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
