import pytest
from django.db import IntegrityError

from apps.academics.models import Enrollment
from tests.factories import ClassroomFactory, EnrollmentFactory, StudentFactory


@pytest.mark.django_db
class TestEnrollment:
    def test_creation_is_valid(self):
        enrollment = EnrollmentFactory()
        assert enrollment.pk

    def test_save_forces_academic_year_from_classroom(self):
        classroom = ClassroomFactory()
        student = StudentFactory(school=classroom.school)
        enrollment = Enrollment(
            school=classroom.school, student=student, classroom=classroom, academic_year=None
        )
        enrollment.save()
        assert enrollment.academic_year_id == classroom.academic_year_id

    def test_a_student_can_only_be_enrolled_once_per_academic_year(self):
        classroom = ClassroomFactory()
        student = StudentFactory(school=classroom.school)
        EnrollmentFactory(
            student=student, classroom=classroom, academic_year=classroom.academic_year
        )
        other_classroom = ClassroomFactory(
            academic_year=classroom.academic_year, level=classroom.level
        )
        with pytest.raises(IntegrityError):
            Enrollment.objects.bulk_create(
                [
                    Enrollment(
                        school=classroom.school,
                        student=student,
                        classroom=other_classroom,
                        academic_year=classroom.academic_year,
                    )
                ]
            )
