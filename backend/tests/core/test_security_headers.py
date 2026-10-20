import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.middleware import SecurityHeadersMiddleware

pytestmark = pytest.mark.django_db


def test_security_headers_present_on_health_endpoint(client):
    response = client.get("/api/health/")

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"]
    assert response["Permissions-Policy"]
    assert response["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )


def test_security_headers_skip_non_api_paths():
    middleware = SecurityHeadersMiddleware(lambda request: HttpResponse())
    request = RequestFactory().get("/admin/")

    response = middleware(request)

    assert "Content-Security-Policy" not in response
    assert "Permissions-Policy" in response  # toujours posé, quel que soit le chemin


def test_security_headers_use_setdefault_and_never_override_an_existing_header():
    def get_response(request):
        response = HttpResponse()
        response["Content-Security-Policy"] = "default-src 'self'"
        return response

    middleware = SecurityHeadersMiddleware(get_response)
    request = RequestFactory().get("/api/whatever/")

    response = middleware(request)

    assert response["Content-Security-Policy"] == "default-src 'self'"
