"""Filtres et tris stricts pour les ressources du calendrier et des classes."""

import django_filters
from rest_framework import filters
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear, Classroom, Level, Sequence


class StrictOrderingFilter(filters.OrderingFilter):
    """OrderingFilter avec validation stricte contre une liste blanche.

    Refuse (400) tout paramètre de tri qui ne figure pas explicitement
    dans `ordering_fields` de la vue, empêchant les fuites ou injections SQL.
    """

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",") if param.strip()]
            valid_fields = getattr(view, "ordering_fields", [])
            for field in fields:
                stripped = field.lstrip("-+")
                if stripped not in valid_fields:
                    raise ValidationError(
                        {"ordering": f"Le champ de tri '{field}' n'est pas autorisé."}
                    )
        return super().get_ordering(request, queryset, view)


class AcademicYearFilter(django_filters.FilterSet):
    """Filtres pour les années scolaires."""

    class Meta:
        model = AcademicYear
        fields = ["is_active", "is_archived"]


class SequenceFilter(django_filters.FilterSet):
    """Filtres pour les séquences."""

    class Meta:
        model = Sequence
        fields = ["academic_year", "number"]


class LevelFilter(django_filters.FilterSet):
    """Filtres pour les niveaux."""

    class Meta:
        model = Level
        fields = []


class ClassroomFilter(django_filters.FilterSet):
    """Filtres pour les classes."""

    class Meta:
        model = Classroom
        fields = ["academic_year", "level"]
