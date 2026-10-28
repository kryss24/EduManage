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


def test_exception_handler_handles_django_validation_error():
    from django.core.exceptions import ValidationError as DjangoValidationError

    request = APIRequestFactory().get("/")
    # Dict error
    exc_dict = DjangoValidationError({"label": ["Ce champ est requis."]})
    resp_dict = exception_handler(exc_dict, {"request": request})
    assert resp_dict.status_code == 400
    assert "label" in resp_dict.data

    # List error
    exc_list = DjangoValidationError(["Erreur globale."])
    resp_list = exception_handler(exc_list, {"request": request})
    assert resp_list.status_code == 400
    assert "non_field_errors" in resp_list.data


def test_exception_handler_handles_protected_error():
    from django.db.models import ProtectedError

    request = APIRequestFactory().delete("/")
    exc = ProtectedError("protected msg", [])
    response = exception_handler(exc, {"request": request})
    assert response.status_code == 409
    assert response.data == {
        "detail": "Impossible de supprimer cet élément car d'autres ressources en dépendent."
    }


def test_exception_handler_handles_integrity_error():
    from django.db import IntegrityError

    request = APIRequestFactory().post("/")
    exc = IntegrityError("duplicate key value violates unique constraint xyz")
    response = exception_handler(exc, {"request": request})
    assert response.status_code == 409
    assert response.data == {"detail": "Un conflit d'intégrité est survenu."}
    assert "violates unique constraint" not in str(response.data)
