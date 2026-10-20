import pytest

from apps.core.models import AuditLog
from tests.conftest import TRUSTED_ORIGIN, login
from tests.factories import DEFAULT_TEST_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "Un-Nouveau-Mot-De-Passe-Solide-2026!"


def test_change_password_requires_authentication(api_client):
    response = api_client.post(
        "/api/auth/change-password/",
        {"old_password": DEFAULT_TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 401


def test_change_password_rejects_wrong_old_password(auth_client):
    user = UserFactory()
    client = auth_client(user)
    response = client.post(
        "/api/auth/change-password/",
        {"old_password": "mauvais-ancien-mdp", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 400


def test_change_password_rejects_weak_new_password(auth_client):
    user = UserFactory()
    client = auth_client(user)
    response = client.post(
        "/api/auth/change-password/",
        {"old_password": DEFAULT_TEST_PASSWORD, "new_password": "short1"},
        format="json",
    )
    assert response.status_code == 400


def test_change_password_success_allows_login_with_new_password(api_client, auth_client):
    user = UserFactory()
    client = auth_client(user)
    response = client.post(
        "/api/auth/change-password/",
        {"old_password": DEFAULT_TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 204

    assert login(api_client, user.email, DEFAULT_TEST_PASSWORD).status_code == 401
    assert login(api_client, user.email, NEW_PASSWORD).status_code == 200


def test_change_password_invalidates_existing_refresh_token(api_client, auth_client):
    user = UserFactory()
    client = auth_client(user)  # pose le cookie de refresh sur `api_client`

    client.post(
        "/api/auth/change-password/",
        {"old_password": DEFAULT_TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    refresh_response = api_client.post("/api/auth/refresh/", headers={"Origin": TRUSTED_ORIGIN})
    assert refresh_response.status_code == 401


def test_change_password_records_audit_entry(auth_client):
    user = UserFactory()
    client = auth_client(user)
    client.post(
        "/api/auth/change-password/",
        {"old_password": DEFAULT_TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert AuditLog.objects.filter(action="password_changed", user=user).exists()
