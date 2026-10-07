import datetime

import factory

from apps.academics.models import (
    AcademicYear,
    Classroom,
    ClassroomTeacher,
    Enrollment,
    Gender,
    Guardian,
    LanguageSection,
    Level,
    Relationship,
    Sequence,
    Student,
    StudentGuardian,
    Subject,
    Teacher,
)

from .tenants import SchoolFactory


class AcademicYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcademicYear
        exclude = ("n",)

    n = factory.Sequence(lambda n: n)
    school = factory.SubFactory(SchoolFactory)
    label = factory.LazyAttribute(lambda o: f"{2020 + o.n}-{2021 + o.n}")
    start_date = factory.LazyAttribute(lambda o: datetime.date(2020 + o.n, 9, 1))
    end_date = factory.LazyAttribute(lambda o: datetime.date(2021 + o.n, 6, 30))
    is_active = False
    is_archived = False


class SequenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sequence

    school = factory.SelfAttribute("academic_year.school")
    academic_year = factory.SubFactory(AcademicYearFactory)
    number = 1
    start_date = factory.LazyAttribute(lambda o: o.academic_year.start_date)
    end_date = factory.LazyAttribute(
        lambda o: o.academic_year.start_date + datetime.timedelta(days=30)
    )


class LevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Level

    school = factory.SubFactory(SchoolFactory)
    name = factory.Sequence(lambda n: f"Niveau {n}")
    order = factory.Sequence(lambda n: n + 1)


class ClassroomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Classroom

    school = factory.SelfAttribute("academic_year.school")
    academic_year = factory.SubFactory(AcademicYearFactory)
    level = factory.SubFactory(LevelFactory, school=factory.SelfAttribute("..academic_year.school"))
    name = factory.Sequence(lambda n: f"Classe {n}")


class TeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Teacher

    school = factory.SubFactory(SchoolFactory)
    user = None
    last_name = factory.Sequence(lambda n: f"Enseignant {n}")
    first_name = "Prénom"
    phone = ""
    language_section = LanguageSection.FR
    monthly_salary = None
    is_active = True


class ClassroomTeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClassroomTeacher

    school = factory.SelfAttribute("classroom.school")
    classroom = factory.SubFactory(ClassroomFactory)
    section = LanguageSection.FR
    teacher = factory.SubFactory(
        TeacherFactory,
        school=factory.SelfAttribute("..classroom.school"),
        language_section=factory.SelfAttribute("..section"),
    )


class SubjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subject

    school = factory.SelfAttribute("classroom.school")
    classroom = factory.SubFactory(ClassroomFactory)
    name = factory.Sequence(lambda n: f"Matière {n}")
    coefficient = 2
    teacher = factory.LazyAttribute(
        lambda o: ClassroomTeacherFactory(classroom=o.classroom, section=LanguageSection.FR).teacher
    )


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    school = factory.SubFactory(SchoolFactory)
    matricule = factory.Sequence(lambda n: f"MAT-{n:05d}")
    last_name = factory.Sequence(lambda n: f"Élève {n}")
    first_name = "Prénom"
    birth_date = datetime.date(2015, 1, 1)
    gender = Gender.MALE


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    school = factory.SelfAttribute("classroom.school")
    classroom = factory.SubFactory(ClassroomFactory)
    student = factory.SubFactory(StudentFactory, school=factory.SelfAttribute("..classroom.school"))
    academic_year = factory.SelfAttribute("classroom.academic_year")


class GuardianFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Guardian

    school = factory.SubFactory(SchoolFactory)
    user = None
    last_name = factory.Sequence(lambda n: f"Tuteur {n}")
    first_name = "Prénom"
    phone = factory.Sequence(lambda n: f"+237 6{n:08d}")
    email = ""


class StudentGuardianFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentGuardian

    school = factory.SelfAttribute("student.school")
    student = factory.SubFactory(StudentFactory)
    guardian = factory.SubFactory(GuardianFactory, school=factory.SelfAttribute("..student.school"))
    relationship = Relationship.FATHER
