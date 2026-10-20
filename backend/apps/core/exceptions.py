"""Gestionnaire d'exceptions DRF : jamais de trace ni de détail interne."""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("security")


def exception_handler(exc, context):
    """Délègue au gestionnaire DRF standard, puis masque tout le reste.

    Les `APIException` (401/403/404/429...) gardent leur réponse JSON
    habituelle. Toute exception imprévue (bug, erreur tierce) est
    journalisée côté serveur sans détail renvoyé au client : réponse 500
    générique uniquement.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    logger.exception(
        "Erreur interne non gérée",
        extra={"path": getattr(request, "path", None)},
    )
    return Response({"detail": "Une erreur interne est survenue."}, status=500)
