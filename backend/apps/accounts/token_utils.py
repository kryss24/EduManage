"""Utilitaires autour des jetons JWT (hors flux de vue standard)."""

from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch


def register_outstanding_token(token, user) -> None:
    """Enregistre un refresh token tout juste émis (ou muté par rotation
    manuelle) dans la liste des jetons actifs.

    `djangorestframework-simplejwt` 5.3.x (version installée) n'a pas encore
    de méthode `Token.outstand()` : seul `RefreshToken.for_user()` enregistre
    automatiquement un `OutstandingToken`. Après une rotation manuelle
    (`set_jti()`/`set_exp()`/`set_iat()`), le nouveau jeton doit être
    enregistré explicitement, sinon il échapperait à
    `blacklist_all_outstanding_tokens` (changement de mot de passe).
    """
    OutstandingToken.objects.get_or_create(
        jti=token[api_settings.JTI_CLAIM],
        defaults={
            "user": user,
            "token": str(token),
            "created_at": token.current_time,
            "expires_at": datetime_from_epoch(token["exp"]),
        },
    )


def blacklist_all_outstanding_tokens(user) -> int:
    """Met en liste noire tous les refresh tokens encore valides de `user`.

    Utilisé par le changement de mot de passe : toute session ouverte sur
    un autre appareil doit être coupée. Recette documentée de
    `djangorestframework-simplejwt` (app `token_blacklist`).
    """
    count = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        count += int(created)
    return count
