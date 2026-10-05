import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_returns_ok():
    client = APIClient()
    url = reverse("core:health")

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_health_check_is_public(client):
    """L'endpoint de santé doit rester accessible sans authentification."""
    response = client.get("/api/health/")

    assert response.status_code != status.HTTP_401_UNAUTHORIZED
