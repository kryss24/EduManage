"""Réglages pour l'exécution des tests (pytest)."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import DATABASES, REST_FRAMEWORK, env

DEBUG = False

SECRET_KEY = env("SECRET_KEY", default="test-secret-key")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Les tests ne doivent jamais tourner sur autre chose que PostgreSQL : les
# contraintes d'exclusion, CheckConstraint complexes et comportements UUID
# du modèle de données (SCRUM-7) ne sont pas portables sur SQLite.
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        "config.settings.test exige une base PostgreSQL (DATABASE_URL doit utiliser "
        f"postgres://...). Moteur détecté : {DATABASES['default']['ENGINE']!r}."
    )

# Hasher rapide par défaut pour la vitesse des tests ; un test dédié
# (tests/accounts/test_password_hashing.py) force temporairement les
# hashers réels pour vérifier que le hash de production commence par
# "argon2$".
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Pas de HTTPS dans le client de test.
AUTH_COOKIE_SECURE = False

# Throttling désactivé par défaut : les tests dédiés l'activent eux-mêmes
# via `override_settings` avec des limites abaissées.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": (), "DEFAULT_THROTTLE_RATES": {}}

ADMIN_ENABLED = True
