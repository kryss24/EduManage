"""AUTH-02 : la matrice de permissions doit correspondre exactement au
cahier des charges. La copie ci-dessous est écrite en dur, indépendamment
de `apps.accounts.features.FEATURE_MATRIX`, pour détecter une régression
dans le code plutôt que de se comparer à elle-même.
"""

import itertools

import pytest

from apps.accounts.features import FEATURE_MATRIX, access_level_for, level_satisfies
from apps.accounts.models import User

A, E, L, N = "A", "E", "L", "-"
ROLES = [
    User.Role.SUPER_ADMIN,
    User.Role.SCHOOL_ADMIN,
    User.Role.TEACHER,
    User.Role.PARENT,
    User.Role.CASHIER,
]

EXPECTED_MATRIX = {
    "tenants": {"SUPER_ADMIN": A, "SCHOOL_ADMIN": N, "TEACHER": N, "PARENT": N, "CASHIER": N},
    "school_settings": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": N,
        "PARENT": N,
        "CASHIER": N,
    },
    "classrooms": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": L,
        "PARENT": N,
        "CASHIER": N,
    },
    "students": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": L,
        "PARENT": L,
        "CASHIER": N,
    },
    "teachers": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": L,
        "PARENT": N,
        "CASHIER": N,
    },
    "grades": {"SUPER_ADMIN": A, "SCHOOL_ADMIN": A, "TEACHER": E, "PARENT": N, "CASHIER": N},
    "report_cards": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": L,
        "PARENT": L,
        "CASHIER": N,
    },
    "tuition_payments": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": N,
        "PARENT": L,
        "CASHIER": E,
    },
    "teacher_salaries": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": N,
        "PARENT": N,
        "CASHIER": E,
    },
    "financial_reports": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": N,
        "PARENT": N,
        "CASHIER": L,
    },
    "communications": {
        "SUPER_ADMIN": A,
        "SCHOOL_ADMIN": A,
        "TEACHER": E,
        "PARENT": L,
        "CASHIER": N,
    },
}


def test_AUTH_02_feature_matrix_has_exactly_the_expected_features():
    assert set(FEATURE_MATRIX.keys()) == set(EXPECTED_MATRIX.keys())


@pytest.mark.parametrize(
    "feature,role",
    list(itertools.product(EXPECTED_MATRIX.keys(), ROLES)),
)
def test_AUTH_02_feature_matrix_matches_cahier_des_charges(feature, role):
    expected = EXPECTED_MATRIX[feature][role]
    actual = access_level_for(role, feature)
    assert actual == expected, f"{feature}/{role} : attendu {expected!r}, obtenu {actual!r}"


@pytest.mark.parametrize(
    "granted,required,expected",
    [
        (A, A, True),
        (A, E, True),
        (A, L, True),
        (A, N, True),
        (E, A, False),
        (E, E, True),
        (E, L, True),
        (L, E, False),
        (L, L, True),
        (N, L, False),
        (N, N, True),
    ],
)
def test_AUTH_02_level_satisfies_is_a_total_order(granted, required, expected):
    assert level_satisfies(granted, required) is expected


def test_AUTH_02_unknown_feature_grants_no_access():
    assert access_level_for(User.Role.SUPER_ADMIN, "does_not_exist") == N
