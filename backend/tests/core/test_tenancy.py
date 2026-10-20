"""SEC-01 : isolation multi-tenant applicative.

Utilise le ViewSet de test `tests.tenancy_testkit.LevelTestViewSet`
(modèle `Level`, `feature="classrooms"`) monté uniquement sous
`tests.urls_test`, pour exercer `TenantScopedViewSetMixin` et
`TenantModelSerializer` sans CRUD métier en production.
"""

import uuid

import pytest

from apps.core.models import AuditLog
from apps.core.tenancy import SchoolScopeError, TenantPrimaryKeyRelatedField, get_request_school
from tests.factories import LevelFactory, SchoolFactory, SuperAdminFactory, UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls_test")]

LEVELS_URL = "/api/test/levels/"


def _detail_url(level):
    return f"{LEVELS_URL}{level.id}/"


def test_SEC_01_list_is_scoped_to_own_school(auth_client):
    school_a = SchoolFactory()
    school_b = SchoolFactory()
    own_level = LevelFactory(school=school_a)
    LevelFactory(school=school_b)
    user = UserFactory(school=school_a)

    client = auth_client(user)
    response = client.get(LEVELS_URL)

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {str(own_level.id)}


def test_SEC_01_retrieve_other_school_object_returns_404(auth_client):
    school_a = SchoolFactory()
    other_school = SchoolFactory()
    other_level = LevelFactory(school=other_school)
    user = UserFactory(school=school_a)

    client = auth_client(user)
    response = client.get(_detail_url(other_level))

    assert response.status_code == 404


def test_SEC_01_update_other_school_object_returns_404_even_with_url_id(auth_client):
    school_a = SchoolFactory()
    other_school = SchoolFactory()
    other_level = LevelFactory(school=other_school, order=1)
    user = UserFactory(school=school_a)

    client = auth_client(user)
    response = client.patch(_detail_url(other_level), {"name": "Piraté"}, format="json")

    assert response.status_code == 404
    other_level.refresh_from_db()
    assert other_level.name != "Piraté"


def test_SEC_01_delete_other_school_object_returns_404(auth_client):
    school_a = SchoolFactory()
    other_school = SchoolFactory()
    other_level = LevelFactory(school=other_school)
    user = UserFactory(school=school_a)

    client = auth_client(user)
    response = client.delete(_detail_url(other_level))

    assert response.status_code == 404
    assert type(other_level).objects.filter(pk=other_level.pk).exists()


def test_SEC_01_school_in_request_body_is_ignored_on_create(auth_client):
    own_school = SchoolFactory()
    other_school = SchoolFactory()
    user = UserFactory(school=own_school)

    client = auth_client(user)
    response = client.post(
        LEVELS_URL,
        {"name": "CP1", "order": 1, "school": str(other_school.id)},
        format="json",
    )

    assert response.status_code == 201, response.content
    assert response.json()["school"] == str(own_school.id)


def test_SEC_01_normal_user_cannot_choose_school_via_header(auth_client):
    own_school = SchoolFactory()
    other_school = SchoolFactory()
    LevelFactory(school=other_school)
    user = UserFactory(school=own_school)

    client = auth_client(user)
    response = client.get(LEVELS_URL, headers={"X-School-Id": str(other_school.id)})

    assert response.status_code == 200
    assert response.json() == []  # toujours scopé sur sa propre école, en-tête ignoré.


def test_SEC_01_superadmin_without_header_returns_400(auth_client):
    admin = SuperAdminFactory()
    client = auth_client(admin)

    response = client.get(LEVELS_URL)
    assert response.status_code == 400


def test_SEC_01_superadmin_with_valid_header_succeeds_and_audits(auth_client):
    school = SchoolFactory()
    level = LevelFactory(school=school)
    admin = SuperAdminFactory()

    client = auth_client(admin)
    response = client.get(LEVELS_URL, headers={"X-School-Id": str(school.id)})

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(level.id)}
    assert AuditLog.objects.filter(
        action="superadmin_tenant_access", user=admin, school=school
    ).exists()


def test_SEC_01_superadmin_with_unknown_school_id_is_rejected(auth_client):
    admin = SuperAdminFactory()
    client = auth_client(admin)

    response = client.get(LEVELS_URL, headers={"X-School-Id": str(uuid.uuid4())})
    assert response.status_code == 400


def test_SEC_01_superadmin_with_inactive_school_id_is_rejected(auth_client):
    school = SchoolFactory(is_active=False)
    admin = SuperAdminFactory()
    client = auth_client(admin)

    response = client.get(LEVELS_URL, headers={"X-School-Id": str(school.id)})
    assert response.status_code == 400


def test_SEC_01_get_request_school_rejects_malformed_header(rf):
    admin = SuperAdminFactory()
    request = rf.get("/", headers={"X-School-Id": "not-a-uuid"})
    request.user = admin

    with pytest.raises(SchoolScopeError):
        get_request_school(request)


def test_SEC_01_tenant_primary_key_field_rejects_object_from_other_school(rf):
    own_school = SchoolFactory()
    other_school = SchoolFactory()
    own_level = LevelFactory(school=own_school)
    other_level = LevelFactory(school=other_school)
    user = UserFactory(school=own_school)

    request = rf.get("/")
    request.user = user
    field = TenantPrimaryKeyRelatedField(queryset=type(own_level).objects.all())
    field._context = {"request": request}

    assert field.to_internal_value(str(own_level.id)) == own_level

    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        field.to_internal_value(str(other_level.id))
