import pytest

from apps.academics.models import ClassroomTeacher, LanguageSection, Teacher
from apps.accounts.models import User
from apps.accounts.scoping import classrooms_visible_to, students_visible_to
from tests.factories import (
    ClassroomFactory,
    EnrollmentFactory,
    GuardianFactory,
    SchoolFactory,
    StudentFactory,
    StudentGuardianFactory,
    SuperAdminFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_classrooms_visible_to_school_admin_sees_all_school_classrooms():
    school = SchoolFactory()
    own = ClassroomFactory(academic_year__school=school)
    ClassroomFactory()  # autre école
    admin = UserFactory(school=school, role=User.Role.SCHOOL_ADMIN)

    result = classrooms_visible_to(admin)
    assert set(result) == {own}


def test_classrooms_visible_to_super_admin_requires_explicit_school():
    school = SchoolFactory()
    own = ClassroomFactory(academic_year__school=school)
    admin = SuperAdminFactory()

    result = classrooms_visible_to(admin, school=school)
    assert set(result) == {own}


def test_classrooms_visible_to_teacher_sees_only_own_classrooms():
    school = SchoolFactory()
    teacher_user = UserFactory(school=school, role=User.Role.TEACHER)
    teacher = Teacher.objects.create(
        school=school,
        user=teacher_user,
        last_name="Prof",
        first_name="Un",
        language_section=LanguageSection.FR,
    )
    own_classroom = ClassroomFactory(academic_year__school=school)
    ClassroomTeacher.objects.create(
        school=school, classroom=own_classroom, teacher=teacher, section=LanguageSection.FR
    )
    other_classroom = ClassroomFactory(academic_year__school=school)  # pas affecté

    result = classrooms_visible_to(teacher_user)
    assert set(result) == {own_classroom}
    assert other_classroom not in result


def test_classrooms_visible_to_parent_and_cashier_are_empty():
    school = SchoolFactory()
    ClassroomFactory(academic_year__school=school)
    parent = UserFactory(school=school, role=User.Role.PARENT)
    cashier = UserFactory(school=school, role=User.Role.CASHIER)

    assert classrooms_visible_to(parent).count() == 0
    assert classrooms_visible_to(cashier).count() == 0


def test_students_visible_to_school_admin_and_cashier_see_all_school_students():
    school = SchoolFactory()
    own_student = StudentFactory(school=school)
    StudentFactory()  # autre école
    admin = UserFactory(school=school, role=User.Role.SCHOOL_ADMIN)
    cashier = UserFactory(school=school, role=User.Role.CASHIER)

    assert set(students_visible_to(admin)) == {own_student}
    assert set(students_visible_to(cashier)) == {own_student}


def test_students_visible_to_parent_sees_only_own_children():
    school = SchoolFactory()
    parent_user = UserFactory(school=school, role=User.Role.PARENT)
    guardian = GuardianFactory(school=school, user=parent_user)
    own_child = StudentFactory(school=school)
    StudentGuardianFactory(school=school, student=own_child, guardian=guardian)

    other_parent_user = UserFactory(school=school, role=User.Role.PARENT)
    other_guardian = GuardianFactory(school=school, user=other_parent_user)
    other_child = StudentFactory(school=school)
    StudentGuardianFactory(school=school, student=other_child, guardian=other_guardian)

    result = students_visible_to(parent_user)
    assert set(result) == {own_child}
    assert other_child not in result


def test_students_visible_to_parent_never_sees_children_from_another_school():
    school = SchoolFactory()
    other_school = SchoolFactory()
    parent_user = UserFactory(school=school, role=User.Role.PARENT)
    guardian = GuardianFactory(school=school, user=parent_user)
    own_child = StudentFactory(school=school)
    StudentGuardianFactory(school=school, student=own_child, guardian=guardian)

    foreign_student = StudentFactory(school=other_school)

    result = students_visible_to(parent_user)
    assert foreign_student not in result


def test_students_visible_to_teacher_sees_only_students_of_own_classrooms():
    school = SchoolFactory()
    teacher_user = UserFactory(school=school, role=User.Role.TEACHER)
    teacher = Teacher.objects.create(
        school=school,
        user=teacher_user,
        last_name="Prof",
        first_name="Deux",
        language_section=LanguageSection.FR,
    )
    own_classroom = ClassroomFactory(academic_year__school=school)
    ClassroomTeacher.objects.create(
        school=school, classroom=own_classroom, teacher=teacher, section=LanguageSection.FR
    )
    enrolled_student = EnrollmentFactory(classroom=own_classroom).student

    other_classroom = ClassroomFactory(academic_year=own_classroom.academic_year)
    other_student = EnrollmentFactory(classroom=other_classroom).student

    result = students_visible_to(teacher_user)
    assert enrolled_student in result
    assert other_student not in result
