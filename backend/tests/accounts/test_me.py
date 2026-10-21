import datetime

import jwt
import pytest

from tests.conftest import login
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/auth/me/")
    assert response.status_code == 401


def test_me_matches_login_payload_shape(auth_client):
    user = UserFactory()
    client = auth_client(user)
    response = client.get("/api/auth/me/")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == user.email
    assert body["school"]["id"] == str(user.school_id)
    assert "permissions" in body
    assert "access" not in body


def test_me_rejects_expired_access_token(auth_client, settings):
    user = UserFactory()
    client = auth_client(user)

    payload = {
        "token_type": "access",
        "exp": datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(minutes=1),
        "iat": datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(minutes=11),
        "jti": "expired-token",
        "user_id": str(user.id),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    expired = jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")

    response = client.get("/api/auth/me/")
    assert response.status_code == 401


def test_me_rejects_token_with_tampered_signature(api_client):
    user = UserFactory()
    valid_token = login(api_client, user.email).json()["access"]
    tampered = valid_token[:-1] + ("A" if valid_token[-1] != "A" else "B")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")

    response = api_client.get("/api/auth/me/")
    assert response.status_code == 401
