import datetime

import pytest
import time_machine

from apps.accounts.models import User
from tests.factories.academics import (
    AcademicYearFactory,
    LevelFactory,
    SequenceFactory,
)
from tests.factories.accounts import UserFactory
from tests.factories.tenants import SchoolFactory


@pytest.mark.django_db
def test_CONTEXT_no_active_year(auth_client):
    """Quand aucune année n'est active, active_year et current_sequence
    valent null, sequences est vide.
    """
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    # Création d'une année inactive et d'un niveau
    AcademicYearFactory(school=school, is_active=False)
    LevelFactory(school=school, name="CP", order=1)

    res = client.get("/api/academics/context/")
    assert res.status_code == 200
    data = res.json()
    assert data["active_year"] is None
    assert data["sequences"] == []
    assert data["current_sequence"] is None
    assert len(data["levels"]) == 1
    assert data["levels"][0]["name"] == "CP"


@pytest.mark.django_db
def test_CONTEXT_active_year_and_current_sequence_with_timezone(auth_client):
    """L'année active, les séquences et la séquence courante sont
    retournées selon la date et le fuseau de l'école.
    """
    # Fuseau horaire Africa/Douala (UTC+1 toute l'année, pas de DST)
    school = SchoolFactory(timezone="Africa/Douala")
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(
        school=school,
        label="2025-2026",
        is_active=True,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    s1 = SequenceFactory(
        academic_year=year,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 31),
    )
    s2 = SequenceFactory(
        academic_year=year,
        number=2,
        start_date=datetime.date(2025, 11, 1),
        end_date=datetime.date(2025, 12, 15),
    )
    LevelFactory(school=school, name="CP", order=1)
    LevelFactory(school=school, name="CE1", order=2)

    # Cas 1 : À 22:30:00 UTC le 31 octobre 2025
    # À Douala (UTC+1), il est 23:30:00 le 31 octobre 2025 -> Séquence 1 en cours
    with time_machine.travel(datetime.datetime(2025, 10, 31, 22, 30, 0, tzinfo=datetime.UTC)):
        client = auth_client(admin)
        res1 = client.get("/api/academics/context/")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["active_year"]["id"] == str(year.id)
        assert len(data1["sequences"]) == 2
        assert data1["current_sequence"] is not None
        assert data1["current_sequence"]["number"] == 1
        assert data1["current_sequence"]["id"] == str(s1.id)

    # Cas 2 (cas limite minuit) : À 23:30:00 UTC le 31 octobre 2025
    # En UTC, la date est toujours le 31 octobre.
    # Mais à Douala (UTC+1), il est 00:30:00 le 1er novembre 2025 -> Séquence 2 en cours !
    with time_machine.travel(datetime.datetime(2025, 10, 31, 23, 30, 0, tzinfo=datetime.UTC)):
        client = auth_client(admin)
        res2 = client.get("/api/academics/context/")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["current_sequence"] is not None
        assert data2["current_sequence"]["number"] == 2
        assert data2["current_sequence"]["id"] == str(s2.id)

    # Cas 3 : En vacances (hors séquence) -> current_sequence est null
    with time_machine.travel(datetime.datetime(2025, 12, 25, 12, 0, 0, tzinfo=datetime.UTC)):
        client = auth_client(admin)
        res3 = client.get("/api/academics/context/")
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["current_sequence"] is None
        assert data3["active_year"] is not None
