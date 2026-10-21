"""Journal d'audit (succès) et journalisation de sécurité (échecs).

Règle absolue : jamais de mot de passe, jeton ou cookie dans `metadata` ou
dans les logs. Les adresses email sont systématiquement masquées avant
d'être journalisées, qu'elles finissent dans `AuditLog` ou dans le logger
``security`` — ce dernier peut atterrir dans un agrégateur de logs moins
strictement contrôlé que la base de données.
"""

import logging

from axes.helpers import get_client_ip_address

from apps.core.models import AuditLog

security_logger = logging.getLogger("security")


def mask_email(email: str) -> str:
    """Masque une adresse email pour la journalisation (ex. ``j***n@ex.com``)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[0]}*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


def get_client_ip(request):
    if request is None:
        return None
    return get_client_ip_address(request)


def record_audit(
    request, action, entity_type="", entity_id="", metadata=None, school=None, user=None
):
    """Écrit une entrée dans `core.AuditLog`.

    `user` peut être forcé explicitement pour les vues qui résolvent
    l'utilisateur sans authentification DRF standard (ex. `logout`, qui lit
    le refresh token du cookie plutôt que `request.user`). Sinon,
    l'utilisateur authentifié de la requête est utilisé.

    `school` peut être forcé explicitement (ex. : école cible consultée par
    un SUPER_ADMIN via `X-School-Id`, différente de son propre rattachement
    qui est toujours `None`). Sinon, l'école de l'utilisateur est utilisée.
    """
    if user is None:
        request_user = getattr(request, "user", None)
        user = request_user if getattr(request_user, "is_authenticated", False) else None
    if school is None and user is not None:
        school = user.school

    AuditLog.objects.create(
        school=school,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        ip_address=get_client_ip(request),
        metadata=metadata or {},
    )


def log_security_event(event: str, request=None, **fields):
    """Journalise un évènement de sécurité qui n'aboutit pas forcément à une
    entrée d'audit (ex. tentative de connexion échouée dont on ne connaît
    pas l'utilisateur)."""
    security_logger.warning(
        event,
        extra={"event": event, "ip": get_client_ip(request), **fields},
    )
