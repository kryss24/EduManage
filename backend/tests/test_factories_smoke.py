import pytest

from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    ClassroomTeacherFactory,
    EnrollmentFactory,
    GradeFactory,
    GuardianFactory,
    LevelFactory,
    SchoolFactory,
    SequenceFactory,
    StudentFactory,
    StudentGuardianFactory,
    SubjectFactory,
    TeacherFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_every_factory_builds_a_valid_instance():
    assert SchoolFactory().pk
    assert UserFactory().pk
    assert AcademicYearFactory().pk
    assert SequenceFactory().pk
    assert LevelFactory().pk
    assert ClassroomFactory().pk
    assert TeacherFactory().pk
    assert ClassroomTeacherFactory().pk
    assert SubjectFactory().pk
    assert StudentFactory().pk
    assert EnrollmentFactory().pk
    assert GuardianFactory().pk
    assert StudentGuardianFactory().pk
    assert GradeFactory().pk
