"""Jeu de données de démonstration, idempotent et déterministe.

Crée deux écoles ``[DEMO] ...`` afin de pouvoir tester l'isolation entre
tenants en conditions proches du réel. Relancer la commande ne crée pas de
doublons : chaque entité est retrouvée via une clé naturelle stable
(matricule, email, libellé...).
"""

import random
from collections import Counter
from datetime import date
from decimal import Decimal
from os import environ

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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
from apps.accounts.models import User
from apps.grades.models import Grade
from apps.tenants.models import School

# Valeur d'exemple de .env.example : son usage tel quel doit être refusé.
PLACEHOLDER_PASSWORD = "CHANGE_ME_avant_de_lancer_le_seed"

RNG_SEED = 20252026

LEVELS = [("CP1", 1), ("CP2", 2), ("CE1", 3), ("CE2", 4), ("CM1", 5), ("CM2", 6)]

FRENCH_SUBJECTS = [
    ("Français", 4),
    ("Mathématiques", 4),
    ("Sciences", 2),
    ("Histoire-Géographie", 2),
    ("Éducation civique", 1),
]
ENGLISH_SUBJECTS = [("English Language", 2), ("Literature", 1)]

# Six séquences non chevauchantes comprises dans l'année scolaire 2025-2026.
SEQUENCE_DATES = [
    (date(2025, 9, 1), date(2025, 10, 24)),
    (date(2025, 10, 27), date(2025, 12, 19)),
    (date(2026, 1, 5), date(2026, 2, 13)),
    (date(2026, 2, 16), date(2026, 3, 27)),
    (date(2026, 3, 30), date(2026, 5, 8)),
    (date(2026, 5, 11), date(2026, 6, 30)),
]

STUDENTS_PER_CLASSROOM = 15
GUARDIANS_PER_SCHOOL = 10

FIRST_NAMES_MALE = [
    "Jean",
    "Paul",
    "Pierre",
    "Emmanuel",
    "Joseph",
    "Samuel",
    "Patrick",
    "Eric",
    "Christian",
    "Michel",
    "Arnaud",
    "Yannick",
    "Hervé",
    "Boris",
    "Franck",
    "Alain",
    "Serge",
    "Thierry",
    "Gaston",
    "Blaise",
]
FIRST_NAMES_FEMALE = [
    "Marie",
    "Grace",
    "Esther",
    "Chantal",
    "Brenda",
    "Carine",
    "Sandrine",
    "Pauline",
    "Nadège",
    "Rosine",
    "Aurélie",
    "Yvonne",
    "Clarisse",
    "Honorine",
    "Delphine",
    "Francine",
    "Josiane",
    "Linda",
    "Vanessa",
    "Odette",
]
LAST_NAMES = [
    "Nkomo",
    "Mballa",
    "Ngo",
    "Fotso",
    "Kamga",
    "Tchoumi",
    "Biyong",
    "Ewane",
    "Nguema",
    "Essomba",
    "Ateba",
    "Nnomo",
    "Talla",
    "Djoumessi",
    "Abena",
    "Etoundi",
    "Bisso",
    "Nkeng",
    "Mendomo",
    "Ngassa",
    "Tabi",
    "Wandji",
    "Zang",
    "Moukouri",
    "Fouda",
]

SCHOOLS_CONFIG = [
    {
        "name": "[DEMO] École Les Palmiers",
        "city": "Douala",
        "code": "A",
        "domain": "ecole-demo-a.test",
        "extra_cm2_classroom": True,
    },
    {
        "name": "[DEMO] École Horizon",
        "city": "Yaoundé",
        "code": "B",
        "domain": "ecole-demo-b.test",
        "extra_cm2_classroom": False,
    },
]


def slugify_simple(text):
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "â": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "û": "u",
        "ù": "u",
        "ç": "c",
        "ö": "o",
        "ü": "u",
    }
    lowered = text.lower()
    for accented, plain in replacements.items():
        lowered = lowered.replace(accented, plain)
    return "".join(c if c.isalnum() else "-" for c in lowered).strip("-")


def make_phone(n):
    return f"+237 6{n:08d}"


def random_name(rng, gender):
    first_names = FIRST_NAMES_MALE if gender == Gender.MALE else FIRST_NAMES_FEMALE
    return rng.choice(first_names), rng.choice(LAST_NAMES)


def random_grade_value(rng):
    raw = rng.gauss(12, 3)
    rounded = round(raw * 2) / 2
    rounded = max(0.0, min(20.0, rounded))
    return Decimal(str(rounded)).quantize(Decimal("0.01"))


class Command(BaseCommand):
    help = "Crée (ou met à jour) un jeu de données de démonstration pour deux écoles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Autorise l'exécution même si DEBUG=False.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime uniquement les données de démo (écoles '[DEMO] ...') et s'arrête.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            with transaction.atomic():
                counts = self._delete_demo_data()
            self.stdout.write(self.style.SUCCESS("Données de démonstration supprimées :"))
            for key, value in counts.items():
                self.stdout.write(f"  {key}: {value}")
            return

        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Cette commande ne doit pas être exécutée avec DEBUG=False (utilisez --force si "
                "vous savez ce que vous faites)."
            )

        password = self._get_password()

        with transaction.atomic():
            summary = self._seed(password)

        self.stdout.write(self.style.SUCCESS("Jeu de données de démonstration prêt :"))
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")

    # -- Mot de passe ------------------------------------------------------

    def _get_password(self):
        password = environ.get("SEED_USER_PASSWORD", "")
        if not password:
            raise CommandError(
                "SEED_USER_PASSWORD est obligatoire pour lancer le seed (voir .env.example)."
            )
        if password == PLACEHOLDER_PASSWORD:
            raise CommandError(
                "SEED_USER_PASSWORD a encore sa valeur d'exemple : définissez un vrai mot de passe."
            )
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise CommandError(
                "SEED_USER_PASSWORD ne respecte pas les règles de mot de passe : "
                + " ".join(exc.messages)
            ) from exc
        return password

    # -- Suppression (--reset) --------------------------------------------

    def _delete_demo_data(self):
        demo_schools = School.objects.filter(name__startswith="[DEMO]")
        if not demo_schools.exists():
            return {"schools": 0}
        school_ids = list(demo_schools.values_list("pk", flat=True))
        counts = {}
        counts["grades"] = Grade.objects.filter(school_id__in=school_ids).delete()[0]
        counts["student_guardians"] = StudentGuardian.objects.filter(
            school_id__in=school_ids
        ).delete()[0]
        counts["enrollments"] = Enrollment.objects.filter(school_id__in=school_ids).delete()[0]
        counts["classroom_teachers"] = ClassroomTeacher.objects.filter(
            school_id__in=school_ids
        ).delete()[0]
        counts["subjects"] = Subject.objects.filter(school_id__in=school_ids).delete()[0]
        counts["classrooms"] = Classroom.objects.filter(school_id__in=school_ids).delete()[0]
        counts["sequences"] = Sequence.objects.filter(school_id__in=school_ids).delete()[0]
        counts["students"] = Student.objects.filter(school_id__in=school_ids).delete()[0]
        counts["guardians"] = Guardian.objects.filter(school_id__in=school_ids).delete()[0]
        counts["teachers"] = Teacher.objects.filter(school_id__in=school_ids).delete()[0]
        counts["levels"] = Level.objects.filter(school_id__in=school_ids).delete()[0]
        counts["academic_years"] = AcademicYear.objects.filter(school_id__in=school_ids).delete()[0]
        counts["users"] = User.objects.filter(school_id__in=school_ids).delete()[0]
        counts["schools"] = demo_schools.delete()[0]
        return counts

    # -- Création -----------------------------------------------------------

    def _seed(self, password):
        rng = random.Random(RNG_SEED)
        summary = Counter()

        for school_cfg in SCHOOLS_CONFIG:
            school = self._seed_school(school_cfg, summary)
            academic_year = self._seed_academic_year(school, summary)
            sequences = self._seed_sequences(school, academic_year, summary)
            levels = self._seed_levels(school, summary)
            classrooms = self._seed_classrooms(school, academic_year, levels, school_cfg, summary)

            self._seed_staff_user(
                school, school_cfg, "admin", User.Role.SCHOOL_ADMIN, password, summary
            )
            self._seed_staff_user(
                school, school_cfg, "caisse", User.Role.CASHIER, password, summary
            )

            for classroom in classrooms:
                fr_teacher = self._seed_teacher(
                    school, school_cfg, classroom, LanguageSection.FR, password, rng, summary
                )
                en_teacher = self._seed_teacher(
                    school, school_cfg, classroom, LanguageSection.EN, password, rng, summary
                )
                self._seed_classroom_teacher(
                    school, classroom, fr_teacher, LanguageSection.FR, summary
                )
                self._seed_classroom_teacher(
                    school, classroom, en_teacher, LanguageSection.EN, summary
                )
                self._seed_subjects(school, classroom, fr_teacher, en_teacher, summary)

            students_by_classroom = self._seed_students(
                school, school_cfg, classrooms, rng, summary
            )
            all_students = [
                student
                for _classroom, students in students_by_classroom.values()
                for student in students
            ]
            self._seed_enrollments(school, academic_year, students_by_classroom, summary)
            self._seed_guardians(school, school_cfg, all_students, password, rng, summary)
            self._seed_grades(school, classrooms, sequences[:2], rng, summary)

        return summary

    def _seed_school(self, school_cfg, summary):
        school, created = School.objects.get_or_create(
            name=school_cfg["name"],
            defaults={"city": school_cfg["city"], "plan": School.Plan.STANDARD},
        )
        summary["schools"] += int(created)
        return school

    def _seed_academic_year(self, school, summary):
        academic_year, created = AcademicYear.objects.get_or_create(
            school=school,
            label="2025-2026",
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2026, 6, 30),
                "is_active": True,
            },
        )
        summary["academic_years"] += int(created)
        return academic_year

    def _seed_sequences(self, school, academic_year, summary):
        sequences = []
        for number, (start, end) in enumerate(SEQUENCE_DATES, start=1):
            sequence, created = Sequence.objects.get_or_create(
                academic_year=academic_year,
                number=number,
                defaults={"school": school, "start_date": start, "end_date": end},
            )
            summary["sequences"] += int(created)
            sequences.append(sequence)
        return sequences

    def _seed_levels(self, school, summary):
        levels = {}
        for name, order in LEVELS:
            level, created = Level.objects.get_or_create(
                school=school, name=name, defaults={"order": order}
            )
            summary["levels"] += int(created)
            levels[name] = level
        return levels

    def _seed_classrooms(self, school, academic_year, levels, school_cfg, summary):
        classrooms = []
        for name, _order in LEVELS:
            classroom, created = Classroom.objects.get_or_create(
                academic_year=academic_year,
                name=name,
                defaults={"school": school, "level": levels[name]},
            )
            summary["classrooms"] += int(created)
            classrooms.append(classroom)
            if name == "CM2" and school_cfg["extra_cm2_classroom"]:
                extra, created = Classroom.objects.get_or_create(
                    academic_year=academic_year,
                    name="CM2 B",
                    defaults={"school": school, "level": levels[name]},
                )
                summary["classrooms"] += int(created)
                classrooms.append(extra)
        return classrooms

    def _seed_staff_user(self, school, school_cfg, local_part, role, password, summary):
        email = f"{local_part}@{school_cfg['domain']}"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "École",
                "last_name": role.label,
                "role": role,
                "school": school,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        summary["users"] += int(created)
        return user

    def _seed_teacher(self, school, school_cfg, classroom, section, password, rng, summary):
        slug = slugify_simple(classroom.name)
        email = f"enseignant.{slug}.{section.lower()}@{school_cfg['domain']}"
        gender = rng.choice([Gender.MALE, Gender.FEMALE])
        first_name, last_name = random_name(rng, gender)

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "role": User.Role.TEACHER,
                "school": school,
            },
        )
        if user_created:
            user.set_password(password)
            user.save(update_fields=["password"])
        summary["users"] += int(user_created)

        teacher, teacher_created = Teacher.objects.get_or_create(
            user=user,
            defaults={
                "school": school,
                "last_name": last_name,
                "first_name": first_name,
                "language_section": section,
            },
        )
        summary["teachers"] += int(teacher_created)
        return teacher

    def _seed_classroom_teacher(self, school, classroom, teacher, section, summary):
        _, created = ClassroomTeacher.objects.get_or_create(
            classroom=classroom,
            section=section,
            defaults={"school": school, "teacher": teacher},
        )
        summary["classroom_teachers"] += int(created)

    def _seed_subjects(self, school, classroom, fr_teacher, en_teacher, summary):
        for name, coefficient in FRENCH_SUBJECTS:
            _, created = Subject.objects.get_or_create(
                classroom=classroom,
                name=name,
                defaults={"school": school, "teacher": fr_teacher, "coefficient": coefficient},
            )
            summary["subjects"] += int(created)
        for name, coefficient in ENGLISH_SUBJECTS:
            _, created = Subject.objects.get_or_create(
                classroom=classroom,
                name=name,
                defaults={"school": school, "teacher": en_teacher, "coefficient": coefficient},
            )
            summary["subjects"] += int(created)

    def _seed_students(self, school, school_cfg, classrooms, rng, summary):
        students_by_classroom = {}
        counter = 1
        for classroom in classrooms:
            level_order = classroom.level.order
            students = []
            for _ in range(STUDENTS_PER_CLASSROOM):
                gender = rng.choice([Gender.MALE, Gender.FEMALE])
                first_name, last_name = random_name(rng, gender)
                matricule = f"DEMO-{school_cfg['code']}-{counter:04d}"
                counter += 1
                age = 5 + level_order
                birth_year = 2025 - age
                birth_month = rng.randint(1, 12)
                birth_day = rng.randint(1, 28)
                student, created = Student.objects.get_or_create(
                    school=school,
                    matricule=matricule,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "gender": gender,
                        "birth_date": date(birth_year, birth_month, birth_day),
                    },
                )
                summary["students"] += int(created)
                students.append(student)
            students_by_classroom[classroom.pk] = (classroom, students)
        return students_by_classroom

    def _seed_enrollments(self, school, academic_year, students_by_classroom, summary):
        for classroom, students in students_by_classroom.values():
            for student in students:
                _, created = Enrollment.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    defaults={"school": school, "classroom": classroom},
                )
                summary["enrollments"] += int(created)

    def _seed_guardians(self, school, school_cfg, students, password, rng, summary):
        shuffled_students = list(students)
        rng.shuffle(shuffled_students)
        student_groups = []
        index = 0
        for _ in range(GUARDIANS_PER_SCHOOL):
            if index >= len(shuffled_students):
                break
            size = min(rng.choice([1, 1, 2, 3]), len(shuffled_students) - index)
            student_groups.append(shuffled_students[index : index + size])
            index += size

        # Décalage déterministe par école pour que les deux écoles ne
        # génèrent jamais le même numéro de téléphone (clé naturelle).
        code_offset = {"A": 0, "B": 1000}[school_cfg["code"]]

        for i, group in enumerate(student_groups, start=1):
            gender = rng.choice([Gender.MALE, Gender.FEMALE])
            first_name, last_name = random_name(rng, gender)
            phone = make_phone(code_offset + i)
            relationship = Relationship.FATHER if gender == Gender.MALE else Relationship.MOTHER

            user = None
            if i % 2 == 0:
                email = f"parent{i}@{school_cfg['domain']}"
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "role": User.Role.PARENT,
                        "school": school,
                    },
                )
                if user_created:
                    user.set_password(password)
                    user.save(update_fields=["password"])
                summary["users"] += int(user_created)

            guardian, created = Guardian.objects.get_or_create(
                school=school,
                phone=phone,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "user": user,
                },
            )
            summary["guardians"] += int(created)

            for student in group:
                _, sg_created = StudentGuardian.objects.get_or_create(
                    student=student,
                    guardian=guardian,
                    defaults={"school": school, "relationship": relationship},
                )
                summary["student_guardians"] += int(sg_created)

    def _seed_grades(self, school, classrooms, sequences, rng, summary):
        existing = set(
            Grade.objects.filter(school=school).values_list(
                "student_id", "subject_id", "sequence_id"
            )
        )
        new_grades = []
        for classroom in classrooms:
            enrolled_students = [
                enrollment.student
                for enrollment in Enrollment.objects.filter(classroom=classroom).select_related(
                    "student"
                )
            ]
            subjects = list(
                Subject.objects.filter(classroom=classroom).select_related("teacher__user")
            )
            for subject in subjects:
                if subject.teacher.user_id is None:
                    continue
                for sequence in sequences:
                    for student in enrolled_students:
                        # `rng` est toujours consommé, même si la note existe déjà,
                        # pour que l'état du générateur reste identique entre deux
                        # exécutions (idempotence des données générées ensuite).
                        value = random_grade_value(rng)
                        key = (student.pk, subject.pk, sequence.pk)
                        if key in existing:
                            continue
                        existing.add(key)
                        new_grades.append(
                            Grade(
                                school=school,
                                student=student,
                                subject=subject,
                                sequence=sequence,
                                value=value,
                                entered_by=subject.teacher.user,
                            )
                        )
        Grade.objects.bulk_create(new_grades)
        summary["grades"] += len(new_grades)
