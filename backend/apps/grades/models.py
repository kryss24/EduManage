"""Notes saisies par séquence. Moyennes, rangs et appréciations sont calculés
ailleurs (service dédié), jamais stockés sur ce modèle.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.academics.models import Enrollment
from apps.accounts.models import User
from apps.core.models import TenantModel


class Grade(TenantModel):
    student = models.ForeignKey(
        "academics.Student", verbose_name="élève", on_delete=models.PROTECT, related_name="grades"
    )
    subject = models.ForeignKey(
        "academics.Subject", verbose_name="matière", on_delete=models.PROTECT, related_name="grades"
    )
    sequence = models.ForeignKey(
        "academics.Sequence",
        verbose_name="séquence",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    value = models.DecimalField("note", max_digits=4, decimal_places=2)
    graded_on = models.DateField("notée le", default=timezone.localdate)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="saisie par",
        on_delete=models.PROTECT,
        related_name="grades_entered",
    )

    class Meta:
        verbose_name = "note"
        verbose_name_plural = "notes"
        ordering = ["sequence", "subject", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "sequence"],
                name="grade_student_subject_sequence_unique",
            ),
            models.CheckConstraint(check=Q(value__gte=0, value__lte=20), name="grade_value_range"),
        ]
        indexes = [models.Index(fields=["sequence", "subject"], name="grade_sequence_subject_idx")]

    def clean(self):
        super().clean()
        errors = {}
        if self.sequence_id and self.subject_id:
            if self.sequence.academic_year_id != self.subject.classroom.academic_year_id:
                errors["sequence"] = (
                    "La séquence doit appartenir à l'année scolaire de la classe de la matière."
                )
        if self.student_id and self.subject_id and self.sequence_id and "sequence" not in errors:
            has_enrollment = Enrollment.objects.filter(
                student_id=self.student_id,
                classroom_id=self.subject.classroom_id,
                academic_year_id=self.sequence.academic_year_id,
            ).exists()
            if not has_enrollment:
                errors["student"] = "L'élève doit être inscrit dans la classe de cette matière."
        if self.entered_by_id:
            entered_by = self.entered_by
            if entered_by.role != User.Role.SUPER_ADMIN and entered_by.school_id != self.school_id:
                errors["entered_by"] = "L'auteur de la saisie doit appartenir à la même école."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} – {self.subject} – {self.value}/20"
