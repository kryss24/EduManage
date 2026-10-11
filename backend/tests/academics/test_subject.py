import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.academics.models import LanguageSection, Subject
from tests.factories import (
    ClassroomFactory,
    ClassroomTeacherFactory,
    SubjectFactory,
    TeacherFactory,
)


@pytest.mark.django_db
class TestSubject:
    def test_creation_is_valid(self):
        subject = SubjectFactory(name="Mathématiques", coefficient=4)
        assert "Mathématiques" in str(subject)

    def test_name_unique_per_classroom(self):
        classroom = ClassroomFactory()
        teacher = ClassroomTeacherFactory(classroom=classroom, section=LanguageSection.FR).teacher
        SubjectFactory(classroom=classroom, teacher=teacher, name="Français")
        with pytest.raises(IntegrityError):
            Subject.objects.bulk_create(
                [
                    Subject(
                        school=classroom.school,
                        classroom=classroom,
                        teacher=teacher,
                        name="Français",
                        coefficient=2,
                    )
                ]
            )

    def test_coefficient_must_be_at_least_1(self):
        classroom = ClassroomFactory()
        teacher = ClassroomTeacherFactory(classroom=classroom, section=LanguageSection.FR).teacher
        with pytest.raises(IntegrityError):
            Subject.objects.bulk_create(
                [
                    Subject(
                        school=classroom.school,
                        classroom=classroom,
                        teacher=teacher,
                        name="Français",
                        coefficient=0,
                    )
                ]
            )

    def test_teacher_must_be_assigned_to_the_classroom(self):
        classroom = ClassroomFactory()
        unrelated_teacher = TeacherFactory(school=classroom.school)
        subject = Subject(
            school=classroom.school,
            classroom=classroom,
            teacher=unrelated_teacher,
            name="Français",
            coefficient=2,
        )
        with pytest.raises(ValidationError):
            subject.full_clean()
