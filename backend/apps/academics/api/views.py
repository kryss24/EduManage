"""Vues DRF pour le calendrier scolaire et la structure des classes."""

from django.db import transaction
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.academics.models import AcademicYear, Classroom, Level, Sequence
from apps.accounts.features import AccessLevel
from apps.accounts.permissions import HasFeatureAccess
from apps.accounts.scoping import classrooms_visible_to
from apps.core.audit import record_audit
from apps.core.pagination import StandardPagination
from apps.core.tenancy import SchoolIsActive, TenantScopedViewSetMixin, get_request_school

from .filters import AcademicYearFilter, ClassroomFilter, SequenceFilter, StrictOrderingFilter
from .serializers import (
    AcademicContextSerializer,
    AcademicYearSerializer,
    ClassroomSerializer,
    LevelSerializer,
    SequencePeriodSerializer,
    SequenceSerializer,
)
from .services import (
    YearArchivedError,
    activate_academic_year,
    archive_academic_year,
    delete_academic_year,
    delete_classroom,
    delete_level,
    delete_sequence,
    generate_sequences_for_year,
    get_academic_context,
)


@extend_schema_view(
    list=extend_schema(summary="Lister les années scolaires"),
    retrieve=extend_schema(summary="Détail d'une année scolaire"),
    create=extend_schema(summary="Créer une année scolaire"),
    update=extend_schema(summary="Modifier une année scolaire"),
    partial_update=extend_schema(summary="Modifier partiellement une année scolaire"),
    destroy=extend_schema(summary="Supprimer une année scolaire"),
)
class AcademicYearViewSet(TenantScopedViewSetMixin, ModelViewSet):
    """CRUD des années scolaires et actions d'activation/archivage/génération."""

    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"
    feature_required_levels = {
        "destroy": AccessLevel.ADMIN,
        "activate": AccessLevel.ADMIN,
        "archive": AccessLevel.ADMIN,
        "generate_sequences": AccessLevel.ADMIN,
    }
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, StrictOrderingFilter]
    filterset_class = AcademicYearFilter
    search_fields = ["label"]
    ordering_fields = ["start_date", "label"]
    ordering = ["-start_date"]

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(school=self.get_scoped_school())
            record_audit(
                self.request,
                action="create_academic_year",
                entity_type="AcademicYear",
                entity_id=instance.id,
                metadata={"label": instance.label},
                school=instance.school,
            )

    def perform_update(self, serializer):
        if serializer.instance.is_archived:
            raise YearArchivedError()
        with transaction.atomic():
            instance = serializer.save()
            record_audit(
                self.request,
                action="update_academic_year",
                entity_type="AcademicYear",
                entity_id=instance.id,
                metadata={"label": instance.label},
                school=instance.school,
            )

    def perform_destroy(self, instance):
        delete_academic_year(instance, request=self.request)

    @extend_schema(
        summary="Activer une année scolaire",
        request=None,
        responses={200: AcademicYearSerializer},
    )
    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        instance = self.get_object()
        activated = activate_academic_year(instance, request=request)
        serializer = self.get_serializer(activated)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Archiver une année scolaire",
        request=None,
        responses={200: AcademicYearSerializer},
    )
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        instance = self.get_object()
        archived = archive_academic_year(instance, request=request)
        serializer = self.get_serializer(archived)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Générer les 6 séquences d'une année scolaire",
        request=SequencePeriodSerializer(many=True),
        responses={201: SequenceSerializer(many=True)},
    )
    @action(detail=True, methods=["post"], url_path="generate-sequences")
    def generate_sequences(self, request, pk=None):
        instance = self.get_object()
        data = request.data
        if isinstance(data, dict) and "sequences" in data:
            periods = data["sequences"]
        elif isinstance(data, list):
            periods = data
        else:
            raise ValidationError(
                {"detail": "Le corps de la requête doit être une liste de 6 plages de dates."}
            )

        sequences = generate_sequences_for_year(instance, periods, request=request)
        serializer = SequenceSerializer(sequences, many=True, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(summary="Lister les séquences"),
    retrieve=extend_schema(summary="Détail d'une séquence"),
    create=extend_schema(summary="Créer une séquence"),
    update=extend_schema(summary="Modifier une séquence"),
    partial_update=extend_schema(summary="Modifier partiellement une séquence"),
    destroy=extend_schema(summary="Supprimer une séquence"),
)
class SequenceViewSet(TenantScopedViewSetMixin, ModelViewSet):
    """CRUD des séquences scolaires."""

    queryset = Sequence.objects.select_related("academic_year").all()
    serializer_class = SequenceSerializer
    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"
    feature_required_levels = {
        "destroy": AccessLevel.ADMIN,
    }
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, StrictOrderingFilter]
    filterset_class = SequenceFilter
    ordering_fields = ["number", "start_date"]
    ordering = ["number"]

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(school=self.get_scoped_school())
            record_audit(
                self.request,
                action="create_sequence",
                entity_type="Sequence",
                entity_id=instance.id,
                metadata={"number": instance.number},
                school=instance.school,
            )

    def perform_update(self, serializer):
        if serializer.instance.academic_year.is_archived:
            raise YearArchivedError()
        with transaction.atomic():
            instance = serializer.save()
            record_audit(
                self.request,
                action="update_sequence",
                entity_type="Sequence",
                entity_id=instance.id,
                metadata={"number": instance.number},
                school=instance.school,
            )

    def perform_destroy(self, instance):
        delete_sequence(instance, request=self.request)


@extend_schema_view(
    list=extend_schema(summary="Lister les niveaux"),
    retrieve=extend_schema(summary="Détail d'un niveau"),
    create=extend_schema(summary="Créer un niveau"),
    update=extend_schema(summary="Modifier un niveau"),
    partial_update=extend_schema(summary="Modifier partiellement un niveau"),
    destroy=extend_schema(summary="Supprimer un niveau"),
)
class LevelViewSet(TenantScopedViewSetMixin, ModelViewSet):
    """CRUD des niveaux scolaires."""

    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"
    feature_required_levels = {
        "destroy": AccessLevel.ADMIN,
    }
    pagination_class = StandardPagination
    filter_backends = [StrictOrderingFilter]
    ordering_fields = ["order", "name"]
    ordering = ["order"]

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(school=self.get_scoped_school())
            record_audit(
                self.request,
                action="create_level",
                entity_type="Level",
                entity_id=instance.id,
                metadata={"name": instance.name, "order": instance.order},
                school=instance.school,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            record_audit(
                self.request,
                action="update_level",
                entity_type="Level",
                entity_id=instance.id,
                metadata={"name": instance.name, "order": instance.order},
                school=instance.school,
            )

    def perform_destroy(self, instance):
        delete_level(instance, request=self.request)


@extend_schema_view(
    list=extend_schema(summary="Lister les classes"),
    retrieve=extend_schema(summary="Détail d'une classe"),
    create=extend_schema(summary="Créer une classe"),
    update=extend_schema(summary="Modifier une classe"),
    partial_update=extend_schema(summary="Modifier partiellement une classe"),
    destroy=extend_schema(summary="Supprimer une classe"),
)
class ClassroomViewSet(TenantScopedViewSetMixin, ModelViewSet):
    """CRUD des classes."""

    queryset = Classroom.objects.none()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"
    feature_required_levels = {
        "destroy": AccessLevel.ADMIN,
    }
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, StrictOrderingFilter]
    filterset_class = ClassroomFilter
    search_fields = ["name"]
    ordering_fields = ["name", "level__order"]
    ordering = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Classroom.objects.none()
        user = self.request.user
        school = self.get_scoped_school()
        qs = classrooms_visible_to(user, school=school)
        return (
            qs.select_related("academic_year", "level")
            .annotate(students_count=Count("enrollments", distinct=True))
            .distinct()
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(school=self.get_scoped_school())
            record_audit(
                self.request,
                action="create_classroom",
                entity_type="Classroom",
                entity_id=instance.id,
                metadata={"name": instance.name},
                school=instance.school,
            )

    def perform_update(self, serializer):
        if serializer.instance.academic_year.is_archived:
            raise YearArchivedError()
        with transaction.atomic():
            instance = serializer.save()
            record_audit(
                self.request,
                action="update_classroom",
                entity_type="Classroom",
                entity_id=instance.id,
                metadata={"name": instance.name},
                school=instance.school,
            )

    def perform_destroy(self, instance):
        delete_classroom(instance, request=self.request)


class AcademicContextView(APIView):
    """Retourne l'état synthétique du calendrier et de la structure pour l'école."""

    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"

    @extend_schema(
        summary="Contexte scolaire actif de l'école",
        responses={200: AcademicContextSerializer},
    )
    def get(self, request):
        school = get_request_school(request)
        context_data = get_academic_context(school)
        serializer = AcademicContextSerializer(context_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
