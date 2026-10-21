"""Garde-fou : aucun serializer d'authentification n'expose `role`, `school`,
`is_staff` ou `is_superuser` en écriture (SCRUM-8 §5)."""

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    UserSummarySerializer,
)

FORBIDDEN_FIELDS = {"role", "school", "is_staff", "is_superuser"}


def test_login_serializer_has_no_privileged_fields():
    assert FORBIDDEN_FIELDS.isdisjoint(LoginSerializer().fields)


def test_change_password_serializer_has_no_privileged_fields():
    assert FORBIDDEN_FIELDS.isdisjoint(ChangePasswordSerializer().fields)


def test_user_summary_serializer_is_entirely_read_only():
    serializer = UserSummarySerializer()
    assert all(field.read_only for field in serializer.fields.values())
