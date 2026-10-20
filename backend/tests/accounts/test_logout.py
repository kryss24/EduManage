import pytest

from apps.core.models import AuditLog
from tests.conftest import TRUSTED_ORIGIN
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_logout_requires_authentication(api_client):
    response = api_client.post("/api/auth/logout/", headers={"Origin": TRUSTED_ORIGIN})
    assert response.status_code == 401


def test_logout_requires_trusted_origin(api_client, auth_client):
    user = UserFactory()
    client = auth_client(user)
    response = client.post("/api/auth/logout/")
    assert response.status_code == 403


def test_logout_blacklists_refresh_and_clears_cookie(api_client, auth_client):
    user = UserFactory()
    client = auth_client(user)

    response = client.post("/api/auth/logout/", headers={"Origin": TRUSTED_ORIGIN})
    assert response.status_code == 204
    assert response.cookies["edumanage_refresh"].value == ""

    refresh_response = client.post("/api/auth/refresh/", headers={"Origin": TRUSTED_ORIGIN})
    assert refresh_response.status_code == 401


def test_logout_records_audit_entry(api_client, auth_client):
    user = UserFactory()
    client = auth_client(user)
    client.post("/api/auth/logout/", headers={"Origin": TRUSTED_ORIGIN})
    assert AuditLog.objects.filter(action="logout", user=user).exists()
