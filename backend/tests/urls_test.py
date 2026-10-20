"""ROOT_URLCONF de test : API réelle + ViewSet de test tenancy.

N'est chargé que via `@pytest.mark.urls("tests.urls_test")` sur les tests
qui en ont besoin (voir `tests/core/test_tenancy.py`).
"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/test/", include("tests.tenancy_testkit")),
]
