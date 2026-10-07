import pytest
from django.db import IntegrityError

from apps.academics.models import Student
from tests.factories import SchoolFactory, StudentFactory


@pytest.mark.django_db
class TestStudent:
    def test_creation_is_valid(self):
        student = StudentFactory(first_name="Jean", last_name="Mballa", matricule="MAT-1")
        assert "Jean Mballa" in str(student)

    def test_matricule_unique_per_school(self):
        school = SchoolFactory()
        StudentFactory(school=school, matricule="DEMO-0001")
        with pytest.raises(IntegrityError):
            Student.objects.bulk_create(
                [
                    Student(
                        school=school,
                        matricule="DEMO-0001",
                        first_name="X",
                        last_name="Y",
                        birth_date="2015-01-01",
                        gender="M",
                    )
                ]
            )

    def test_same_matricule_allowed_in_different_schools(self):
        StudentFactory(matricule="DEMO-0001")
        StudentFactory(matricule="DEMO-0001")
