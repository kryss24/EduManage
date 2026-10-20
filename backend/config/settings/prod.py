"""Réglages de production.

Ce module échoue volontairement au chargement (`ImproperlyConfigured`) si la
configuration fournie par l'environnement est dangereuse : mieux vaut un
crash au démarrage qu'un déploiement silencieusement non sécurisé.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import JWT_SIGNING_KEY, LOGGING, SECRET_KEY, env

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "no-referrer"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

X_FRAME_OPTIONS = "DENY"

# Interface d'administration Django : jamais exposée en production.
ADMIN_ENABLED = False

# ---------------------------------------------------------------------------
# Journalisation : JSON uniquement en production.
# ---------------------------------------------------------------------------
LOGGING = {
    **LOGGING,
    "handlers": {
        **LOGGING["handlers"],
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
}

# Schéma OpenAPI : uniquement en dev (DEBUG=True), voir config/urls.py.

# ---------------------------------------------------------------------------
# Vérifications de démarrage (échec rapide plutôt qu'un déploiement non sûr)
# ---------------------------------------------------------------------------
if DEBUG:
    raise ImproperlyConfigured("DEBUG doit être désactivé en production (config.settings.prod).")

if not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS doit lister des origines explicites en production (pas de '*')."
    )

if not JWT_SIGNING_KEY or len(JWT_SIGNING_KEY) < 32:
    raise ImproperlyConfigured(
        "JWT_SIGNING_KEY doit être définie et contenir au moins 32 caractères aléatoires."
    )

if JWT_SIGNING_KEY == SECRET_KEY:
    raise ImproperlyConfigured("JWT_SIGNING_KEY doit être distincte de SECRET_KEY.")

_cookie_secure = env.bool("AUTH_COOKIE_SECURE", default=True)
if not _cookie_secure and not env.bool("AUTH_COOKIE_ALLOW_INSECURE", default=False):
    raise ImproperlyConfigured(
        "AUTH_COOKIE_SECURE=False n'est pas autorisé en production sans "
        "AUTH_COOKIE_ALLOW_INSECURE=True explicite (topologie de développement uniquement)."
    )
AUTH_COOKIE_SECURE = _cookie_secure
