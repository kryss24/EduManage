import pytest
from django.contrib.auth.hashers import check_password

from apps.accounts.models import User
from apps.core.models import AuditLog
from tests.conftest import login
from tests.factories import DEFAULT_TEST_PASSWORD, SchoolFactory, UserFactory

pytestmark = pytest.mark.django_db

GENERIC_ERROR = "Identifiants invalides."


def test_login_with_valid_credentials_returns_access_and_payload(api_client):
    user = UserFactory(role=User.Role.SCHOOL_ADMIN)

    response = login(api_client, user.email)

    assert response.status_code == 200
    body = response.json()
    assert "access" in body and body["access"]
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == User.Role.SCHOOL_ADMIN
    assert body["school"]["id"] == str(user.school_id)
    assert body["permissions"]["students"] == "A"
    assert "refresh" not in body
    assert "password" not in response.content.decode()


def test_login_response_never_exposes_password_hash(api_client):
    user = UserFactory()
    response = login(api_client, user.email)
    assert user.password not in response.content.decode()


def test_login_sets_httponly_refresh_cookie(api_client, settings):
    user = UserFactory()
    response = login(api_client, user.email)

    cookie = response.cookies[settings.AUTH_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["path"] == settings.AUTH_COOKIE_PATH
    assert cookie["samesite"] == settings.AUTH_COOKIE_SAMESITE


def test_login_with_wrong_password_returns_generic_error(api_client):
    user = UserFactory()
    response = login(api_client, user.email, "mot-de-passe-incorrect")
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


def test_login_with_unknown_email_returns_same_generic_error(api_client):
    response = login(api_client, "inconnu@example.test", "peu-importe-123456")
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


def test_login_unknown_email_and_wrong_password_responses_are_identical(api_client):
    user = UserFactory()
    r1 = login(api_client, user.email, "mauvais-mot-de-passe")
    r2 = login(api_client, "personne@example.test", "mauvais-mot-de-passe")
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_login_with_inactive_user_is_refused(api_client):
    user = UserFactory(is_active=False)
    response = login(api_client, user.email)
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


def test_login_with_disabled_school_is_refused_with_same_message(api_client):
    school = SchoolFactory(is_active=False)
    user = UserFactory(school=school)
    response = login(api_client, user.email)
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


def test_login_disabled_school_and_wrong_password_responses_are_identical(api_client):
    school = SchoolFactory(is_active=False)
    disabled_school_user = UserFactory(school=school)
    other_user = UserFactory()

    r1 = login(api_client, disabled_school_user.email)
    r2 = login(api_client, other_user.email, "mauvais-mot-de-passe")
    assert r1.json() == r2.json() == {"detail": GENERIC_ERROR}


def test_login_existing_token_is_refused_once_school_disabled(api_client):
    user = UserFactory()
    access = login(api_client, user.email).json()["access"]

    user.school.is_active = False
    user.school.save(update_fields=["is_active"])

    response = api_client.get("/api/auth/me/", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 403


def test_login_super_admin_has_no_school_in_payload(api_client):
    from tests.factories import SuperAdminFactory

    user = SuperAdminFactory()
    response = login(api_client, user.email)
    body = response.json()
    assert body["school"] is None
    assert body["permissions"]["tenants"] == "A"


def test_login_records_audit_entry_on_success(api_client):
    user = UserFactory()
    login(api_client, user.email)
    entry = AuditLog.objects.get(action="login_success")
    assert entry.user_id == user.id
    assert entry.school_id == user.school_id


def test_login_failure_does_not_create_audit_entry(api_client):
    user = UserFactory()
    login(api_client, user.email, "mauvais-mot-de-passe")
    assert not AuditLog.objects.filter(action="login_success").exists()


def test_login_lockout_after_five_consecutive_failures(api_client):
    user = UserFactory()
    for _ in range(5):
        response = login(api_client, user.email, "mauvais-mot-de-passe")
        assert response.status_code == 401

    response = login(api_client, user.email, "mauvais-mot-de-passe")
    assert response.status_code == 429
    assert response.json()["detail"] == GENERIC_ERROR

    # Même avec le bon mot de passe : le verrouillage porte sur (identifiant, IP).
    response = login(api_client, user.email, DEFAULT_TEST_PASSWORD)
    assert response.status_code == 429


def test_login_lockout_records_audit_entry(api_client):
    user = UserFactory()
    for _ in range(6):
        login(api_client, user.email, "mauvais-mot-de-passe")
    assert AuditLog.objects.filter(action="account_locked").exists()


def test_login_lockout_resets_on_successful_login(api_client):
    user = UserFactory()
    for _ in range(4):
        assert login(api_client, user.email, "mauvais-mot-de-passe").status_code == 401

    assert login(api_client, user.email, DEFAULT_TEST_PASSWORD).status_code == 200

    # Le compteur d'échecs a été remis à zéro par la connexion réussie :
    # 4 nouveaux échecs ne doivent donc pas déclencher de verrouillage.
    for _ in range(4):
        assert login(api_client, user.email, "mauvais-mot-de-passe").status_code == 401


def test_login_failed_attempt_does_not_leak_email_in_security_log(api_client, security_caplog):
    user = UserFactory(email="personne-sensible@example.test")
    login(api_client, user.email, "mauvais-mot-de-passe")
    assert "personne-sensible@example.test" not in security_caplog.text


def test_login_authenticate_runs_hasher_for_unknown_user(api_client, monkeypatch):
    """Mitigation de l'énumération par timing : `User().set_password(...)` est
    bien appelée (et donc le hasher réellement exécuté) même sans utilisateur."""
    calls = []
    original = User.set_password

    def spy(self, raw_password):
        calls.append(raw_password)
        return original(self, raw_password)

    monkeypatch.setattr(User, "set_password", spy)
    login(api_client, "personne@example.test", "peu-importe-123456")
    assert calls == ["peu-importe-123456"]


def test_password_hash_never_starts_unusable_after_normal_signup():
    # Garde-fou : s'assurer que `check_password` utilisé par Django ne court-circuite
    # pas silencieusement pour un utilisateur réel (hash "usable").
    user = UserFactory()
    assert check_password(DEFAULT_TEST_PASSWORD, user.password)
