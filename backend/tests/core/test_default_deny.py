"""Défaut = refus : chaque vue d'API, hors liste blanche (health, login,
refresh), doit exiger `HasFeatureAccess` ou l'authentification. Parcourt le
résolveur d'URL réel (`config.urls`) plutôt qu'une liste maintenue à la
main, pour détecter une vue oubliée.
"""

from django.urls import get_resolver
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasFeatureAccess

WHITELIST = {"api/health/", "api/auth/login/", "api/auth/refresh/"}


def _iter_view_classes(resolver, prefix=""):
    for pattern in resolver.url_patterns:
        sub_prefix = prefix + str(pattern.pattern)
        if hasattr(pattern, "url_patterns"):
            yield from _iter_view_classes(pattern, sub_prefix)
            continue
        view_cls = getattr(pattern.callback, "cls", None)
        if view_cls is None:
            continue  # vue non-DRF (ex. admin Django) : hors du périmètre de cette règle.
        yield sub_prefix, view_cls


def test_default_deny_every_api_view_requires_auth_or_feature_access(settings):
    resolver = get_resolver(settings.ROOT_URLCONF)
    checked_paths = []

    for path, view_cls in _iter_view_classes(resolver):
        if path in WHITELIST:
            continue
        checked_paths.append(path)

        permission_classes = list(getattr(view_cls, "permission_classes", []))
        has_feature_access = any(
            isinstance(p, type) and issubclass(p, HasFeatureAccess) for p in permission_classes
        )
        requires_auth = any(
            isinstance(p, type) and issubclass(p, IsAuthenticated) for p in permission_classes
        )
        assert has_feature_access or requires_auth, (
            f"{path} ({view_cls.__name__}) n'exige ni HasFeatureAccess ni authentification : "
            f"permission_classes={permission_classes!r}"
        )

    # Garde-fou : s'assurer que le test a bien parcouru des vues réelles
    # (sinon un refactor cassant le résolveur passerait silencieusement).
    assert len(checked_paths) >= 3
