"""Tests directs de `HasFeatureAccess`, en complément des tests bout-en-bout
de `tests/core/test_tenancy.py` (qui n'exercent qu'une seule fonctionnalité,
`classrooms`, via le ViewSet de test)."""

from types import SimpleNamespace

import pytest

from apps.accounts.features import AccessLevel
from apps.accounts.models import User
from apps.accounts.permissions import HasFeatureAccess

permission = HasFeatureAccess()


def _request(method, user_role):
    return SimpleNamespace(method=method, user=SimpleNamespace(role=user_role))


def _view(feature=None, feature_required_levels=None, action=None):
    return SimpleNamespace(
        feature=feature, feature_required_levels=feature_required_levels, action=action
    )


def test_view_without_feature_is_denied_for_every_role():
    for role in User.Role.values:
        assert permission.has_permission(_request("GET", role), _view(feature=None)) is False


def test_read_access_allows_get_denies_write_for_read_only_role():
    request_get = _request("GET", User.Role.TEACHER)
    request_post = _request("POST", User.Role.TEACHER)
    view = _view(feature="classrooms")  # TEACHER a "L" sur classrooms

    assert permission.has_permission(request_get, view) is True
    assert permission.has_permission(request_post, view) is False


def test_no_access_role_is_denied_on_read_and_write():
    view = _view(feature="classrooms")  # PARENT a "-" sur classrooms
    assert permission.has_permission(_request("GET", User.Role.PARENT), view) is False
    assert permission.has_permission(_request("POST", User.Role.PARENT), view) is False


def test_write_access_role_is_allowed_on_read_and_write():
    view = _view(feature="grades")  # TEACHER a "E" sur grades
    assert permission.has_permission(_request("GET", User.Role.TEACHER), view) is True
    assert permission.has_permission(_request("POST", User.Role.TEACHER), view) is True
    assert permission.has_permission(_request("DELETE", User.Role.TEACHER), view) is True


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_all_write_methods_require_write_level(method):
    view = _view(feature="classrooms")  # TEACHER a seulement "L"
    assert permission.has_permission(_request(method, User.Role.TEACHER), view) is False


def test_feature_required_levels_override_is_honored_per_action():
    # Un parent a "L" sur report_cards : sans override, un DELETE serait refusé.
    view = _view(
        feature="report_cards",
        feature_required_levels={"destroy": AccessLevel.READ},
        action="destroy",
    )
    request = _request("DELETE", User.Role.PARENT)
    assert permission.has_permission(request, view) is True


def test_feature_required_levels_only_applies_to_the_matching_action():
    view = _view(
        feature="report_cards",
        feature_required_levels={"destroy": AccessLevel.READ},
        action="update",  # pas "destroy" : retombe sur la règle par défaut (E pour write)
    )
    request = _request("PATCH", User.Role.PARENT)  # PARENT n'a que "L"
    assert permission.has_permission(request, view) is False
