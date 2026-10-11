import pytest

from apps.tenants.models import School
from tests.factories import SchoolFactory


@pytest.mark.django_db
class TestSchool:
    def test_creation_is_valid(self):
        school = SchoolFactory(name="École A", city="Douala")
        assert school.pk
        assert str(school) == "École A"
        assert school.plan == School.Plan.STARTER
        assert school.currency == "XAF"
        assert school.is_active is True
