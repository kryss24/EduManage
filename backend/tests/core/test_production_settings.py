"""`config.settings.prod` doit refuser de démarrer avec une configuration
dangereuse. Chaque scénario lance un vrai sous-processus Python qui importe
les réglages (`django.setup()`), pour vérifier le comportement réel au
démarrage plutôt que la seule logique du module en mémoire."""

import os
import subprocess
import sys

from django.conf import settings

BASE_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "SECRET_KEY": "a-fake-secret-key-for-ci-tests-only-not-real",
    "DEBUG": "False",
    "ALLOWED_HOSTS": "example.test",
    "CORS_ALLOWED_ORIGINS": "https://example.test",
    "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
    "JWT_SIGNING_KEY": "a-dedicated-jwt-signing-key-that-is-long-enough-32c",
    "AUTH_COOKIE_SECURE": "True",
}


def _run(overrides):
    env = {**os.environ, **BASE_ENV, **overrides}
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(settings.BASE_DIR),
        timeout=30,
    )


def test_production_settings_load_successfully_with_valid_config():
    result = _run({})
    assert result.returncode == 0, result.stderr


def test_production_settings_fail_if_debug_true():
    result = _run({"DEBUG": "True"})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_production_settings_fail_if_cors_wildcard():
    result = _run({"CORS_ALLOWED_ORIGINS": "*"})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_production_settings_fail_if_cors_empty():
    result = _run({"CORS_ALLOWED_ORIGINS": ""})
    assert result.returncode != 0


def test_production_settings_fail_if_jwt_signing_key_equals_secret_key():
    result = _run({"JWT_SIGNING_KEY": BASE_ENV["SECRET_KEY"]})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_production_settings_fail_if_jwt_signing_key_too_short():
    result = _run({"JWT_SIGNING_KEY": "trop-court"})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_production_settings_fail_if_jwt_signing_key_missing():
    result = _run({"JWT_SIGNING_KEY": ""})
    assert result.returncode != 0


def test_production_settings_fail_if_insecure_cookie_without_explicit_override():
    result = _run({"AUTH_COOKIE_SECURE": "False"})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_production_settings_allow_insecure_cookie_with_explicit_override():
    result = _run({"AUTH_COOKIE_SECURE": "False", "AUTH_COOKIE_ALLOW_INSECURE": "True"})
    assert result.returncode == 0, result.stderr
