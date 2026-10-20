"""Isolation applicative multi-tenant.

Socle réutilisé par tous les CRUD à venir (années, classes, élèves...) :
résolution de l'école de la requête, permission d'école active, mixin de
ViewSet et serializers filtrant systématiquement par école.
"""

import uuid

from rest_framework import permissions, serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.accounts.models import User
from apps.core.audit import record_audit

SCHOOL_HEADER = "X-School-Id"


class SchoolScopeError(Exception):
    """L'école de la requête ne peut pas être déterminée (→ 400)."""


def get_request_school(request):
    """Retourne l'école (`tenants.School`) sur laquelle porte la requête.

    - Pour tout rôle sauf SUPER_ADMIN : toujours `request.user.school`.
      Aucune autre source (en-tête, paramètre, corps) n'est jamais prise en
      compte : un utilisateur normal ne peut pas choisir une autre école.
    - Pour un SUPER_ADMIN : l'école est désignée par l'en-tête
      `X-School-Id` (UUID d'une école existante et active). Chaque accès
      réussi est journalisé (`superadmin_tenant_access`).

    Lève `SchoolScopeError` si l'école ne peut pas être déterminée ; le code
    appelant doit la traduire en réponse 400.
    """
    from apps.tenants.models import School  # import tardif : évite un cycle

    user = request.user
    if not getattr(user, "is_authenticated", False):
        raise SchoolScopeError("Authentification requise.")

    if user.role != User.Role.SUPER_ADMIN:
        if not user.school_id:
            raise SchoolScopeError("Aucune école n'est associée à ce compte.")
        return user.school

    header_value = request.headers.get(SCHOOL_HEADER)
    if not header_value:
        raise SchoolScopeError(
            f"L'en-tête {SCHOOL_HEADER} est obligatoire pour un super administrateur."
        )
    try:
        school_id = uuid.UUID(header_value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise SchoolScopeError("Identifiant d'école invalide.") from exc

    try:
        school = School.objects.get(pk=school_id, is_active=True)
    except School.DoesNotExist as exc:
        raise SchoolScopeError("École introuvable ou inactive.") from exc

    record_audit(
        request,
        action="superadmin_tenant_access",
        entity_type="School",
        entity_id=str(school.id),
        school=school,
    )
    return school


class SchoolIsActive(permissions.BasePermission):
    """Refuse l'accès si l'école de l'utilisateur authentifié est désactivée.

    Une école désactivée coupe immédiatement les accès de tous ses membres,
    même avec un token d'accès encore valide : `request.user` est rechargé
    depuis la base à chaque requête par `JWTAuthentication` (jamais depuis
    les claims du token), donc `user.school.is_active` reflète toujours
    l'état réel.
    """

    message = "Ce compte n'a plus accès à l'application."

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return True  # laissé à IsAuthenticated
        if user.role == User.Role.SUPER_ADMIN:
            return True
        return user.school is not None and user.school.is_active


class TenantScopedViewSetMixin:
    """Mixin pour ViewSets DRF opérant sur un `TenantModel`.

    - `get_queryset()` filtre toujours sur l'école de la requête.
    - `perform_create()` injecte cette même école, quoi que le corps de la
      requête ait pu envoyer.
    - Un objet d'une autre école renvoie 404 (jamais 403, pour ne pas en
      révéler l'existence) : le filtrage du queryset avant résolution de
      l'objet dans `get_object()` suffit à obtenir ce comportement.
    """

    def get_scoped_school(self):
        """École de la requête, résolue une seule fois par instance de vue
        (évite de journaliser deux fois l'accès SUPER_ADMIN pour une seule
        requête qui appellerait `get_queryset()` puis `perform_create()`)."""
        if not hasattr(self, "_scoped_school"):
            try:
                self._scoped_school = get_request_school(self.request)
            except SchoolScopeError as exc:
                raise DRFValidationError({"detail": str(exc)}) from exc
        return self._scoped_school

    def get_queryset(self):
        return super().get_queryset().for_school(self.get_scoped_school())

    def perform_create(self, serializer):
        serializer.save(school=self.get_scoped_school())


class TenantModelSerializer(serializers.ModelSerializer):
    """`ModelSerializer` pour un `TenantModel` : `school` toujours en
    lecture seule, jamais pris depuis le corps de la requête."""

    school = serializers.PrimaryKeyRelatedField(read_only=True)


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """`PrimaryKeyRelatedField` filtré sur l'école de la requête courante.

    Empêche de référencer un objet d'une autre école : une tentative se
    traduit par une 400 générique (DRF ne trouve pas l'objet dans le
    queryset filtré), sans jamais révéler que l'objet existe ailleurs.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        if request is None:
            return queryset.none()
        try:
            school = get_request_school(request)
        except SchoolScopeError:
            return queryset.none()
        return queryset.for_school(school)
