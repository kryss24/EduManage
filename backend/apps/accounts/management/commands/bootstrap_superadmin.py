"""Crée (ou vérifie) le compte SUPER_ADMIN de départ, de façon idempotente.

Lu depuis l'environnement (`SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`,
`SUPERADMIN_NOM`, `SUPERADMIN_PRENOM`) plutôt que depuis des arguments de
ligne de commande : le mot de passe ne doit jamais apparaître dans
l'historique du shell ni dans les journaux de process.
"""

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.core.audit import mask_email, security_logger
from apps.core.models import AuditLog

# Préfixe de la valeur d'exemple de .env.example : son usage tel quel doit être refusé.
PLACEHOLDER_PASSWORD_PREFIX = "CHANGE_ME"


class Command(BaseCommand):
    help = (
        "Crée le compte SUPER_ADMIN de départ à partir de SUPERADMIN_EMAIL/"
        "SUPERADMIN_PASSWORD. Idempotente : n'écrase jamais un mot de passe "
        "existant sauf --reset-password."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Réinitialise le mot de passe d'un superadmin déjà existant.",
        )

    def handle(self, *args, **options):
        email = settings.SUPERADMIN_EMAIL.strip()
        password = settings.SUPERADMIN_PASSWORD

        if not email:
            raise CommandError("SUPERADMIN_EMAIL est obligatoire (voir .env.example).")
        if not password:
            raise CommandError("SUPERADMIN_PASSWORD est obligatoire (voir .env.example).")
        if password.startswith(PLACEHOLDER_PASSWORD_PREFIX):
            raise CommandError(
                "SUPERADMIN_PASSWORD a encore sa valeur d'exemple : définissez un vrai "
                "mot de passe avant de relancer cette commande."
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        if user is not None and not options["reset_password"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Le superadmin {email} existe déjà : aucune modification "
                    "(utilisez --reset-password pour changer son mot de passe)."
                )
            )
            return

        self._validate_password(password, email)

        created = user is None
        with transaction.atomic():
            if created:
                user = User(
                    email=email,
                    first_name=settings.SUPERADMIN_PRENOM,
                    last_name=settings.SUPERADMIN_NOM,
                    role=User.Role.SUPER_ADMIN,
                    school=None,
                    is_staff=True,
                    is_superuser=True,
                )
            user.set_password(password)
            user.save()
            self._record_bootstrap_audit(user, created)

        security_logger.info(
            "superadmin_bootstrap",
            extra={
                "event": "superadmin_bootstrap",
                "email": mask_email(email),
                "account_created": created,
            },
        )

        action = "créé" if created else "mot de passe réinitialisé pour"
        self.stdout.write(self.style.SUCCESS(f"Superadmin {action} : {email}."))

    @staticmethod
    def _validate_password(password, email):
        dummy_user = User(email=email, role=User.Role.SUPER_ADMIN)
        try:
            validate_password(password, user=dummy_user)
        except DjangoValidationError as exc:
            raise CommandError(
                "SUPERADMIN_PASSWORD ne respecte pas les règles de mot de passe : "
                + " ".join(exc.messages)
            ) from exc

    @staticmethod
    def _record_bootstrap_audit(user, created):
        AuditLog.objects.create(
            school=None,
            user=user,
            action="superadmin_bootstrap",
            entity_type="User",
            entity_id=str(user.id),
            metadata={"created": created},
        )
