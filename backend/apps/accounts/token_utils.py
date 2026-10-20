"""Utilitaires autour des jetons JWT (hors flux de vue standard)."""

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


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
