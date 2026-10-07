import pytest
from django.db import IntegrityError

from apps.academics.models import StudentGuardian
from tests.factories import GuardianFactory, StudentFactory, StudentGuardianFactory


@pytest.mark.django_db
class TestStudentGuardian:
    def test_creation_is_valid(self):
        link = StudentGuardianFactory()
        assert link.pk

    def test_unique_per_student_and_guardian(self):
        student = StudentFactory()
        guardian = GuardianFactory(school=student.school)
        StudentGuardianFactory(student=student, guardian=guardian)
        with pytest.raises(IntegrityError):
            StudentGuardian.objects.bulk_create(
                [StudentGuardian(school=student.school, student=student, guardian=guardian)]
            )

    def test_one_guardian_can_be_linked_to_several_students(self):
        guardian = GuardianFactory()
        student1 = StudentFactory(school=guardian.school)
        student2 = StudentFactory(school=guardian.school)
        StudentGuardianFactory(student=student1, guardian=guardian)
        StudentGuardianFactory(student=student2, guardian=guardian)
