from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/academics/", include("apps.academics.api.urls")),
]

if settings.ADMIN_ENABLED:
    from django.contrib import admin

    urlpatterns.append(path("admin/", admin.site.urls))

if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="schema-docs",
        ),
    ]
