import logging

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from tests.factories import DEFAULT_TEST_PASSWORD, SchoolFactory

TRUSTED_ORIGIN = "http://localhost:3000"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Crée la table du cache en base (`createcachetable`) après les
    migrations : le throttling DRF (cache partagé, voir §2) en a besoin,
    et `createcachetable` n'est pas une migration Django classique."""
    with django_db_blocker.unblock():
        call_command("createcachetable")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def security_caplog(caplog):
    """`caplog` qui capture bien le logger "security", configuré avec
    `propagate=False` en production (voir `config.settings.base.LOGGING`) :
    sans ce détour, `caplog` (qui n'écoute que le logger racine) ne verrait
    jamais ses messages et un test de non-fuite passerait pour la mauvaise
    raison (silence total plutôt qu'absence du secret recherché)."""
    logger = logging.getLogger("security")
    previous_propagate = logger.propagate
    logger.propagate = True
    caplog.set_level(logging.INFO, logger="security")
    try:
        yield caplog
    finally:
        logger.propagate = previous_propagate


@pytest.fixture
def school(db):
    return SchoolFactory()


@pytest.fixture
def other_school(db):
    return SchoolFactory()


def login(api_client, email, password=DEFAULT_TEST_PASSWORD):
    return api_client.post(
        "/api/auth/login/",
        {"email": email, "password": password},
        format="json",
        headers={"Origin": TRUSTED_ORIGIN},
    )


@pytest.fixture
def login_as():
    """Connecte `api_client` en tant que `user` : pose le cookie de refresh
    et renvoie l'access token (à placer dans l'en-tête Authorization)."""

    def _login_as(api_client, user, password=DEFAULT_TEST_PASSWORD):
        response = login(api_client, user.email, password)
        assert response.status_code == 200, response.content
        return response.json()["access"]

    return _login_as


@pytest.fixture
def auth_client(api_client, login_as):
    """`APIClient` déjà authentifié (en-tête `Authorization`) pour `user`."""

    def _auth_client(user, password=DEFAULT_TEST_PASSWORD):
        access = login_as(api_client, user, password)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return api_client

    return _auth_client
