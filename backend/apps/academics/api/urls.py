"""Routage des endpoints /api/academics/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicContextView,
    AcademicYearViewSet,
    ClassroomViewSet,
    LevelViewSet,
    SequenceViewSet,
)

router = DefaultRouter()
router.register("years", AcademicYearViewSet, basename="academic-year")
router.register("sequences", SequenceViewSet, basename="sequence")
router.register("levels", LevelViewSet, basename="level")
router.register("classrooms", ClassroomViewSet, basename="classroom")

urlpatterns = [
    path("context/", AcademicContextView.as_view(), name="academic-context"),
    path("", include(router.urls)),
]
