"""Permission DRF à échec fermé, basée sur la matrice de fonctionnalités."""

from rest_framework.permissions import BasePermission

from apps.accounts.features import AccessLevel, access_level_for, level_satisfies

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class HasFeatureAccess(BasePermission):
    """La vue doit déclarer `feature` (une clé de `FEATURE_MATRIX`).

    **Échec fermé** : une vue sans attribut `feature` refuse l'accès à tout
    le monde, y compris un `SUPER_ADMIN` — c'est un bug de la vue à
    corriger, jamais un accès à accorder par défaut.

    Le niveau requis dépend par défaut de la méthode HTTP (lecture = `L`,
    écriture = `E`) ; une vue peut préciser des niveaux par action via
    `feature_required_levels = {"destroy": AccessLevel.ADMIN, ...}`.
    """

    message = "Vous n'avez pas accès à cette fonctionnalité."

    def has_permission(self, request, view):
        feature = getattr(view, "feature", None)
        if not feature:
            return False
        required = self._required_level(request, view)
        role = getattr(request.user, "role", None)
        granted = access_level_for(role, feature)
        return level_satisfies(granted, required)

    @staticmethod
    def _required_level(request, view):
        overrides = getattr(view, "feature_required_levels", None)
        action = getattr(view, "action", None)
        if overrides and action in overrides:
            return overrides[action]
        if request.method in _WRITE_METHODS:
            return AccessLevel.WRITE
        return AccessLevel.READ
