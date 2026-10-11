import pytest
from django.db.models import ProtectedError

from tests.factories import EnrollmentFactory


@pytest.mark.django_db
class TestProtectOnDelete:
    def test_cannot_delete_school_with_dependents(self):
        enrollment = EnrollmentFactory()
        with pytest.raises(ProtectedError):
            enrollment.school.delete()

    def test_cannot_delete_academic_year_with_dependents(self):
        enrollment = EnrollmentFactory()
        with pytest.raises(ProtectedError):
            enrollment.academic_year.delete()

    def test_cannot_delete_classroom_with_dependents(self):
        enrollment = EnrollmentFactory()
        with pytest.raises(ProtectedError):
            enrollment.classroom.delete()

    def test_cannot_delete_student_with_dependents(self):
        enrollment = EnrollmentFactory()
        with pytest.raises(ProtectedError):
            enrollment.student.delete()
