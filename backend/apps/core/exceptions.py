"""Gestionnaire d'exceptions DRF : jamais de trace ni de détail interne."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("security")


def exception_handler(exc, context):
    """Délègue au gestionnaire DRF standard, gère les exceptions Django métier/BD,
    puis masque tout le reste derrière une 500 générique.

    - Les `APIException` DRF gardent leur réponse JSON habituelle.
    - `ValidationError` Django (ex. levée par `full_clean()`) → 400 formaté DRF par champ.
    - `ProtectedError` Django (suppression protégée) → 409 avec message clair.
    - `IntegrityError` Django (conflit d'intégrité / contrainte BD) → 409 générique.
    - Toute exception imprévue est journalisée côté serveur sans fuite technique (500).
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, DjangoValidationError):
        data = serializers.as_serializer_error(exc)
        if isinstance(data, list):
            data = {"non_field_errors": data}
        return Response(data, status=400)

    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "Impossible de supprimer cet élément car d'autres ressources en dépendent."},
            status=409,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": "Un conflit d'intégrité est survenu."},
            status=409,
        )

    request = context.get("request")
    logger.exception(
        "Erreur interne non gérée",
        extra={"path": getattr(request, "path", None)},
    )
    return Response({"detail": "Une erreur interne est survenue."}, status=500)
