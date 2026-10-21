"""Les tests tournent avec un hasher rapide (MD5) pour la vitesse (voir
`config.settings.test`), mais ce test force temporairement les hashers
réels de production pour vérifier qu'un mot de passe est bien haché avec
Argon2 (premier hasher de la liste) en dehors de la suite de tests."""

import pytest
from django.test import override_settings

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PRODUCTION_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]


def test_real_password_hash_starts_with_argon2():
    # `UserFactory` hache déjà le mot de passe à la création (post-génération) :
    # sous les hashers de production, c'est donc Argon2 (premier de la liste)
    # qui est utilisé, sans avoir besoin de rappeler `set_password` nous-mêmes.
    with override_settings(PASSWORD_HASHERS=PRODUCTION_HASHERS):
        user = UserFactory()
    assert user.password.startswith("argon2$")


def test_existing_bcrypt_hash_still_verifies_even_though_argon2_is_first():
    from django.contrib.auth.hashers import BCryptSHA256PasswordHasher

    hasher = BCryptSHA256PasswordHasher()
    with override_settings(PASSWORD_HASHERS=PRODUCTION_HASHERS):
        user = UserFactory()
        user.password = hasher.encode("Un-Mot-De-Passe-2026!", hasher.salt())
        user.save(update_fields=["password"])
        assert user.check_password("Un-Mot-De-Passe-2026!") is True
