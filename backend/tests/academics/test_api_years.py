"""Tests complets pour l'API des années scolaires et generate-sequences."""

import datetime
from concurrent.futures import ThreadPoolExecutor

import pytest

from apps.accounts.models import User
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    LevelFactory,
    SchoolFactory,
    SequenceFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_YEARS_create_success_and_validations(auth_client):
    """Création d'une année scolaire et validations élémentaires."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # Création valide
    res = client.post(
        "/api/academics/years/",
        {
            "label": "2025-2026",
            "start_date": "2025-09-01",
            "end_date": "2026-06-30",
        },
        format="json",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["label"] == "2025-2026"
    assert data["is_active"] is False
    assert data["is_archived"] is False

    # Dates inversées -> 400
    res_inv = client.post(
        "/api/academics/years/",
        {
            "label": "2027-2028",
            "start_date": "2028-06-30",
            "end_date": "2027-09-01",
        },
        format="json",
    )
    assert res_inv.status_code == 400
    assert "end_date" in res_inv.json()

    # Dates identiques -> 400
    res_eq = client.post(
        "/api/academics/years/",
        {
            "label": "2028-2029",
            "start_date": "2028-09-01",
            "end_date": "2028-09-01",
        },
        format="json",
    )
    assert res_eq.status_code == 400
    assert "end_date" in res_eq.json()

    # Libellé dupliqué (casse différente) -> 400
    res_dup = client.post(
        "/api/academics/years/",
        {
            "label": "2025-2026",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
        },
        format="json",
    )
    assert res_dup.status_code == 400
    assert "label" in res_dup.json()

    # Chevauchement de dates avec une autre année de l'école -> 400
    res_ovl = client.post(
        "/api/academics/years/",
        {
            "label": "2025-2026 Bis",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        format="json",
    )
    assert res_ovl.status_code == 400


def test_YEARS_activation_flow(auth_client):
    """Activation : bascule atomique, une seule active, refusée si archivée."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year1 = AcademicYearFactory(
        school=school,
        label="2024-2025",
        start_date=datetime.date(2024, 9, 1),
        end_date=datetime.date(2025, 6, 30),
        is_active=True,
    )
    year2 = AcademicYearFactory(
        school=school,
        label="2025-2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
        is_active=False,
    )

    # Activer year2 : désactive year1
    res = client.post(f"/api/academics/years/{year2.id}/activate/")
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    year1.refresh_from_db()
    year2.refresh_from_db()
    assert year1.is_active is False
    assert year2.is_active is True

    # Réactiver year2 : idempotent (200)
    res_idem = client.post(f"/api/academics/years/{year2.id}/activate/")
    assert res_idem.status_code == 200
    assert res_idem.json()["is_active"] is True

    # Activer une année archivée -> 409
    year_arch = AcademicYearFactory(
        school=school,
        label="2023-2024",
        start_date=datetime.date(2023, 9, 1),
        end_date=datetime.date(2024, 6, 30),
        is_active=False,
        is_archived=True,
    )
    res_arch = client.post(f"/api/academics/years/{year_arch.id}/activate/")
    assert res_arch.status_code == 409


def test_YEARS_archiving_flow(auth_client):
    """Archivage : refusé si active, idempotent si déjà archivée."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year_active = AcademicYearFactory(
        school=school,
        label="2025-2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
        is_active=True,
    )
    year_inactive = AcademicYearFactory(
        school=school,
        label="2024-2025",
        start_date=datetime.date(2024, 9, 1),
        end_date=datetime.date(2025, 6, 30),
        is_active=False,
    )

    # Tenter d'archiver l'année active -> 409
    res_act = client.post(f"/api/academics/years/{year_active.id}/archive/")
    assert res_act.status_code == 409
    assert "activer d'abord une autre année" in res_act.json()["detail"].lower()

    # Archiver l'année inactive -> 200
    res_inact = client.post(f"/api/academics/years/{year_inactive.id}/archive/")
    assert res_inact.status_code == 200
    assert res_inact.json()["is_archived"] is True

    year_inactive.refresh_from_db()
    assert year_inactive.is_archived is True

    # Idempotence : archiver à nouveau -> 200
    res_inact2 = client.post(f"/api/academics/years/{year_inactive.id}/archive/")
    assert res_inact2.status_code == 200
    assert res_inact2.json()["is_archived"] is True


def test_YEARS_archived_year_is_read_only(auth_client):
    """Une année archivée est en lecture seule (409, code year_archived)
    pour elle-même, ses séquences et classes.
    """
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    arch_year = AcademicYearFactory(
        school=school,
        label="2022-2023",
        start_date=datetime.date(2022, 9, 1),
        end_date=datetime.date(2023, 6, 30),
        is_archived=True,
    )
    seq = SequenceFactory(
        academic_year=arch_year,
        school=school,
        number=1,
        start_date=datetime.date(2022, 9, 1),
        end_date=datetime.date(2022, 10, 15),
    )
    lvl = LevelFactory(school=school)
    cls = ClassroomFactory(academic_year=arch_year, level=lvl, school=school, name="CM2 A")

    # 1. Modification année archivée -> 409 year_archived
    res_mod_y = client.patch(f"/api/academics/years/{arch_year.id}/", {"label": "2022-2023 Mod"})
    assert res_mod_y.status_code == 409
    assert res_mod_y.json().get("code") == "year_archived"

    # 2. Suppression année archivée -> 409 year_archived
    res_del_y = client.delete(f"/api/academics/years/{arch_year.id}/")
    assert res_del_y.status_code == 409
    assert res_del_y.json().get("code") == "year_archived"

    # 3. Création séquence sur année archivée -> 409 year_archived
    res_cre_s = client.post(
        "/api/academics/sequences/",
        {
            "academic_year": str(arch_year.id),
            "number": 2,
            "start_date": "2022-10-16",
            "end_date": "2022-11-30",
        },
        format="json",
    )
    assert res_cre_s.status_code == 409
    assert res_cre_s.json().get("code") == "year_archived"

    # 4. Modification séquence d'une année archivée -> 409 year_archived
    res_mod_s = client.patch(f"/api/academics/sequences/{seq.id}/", {"end_date": "2022-10-14"})
    assert res_mod_s.status_code == 409
    assert res_mod_s.json().get("code") == "year_archived"

    # 5. Suppression séquence d'une année archivée -> 409 year_archived
    res_del_s = client.delete(f"/api/academics/sequences/{seq.id}/")
    assert res_del_s.status_code == 409
    assert res_del_s.json().get("code") == "year_archived"

    # 6. Création classe sur année archivée -> 409 year_archived
    res_cre_c = client.post(
        "/api/academics/classrooms/",
        {"academic_year": str(arch_year.id), "level": str(lvl.id), "name": "CP1 B"},
        format="json",
    )
    assert res_cre_c.status_code == 409
    assert res_cre_c.json().get("code") == "year_archived"

    # 7. Modification classe d'une année archivée -> 409 year_archived
    res_mod_c = client.patch(f"/api/academics/classrooms/{cls.id}/", {"name": "CM2 A Bis"})
    assert res_mod_c.status_code == 409
    assert res_mod_c.json().get("code") == "year_archived"

    # 8. Suppression classe d'une année archivée -> 409 year_archived
    res_del_c = client.delete(f"/api/academics/classrooms/{cls.id}/")
    assert res_del_c.status_code == 409
    assert res_del_c.json().get("code") == "year_archived"


def test_YEARS_delete_protection(auth_client):
    """Suppression refusée (409) si des séquences ou des classes existent."""
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

    # A des séquences -> 409
    res = client.delete(f"/api/academics/years/{year.id}/")
    assert res.status_code == 409
    assert "séquences ou des classes" in res.json()["detail"]

    # Supprimer la séquence
    seq.delete()

    # Ajouter une classe -> 409
    lvl = LevelFactory(school=school)
    cls = ClassroomFactory(academic_year=year, level=lvl, school=school)
    res_cls = client.delete(f"/api/academics/years/{year.id}/")
    assert res_cls.status_code == 409

    # Supprimer la classe -> 204
    cls.delete()
    res_ok = client.delete(f"/api/academics/years/{year.id}/")
    assert res_ok.status_code == 204


def test_YEARS_generate_sequences_flow(auth_client):
    """Action generate-sequences : validation des 6 plages, atomicité, unicité."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(
        school=school,
        label="2030-2031",
        start_date=datetime.date(2030, 9, 1),
        end_date=datetime.date(2031, 6, 30),
    )

    valid_periods = [
        {"start_date": "2030-09-01", "end_date": "2030-10-15"},
        {"start_date": "2030-10-16", "end_date": "2030-11-30"},
        {"start_date": "2030-12-01", "end_date": "2031-01-31"},
        {"start_date": "2031-02-01", "end_date": "2031-03-15"},
        {"start_date": "2031-03-16", "end_date": "2031-04-30"},
        {"start_date": "2031-05-01", "end_date": "2031-06-30"},
    ]

    # Moins de 6 plages -> 400
    res_5 = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/", valid_periods[:5], format="json"
    )
    assert res_5.status_code == 400

    # Plus de 6 plages -> 400
    res_7 = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/",
        valid_periods + [{"start_date": "2031-07-01", "end_date": "2031-07-31"}],
        format="json",
    )
    assert res_7.status_code == 400

    # Plage hors de l'année (séquence 1 commence trop tôt) -> 400 indiquant la séquence 1
    bad_periods = [dict(p) for p in valid_periods]
    bad_periods[0] = {"start_date": "2030-08-15", "end_date": "2030-10-15"}
    res_bad1 = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/", bad_periods, format="json"
    )
    assert res_bad1.status_code == 400
    assert "1" in str(res_bad1.json())
    assert year.sequences.count() == 0  # Atomicité : rien n'a été créé

    # Ordre incorrect (séquence 4 avant la fin de la séquence 3) -> 400 indiquant la séquence 4
    bad_order_periods = [dict(p) for p in valid_periods]
    bad_order_periods[3] = {"start_date": "2031-01-15", "end_date": "2031-03-15"}
    res_bad4 = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/", bad_order_periods, format="json"
    )
    assert res_bad4.status_code == 400
    assert "4" in str(res_bad4.json())
    assert year.sequences.count() == 0  # Atomicité

    # Génération valide -> 201 avec 6 séquences
    res_ok = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/", valid_periods, format="json"
    )
    assert res_ok.status_code == 201
    created_seqs = res_ok.json()
    assert len(created_seqs) == 6
    assert [s["number"] for s in created_seqs] == [1, 2, 3, 4, 5, 6]
    assert [s["trimester"] for s in created_seqs] == [1, 1, 2, 2, 3, 3]

    # Re-générer alors que des séquences existent -> 409
    res_exist = client.post(
        f"/api/academics/years/{year.id}/generate-sequences/", valid_periods, format="json"
    )
    assert res_exist.status_code == 409


@pytest.mark.django_db(transaction=True)
def test_YEARS_activate_concurrency():
    """Test de concurrence sur activate_academic_year : une seule année active garantie."""
    from django.db import connection

    from apps.academics.api.services import activate_academic_year
    from apps.academics.models import AcademicYear

    school = SchoolFactory()
    year_a = AcademicYearFactory(
        school=school,
        label="2032-2033",
        start_date=datetime.date(2032, 9, 1),
        end_date=datetime.date(2033, 6, 30),
    )
    year_b = AcademicYearFactory(
        school=school,
        label="2033-2034",
        start_date=datetime.date(2033, 9, 1),
        end_date=datetime.date(2034, 6, 30),
    )

    def do_activate(year_id):
        try:
            y = AcademicYear.objects.get(id=year_id)
            activate_academic_year(y)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_activate, year_a.id)
        f2 = executor.submit(do_activate, year_b.id)
        f1.result()
        f2.result()

    active_count = AcademicYear.objects.filter(school=school, is_active=True).count()
    assert active_count == 1
