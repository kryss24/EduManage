"""Calendrier scolaire, structure (niveaux/classes/matières) et personnes.

Les calculs de moyennes/rangs, le workflow de validation des notes et les
bulletins ne font pas partie de ce ticket (voir `docs/modele-donnees.md`).
"""

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeBoundary, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import User, phone_validator
from apps.core.db import DateRange
from apps.core.models import TenantModel


class LanguageSection(models.TextChoices):
    FR = "FR", "Français"
    EN = "EN", "Anglais"


# ---------------------------------------------------------------------------
# Calendrier
# ---------------------------------------------------------------------------


class AcademicYear(TenantModel):
    label = models.CharField("libellé", max_length=20)
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")
    is_active = models.BooleanField("active", default=False)
    is_archived = models.BooleanField("archivée", default=False)

    class Meta:
        verbose_name = "année scolaire"
        verbose_name_plural = "années scolaires"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "label"], name="academicyear_school_label_unique"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")), name="academicyear_end_after_start"
            ),
            models.CheckConstraint(
                condition=~Q(is_active=True, is_archived=True),
                name="academicyear_not_active_and_archived",
            ),
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_active=True),
                name="academicyear_one_active_per_school",
            ),
            ExclusionConstraint(
                name="academicyear_no_date_overlap",
                expressions=[
                    ("school", RangeOperators.EQUAL),
                    (
                        DateRange(
                            "start_date",
                            "end_date",
                            RangeBoundary(inclusive_lower=True, inclusive_upper=True),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]

    def __str__(self):
        return f"{self.label} ({self.school.name})"


class Sequence(TenantModel):
    academic_year = models.ForeignKey(
        "AcademicYear",
        verbose_name="année scolaire",
        on_delete=models.PROTECT,
        related_name="sequences",
    )
    number = models.PositiveSmallIntegerField("numéro")
    start_date = models.DateField("date de début")
    end_date = models.DateField("date de fin")

    class Meta:
        verbose_name = "séquence"
        verbose_name_plural = "séquences"
        ordering = ["academic_year", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "number"], name="sequence_academic_year_number_unique"
            ),
            models.CheckConstraint(
                condition=Q(number__gte=1, number__lte=6), name="sequence_number_range"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")), name="sequence_end_after_start"
            ),
            ExclusionConstraint(
                name="sequence_no_date_overlap",
                expressions=[
                    ("academic_year", RangeOperators.EQUAL),
                    (
                        DateRange(
                            "start_date",
                            "end_date",
                            RangeBoundary(inclusive_lower=True, inclusive_upper=True),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]

    @property
    def trimester(self):
        return (self.number + 1) // 2

    def clean(self):
        super().clean()
        if self.academic_year_id and self.start_date and self.end_date:
            year = self.academic_year
            errors = {}
            if self.start_date < year.start_date:
                errors["start_date"] = "La date de début doit être comprise dans l'année scolaire."
            if self.end_date > year.end_date:
                errors["end_date"] = "La date de fin doit être comprise dans l'année scolaire."
            if errors:
                raise ValidationError(errors)

    def __str__(self):
        return f"Séquence {self.number} – {self.academic_year.label}"


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


class Level(TenantModel):
    name = models.CharField("nom", max_length=50)
    order = models.PositiveSmallIntegerField("ordre")

    class Meta:
        verbose_name = "niveau"
        verbose_name_plural = "niveaux"
        ordering = ["school", "order"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="level_school_name_unique"),
            models.UniqueConstraint(fields=["school", "order"], name="level_school_order_unique"),
        ]

    def __str__(self):
        return self.name


class Classroom(TenantModel):
    academic_year = models.ForeignKey(
        "AcademicYear",
        verbose_name="année scolaire",
        on_delete=models.PROTECT,
        related_name="classrooms",
    )
    level = models.ForeignKey(
        "Level", verbose_name="niveau", on_delete=models.PROTECT, related_name="classrooms"
    )
    name = models.CharField("nom", max_length=50)

    class Meta:
        verbose_name = "classe"
        verbose_name_plural = "classes"
        ordering = ["academic_year", "level__order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "name"], name="classroom_academic_year_name_unique"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year.label})"


class Teacher(TenantModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="compte utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_profile",
    )
    last_name = models.CharField("nom", max_length=150)
    first_name = models.CharField("prénom", max_length=150)
    phone = models.CharField("téléphone", max_length=20, blank=True, validators=[phone_validator])
    language_section = models.CharField(
        "section linguistique", max_length=2, choices=LanguageSection.choices
    )
    monthly_salary = models.PositiveIntegerField("salaire mensuel (FCFA)", null=True, blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "enseignant"
        verbose_name_plural = "enseignants"
        ordering = ["last_name", "first_name"]

    def clean(self):
        super().clean()
        if self.user_id:
            errors = {}
            if self.user.role != User.Role.TEACHER:
                errors["user"] = "Le compte associé doit avoir le rôle Enseignant."
            elif self.user.school_id != self.school_id:
                errors["user"] = "Le compte associé doit appartenir à la même école."
            if errors:
                raise ValidationError(errors)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ClassroomTeacher(TenantModel):
    classroom = models.ForeignKey(
        "Classroom",
        verbose_name="classe",
        on_delete=models.PROTECT,
        related_name="classroom_teachers",
    )
    teacher = models.ForeignKey(
        "Teacher",
        verbose_name="enseignant",
        on_delete=models.PROTECT,
        related_name="classroom_teachers",
    )
    section = models.CharField(
        "section linguistique", max_length=2, choices=LanguageSection.choices
    )

    class Meta:
        verbose_name = "affectation enseignant/classe"
        verbose_name_plural = "affectations enseignant/classe"
        ordering = ["classroom", "section"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "section"], name="classroomteacher_classroom_section_unique"
            ),
            models.UniqueConstraint(
                fields=["classroom", "teacher"], name="classroomteacher_classroom_teacher_unique"
            ),
        ]

    def clean(self):
        super().clean()
        if self.teacher_id and self.section != self.teacher.language_section:
            raise ValidationError(
                {"section": "La section doit correspondre à la section de l'enseignant."}
            )

    def __str__(self):
        return f"{self.classroom} – {self.get_section_display()} – {self.teacher}"


class Subject(TenantModel):
    classroom = models.ForeignKey(
        "Classroom", verbose_name="classe", on_delete=models.PROTECT, related_name="subjects"
    )
    teacher = models.ForeignKey(
        "Teacher", verbose_name="enseignant", on_delete=models.PROTECT, related_name="subjects"
    )
    name = models.CharField("nom", max_length=100)
    coefficient = models.PositiveSmallIntegerField("coefficient")

    class Meta:
        verbose_name = "matière"
        verbose_name_plural = "matières"
        ordering = ["classroom", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "name"], name="subject_classroom_name_unique"
            ),
            models.CheckConstraint(
                condition=Q(coefficient__gte=1), name="subject_coefficient_min_1"
            ),
        ]

    def clean(self):
        super().clean()
        if self.classroom_id and self.teacher_id:
            is_assigned = ClassroomTeacher.objects.filter(
                classroom_id=self.classroom_id, teacher_id=self.teacher_id
            ).exists()
            if not is_assigned:
                raise ValidationError({"teacher": "L'enseignant doit être affecté à cette classe."})

    def __str__(self):
        return f"{self.name} ({self.classroom})"


# ---------------------------------------------------------------------------
# Personnes
# ---------------------------------------------------------------------------


class Gender(models.TextChoices):
    MALE = "M", "Masculin"
    FEMALE = "F", "Féminin"


class Student(TenantModel):
    matricule = models.CharField("matricule", max_length=30)
    last_name = models.CharField("nom", max_length=150)
    first_name = models.CharField("prénom", max_length=150)
    birth_date = models.DateField("date de naissance")
    gender = models.CharField("sexe", max_length=1, choices=Gender.choices)
    photo = models.ImageField("photo", upload_to="students/photos/", blank=True, null=True)

    class Meta:
        verbose_name = "élève"
        verbose_name_plural = "élèves"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "matricule"], name="student_school_matricule_unique"
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.matricule})"


class Enrollment(TenantModel):
    student = models.ForeignKey(
        "Student", verbose_name="élève", on_delete=models.PROTECT, related_name="enrollments"
    )
    classroom = models.ForeignKey(
        "Classroom", verbose_name="classe", on_delete=models.PROTECT, related_name="enrollments"
    )
    academic_year = models.ForeignKey(
        "AcademicYear",
        verbose_name="année scolaire",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )

    class Meta:
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"
        ordering = ["academic_year", "classroom", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year"], name="enrollment_student_academic_year_unique"
            ),
        ]

    def save(self, *args, **kwargs):
        if self.classroom_id:
            self.academic_year_id = self.classroom.academic_year_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} → {self.classroom}"


class Guardian(TenantModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="compte utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardian_profile",
    )
    last_name = models.CharField("nom", max_length=150)
    first_name = models.CharField("prénom", max_length=150, blank=True)
    phone = models.CharField("téléphone", max_length=20, validators=[phone_validator])
    email = models.EmailField("email", blank=True)

    class Meta:
        verbose_name = "parent/tuteur"
        verbose_name_plural = "parents/tuteurs"
        ordering = ["last_name", "first_name"]

    def clean(self):
        super().clean()
        if self.user_id:
            errors = {}
            if self.user.role != User.Role.PARENT:
                errors["user"] = "Le compte associé doit avoir le rôle Parent."
            elif self.user.school_id != self.school_id:
                errors["user"] = "Le compte associé doit appartenir à la même école."
            if errors:
                raise ValidationError(errors)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone


class Relationship(models.TextChoices):
    FATHER = "FATHER", "Père"
    MOTHER = "MOTHER", "Mère"
    TUTOR = "TUTOR", "Tuteur"
    OTHER = "OTHER", "Autre"


class StudentGuardian(TenantModel):
    student = models.ForeignKey(
        "Student", verbose_name="élève", on_delete=models.PROTECT, related_name="student_guardians"
    )
    guardian = models.ForeignKey(
        "Guardian",
        verbose_name="parent/tuteur",
        on_delete=models.PROTECT,
        related_name="student_guardians",
    )
    relationship = models.CharField(
        "lien de parenté", max_length=10, choices=Relationship.choices, blank=True
    )

    class Meta:
        verbose_name = "lien élève/tuteur"
        verbose_name_plural = "liens élève/tuteur"
        ordering = ["student", "guardian"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"], name="studentguardian_student_guardian_unique"
            ),
        ]

    def __str__(self):
        return f"{self.student} – {self.guardian}"
