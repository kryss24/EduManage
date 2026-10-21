import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.core.models import AuditLog
from tests.conftest import login

pytestmark = pytest.mark.django_db

PASSWORD = "Un-Mot-De-Passe-Superadmin-2026!"


def _configure(settings, email="superadmin@edumanage.test", password=PASSWORD):
    settings.SUPERADMIN_EMAIL = email
    settings.SUPERADMIN_PASSWORD = password
    settings.SUPERADMIN_NOM = "Administrateur"
    settings.SUPERADMIN_PRENOM = "Super"


def test_bootstrap_creates_super_admin_without_school(settings):
    _configure(settings)
    call_command("bootstrap_superadmin")

    user = User.objects.get(email="superadmin@edumanage.test")
    assert user.role == User.Role.SUPER_ADMIN
    assert user.school is None
    assert user.is_staff and user.is_superuser
    assert user.check_password(PASSWORD)


def test_bootstrap_is_idempotent_and_does_not_overwrite_password(settings):
    _configure(settings)
    call_command("bootstrap_superadmin")
    call_command("bootstrap_superadmin")  # deuxième exécution : aucun changement

    user = User.objects.get(email="superadmin@edumanage.test")
    assert User.objects.filter(email="superadmin@edumanage.test").count() == 1
    assert user.check_password(PASSWORD)


def test_bootstrap_second_run_does_not_change_password_even_if_env_changes(settings):
    _configure(settings)
    call_command("bootstrap_superadmin")

    _configure(settings, password="Un-Autre-Mot-De-Passe-2026!")
    call_command("bootstrap_superadmin")

    user = User.objects.get(email="superadmin@edumanage.test")
    assert user.check_password(PASSWORD)
    assert not user.check_password("Un-Autre-Mot-De-Passe-2026!")


def test_bootstrap_reset_password_flag_changes_password(settings):
    _configure(settings)
    call_command("bootstrap_superadmin")

    _configure(settings, password="Un-Autre-Mot-De-Passe-2026!")
    call_command("bootstrap_superadmin", "--reset-password")

    user = User.objects.get(email="superadmin@edumanage.test")
    assert user.check_password("Un-Autre-Mot-De-Passe-2026!")


def test_bootstrap_rejects_weak_password(settings):
    _configure(settings, password="short")
    with pytest.raises(CommandError):
        call_command("bootstrap_superadmin")
    assert not User.objects.filter(email="superadmin@edumanage.test").exists()


def test_bootstrap_rejects_placeholder_password(settings):
    _configure(settings, password="CHANGE_ME_with_a_strong_password")
    with pytest.raises(CommandError):
        call_command("bootstrap_superadmin")


def test_bootstrap_rejects_missing_email(settings):
    _configure(settings, email="")
    with pytest.raises(CommandError):
        call_command("bootstrap_superadmin")


def test_bootstrap_rejects_missing_password(settings):
    _configure(settings, password="")
    with pytest.raises(CommandError):
        call_command("bootstrap_superadmin")


def test_bootstrap_created_user_can_log_in(settings, api_client):
    _configure(settings)
    call_command("bootstrap_superadmin")

    response = login(api_client, "superadmin@edumanage.test", PASSWORD)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == User.Role.SUPER_ADMIN


def test_bootstrap_records_audit_entry(settings):
    _configure(settings)
    call_command("bootstrap_superadmin")
    assert AuditLog.objects.filter(action="superadmin_bootstrap").exists()


def test_bootstrap_never_logs_the_password(settings, security_caplog):
    _configure(settings, password="Un-Mot-De-Passe-Bien-Specifique-2026!")
    call_command("bootstrap_superadmin")
    assert "Un-Mot-De-Passe-Bien-Specifique-2026!" not in security_caplog.text
