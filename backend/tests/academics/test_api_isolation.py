"""Tests d'isolation multi-tenant et de visibilité enseignant pour /api/academics/."""

import datetime
import uuid

import pytest

from apps.accounts.models import User
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    ClassroomTeacherFactory,
    LevelFactory,
    SchoolFactory,
    SequenceFactory,
    SuperAdminFactory,
    TeacherFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_SEC_01_other_school_objects_return_404_on_all_methods(auth_client):
    """Un objet d'une autre école renvoie systématiquement 404."""
    school_a = SchoolFactory()
    school_b = SchoolFactory()

    admin_a = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school_a)
    client_a = auth_client(admin_a)

    year_b = AcademicYearFactory(
        school=school_b, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    seq_b = SequenceFactory(
        academic_year=year_b,
        school=school_b,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 15),
    )
    lvl_b = LevelFactory(school=school_b)
    cls_b = ClassroomFactory(academic_year=year_b, level=lvl_b, school=school_b)

    # Lecture (GET detail) -> 404
    assert client_a.get(f"/api/academics/years/{year_b.id}/").status_code == 404
    assert client_a.get(f"/api/academics/sequences/{seq_b.id}/").status_code == 404
    assert client_a.get(f"/api/academics/levels/{lvl_b.id}/").status_code == 404
    assert client_a.get(f"/api/academics/classrooms/{cls_b.id}/").status_code == 404

    # Modification (PATCH) -> 404
    assert (
        client_a.patch(f"/api/academics/years/{year_b.id}/", {"label": "Hack"}).status_code == 404
    )
    assert (
        client_a.patch(
            f"/api/academics/sequences/{seq_b.id}/", {"end_date": "2025-10-10"}
        ).status_code
        == 404
    )
    assert client_a.patch(f"/api/academics/levels/{lvl_b.id}/", {"name": "Hack"}).status_code == 404
    assert (
        client_a.patch(f"/api/academics/classrooms/{cls_b.id}/", {"name": "Hack"}).status_code
        == 404
    )

    # Suppression (DELETE) -> 404
    assert client_a.delete(f"/api/academics/years/{year_b.id}/").status_code == 404
    assert client_a.delete(f"/api/academics/sequences/{seq_b.id}/").status_code == 404
    assert client_a.delete(f"/api/academics/levels/{lvl_b.id}/").status_code == 404
    assert client_a.delete(f"/api/academics/classrooms/{cls_b.id}/").status_code == 404

    # Actions spécifiques sur l'année de l'autre école -> 404
    assert client_a.post(f"/api/academics/years/{year_b.id}/activate/").status_code == 404
    assert client_a.post(f"/api/academics/years/{year_b.id}/archive/").status_code == 404
    assert (
        client_a.post(
            f"/api/academics/years/{year_b.id}/generate-sequences/", [], format="json"
        ).status_code
        == 404
    )


def test_SEC_01_referencing_other_school_foreign_keys_returns_400(auth_client):
    """Référencer une année ou un niveau d'une autre école renvoie 400 générique."""
    school_a = SchoolFactory()
    school_b = SchoolFactory()

    admin_a = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school_a)
    client_a = auth_client(admin_a)

    year_a = AcademicYearFactory(
        school=school_a, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    lvl_a = LevelFactory(school=school_a)

    year_b = AcademicYearFactory(
        school=school_b, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    lvl_b = LevelFactory(school=school_b)

    # Création séquence pour année de l'école B -> 400
    res_seq = client_a.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year_b.id),
            "number": 1,
            "start_date": "2025-09-01",
            "end_date": "2025-10-15",
        },
        format="json",
    )
    assert res_seq.status_code == 400
    assert "academic_year" in res_seq.json()

    # Création classe avec année de l'école B -> 400
    res_cls_year = client_a.post(
        "/api/academics/classrooms/",
        {"academic_year": str(year_b.id), "level": str(lvl_a.id), "name": "CP1 A"},
        format="json",
    )
    assert res_cls_year.status_code == 400
    assert "academic_year" in res_cls_year.json()

    # Création classe avec niveau de l'école B -> 400
    res_cls_lvl = client_a.post(
        "/api/academics/classrooms/",
        {"academic_year": str(year_a.id), "level": str(lvl_b.id), "name": "CP1 A"},
        format="json",
    )
    assert res_cls_lvl.status_code == 400
    assert "level" in res_cls_lvl.json()


def test_SEC_01_school_field_in_request_body_is_ignored(auth_client):
    """Le champ 'school' dans le corps est ignoré au profit de l'école de la session."""
    school_a = SchoolFactory()
    school_b = SchoolFactory()

    admin_a = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school_a)
    client_a = auth_client(admin_a)

    res = client_a.post(
        "/api/academics/years/",
        {
            "label": "2028-2029",
            "start_date": "2028-09-01",
            "end_date": "2029-06-30",
            "school": str(school_b.id),
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["school"] == str(school_a.id)


def test_SEC_01_superadmin_scoping(auth_client):
    """SUPER_ADMIN sans X-School-Id -> 400 ; avec en-tête valide -> accès à l'école cible."""
    school = SchoolFactory()
    year = AcademicYearFactory(
        school=school,
        label="2027-2028",
        start_date=datetime.date(2027, 9, 1),
        end_date=datetime.date(2028, 6, 30),
    )

    superadmin = SuperAdminFactory()
    client = auth_client(superadmin)

    # Sans en-tête -> 400
    res_no_header = client.get("/api/academics/years/")
    assert res_no_header.status_code == 400

    # Avec en-tête invalide -> 400
    res_bad_header = client.get("/api/academics/years/", headers={"X-School-Id": str(uuid.uuid4())})
    assert res_bad_header.status_code == 400

    # Avec en-tête valide -> 200 et voit l'année de l'école
    res_valid = client.get("/api/academics/years/", headers={"X-School-Id": str(school.id)})
    assert res_valid.status_code == 200
    assert len(res_valid.json()["results"]) == 1
    assert res_valid.json()["results"][0]["id"] == str(year.id)


def test_AUTH_02_teacher_sees_all_years_sequences_levels_of_school(auth_client):
    """L'enseignant voit toutes les années, séquences et niveaux de son école."""
    school = SchoolFactory()
    teacher_user = UserFactory(role=User.Role.TEACHER, school=school)
    client = auth_client(teacher_user)

    year = AcademicYearFactory(
        school=school, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    seq = SequenceFactory(
        academic_year=year,
        school=school,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 15),
    )
    lvl = LevelFactory(school=school)

    # Lister
    res_y = client.get("/api/academics/years/")
    assert res_y.status_code == 200
    assert any(item["id"] == str(year.id) for item in res_y.json()["results"])

    res_s = client.get("/api/academics/sequences/")
    assert res_s.status_code == 200
    assert any(item["id"] == str(seq.id) for item in res_s.json()["results"])

    res_l = client.get("/api/academics/levels/")
    assert res_l.status_code == 200
    assert any(item["id"] == str(lvl.id) for item in res_l.json()["results"])


def test_AUTH_02_teacher_sees_only_own_assigned_classrooms(auth_client):
    """L'enseignant ne voit que les classes auxquelles il est affecté
    (liste et détail, 404 sinon).
    """
    school = SchoolFactory()
    teacher_user = UserFactory(role=User.Role.TEACHER, school=school)
    teacher_profile = TeacherFactory(user=teacher_user, school=school)

    other_teacher = TeacherFactory(school=school)

    year = AcademicYearFactory(
        school=school, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    lvl = LevelFactory(school=school)

    # Classe 1 : affectée à teacher_user
    cls_own = ClassroomFactory(academic_year=year, level=lvl, school=school, name="CM1 A")
    ClassroomTeacherFactory(classroom=cls_own, teacher=teacher_profile)

    # Classe 2 : affectée à other_teacher
    cls_other = ClassroomFactory(academic_year=year, level=lvl, school=school, name="CM2 B")
    ClassroomTeacherFactory(classroom=cls_other, teacher=other_teacher)

    client = auth_client(teacher_user)

    # Liste des classes
    res_list = client.get("/api/academics/classrooms/")
    assert res_list.status_code == 200
    classroom_ids = [item["id"] for item in res_list.json()["results"]]
    assert str(cls_own.id) in classroom_ids
    assert str(cls_other.id) not in classroom_ids

    # Détail de sa classe -> 200
    res_own = client.get(f"/api/academics/classrooms/{cls_own.id}/")
    assert res_own.status_code == 200
    assert res_own.json()["name"] == "CM1 A"

    # Détail de l'autre classe -> 404
    res_other = client.get(f"/api/academics/classrooms/{cls_other.id}/")
    assert res_other.status_code == 404
