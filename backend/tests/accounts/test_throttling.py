"""Le throttling DRF est désactivé par défaut dans les tests (voir
`config.settings.test`) : ces tests le réactivent explicitement avec des
limites abaissées, pour rester rapides et déterministes.

`DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` ne sont lus par DRF
qu'une seule fois, à l'import de `rest_framework.views`/`throttling` (classes
attributs figés) : `override_settings` ne les recharge donc pas une fois le
module déjà importé. On monkeypatch donc directement ces classes plutôt que
les réglages Django.
"""

import pytest
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from tests.conftest import TRUSTED_ORIGIN, login
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

ALL_THROTTLES = [ScopedRateThrottle, AnonRateThrottle, UserRateThrottle]
_GENEROUS_RATES = {
    "anon": "1000/min",
    "user": "1000/min",
    "login": "1000/min",
    "refresh": "1000/min",
}


def _enable_throttles(monkeypatch, **overrides):
    rates = {**_GENEROUS_RATES, **overrides}
    monkeypatch.setattr(APIView, "throttle_classes", ALL_THROTTLES)
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", rates)
    monkeypatch.setattr(AnonRateThrottle, "THROTTLE_RATES", rates)
    monkeypatch.setattr(UserRateThrottle, "THROTTLE_RATES", rates)


def test_login_throttle_limits_to_configured_rate_per_ip(monkeypatch, api_client):
    _enable_throttles(monkeypatch, login="2/min")
    user = UserFactory()

    assert login(api_client, user.email, "mauvais-mdp").status_code == 401
    assert login(api_client, user.email, "mauvais-mdp").status_code == 401
    response = login(api_client, user.email, "mauvais-mdp")
    assert response.status_code == 429


def test_refresh_throttle_limits_to_configured_rate(monkeypatch, api_client):
    user = UserFactory()
    login(api_client, user.email)
    _enable_throttles(monkeypatch, refresh="1/min")

    first = api_client.post("/api/auth/refresh/", headers={"Origin": TRUSTED_ORIGIN})
    assert first.status_code == 200
    second = api_client.post("/api/auth/refresh/", headers={"Origin": TRUSTED_ORIGIN})
    assert second.status_code == 429


def test_anon_throttle_limits_unauthenticated_requests(monkeypatch, api_client):
    _enable_throttles(monkeypatch, anon="1/min")

    assert api_client.get("/api/health/").status_code == 200
    response = api_client.get("/api/health/")
    assert response.status_code == 429


def test_user_throttle_limits_authenticated_requests(monkeypatch, auth_client):
    user = UserFactory()
    client = auth_client(user)
    _enable_throttles(monkeypatch, user="1/min")

    assert client.get("/api/auth/me/").status_code == 200
    response = client.get("/api/auth/me/")
    assert response.status_code == 429
