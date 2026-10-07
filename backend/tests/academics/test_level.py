import pytest
from django.db import IntegrityError

from apps.academics.models import Level
from tests.factories import LevelFactory, SchoolFactory


@pytest.mark.django_db
class TestLevel:
    def test_creation_is_valid(self):
        level = LevelFactory(name="CP1", order=1)
        assert str(level) == "CP1"

    def test_name_unique_per_school(self):
        school = SchoolFactory()
        LevelFactory(school=school, name="CP1", order=1)
        with pytest.raises(IntegrityError):
            Level.objects.bulk_create([Level(school=school, name="CP1", order=2)])

    def test_order_unique_per_school(self):
        school = SchoolFactory()
        LevelFactory(school=school, name="CP1", order=1)
        with pytest.raises(IntegrityError):
            Level.objects.bulk_create([Level(school=school, name="CP2", order=1)])

    def test_same_name_and_order_allowed_in_different_schools(self):
        LevelFactory(name="CP1", order=1)
        LevelFactory(name="CP1", order=1)
