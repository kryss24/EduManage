import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_is_postgresql():
    """Les contraintes d'exclusion utilisées (chevauchements de dates) exigent PostgreSQL."""
    assert connection.vendor == "postgresql"
