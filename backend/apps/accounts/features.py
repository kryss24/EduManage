"""Matrice unique des permissions par fonctionnalité et par rôle.

Source de vérité du cahier des charges : toute vérification d'accès (API,
tests, future interface) doit se baser sur `FEATURE_MATRIX` plutôt que sur
une logique dupliquée. Niveaux, du plus faible au plus fort :

- `NONE` (``-``)  : aucun accès.
- `READ` (``L``)  : lecture seule.
- `WRITE` (``E``) : lecture + écriture (création/modification/suppression).
- `ADMIN` (``A``) : administration complète (inclut lecture et écriture).

`A` ⊃ `E` ⊃ `L` ⊃ `-` : un niveau supérieur donne toujours les droits des
niveaux inférieurs (voir `level_satisfies`).
"""

from django.db import models

from apps.accounts.models import User


class AccessLevel(models.TextChoices):
    NONE = "-", "Aucun accès"
    READ = "L", "Lecture"
    WRITE = "E", "Écriture"
    ADMIN = "A", "Administration"


# Ordre croissant des niveaux, utilisé pour les comparaisons (`A` ⊃ `E` ⊃ `L` ⊃ `-`).
_LEVEL_ORDER = {
    AccessLevel.NONE: 0,
    AccessLevel.READ: 1,
    AccessLevel.WRITE: 2,
    AccessLevel.ADMIN: 3,
}

Role = User.Role

# Matrice du cahier des charges : {feature: {role: level}}.
FEATURE_MATRIX = {
    "tenants": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.NONE,
        Role.TEACHER: AccessLevel.NONE,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.NONE,
    },
    "school_settings": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.NONE,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.NONE,
    },
    "classrooms": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.READ,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.NONE,
    },
    "students": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.READ,
        Role.PARENT: AccessLevel.READ,
        Role.CASHIER: AccessLevel.NONE,
    },
    "teachers": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.READ,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.NONE,
    },
    "grades": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.WRITE,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.NONE,
    },
    "report_cards": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.READ,
        Role.PARENT: AccessLevel.READ,
        Role.CASHIER: AccessLevel.NONE,
    },
    "tuition_payments": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.NONE,
        Role.PARENT: AccessLevel.READ,
        Role.CASHIER: AccessLevel.WRITE,
    },
    "teacher_salaries": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.NONE,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.WRITE,
    },
    "financial_reports": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.NONE,
        Role.PARENT: AccessLevel.NONE,
        Role.CASHIER: AccessLevel.READ,
    },
    "communications": {
        Role.SUPER_ADMIN: AccessLevel.ADMIN,
        Role.SCHOOL_ADMIN: AccessLevel.ADMIN,
        Role.TEACHER: AccessLevel.WRITE,
        Role.PARENT: AccessLevel.READ,
        Role.CASHIER: AccessLevel.NONE,
    },
}

FEATURES = tuple(FEATURE_MATRIX.keys())


def level_satisfies(granted: str, required: str) -> bool:
    """`True` si le niveau `granted` couvre au moins le niveau `required`."""
    return _LEVEL_ORDER[granted] >= _LEVEL_ORDER[required]


def access_level_for(role: str, feature: str) -> str:
    """Niveau d'accès d'un rôle sur une fonctionnalité (``-`` si inconnue)."""
    return FEATURE_MATRIX.get(feature, {}).get(role, AccessLevel.NONE)


def permissions_for_role(role: str) -> dict:
    """Dictionnaire ``{feature: level}`` complet pour un rôle (renvoyé par l'API)."""
    return {
        feature: levels.get(role, AccessLevel.NONE) for feature, levels in FEATURE_MATRIX.items()
    }
