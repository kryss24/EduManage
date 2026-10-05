"""Réglages pour l'exécution des tests (pytest)."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECRET_KEY = env("SECRET_KEY", default="test-secret-key")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
