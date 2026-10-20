"""ViewSet et URLconf de test pour `TenantScopedViewSetMixin` /
`TenantModelSerializer`, sans ajouter de CRUD métier en production.

N'est monté que via `@pytest.mark.urls("tests.urls_test")` (voir
`tests/urls_test.py`) : ne doit jamais être accessible en dehors de la
suite de tests (SCRUM-8 §7).
"""

from rest_framework.routers import SimpleRouter
from rest_framework.viewsets import ModelViewSet

from apps.academics.models import Level
from apps.core.tenancy import TenantModelSerializer, TenantScopedViewSetMixin


class LevelTestSerializer(TenantModelSerializer):
    class Meta:
        model = Level
        fields = ["id", "school", "name", "order"]


class LevelTestViewSet(TenantScopedViewSetMixin, ModelViewSet):
    queryset = Level.objects.all()
    serializer_class = LevelTestSerializer
    feature = "classrooms"


router = SimpleRouter()
router.register("levels", LevelTestViewSet, basename="level-test")

urlpatterns = router.urls
