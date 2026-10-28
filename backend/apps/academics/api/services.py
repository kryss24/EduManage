"""Services métier pour le calendrier scolaire et la structure des classes.

Toute la logique métier (activation, archivage, génération des séquences,
création des niveaux par défaut, contexte, suppressions protégées) réside ici.
"""

from __future__ import annotations

import datetime
import zoneinfo

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from apps.academics.models import AcademicYear, Classroom, Level, Sequence
from apps.core.audit import record_audit
from apps.grades.models import Grade
from apps.tenants.models import School


class YearArchivedError(APIException):
    """Refus d'écriture ou de suppression sur une année scolaire archivée."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Cette année scolaire est archivée et ne peut plus être modifiée."
    default_code = "year_archived"

    def __init__(self, detail: str | None = None, code: str | None = None):
        super().__init__(detail=detail or self.default_detail, code=code or self.default_code)
        # Assure la présence de {"detail": "...", "code": "year_archived"} dans le corps JSON
        self.detail = {"detail": str(detail or self.default_detail), "code": self.default_code}


class AcademicConflictError(APIException):
    """Conflit métier (ressources rattachées, contrainte d'état) -> 409."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "L'opération demandée entre en conflit avec l'état actuel des données."
    default_code = "conflict"

    def __init__(self, detail: str | None = None, code: str | None = None):
        super().__init__(detail=detail or self.default_detail, code=code or self.default_code)
        self.detail = {
            "detail": str(detail or self.default_detail),
            "code": code or self.default_code,
        }


def check_year_not_archived(year: AcademicYear | None) -> None:
    """Lève YearArchivedError (409) si l'année scolaire est archivée."""
    if year is not None and year.is_archived:
        raise YearArchivedError()


# ---------------------------------------------------------------------------
# Années scolaires
# ---------------------------------------------------------------------------


def activate_academic_year(year: AcademicYear, request=None) -> AcademicYear:
    """Active une année scolaire de manière atomique.

    Désactive l'éventuelle autre année active de la même école.
    Refusée (409) si l'année est archivée.
    Sans effet (idempotent) si l'année est déjà active.
    """
    with transaction.atomic():
        # Verrouiller l'école pour sérialiser les activations concurrentes au sein d'une même école
        School.objects.select_for_update().get(pk=year.school_id)
        locked_year = AcademicYear.objects.select_for_update().get(pk=year.pk)

        if locked_year.is_archived:
            raise YearArchivedError("Impossible d'activer une année scolaire archivée.")

        if locked_year.is_active:
            return locked_year

        # Désactiver toute autre année active de l'école
        AcademicYear.objects.select_for_update().filter(
            school=locked_year.school, is_active=True
        ).exclude(pk=locked_year.pk).update(is_active=False)

        locked_year.is_active = True
        locked_year.save(update_fields=["is_active", "updated_at"])

        record_audit(
            request,
            action="activate_academic_year",
            entity_type="AcademicYear",
            entity_id=locked_year.id,
            metadata={"label": locked_year.label},
            school=locked_year.school,
        )

        return locked_year


def archive_academic_year(year: AcademicYear, request=None) -> AcademicYear:
    """Archive une année scolaire de manière atomique.

    Refusée (409) si l'année est active.
    Sans effet (idempotent) si l'année est déjà archivée.
    """
    with transaction.atomic():
        locked_year = AcademicYear.objects.select_for_update().get(pk=year.pk)

        if locked_year.is_active:
            raise AcademicConflictError(
                "Impossible d'archiver l'année scolaire active. "
                "Veuillez activer d'abord une autre année scolaire."
            )

        if locked_year.is_archived:
            return locked_year

        locked_year.is_archived = True
        locked_year.save(update_fields=["is_archived", "updated_at"])

        record_audit(
            request,
            action="archive_academic_year",
            entity_type="AcademicYear",
            entity_id=locked_year.id,
            metadata={"label": locked_year.label},
            school=locked_year.school,
        )

        return locked_year


def delete_academic_year(year: AcademicYear, request=None) -> None:
    """Supprime une année scolaire si elle n'a ni séquences ni classes."""
    check_year_not_archived(year)

    if year.sequences.exists() or year.classrooms.exists():
        raise AcademicConflictError(
            "Impossible de supprimer cette année scolaire car des séquences "
            "ou des classes y sont rattachées."
        )

    year_id = str(year.id)
    label = year.label
    school = year.school

    year.delete()

    record_audit(
        request,
        action="delete_academic_year",
        entity_type="AcademicYear",
        entity_id=year_id,
        metadata={"label": label},
        school=school,
    )


def generate_sequences_for_year(
    year: AcademicYear, periods: list[dict], request=None
) -> list[Sequence]:
    """Génère les 6 séquences d'une année scolaire en une transaction atomique.

    `periods` doit contenir exactement 6 dictionnaires {'start_date': date, 'end_date': date}.
    Refusée (409) si l'année est archivée ou possède déjà des séquences.
    400 avec le numéro de la séquence en cause si une plage est invalide.
    """
    check_year_not_archived(year)

    if year.sequences.exists():
        raise AcademicConflictError("Cette année scolaire possède déjà des séquences.")

    if not isinstance(periods, list) or len(periods) != 6:
        raise serializers.ValidationError(
            {"detail": "Exactement 6 plages de dates doivent être fournies."}
        )

    parsed_periods = []
    for i, period in enumerate(periods, start=1):
        if not isinstance(period, dict):
            raise serializers.ValidationError(
                {"detail": f"Plage invalide pour la séquence {i}.", "sequence_number": i}
            )

        start_val = period.get("start_date")
        end_val = period.get("end_date")

        if not start_val or not end_val:
            msg = f"Les dates de début et de fin sont obligatoires pour la séquence {i}."
            raise serializers.ValidationError({"detail": msg, "sequence_number": i})

        try:
            start_date = (
                datetime.date.fromisoformat(str(start_val))
                if isinstance(start_val, str)
                else start_val
            )
            end_date = (
                datetime.date.fromisoformat(str(end_val)) if isinstance(end_val, str) else end_val
            )
        except (ValueError, TypeError):
            msg = f"Format de date invalide (AAAA-MM-JJ attendu) pour la séquence {i}."
            raise serializers.ValidationError({"detail": msg, "sequence_number": i}) from None

        if end_date <= start_date:
            msg = f"La date de fin doit être postérieure à la date de début pour la séquence {i}."
            raise serializers.ValidationError({"detail": msg, "sequence_number": i})

        if start_date < year.start_date or end_date > year.end_date:
            msg = f"La séquence {i} doit être comprise dans les limites de l'année scolaire."
            raise serializers.ValidationError({"detail": msg, "sequence_number": i})

        if parsed_periods:
            prev_end = parsed_periods[-1]["end_date"]
            if start_date <= prev_end:
                msg = f"La séquence {i} doit commencer après la fin de la séquence {i - 1}."
                raise serializers.ValidationError({"detail": msg, "sequence_number": i})

        parsed_periods.append({"number": i, "start_date": start_date, "end_date": end_date})

    with transaction.atomic():
        created_sequences = []
        for p in parsed_periods:
            seq = Sequence(
                school=year.school,
                academic_year=year,
                number=p["number"],
                start_date=p["start_date"],
                end_date=p["end_date"],
            )
            seq.full_clean()
            seq.save()
            created_sequences.append(seq)

        record_audit(
            request,
            action="generate_sequences",
            entity_type="AcademicYear",
            entity_id=year.id,
            metadata={"count": len(created_sequences)},
            school=year.school,
        )

        return created_sequences


# ---------------------------------------------------------------------------
# Séquences
# ---------------------------------------------------------------------------


def delete_sequence(sequence: Sequence, request=None) -> None:
    """Supprime une séquence si aucune note n'y est rattachée."""
    check_year_not_archived(sequence.academic_year)

    if sequence.grades.exists():
        raise AcademicConflictError(
            "Impossible de supprimer cette séquence car des notes y sont associées."
        )

    seq_id = str(sequence.id)
    number = sequence.number
    school = sequence.school

    sequence.delete()

    record_audit(
        request,
        action="delete_sequence",
        entity_type="Sequence",
        entity_id=seq_id,
        metadata={"number": number},
        school=school,
    )


# ---------------------------------------------------------------------------
# Niveaux
# ---------------------------------------------------------------------------

DEFAULT_LEVELS = [
    ("CP1", 1),
    ("CP2", 2),
    ("CE1", 3),
    ("CE2", 4),
    ("CM1", 5),
    ("CM2", 6),
]


def create_default_levels(school: School) -> list[Level]:
    """Crée les niveaux scolaires par défaut pour une école (CP1 à CM2).

    Fonction idempotente : si un niveau avec le même nom (insensible à la casse)
    ou le même ordre existe déjà, il n'est pas recréé.
    """
    levels = []
    with transaction.atomic():
        for name, order in DEFAULT_LEVELS:
            level = Level.objects.filter(school=school).filter(name__iexact=name).first()
            if level is None:
                # Vérifier si l'ordre est déjà pris
                if not Level.objects.filter(school=school, order=order).exists():
                    level = Level.objects.create(school=school, name=name, order=order)
                else:
                    max_order = (
                        Level.objects.filter(school=school).aggregate(Max("order"))["order__max"]
                        or 0
                    )
                    level = Level.objects.create(school=school, name=name, order=max_order + 1)
            levels.append(level)
    return levels


def delete_level(level: Level, request=None) -> None:
    """Supprime un niveau si aucune classe n'y est rattachée."""
    if level.classrooms.exists():
        raise AcademicConflictError(
            "Impossible de supprimer ce niveau car des classes y sont rattachées."
        )

    level_id = str(level.id)
    name = level.name
    school = level.school

    level.delete()

    record_audit(
        request,
        action="delete_level",
        entity_type="Level",
        entity_id=level_id,
        metadata={"name": name},
        school=school,
    )


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


def delete_classroom(classroom: Classroom, request=None) -> None:
    """Supprime une classe si aucune ressource n'en dépend."""
    check_year_not_archived(classroom.academic_year)

    has_enrollments = classroom.enrollments.exists()
    has_subjects = classroom.subjects.exists()
    has_teachers = classroom.classroom_teachers.exists()
    has_grades = Grade.objects.filter(subject__classroom=classroom).exists()

    if has_enrollments or has_subjects or has_teachers or has_grades:
        raise AcademicConflictError(
            "Impossible de supprimer cette classe car des ressources en dépendent "
            "(inscriptions, matières, affectations ou notes).",
            code="classroom_has_dependencies",
        )

    cls_id = str(classroom.id)
    name = classroom.name
    school = classroom.school

    classroom.delete()

    record_audit(
        request,
        action="delete_classroom",
        entity_type="Classroom",
        entity_id=cls_id,
        metadata={"name": name},
        school=school,
    )


# ---------------------------------------------------------------------------
# Contexte scolaire
# ---------------------------------------------------------------------------


def get_academic_context(school: School) -> dict:
    """Retourne l'état synthétique du calendrier et de la structure pour une école.

    `current_sequence` est la séquence de l'année active dont les dates englobent
    la date courante dans le fuseau horaire de l'école (`school.timezone`).
    """
    active_year = AcademicYear.objects.filter(school=school, is_active=True).first()

    sequences = []
    current_sequence = None

    if active_year:
        sequences = list(active_year.sequences.all().order_by("number"))

        try:
            tz = zoneinfo.ZoneInfo(school.timezone or "Africa/Douala")
        except Exception:
            tz = zoneinfo.ZoneInfo("Africa/Douala")

        today = timezone.now().astimezone(tz).date()

        for seq in sequences:
            if seq.start_date <= today <= seq.end_date:
                current_sequence = seq
                break

    levels = list(Level.objects.filter(school=school).order_by("order", "name"))

    return {
        "active_year": active_year,
        "sequences": sequences,
        "current_sequence": current_sequence,
        "levels": levels,
    }
