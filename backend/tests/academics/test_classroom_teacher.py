import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.academics.models import ClassroomTeacher, LanguageSection
from tests.factories import ClassroomFactory, ClassroomTeacherFactory, TeacherFactory


@pytest.mark.django_db
class TestClassroomTeacher:
    def test_creation_is_valid(self):
        ct = ClassroomTeacherFactory(section=LanguageSection.FR)
        assert ct.pk

    def test_one_teacher_per_section_per_classroom(self):
        classroom = ClassroomFactory()
        ClassroomTeacherFactory(classroom=classroom, section=LanguageSection.FR)
        other_teacher = TeacherFactory(school=classroom.school, language_section=LanguageSection.FR)
        with pytest.raises(IntegrityError):
            ClassroomTeacher.objects.bulk_create(
                [
                    ClassroomTeacher(
                        school=classroom.school,
                        classroom=classroom,
                        teacher=other_teacher,
                        section=LanguageSection.FR,
                    )
                ]
            )

    def test_a_teacher_cannot_be_assigned_twice_to_the_same_classroom(self):
        classroom = ClassroomFactory()
        teacher = TeacherFactory(school=classroom.school, language_section=LanguageSection.FR)
        ClassroomTeacherFactory(classroom=classroom, teacher=teacher, section=LanguageSection.FR)
        with pytest.raises(IntegrityError):
            ClassroomTeacher.objects.bulk_create(
                [
                    ClassroomTeacher(
                        school=classroom.school,
                        classroom=classroom,
                        teacher=teacher,
                        section=LanguageSection.EN,
                    )
                ]
            )

    def test_section_must_match_teacher_language_section(self):
        classroom = ClassroomFactory()
        teacher = TeacherFactory(school=classroom.school, language_section=LanguageSection.EN)
        ct = ClassroomTeacher(
            school=classroom.school,
            classroom=classroom,
            teacher=teacher,
            section=LanguageSection.FR,
        )
        with pytest.raises(ValidationError):
            ct.full_clean()
