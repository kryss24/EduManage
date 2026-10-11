"""Pour chaque relation entre modèles de tenant, deux objets d'écoles
différentes ne peuvent pas être reliés : TenantModel.clean() le refuse.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import (
    Classroom,
    ClassroomTeacher,
    Enrollment,
    LanguageSection,
    Sequence,
    StudentGuardian,
    Subject,
)
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    GuardianFactory,
    LevelFactory,
    SchoolFactory,
    StudentFactory,
    TeacherFactory,
)


@pytest.mark.django_db
class TestTenantIsolation:
    def test_sequence_academic_year_must_belong_to_same_school(self):
        other_school_year = AcademicYearFactory()
        school = SchoolFactory()
        seq = Sequence(
            school=school,
            academic_year=other_school_year,
            number=1,
            start_date=other_school_year.start_date,
            end_date=other_school_year.start_date,
        )
        with pytest.raises(ValidationError):
            seq.full_clean()

    def test_classroom_academic_year_must_belong_to_same_school(self):
        other_school_year = AcademicYearFactory()
        school = SchoolFactory()
        level = LevelFactory(school=school)
        classroom = Classroom(school=school, academic_year=other_school_year, level=level, name="X")
        with pytest.raises(ValidationError):
            classroom.full_clean()

    def test_classroom_level_must_belong_to_same_school(self):
        year = AcademicYearFactory()
        other_level = LevelFactory()
        classroom = Classroom(school=year.school, academic_year=year, level=other_level, name="X")
        with pytest.raises(ValidationError):
            classroom.full_clean()

    def test_classroom_teacher_teacher_from_other_school_is_rejected(self):
        classroom = ClassroomFactory()
        other_teacher = TeacherFactory(language_section=LanguageSection.FR)
        ct = ClassroomTeacher(
            school=classroom.school,
            classroom=classroom,
            teacher=other_teacher,
            section=LanguageSection.FR,
        )
        with pytest.raises(ValidationError):
            ct.full_clean()

    def test_subject_classroom_from_other_school_is_rejected(self):
        school = SchoolFactory()
        other_classroom = ClassroomFactory()
        teacher = TeacherFactory(school=school, language_section=LanguageSection.FR)
        subject = Subject(
            school=school,
            classroom=other_classroom,
            teacher=teacher,
            name="Français",
            coefficient=2,
        )
        with pytest.raises(ValidationError):
            subject.full_clean()

    def test_subject_teacher_from_other_school_is_rejected(self):
        classroom = ClassroomFactory()
        other_teacher = TeacherFactory(language_section=LanguageSection.FR)
        subject = Subject(
            school=classroom.school,
            classroom=classroom,
            teacher=other_teacher,
            name="Français",
            coefficient=2,
        )
        with pytest.raises(ValidationError):
            subject.full_clean()

    def test_enrollment_student_from_other_school_is_rejected(self):
        classroom = ClassroomFactory()
        other_student = StudentFactory()
        enrollment = Enrollment(
            school=classroom.school,
            student=other_student,
            classroom=classroom,
            academic_year=classroom.academic_year,
        )
        with pytest.raises(ValidationError):
            enrollment.full_clean()

    def test_enrollment_classroom_from_other_school_is_rejected(self):
        school = SchoolFactory()
        student = StudentFactory(school=school)
        other_classroom = ClassroomFactory()
        enrollment = Enrollment(
            school=school,
            student=student,
            classroom=other_classroom,
            academic_year=other_classroom.academic_year,
        )
        with pytest.raises(ValidationError):
            enrollment.full_clean()

    def test_student_guardian_guardian_from_other_school_is_rejected(self):
        student = StudentFactory()
        other_guardian = GuardianFactory()
        link = StudentGuardian(school=student.school, student=student, guardian=other_guardian)
        with pytest.raises(ValidationError):
            link.full_clean()

    def test_student_guardian_student_from_other_school_is_rejected(self):
        guardian = GuardianFactory()
        other_student = StudentFactory()
        link = StudentGuardian(school=guardian.school, student=other_student, guardian=guardian)
        with pytest.raises(ValidationError):
            link.full_clean()
