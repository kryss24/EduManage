import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.models import User
from apps.grades.models import Grade
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    EnrollmentFactory,
    GradeFactory,
    SequenceFactory,
    StudentFactory,
    SubjectFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestGrade:
    def test_creation_is_valid(self):
        grade = GradeFactory(value=Decimal("15.50"))
        assert grade.value == Decimal("15.50")

    def test_decimal_value_is_stored_and_read_back_without_rounding_error(self):
        grade = GradeFactory(value=Decimal("12.25"))
        grade.refresh_from_db()
        assert grade.value == Decimal("12.25")

    def test_value_must_be_between_0_and_20(self):
        subject = SubjectFactory()
        year = subject.classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=2,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        student = StudentFactory(school=subject.school)
        EnrollmentFactory(student=student, classroom=subject.classroom, academic_year=year)
        teacher_user = UserFactory(role=User.Role.TEACHER, school=subject.school)
        with pytest.raises(IntegrityError):
            Grade.objects.bulk_create(
                [
                    Grade(
                        school=subject.school,
                        student=student,
                        subject=subject,
                        sequence=sequence,
                        value=Decimal("25.00"),
                        entered_by=teacher_user,
                    )
                ]
            )

    def test_unique_per_student_subject_sequence(self):
        grade = GradeFactory()
        with pytest.raises(IntegrityError):
            Grade.objects.bulk_create(
                [
                    Grade(
                        school=grade.school,
                        student=grade.student,
                        subject=grade.subject,
                        sequence=grade.sequence,
                        value=Decimal("10.00"),
                        entered_by=grade.entered_by,
                    )
                ]
            )

    def test_sequence_must_belong_to_subjects_academic_year(self):
        classroom = ClassroomFactory()
        school = classroom.school
        subject = SubjectFactory(classroom=classroom)
        other_year = AcademicYearFactory(school=school, label="Autre année")
        other_sequence = SequenceFactory(
            academic_year=other_year,
            number=1,
            start_date=other_year.start_date,
            end_date=other_year.start_date + datetime.timedelta(days=5),
        )
        student = StudentFactory(school=school)
        EnrollmentFactory(
            student=student, classroom=classroom, academic_year=classroom.academic_year
        )
        teacher_user = UserFactory(role=User.Role.TEACHER, school=school)
        grade = Grade(
            school=school,
            student=student,
            subject=subject,
            sequence=other_sequence,
            value=Decimal("12.00"),
            entered_by=teacher_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()

    def test_student_must_be_enrolled_in_subjects_classroom(self):
        subject = SubjectFactory()
        year = subject.classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=2,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        student = StudentFactory(school=subject.school)  # non inscrit dans la classe
        teacher_user = UserFactory(role=User.Role.TEACHER, school=subject.school)
        grade = Grade(
            school=subject.school,
            student=student,
            subject=subject,
            sequence=sequence,
            value=Decimal("12.00"),
            entered_by=teacher_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()

    def test_entered_by_from_another_school_is_rejected(self):
        subject = SubjectFactory()
        year = subject.classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=2,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        student = StudentFactory(school=subject.school)
        EnrollmentFactory(student=student, classroom=subject.classroom, academic_year=year)
        other_user = UserFactory(role=User.Role.TEACHER)
        grade = Grade(
            school=subject.school,
            student=student,
            subject=subject,
            sequence=sequence,
            value=Decimal("12.00"),
            entered_by=other_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()

    def test_entered_by_super_admin_from_any_school_is_allowed(self):
        subject = SubjectFactory()
        year = subject.classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=2,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        student = StudentFactory(school=subject.school)
        EnrollmentFactory(student=student, classroom=subject.classroom, academic_year=year)
        super_admin = UserFactory(role=User.Role.SUPER_ADMIN, school=None)
        grade = Grade(
            school=subject.school,
            student=student,
            subject=subject,
            sequence=sequence,
            value=Decimal("12.00"),
            entered_by=super_admin,
        )
        grade.full_clean()

    def test_grade_student_from_other_school_is_rejected(self):
        subject = SubjectFactory()
        year = subject.classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=2,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        other_student = StudentFactory()
        teacher_user = UserFactory(role=User.Role.TEACHER, school=subject.school)
        grade = Grade(
            school=subject.school,
            student=other_student,
            subject=subject,
            sequence=sequence,
            value=Decimal("12.00"),
            entered_by=teacher_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()

    def test_grade_subject_from_other_school_is_rejected(self):
        classroom = ClassroomFactory()
        school = classroom.school
        student = StudentFactory(school=school)
        year = classroom.academic_year
        sequence = SequenceFactory(
            academic_year=year,
            number=1,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        other_subject = SubjectFactory()  # appartient à une autre école
        teacher_user = UserFactory(role=User.Role.TEACHER, school=school)
        grade = Grade(
            school=school,
            student=student,
            subject=other_subject,
            sequence=sequence,
            value=Decimal("12.00"),
            entered_by=teacher_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()

    def test_grade_sequence_from_other_school_is_rejected(self):
        subject = SubjectFactory()
        student = StudentFactory(school=subject.school)
        other_sequence = SequenceFactory()
        teacher_user = UserFactory(role=User.Role.TEACHER, school=subject.school)
        grade = Grade(
            school=subject.school,
            student=student,
            subject=subject,
            sequence=other_sequence,
            value=Decimal("12.00"),
            entered_by=teacher_user,
        )
        with pytest.raises(ValidationError):
            grade.full_clean()
