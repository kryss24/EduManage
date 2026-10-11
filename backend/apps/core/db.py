"""Utilitaires PostgreSQL partagés (contraintes d'exclusion sur intervalles)."""

from django.contrib.postgres.fields import DateRangeField
from django.db.models import Func


class DateRange(Func):
    """Expression SQL `daterange(start, end, bounds)` pour les contraintes d'exclusion."""

    function = "DATERANGE"
    output_field = DateRangeField()
