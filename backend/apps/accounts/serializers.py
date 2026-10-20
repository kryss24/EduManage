"""Serializers d'authentification.

Aucun de ces serializers n'expose `role`, `school`, `is_superuser` ou
`is_staff` en écriture : ces champs ne sont jamais modifiables via l'API
(voir SCRUM-8 §5).
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.features import permissions_for_role
from apps.accounts.models import User
from apps.tenants.models import School


class SchoolSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "currency", "timezone"]
        read_only_fields = fields


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Ancien mot de passe incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        validate_password(value, user=user)
        return value


def build_auth_payload(user):
    """Corps commun aux réponses de login, `/me/` et rafraîchissement de
    session : utilisateur, école (absente pour un SUPER_ADMIN) et
    permissions du rôle."""
    payload = {
        "user": UserSummarySerializer(user).data,
        "permissions": permissions_for_role(user.role),
    }
    if user.school_id:
        payload["school"] = SchoolSummarySerializer(user.school).data
    else:
        payload["school"] = None
    return payload
