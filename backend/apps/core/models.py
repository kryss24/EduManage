"""Modèles abstraits communs : horodatage et socle multi-tenant.

Ces classes abstraites sont le socle sur lequel reposent la plupart des
modèles métier (academics, grades...). Elles ne créent pas de table en
elles-mêmes.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    """Socle commun : clé primaire UUID et horodatage de création/modification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_school(self, school_or_id):
        """Filtre le queryset sur une école donnée (instance ou identifiant)."""
        school_id = getattr(school_or_id, "pk", school_or_id)
        return self.filter(school_id=school_id)


class TenantModel(TimeStampedModel):
    """Socle des modèles rattachés à une école (tenant).

    Le manager par défaut ne filtre rien automatiquement : le filtrage par
    requête (en fonction de l'utilisateur authentifié) sera mis en place avec
    les permissions au ticket SCRUM-8. `for_school()` reste disponible pour un
    filtrage explicite.

    `save()` appelle systématiquement `full_clean()` avant l'écriture en base
    afin que les invariants métier (dont la cohérence entre tenants) soient
    garantis quel que soit le point d'entrée (API, shell, script de seed).
    Les contraintes de base de données restent le dernier garde-fou,
    notamment pour les écritures qui contournent `save()` (ex. `bulk_create`).
    """

    school = models.ForeignKey(
        "tenants.School",
        verbose_name="école",
        on_delete=models.PROTECT,
        db_index=True,
        related_name="%(app_label)s_%(class)s_set",
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        for field in self._tenant_foreign_key_fields():
            related = getattr(self, field.name, None)
            if related is not None and related.school_id != self.school_id:
                errors[field.name] = ValidationError(
                    "Cet élément appartient à une autre école.",
                    code="cross_tenant",
                )
        if errors:
            raise ValidationError(errors)

    def _tenant_foreign_key_fields(self):
        """Clés étrangères locales pointant vers un autre `TenantModel`."""
        for field in self._meta.fields:
            if field.name == "school" or not isinstance(field, models.ForeignKey):
                continue
            related_model = field.related_model
            if isinstance(related_model, type) and issubclass(related_model, TenantModel):
                yield field


class AuditLog(models.Model):
    """Journal d'audit en ajout seulement.

    `metadata` ne doit jamais contenir de secrets (mots de passe, jetons) ni
    de données personnelles qui ne seraient pas déjà nécessaires à la
    compréhension de l'action auditée. L'écriture automatique dans ce
    journal (depuis les vues/services) sera mise en place aux tickets
    suivants ; ce modèle n'expose ici que sa structure et ses garanties
    d'immutabilité.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "tenants.School",
        verbose_name="école",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField("action", max_length=100)
    entity_type = models.CharField("type d'entité", max_length=100)
    entity_id = models.CharField("identifiant de l'entité", max_length=64)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    metadata = models.JSONField("métadonnées", default=dict, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "journal d'audit"
        verbose_name_plural = "journaux d'audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "created_at"], name="auditlog_school_created_idx")
        ]

    def __str__(self):
        return f"{self.action} – {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValidationError("Une entrée du journal d'audit ne peut pas être modifiée.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Une entrée du journal d'audit ne peut pas être supprimée.")
