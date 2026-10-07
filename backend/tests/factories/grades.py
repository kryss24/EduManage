import datetime
from decimal import Decimal

import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.grades.models import Grade

from .academics import (
    ClassroomFactory,
    EnrollmentFactory,
    SequenceFactory,
    StudentFactory,
    SubjectFactory,
)
from .accounts import UserFactory


def _make_enrolled_student(classroom):
    student = StudentFactory(school=classroom.school)
    EnrollmentFactory(student=student, classroom=classroom, academic_year=classroom.academic_year)
    return student


class GradeFactory(factory.django.DjangoModelFactory):
    """Construit un graphe cohérent (classe/matière/séquence/inscription).

    Si plusieurs notes doivent partager la même classe, passez explicitement
    `classroom=`, `subject=` et/ou `sequence=` pour éviter de recréer une
    séquence numéro 1 en double sur la même année scolaire.
    """

    class Meta:
        model = Grade
        exclude = ("classroom",)

    classroom = factory.SubFactory(ClassroomFactory)
    school = factory.SelfAttribute("classroom.school")
    subject = factory.LazyAttribute(lambda o: SubjectFactory(classroom=o.classroom))
    sequence = factory.LazyAttribute(
        lambda o: SequenceFactory(
            academic_year=o.classroom.academic_year,
            number=1,
            start_date=o.classroom.academic_year.start_date,
            end_date=o.classroom.academic_year.start_date + datetime.timedelta(days=30),
        )
    )
    student = factory.LazyAttribute(lambda o: _make_enrolled_student(o.classroom))
    entered_by = factory.LazyAttribute(
        lambda o: UserFactory(role=User.Role.TEACHER, school=o.classroom.school)
    )
    value = Decimal("12.00")
    graded_on = factory.LazyFunction(timezone.localdate)
