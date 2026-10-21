"""Le gestionnaire d'exceptions DRF masque toute exception imprévue derrière
une 500 générique, sans jamais renvoyer de trace au client."""

import logging

import pytest
from rest_framework.exceptions import NotFound
from rest_framework.test import APIRequestFactory

from apps.accounts import views as accounts_views
from apps.core.exceptions import exception_handler
from tests.factories import UserFactory


def test_exception_handler_delegates_known_drf_exceptions():
    request = APIRequestFactory().get("/")
    response = exception_handler(NotFound("introuvable"), {"request": request})
    assert response.status_code == 404
    assert response.data == {"detail": "introuvable"}


def test_exception_handler_masks_unexpected_exceptions(caplog):
    caplog.set_level(logging.ERROR)
    request = APIRequestFactory().get("/api/whatever/")

    response = exception_handler(
        RuntimeError("boum, détail interne sensible"), {"request": request}
    )

    assert response.status_code == 500
    assert response.data == {"detail": "Une erreur interne est survenue."}
    assert "boum, détail interne sensible" not in str(response.data)


@pytest.mark.django_db
def test_unhandled_exception_in_a_real_view_returns_generic_500(auth_client, monkeypatch):
    def boom(self, request):
        raise RuntimeError("panne interne simulée")

    monkeypatch.setattr(accounts_views.MeView, "get", boom)

    user = UserFactory()
    client = auth_client(user)
    response = client.get("/api/auth/me/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Une erreur interne est survenue."}
