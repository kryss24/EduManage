"""Utilisateur personnalisé : connexion par email, rôle et école de rattachement.

L'authentification (JWT), le hachage avancé, le verrouillage de compte, etc.
ne font pas partie de ce ticket et seront traités au ticket SCRUM-8.
"""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ]{8,15}$",
    message=(
        "Le numéro de téléphone doit contenir entre 8 et 15 chiffres "
        "(espaces autorisés, « + » initial optionnel)."
    ),
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = User.Role.SUPER_ADMIN
        extra_fields["school"] = None
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super administrateur"
        SCHOOL_ADMIN = "SCHOOL_ADMIN", "Administrateur d'école"
        TEACHER = "TEACHER", "Enseignant"
        PARENT = "PARENT", "Parent"
        CASHIER = "CASHIER", "Caissier"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # `unique=True` satisfait la vérification système de Django pour le
    # USERNAME_FIELD ; l'unicité réellement appliquée (insensible à la casse)
    # est portée par la contrainte `user_email_lower_unique` ci-dessous.
    email = models.EmailField("email", max_length=254, unique=True)
    last_name = models.CharField("nom", max_length=150)
    first_name = models.CharField("prénom", max_length=150)
    phone = models.CharField("téléphone", max_length=20, blank=True, validators=[phone_validator])
    role = models.CharField("rôle", max_length=20, choices=Role.choices)
    school = models.ForeignKey(
        "tenants.School",
        verbose_name="école",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("accès admin", default=False)
    date_joined = models.DateTimeField("inscrit le", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_lower_unique"),
            models.CheckConstraint(
                condition=(
                    Q(role="SUPER_ADMIN", school__isnull=True)
                    | (~Q(role="SUPER_ADMIN") & Q(school__isnull=False))
                ),
                name="user_super_admin_has_no_school",
            ),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)
