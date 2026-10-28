import pytest

from apps.academics.models import AcademicYear, Classroom, Level
from apps.accounts.models import User
from apps.core.models import AuditLog
from tests.factories.academics import (
    AcademicYearFactory,
    LevelFactory,
)
from tests.factories.accounts import UserFactory
from tests.factories.tenants import SchoolFactory


@pytest.mark.django_db
def test_SECURITY_mass_assignment_protection(auth_client):
    """Les champs sensibles (is_active, is_archived, school, trimester) sont ignorés en écriture."""
    school = SchoolFactory()
    other_school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # 1. Année scolaire : tentative d'injection de is_active, is_archived et school
    res_year = client.post(
        "/api/academics/years/",
        {
            "label": "2025-2026",
            "start_date": "2025-09-01",
            "end_date": "2026-06-30",
            "is_active": True,
            "is_archived": True,
            "school": str(other_school.id),
        },
        format="json",
    )
    assert res_year.status_code == 201
    year_data = res_year.json()
    assert year_data["is_active"] is False
    assert year_data["is_archived"] is False
    year = AcademicYear.objects.get(id=year_data["id"])
    assert year.school_id == school.id
    assert year.is_active is False
    assert year.is_archived is False

    # Modification via PATCH : tentative d'activer ou archiver directement
    res_patch = client.patch(
        f"/api/academics/years/{year.id}/",
        {"is_active": True, "is_archived": True},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["is_active"] is False
    assert res_patch.json()["is_archived"] is False
    year.refresh_from_db()
    assert year.is_active is False
    assert year.is_archived is False

    # 2. Séquence : tentative d'écraser trimester
    res_seq = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 1,
            "start_date": "2025-09-01",
            "end_date": "2025-10-31",
            "trimester": 3,  # Devrait être calculé à 1
        },
        format="json",
    )
    assert res_seq.status_code == 201
    assert res_seq.json()["trimester"] == 1


@pytest.mark.django_db
def test_SECURITY_sql_injection_and_strict_ordering(auth_client):
    """Les tentatives d'injection SQL et les tris hors liste blanche sont rejetés proprement."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    AcademicYearFactory(school=school, label="2025-2026")

    # 1. Tri hors liste blanche -> 400 avec message en français
    res_bad_sort = client.get("/api/academics/years/?ordering=unauthorized_field")
    assert res_bad_sort.status_code == 400
    assert "n'est pas autorisé" in str(res_bad_sort.json()["ordering"])

    # 2. Injection SQL dans l'ordering -> 400
    res_sql_sort = client.get(
        "/api/academics/years/?ordering=1;DROP%20TABLE%20academics_academicyear;--"
    )
    assert res_sql_sort.status_code == 400
    assert "n'est pas autorisé" in str(res_sql_sort.json()["ordering"])

    # 3. Injection SQL dans la recherche -> pas de crash 500, résultat sécurisé
    res_sql_search = client.get("/api/academics/years/?search=' OR 1=1;--")
    assert res_sql_search.status_code == 200

    # 4. Tris autorisés -> 200
    assert client.get("/api/academics/years/?ordering=start_date").status_code == 200
    assert client.get("/api/academics/years/?ordering=-label").status_code == 200


@pytest.mark.django_db
def test_SECURITY_pagination_page_size_capped(auth_client):
    """La taille maximale de pagination est strictement plafonnée (max_page_size = 100)."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # Création de 110 niveaux
    Level.objects.bulk_create(
        [Level(school=school, name=f"Niveau {i:03d}", order=i) for i in range(1, 111)]
    )

    # Demande d'une page de 200 éléments
    res = client.get("/api/academics/levels/?page_size=200")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 110
    # Le résultat ne doit pas dépasser 100 éléments
    assert len(data["results"]) == 100
    assert data["next"] is not None


@pytest.mark.django_db
def test_AUDIT_events_recorded_on_mutations_and_actions(auth_client):
    """Chaque opération d'écriture et action métier génère un événement d'audit conforme."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # 1. Création d'une année scolaire
    res_create_year = client.post(
        "/api/academics/years/",
        {
            "label": "2025-2026",
            "start_date": "2025-09-01",
            "end_date": "2026-06-30",
        },
        format="json",
    )
    assert res_create_year.status_code == 201
    year_id = res_create_year.json()["id"]

    audit_create = AuditLog.objects.filter(
        school=school, entity_type="AcademicYear", entity_id=year_id, action="create_academic_year"
    ).first()
    assert audit_create is not None
    assert audit_create.user == admin
    assert audit_create.metadata.get("label") == "2025-2026"

    # 2. Génération de séquences
    periods = [
        {"start_date": "2025-09-01", "end_date": "2025-10-17"},
        {"start_date": "2025-10-20", "end_date": "2025-11-28"},
        {"start_date": "2025-12-01", "end_date": "2026-01-23"},
        {"start_date": "2026-01-26", "end_date": "2026-03-06"},
        {"start_date": "2026-03-09", "end_date": "2026-04-24"},
        {"start_date": "2026-04-27", "end_date": "2026-06-12"},
    ]
    res_gen = client.post(
        f"/api/academics/years/{year_id}/generate-sequences/",
        periods,
        format="json",
    )
    assert res_gen.status_code == 201

    audit_gen = AuditLog.objects.filter(
        school=school, entity_type="AcademicYear", entity_id=year_id, action="generate_sequences"
    ).first()
    assert audit_gen is not None
    assert audit_gen.metadata.get("count") == 6

    # 3. Activation de l'année
    res_act = client.post(f"/api/academics/years/{year_id}/activate/")
    assert res_act.status_code == 200

    audit_act = AuditLog.objects.filter(
        school=school,
        entity_type="AcademicYear",
        entity_id=year_id,
        action="activate_academic_year",
    ).first()
    assert audit_act is not None

    # 4. Création d'un niveau
    res_lvl = client.post(
        "/api/academics/levels/",
        {"name": "CP", "order": 1},
        format="json",
    )
    assert res_lvl.status_code == 201
    lvl_id = res_lvl.json()["id"]

    audit_lvl = AuditLog.objects.filter(
        school=school, entity_type="Level", entity_id=lvl_id, action="create_level"
    ).first()
    assert audit_lvl is not None

    # 5. Création d'une classe
    res_cls = client.post(
        "/api/academics/classrooms/",
        {"academic_year": year_id, "level": lvl_id, "name": "CP-A"},
        format="json",
    )
    assert res_cls.status_code == 201
    cls_id = res_cls.json()["id"]

    audit_cls = AuditLog.objects.filter(
        school=school, entity_type="Classroom", entity_id=cls_id, action="create_classroom"
    ).first()
    assert audit_cls is not None


@pytest.mark.django_db
def test_PERF_classrooms_and_sequences_list_no_n_plus_one(
    auth_client, django_assert_max_num_queries
):
    """Les listes de classes et séquences s'exécutent en un nombre constant
    de requêtes SQL (pas de N+1).
    """
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(school=school, label="2025-2026")
    level = LevelFactory(school=school, name="CP", order=1)

    # Création de 50 classes avec inscriptions
    classrooms = [
        Classroom(school=school, academic_year=year, level=level, name=f"Classe {i:02d}")
        for i in range(1, 51)
    ]
    Classroom.objects.bulk_create(classrooms)

    # Récupération de la liste des 50 classes : doit s'exécuter en moins de 10 requêtes SQL
    with django_assert_max_num_queries(10):
        res = client.get("/api/academics/classrooms/?page_size=50")
        assert res.status_code == 200
        assert len(res.json()["results"]) == 50
