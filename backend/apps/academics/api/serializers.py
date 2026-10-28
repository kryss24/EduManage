"""Serializers pour le calendrier scolaire et la structure des classes."""

from django.db.models import Max
from rest_framework import serializers

from apps.academics.models import AcademicYear, Classroom, Level, Sequence
from apps.core.tenancy import (
    TenantModelSerializer,
    TenantPrimaryKeyRelatedField,
    get_request_school,
)

from .services import YearArchivedError, check_year_not_archived


class AcademicYearSerializer(TenantModelSerializer):
    """Serializer pour les années scolaires."""

    is_active = serializers.BooleanField(read_only=True)
    is_archived = serializers.BooleanField(read_only=True)

    class Meta:
        model = AcademicYear
        fields = [
            "id",
            "school",
            "label",
            "start_date",
            "end_date",
            "is_active",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "school", "is_active", "is_archived", "created_at", "updated_at"]

    def _get_school(self):
        request = self.context.get("request")
        if request:
            return get_request_school(request)
        if self.instance:
            return self.instance.school
        raise serializers.ValidationError("Impossible de déterminer l'école de la requête.")

    def validate(self, attrs):
        # Vérification année archivée en cas de modification
        if self.instance is not None and self.instance.is_archived:
            raise YearArchivedError()

        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        label = attrs.get("label", getattr(self.instance, "label", None))

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit être postérieure à la date de début."}
            )

        school = self._get_school()

        # Unicité du libellé par école (insensible à la casse)
        if label:
            qs = AcademicYear.objects.filter(school=school, label__iexact=label.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"label": "Une année scolaire avec ce libellé existe déjà pour cette école."}
                )

        # Absence de chevauchement de dates avec une autre année de l'école
        if start_date and end_date:
            overlap_qs = AcademicYear.objects.filter(
                school=school,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if self.instance:
                overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
            if overlap_qs.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Les dates chevauchent une autre année scolaire de l'école."
                        ]
                    }
                )

        return attrs


class SequenceSerializer(TenantModelSerializer):
    """Serializer pour les séquences scolaires."""

    academic_year = TenantPrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        required=True,
    )
    trimester = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sequence
        fields = [
            "id",
            "school",
            "academic_year",
            "number",
            "trimester",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "school", "trimester", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        instance = self.instance

        if instance is not None:
            # Année scolaire immuable après création
            if "academic_year" in attrs and attrs["academic_year"] != instance.academic_year:
                raise serializers.ValidationError(
                    {"academic_year": "L'année scolaire d'une séquence ne peut pas être modifiée."}
                )
            check_year_not_archived(instance.academic_year)
            academic_year = instance.academic_year
        else:
            academic_year = attrs.get("academic_year")
            check_year_not_archived(academic_year)

        number = attrs.get("number", getattr(instance, "number", None))
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))

        if number is not None and (number < 1 or number > 6):
            raise serializers.ValidationError(
                {"number": "Le numéro de séquence doit être compris entre 1 et 6."}
            )

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit être postérieure à la date de début."}
            )

        if academic_year and start_date and end_date:
            if start_date < academic_year.start_date:
                raise serializers.ValidationError(
                    {"start_date": "La date de début doit être comprise dans l'année scolaire."}
                )
            if end_date > academic_year.end_date:
                raise serializers.ValidationError(
                    {"end_date": "La date de fin doit être comprise dans l'année scolaire."}
                )

            # Unicité du numéro par année
            num_qs = Sequence.objects.filter(academic_year=academic_year, number=number)
            if instance:
                num_qs = num_qs.exclude(pk=instance.pk)
            if num_qs.exists():
                raise serializers.ValidationError(
                    {"number": "Ce numéro de séquence existe déjà pour cette année scolaire."}
                )

            # Absence de chevauchement de dates au sein de l'année
            overlap_qs = Sequence.objects.filter(
                academic_year=academic_year,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if instance:
                overlap_qs = overlap_qs.exclude(pk=instance.pk)
            if overlap_qs.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Les dates chevauchent une autre séquence de cette année scolaire."
                        ]
                    }
                )

            # Ordre chronologique cohérent avec le numéro :
            # la séquence n commence après la fin de n-1 et finit avant le début de n+1
            other_sequences = Sequence.objects.filter(academic_year=academic_year)
            if instance:
                other_sequences = other_sequences.exclude(pk=instance.pk)

            for other in other_sequences:
                if other.number < number and start_date <= other.end_date:
                    msg = (
                        f"La séquence {number} doit commencer après la fin de "
                        f"la séquence {other.number}."
                    )
                    raise serializers.ValidationError({"start_date": msg})
                if other.number > number and end_date >= other.start_date:
                    msg = (
                        f"La séquence {number} doit finir avant le début de "
                        f"la séquence {other.number}."
                    )
                    raise serializers.ValidationError({"end_date": msg})

        return attrs


class SequencePeriodSerializer(serializers.Serializer):
    """Schéma d'une plage de dates pour la génération des séquences."""

    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)


class LevelSerializer(TenantModelSerializer):
    """Serializer pour les niveaux scolaires."""

    order = serializers.IntegerField(required=False)

    class Meta:
        model = Level
        fields = [
            "id",
            "school",
            "name",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "school", "created_at", "updated_at"]

    def _get_school(self):
        request = self.context.get("request")
        if request:
            return get_request_school(request)
        if self.instance:
            return self.instance.school
        raise serializers.ValidationError("Impossible de déterminer l'école de la requête.")

    def validate_name(self, value):
        name = value.strip()
        school = self._get_school()
        qs = Level.objects.filter(school=school, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un niveau avec ce nom existe déjà pour cette école.")
        return name

    def validate_order(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("L'ordre doit être un entier positif supérieur à 0.")
        school = self._get_school()
        if value is not None:
            qs = Level.objects.filter(school=school, order=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Un niveau avec cet ordre existe déjà pour cette école."
                )
        return value

    def create(self, validated_data):
        if "order" not in validated_data or validated_data["order"] is None:
            school = validated_data.get("school") or self._get_school()
            max_order = (
                Level.objects.filter(school=school).aggregate(Max("order"))["order__max"] or 0
            )
            validated_data["order"] = max_order + 1
        return super().create(validated_data)


class ClassroomSerializer(TenantModelSerializer):
    """Serializer pour les classes."""

    academic_year = TenantPrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        required=True,
    )
    level = TenantPrimaryKeyRelatedField(
        queryset=Level.objects.all(),
        required=True,
    )
    academic_year_label = serializers.CharField(source="academic_year.label", read_only=True)
    level_name = serializers.CharField(source="level.name", read_only=True)
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [
            "id",
            "school",
            "academic_year",
            "academic_year_label",
            "level",
            "level_name",
            "name",
            "students_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school",
            "academic_year_label",
            "level_name",
            "students_count",
            "created_at",
            "updated_at",
        ]
        validators = []

    def get_students_count(self, obj) -> int:
        if hasattr(obj, "students_count"):
            return obj.students_count
        return obj.enrollments.count()

    def validate(self, attrs):
        instance = self.instance

        if instance is not None:
            # Année scolaire immuable après création
            if "academic_year" in attrs and attrs["academic_year"] != instance.academic_year:
                raise serializers.ValidationError(
                    {"academic_year": "L'année scolaire d'une classe ne peut pas être modifiée."}
                )
            check_year_not_archived(instance.academic_year)
            academic_year = instance.academic_year
        else:
            academic_year = attrs.get("academic_year")
            check_year_not_archived(academic_year)

        name = attrs.get("name", getattr(instance, "name", None))

        if academic_year and name:
            name_clean = name.strip()
            qs = Classroom.objects.filter(academic_year=academic_year, name__iexact=name_clean)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "Une classe avec ce nom existe déjà pour cette année scolaire."}
                )

        return attrs


class AcademicContextSerializer(serializers.Serializer):
    """Serializer pour le contexte scolaire global (/api/academics/context/)."""

    active_year = AcademicYearSerializer(allow_null=True)
    sequences = SequenceSerializer(many=True)
    current_sequence = SequenceSerializer(allow_null=True)
    levels = LevelSerializer(many=True)
