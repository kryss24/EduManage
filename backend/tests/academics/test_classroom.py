import pytest
from django.db import IntegrityError

from apps.academics.models import Classroom
from tests.factories import AcademicYearFactory, ClassroomFactory, LevelFactory


@pytest.mark.django_db
class TestClassroom:
    def test_creation_is_valid(self):
        classroom = ClassroomFactory(name="CM2")
        assert "CM2" in str(classroom)

    def test_name_unique_per_academic_year(self):
        year = AcademicYearFactory()
        level = LevelFactory(school=year.school)
        ClassroomFactory(academic_year=year, level=level, name="CM2")
        with pytest.raises(IntegrityError):
            Classroom.objects.bulk_create(
                [Classroom(school=year.school, academic_year=year, level=level, name="CM2")]
            )

    def test_same_name_allowed_in_different_academic_years(self):
        ClassroomFactory(name="CM2")
        ClassroomFactory(name="CM2")
