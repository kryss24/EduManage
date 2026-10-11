"""École (tenant) : chaque école est un client isolé du SaaS EduManage.

Les quotas associés aux formules (`plan`) seront appliqués par des services
applicatifs ultérieurement ; ce ticket ne pose que la structure de données.
"""

from django.db import models

from apps.core.models import TimeStampedModel


class School(TimeStampedModel):
    class Plan(models.TextChoices):
        STARTER = "STARTER", "Starter"
        STANDARD = "STANDARD", "Standard"
        PREMIUM = "PREMIUM", "Premium"

    name = models.CharField("nom", max_length=200)
    city = models.CharField("ville", max_length=100)
    logo = models.ImageField("logo", upload_to="schools/logos/", blank=True, null=True)
    plan = models.CharField("formule", max_length=20, choices=Plan.choices, default=Plan.STARTER)
    currency = models.CharField("devise", max_length=3, default="XAF")
    timezone = models.CharField("fuseau horaire", max_length=50, default="Africa/Douala")
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "école"
        verbose_name_plural = "écoles"
        ordering = ["name"]

    def __str__(self):
        return self.name
