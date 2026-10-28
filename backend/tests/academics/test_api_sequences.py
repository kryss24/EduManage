"""Tests complets pour l'API des séquences scolaires."""

import datetime

import pytest

from apps.accounts.models import User
from apps.grades.models import Grade
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    EnrollmentFactory,
    LevelFactory,
    SchoolFactory,
    SequenceFactory,
    StudentFactory,
    SubjectFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_SEQUENCES_crud_and_validations(auth_client):
    """CRUD des séquences et validations métier (numéro, ordre, bornes, trimestre)."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(
        school=school,
        label="2025-2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
    )

    # 1. Création séquence 1 valide
    res1 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 1,
            "start_date": "2025-09-01",
            "end_date": "2025-10-15",
        },
        format="json",
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["number"] == 1
    assert d1["trimester"] == 1  # (1+1)//2 = 1

    # 2. Création séquence 2 valide
    res2 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 2,
            "start_date": "2025-10-16",
            "end_date": "2025-11-30",
        },
        format="json",
    )
    assert res2.status_code == 201
    assert res2.json()["trimester"] == 1

    # 3. Création séquence 3 valide (trimestre 2)
    res3 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 3,
            "start_date": "2025-12-01",
            "end_date": "2026-01-31",
        },
        format="json",
    )
    assert res3.status_code == 201
    assert res3.json()["trimester"] == 2  # (3+1)//2 = 2

    # 4. Numéro dupliqué -> 400
    res_dup = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 1,
            "start_date": "2026-02-01",
            "end_date": "2026-03-15",
        },
        format="json",
    )
    assert res_dup.status_code == 400
    assert "number" in res_dup.json()

    # 5. Numéro hors bornes 1-6 -> 400
    res_0 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 0,
            "start_date": "2026-02-01",
            "end_date": "2026-03-15",
        },
        format="json",
    )
    assert res_0.status_code == 400

    res_7 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 7,
            "start_date": "2026-02-01",
            "end_date": "2026-03-15",
        },
        format="json",
    )
    assert res_7.status_code == 400

    # 6. Dates hors de l'année scolaire -> 400
    res_before = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 4,
            "start_date": "2025-08-15",
            "end_date": "2025-08-30",
        },
        format="json",
    )
    assert res_before.status_code == 400

    res_after = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 4,
            "start_date": "2026-07-01",
            "end_date": "2026-07-15",
        },
        format="json",
    )
    assert res_after.status_code == 400

    # 7. Ordre chronologique incohérent (sans chevauchement) :
    # On crée d'abord la séquence 5 (avril), puis on tente de créer la séquence 4
    # en mai (après séquence 5) -> 400 sur end_date
    res_s5 = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 5,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
        format="json",
    )
    assert res_s5.status_code == 201

    res_incoherent = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(year.id),
            "number": 4,
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
        },
        format="json",
    )
    assert res_incoherent.status_code == 400
    assert "end_date" in res_incoherent.json()


def test_SEQUENCES_immutable_academic_year(auth_client):
    """L'année scolaire d'une séquence est immuable après création."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year1 = AcademicYearFactory(
        school=school,
        label="2025-2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    year2 = AcademicYearFactory(
        school=school,
        label="2026-2027",
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2027, 6, 30),
    )

    seq = SequenceFactory(
        academic_year=year1,
        school=school,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 15),
    )

    res = client.patch(
        f"/api/academics/sequences/{seq.id}/",
        {"academic_year": str(year2.id)},
        format="json",
    )
    assert res.status_code == 400
    assert "academic_year" in res.json()


def test_SEQUENCES_delete_protection_with_grades(auth_client):
    """Suppression d'une séquence refusée (409) si des notes existent."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(
        school=school,
        label="2025-2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    seq = SequenceFactory(
        academic_year=year,
        school=school,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 15),
    )
    lvl = LevelFactory(school=school)
    cls = ClassroomFactory(academic_year=year, level=lvl, school=school)
    subj = SubjectFactory(classroom=cls, school=school)
    student = StudentFactory(school=school)
    EnrollmentFactory(student=student, classroom=cls, academic_year=year, school=school)

    # Créer une note attachée à cette séquence
    Grade.objects.create(
        school=school,
        student=student,
        subject=subj,
        sequence=seq,
        value=15.5,
        entered_by=admin,
    )

    # Tentative de suppression de la séquence -> 409
    res = client.delete(f"/api/academics/sequences/{seq.id}/")
    assert res.status_code == 409
    assert "notes y sont associées" in res.json()["detail"]

    # Suppression sans note -> 204
    seq2 = SequenceFactory(
        academic_year=year,
        school=school,
        number=2,
        start_date=datetime.date(2025, 10, 16),
        end_date=datetime.date(2025, 11, 30),
    )
    res2 = client.delete(f"/api/academics/sequences/{seq2.id}/")
    assert res2.status_code == 204
