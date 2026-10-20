import datetime

import jwt
import pytest
import time_machine
from rest_framework_simplejwt.tokens import RefreshToken

from tests.conftest import TRUSTED_ORIGIN, login
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _refresh(api_client, origin=TRUSTED_ORIGIN):
    headers = {"Origin": origin} if origin else {}
    return api_client.post("/api/auth/refresh/", headers=headers)


def test_refresh_without_cookie_is_unauthorized(api_client):
    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_rotates_access_and_refresh_tokens(api_client):
    user = UserFactory()
    login(api_client, user.email)
    old_refresh_cookie = api_client.cookies["edumanage_refresh"].value

    response = _refresh(api_client)

    assert response.status_code == 200
    assert "access" in response.json()
    new_refresh_cookie = response.cookies["edumanage_refresh"].value
    assert new_refresh_cookie != old_refresh_cookie


def test_refresh_without_trusted_origin_is_forbidden(api_client):
    user = UserFactory()
    login(api_client, user.email)
    response = _refresh(api_client, origin=None)
    assert response.status_code == 403


def test_refresh_with_untrusted_origin_is_forbidden(api_client):
    user = UserFactory()
    login(api_client, user.email)
    response = _refresh(api_client, origin="https://attacker.example")
    assert response.status_code == 403


def test_refresh_reused_old_token_is_rejected(api_client):
    user = UserFactory()
    login(api_client, user.email)
    old_cookie_value = api_client.cookies["edumanage_refresh"].value

    assert _refresh(api_client).status_code == 200

    api_client.cookies["edumanage_refresh"] = old_cookie_value
    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_with_forged_token_is_rejected(api_client):
    api_client.cookies["edumanage_refresh"] = "not-a-real-token"
    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_with_none_algorithm_token_is_rejected(api_client):
    user = UserFactory()
    payload = {
        "token_type": "refresh",
        "exp": datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(hours=8),
        "iat": datetime.datetime.now(tz=datetime.UTC),
        "jti": "forged",
        "user_id": str(user.id),
    }
    forged = jwt.encode(payload, key="", algorithm="none")
    api_client.cookies["edumanage_refresh"] = forged
    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_for_deleted_user_is_rejected(api_client):
    user = UserFactory()
    login(api_client, user.email)
    user.delete()

    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_for_deactivated_user_is_rejected(api_client):
    user = UserFactory()
    login(api_client, user.email)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_uuid_user_id_claim_round_trips(api_client):
    user = UserFactory()
    response = login(api_client, user.email)
    access = response.json()["access"]
    decoded = jwt.decode(access, options={"verify_signature": False})
    assert decoded["user_id"] == str(user.id)

    refresh_response = _refresh(api_client)
    new_access = refresh_response.json()["access"]
    new_decoded = jwt.decode(new_access, options={"verify_signature": False})
    assert new_decoded["user_id"] == str(user.id)


def test_refresh_token_has_issuer_and_audience_claims(settings):
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    decoded = jwt.decode(str(refresh), options={"verify_signature": False})
    assert decoded["iss"] == settings.JWT_ISSUER
    assert decoded["aud"] == settings.JWT_AUDIENCE


def test_refresh_session_expires_after_8h_of_inactivity(api_client):
    user = UserFactory()
    with time_machine.travel("2026-01-01 00:00:00", tick=False) as traveller:
        login(api_client, user.email)
        traveller.shift(datetime.timedelta(hours=8, minutes=1))
        response = _refresh(api_client)
    assert response.status_code == 401


def test_refresh_rotation_extends_session_by_8h_each_time(api_client):
    user = UserFactory()
    with time_machine.travel("2026-01-01 00:00:00", tick=False) as traveller:
        login(api_client, user.email)

        # Rafraîchissements réguliers toutes les 7h : la session ne doit
        # jamais expirer puisque chaque rotation redonne 8h.
        for _ in range(3):
            traveller.shift(datetime.timedelta(hours=7))
            assert _refresh(api_client).status_code == 200

        # Mais 8h sans la moindre activité après le dernier refresh expire bien.
        traveller.shift(datetime.timedelta(hours=8, minutes=1))
        assert _refresh(api_client).status_code == 401
