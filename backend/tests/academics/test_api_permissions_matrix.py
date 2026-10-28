"""Tests de la matrice des droits pour les endpoints /api/academics/.

Paramétré : (5 rôles + anonyme) × 4 ressources × méthodes et actions.
Comparé à un tableau écrit en dur dans le test (401 / 403 / 200 / 201 / 204 attendus).
"""

import datetime

import pytest

from apps.accounts.models import User
from tests.factories import (
    AcademicYearFactory,
    ClassroomFactory,
    ClassroomTeacherFactory,
    LevelFactory,
    SchoolFactory,
    SequenceFactory,
    SuperAdminFactory,
    TeacherFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# Matrice attendue écrite en dur : (role_name, resource, action, expected_status)
# Rôles : "ANONYMOUS", "CASHIER", "PARENT", "TEACHER", "SCHOOL_ADMIN", "SUPER_ADMIN"
# Ressources : "years", "sequences", "levels", "classrooms"
# Actions : "list", "detail", "create", "update", "delete",
#           "activate", "archive", "generate_sequences"

ACTIONS_BY_RESOURCE = {
    "years": [
        "list",
        "detail",
        "create",
        "update",
        "delete",
        "activate",
        "archive",
        "generate_sequences",
    ],
    "sequences": ["list", "detail", "create", "update", "delete"],
    "levels": ["list", "detail", "create", "update", "delete"],
    "classrooms": ["list", "detail", "create", "update", "delete"],
}


def _get_expected_status(role: str, action: str) -> int:
    if role == "ANONYMOUS":
        return 401

    if role in ("CASHIER", "PARENT"):
        return 403

    if role == "TEACHER":
        if action in ("list", "detail"):
            return 200
        return 403

    if role in ("SCHOOL_ADMIN", "SUPER_ADMIN"):
        if action in ("list", "detail", "activate", "archive"):
            return 200
        if action in ("create", "generate_sequences"):
            return 201
        if action == "delete":
            return 204
        if action == "update":
            return 200

    raise ValueError(f"Combinaison inconnue {role} / {action}")


MATRIX_CASES = []
for role in ["ANONYMOUS", "CASHIER", "PARENT", "TEACHER", "SCHOOL_ADMIN", "SUPER_ADMIN"]:
    for resource, actions in ACTIONS_BY_RESOURCE.items():
        for action in actions:
            expected = _get_expected_status(role, action)
            MATRIX_CASES.append((role, resource, action, expected))


@pytest.mark.parametrize("role,resource,action,expected_status", MATRIX_CASES)
def test_AUTH_02_permissions_matrix(role, resource, action, expected_status, api_client, login_as):
    school = SchoolFactory()

    # Utilisateur de la requête
    if role == "ANONYMOUS":
        client = api_client
        headers = {}
    elif role == "SUPER_ADMIN":
        user = SuperAdminFactory()
        access = login_as(api_client, user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        client = api_client
        headers = {"X-School-Id": str(school.id)}
    else:
        user_role = getattr(User.Role, role)
        user = UserFactory(role=user_role, school=school)
        access = login_as(api_client, user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        client = api_client
        headers = {}

    # Données de test
    year = AcademicYearFactory(
        school=school, start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 6, 30)
    )
    sequence = SequenceFactory(
        academic_year=year,
        school=school,
        number=1,
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2025, 10, 15),
    )
    level = LevelFactory(school=school)
    classroom = ClassroomFactory(academic_year=year, level=level, school=school)

    # Si enseignant, s'assurer qu'il est affecté à la classe pour qu'il puisse la voir au détail
    if role == "TEACHER":
        teacher_profile = TeacherFactory(user=user, school=school)
        ClassroomTeacherFactory(classroom=classroom, teacher=teacher_profile)

    # Identifier l'URL et la méthode
    url = f"/api/academics/{resource}/"
    detail_map = {
        "years": year.id,
        "sequences": sequence.id,
        "levels": level.id,
        "classrooms": classroom.id,
    }
    detail_url = f"{url}{detail_map[resource]}/"

    if action == "list":
        resp = client.get(url, headers=headers)
    elif action == "detail":
        resp = client.get(detail_url, headers=headers)
    elif action == "create":
        payloads = {
            "years": {
                "label": "2030-2031",
                "start_date": "2030-09-01",
                "end_date": "2031-06-30",
            },
            "sequences": {
                "academic_year": str(year.id),
                "number": 2,
                "start_date": "2025-10-16",
                "end_date": "2025-11-30",
            },
            "levels": {"name": "SIL", "order": 99},
            "classrooms": {
                "academic_year": str(year.id),
                "level": str(level.id),
                "name": "SIL A",
            },
        }
        resp = client.post(url, payloads[resource], format="json", headers=headers)
    elif action == "update":
        payloads = {
            "years": {"label": "2025-2026 Bis"},
            "sequences": {"end_date": "2025-10-14"},
            "levels": {"name": "Niveau Modifié"},
            "classrooms": {"name": "Classe Modifiée"},
        }
        resp = client.patch(detail_url, payloads[resource], format="json", headers=headers)
    elif action == "delete":
        # Pour delete sur years/sequences/levels/classrooms, créer objets sans dépendances
        if resource == "years":
            del_year = AcademicYearFactory(
                school=school,
                start_date=datetime.date(2035, 1, 1),
                end_date=datetime.date(2035, 12, 31),
            )
            del_url = f"{url}{del_year.id}/"
        elif resource == "sequences":
            del_seq = SequenceFactory(
                academic_year=year,
                school=school,
                number=2,
                start_date=datetime.date(2025, 10, 16),
                end_date=datetime.date(2025, 11, 30),
            )
            del_url = f"{url}{del_seq.id}/"
        elif resource == "levels":
            del_lvl = LevelFactory(school=school)
            del_url = f"{url}{del_lvl.id}/"
        else:
            del_cls = ClassroomFactory(academic_year=year, level=level, school=school)
            if role == "TEACHER":
                ClassroomTeacherFactory(classroom=del_cls, teacher=teacher_profile)
            del_url = f"{url}{del_cls.id}/"
        resp = client.delete(del_url, headers=headers)
    elif action == "activate":
        target_year = AcademicYearFactory(
            school=school,
            start_date=datetime.date(2038, 1, 1),
            end_date=datetime.date(2038, 12, 31),
        )
        resp = client.post(f"/api/academics/years/{target_year.id}/activate/", headers=headers)
    elif action == "archive":
        target_year = AcademicYearFactory(
            school=school,
            start_date=datetime.date(2039, 1, 1),
            end_date=datetime.date(2039, 12, 31),
        )
        resp = client.post(f"/api/academics/years/{target_year.id}/archive/", headers=headers)
    elif action == "generate_sequences":
        gen_year = AcademicYearFactory(
            school=school,
            start_date=datetime.date(2040, 1, 1),
            end_date=datetime.date(2040, 12, 31),
        )
        periods = [
            {"start_date": "2040-01-01", "end_date": "2040-02-15"},
            {"start_date": "2040-02-16", "end_date": "2040-03-31"},
            {"start_date": "2040-04-01", "end_date": "2040-05-15"},
            {"start_date": "2040-05-16", "end_date": "2040-06-30"},
            {"start_date": "2040-07-01", "end_date": "2040-08-15"},
            {"start_date": "2040-08-16", "end_date": "2040-09-30"},
        ]
        resp = client.post(
            f"/api/academics/years/{gen_year.id}/generate-sequences/",
            periods,
            format="json",
            headers=headers,
        )

    assert resp.status_code == expected_status, (
        f"Échec pour {role} {resource} {action} : "
        f"{resp.status_code} != {expected_status} ({resp.content})"
    )
