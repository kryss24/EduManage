import pytest
from django.test import RequestFactory

from apps.core.audit import log_security_event, mask_email, record_audit
from apps.core.models import AuditLog
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "email,expected",
    [
        ("j@example.com", "j*@example.com"),
        ("jo@example.com", "j*@example.com"),
        ("jonathan@example.com", "j******n@example.com"),
        ("", "***"),
        ("not-an-email", "***"),
    ],
)
def test_mask_email(email, expected):
    assert mask_email(email) == expected


def test_record_audit_writes_expected_fields():
    user = UserFactory()
    request = RequestFactory().post("/api/auth/login/")
    request.user = user

    record_audit(request, action="login_success", entity_type="User", entity_id=str(user.id))

    entry = AuditLog.objects.get(action="login_success")
    assert entry.user == user
    assert entry.school == user.school
    assert entry.entity_type == "User"
    assert entry.entity_id == str(user.id)


def test_record_audit_allows_explicit_school_override():
    user = UserFactory()  # SUPER_ADMIN n'a pas d'école propre, mais ici un utilisateur normal
    other_school = UserFactory().school
    request = RequestFactory().get("/")
    request.user = user

    record_audit(request, action="superadmin_tenant_access", school=other_school)

    entry = AuditLog.objects.get(action="superadmin_tenant_access")
    assert entry.school == other_school


def test_record_audit_anonymous_request_has_no_user():
    from django.contrib.auth.models import AnonymousUser

    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    record_audit(request, action="account_locked", metadata={"email": "m***@example.com"})

    entry = AuditLog.objects.get(action="account_locked")
    assert entry.user is None
    assert entry.school is None


def test_log_security_event_never_crashes_on_reserved_logrecord_keys(security_caplog):
    request = RequestFactory().get("/")
    # "message" et "created" sont des attributs réservés de LogRecord : un
    # champ `extra` du même nom ferait planter le logger (voir le bug
    # corrigé dans bootstrap_superadmin).
    log_security_event("login_failed", request, email="m***@example.com")
    assert "login_failed" in security_caplog.text
