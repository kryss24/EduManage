"""Tests complets pour l'API des niveaux scolaires et de la fonction create_default_levels."""

import pytest

from apps.academics.api.services import create_default_levels
from apps.academics.models import Level
from apps.accounts.models import User
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    LevelFactory,
    SchoolFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_LEVELS_crud_and_validations(auth_client):
    """CRUD des niveaux : unicité du nom insensible à la casse, ordre positif et unique."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # 1. Création niveau avec ordre spécifié
    res1 = client.post(
        "/api/academics/levels/",
        {"name": "CP1", "order": 1},
        format="json",
    )
    assert res1.status_code == 201
    assert res1.json()["name"] == "CP1"
    assert res1.json()["order"] == 1

    # 2. Nom dupliqué (casse différente) -> 400
    res_dup_name = client.post(
        "/api/academics/levels/",
        {"name": "cp1", "order": 2},
        format="json",
    )
    assert res_dup_name.status_code == 400
    assert "name" in res_dup_name.json()

    # 3. Ordre dupliqué -> 400
    res_dup_order = client.post(
        "/api/academics/levels/",
        {"name": "CP2", "order": 1},
        format="json",
    )
    assert res_dup_order.status_code == 400
    assert "order" in res_dup_order.json()

    # 4. Ordre négatif ou nul -> 400
    res_zero = client.post(
        "/api/academics/levels/",
        {"name": "CP2", "order": 0},
        format="json",
    )
    assert res_zero.status_code == 400
    assert "order" in res_zero.json()


def test_LEVELS_auto_order_generation(auth_client):
    """Si order est omis, il vaut max(order) + 1 (ou 1 si premier)."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # Premier niveau sans ordre -> order = 1
    res1 = client.post("/api/academics/levels/", {"name": "CP1"}, format="json")
    assert res1.status_code == 201
    assert res1.json()["order"] == 1

    # Deuxième niveau sans ordre -> order = 2
    res2 = client.post("/api/academics/levels/", {"name": "CP2"}, format="json")
    assert res2.status_code == 201
    assert res2.json()["order"] == 2

    # Troisième niveau avec ordre 10
    res10 = client.post("/api/academics/levels/", {"name": "CM2", "order": 10}, format="json")
    assert res10.status_code == 201
    assert res10.json()["order"] == 10

    # Quatrième niveau sans ordre -> order = 11 (max + 1)
    res11 = client.post("/api/academics/levels/", {"name": "CE1"}, format="json")
    assert res11.status_code == 201
    assert res11.json()["order"] == 11


def test_LEVELS_delete_protection(auth_client):
    """Suppression refusée (409) si des classes sont rattachées au niveau."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(school=school)
    lvl = LevelFactory(school=school)
    cls = ClassroomFactory(academic_year=year, level=lvl, school=school)

    # A des classes -> 409
    res = client.delete(f"/api/academics/levels/{lvl.id}/")
    assert res.status_code == 409
    assert "classes y sont rattachées" in res.json()["detail"]

    # Supprimer la classe puis le niveau -> 204
    cls.delete()
    res_ok = client.delete(f"/api/academics/levels/{lvl.id}/")
    assert res_ok.status_code == 204


def test_LEVELS_create_default_levels_idempotency():
    """create_default_levels crée CP1 à CM2 et est strictement idempotente."""
    school = SchoolFactory()

    # Premier appel : crée 6 niveaux
    levels_1 = create_default_levels(school)
    assert len(levels_1) == 6
    names = [lvl.name for lvl in levels_1]
    orders = [lvl.order for lvl in levels_1]
    assert names == ["CP1", "CP2", "CE1", "CE2", "CM1", "CM2"]
    assert orders == [1, 2, 3, 4, 5, 6]
    assert Level.objects.filter(school=school).count() == 6

    # Deuxième appel : aucun doublon créé
    levels_2 = create_default_levels(school)
    assert len(levels_2) == 6
    assert Level.objects.filter(school=school).count() == 6
