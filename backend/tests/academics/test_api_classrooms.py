import pytest

from apps.academics.models import (
    Classroom,
)
from apps.accounts.models import User
from tests.factories.academics import (
    AcademicYearFactory,
    ClassroomFactory,
    ClassroomTeacherFactory,
    EnrollmentFactory,
    LevelFactory,
    SubjectFactory,
    TeacherFactory,
)
from tests.factories.accounts import UserFactory
from tests.factories.grades import GradeFactory
from tests.factories.tenants import SchoolFactory


@pytest.mark.django_db
def test_CLASSROOMS_crud_and_validations(auth_client):
    """CRUD des classes, unicité du nom par année,
    immuabilité de l'année scolaire et compteur d'élèves.
    """
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(school=school, label="2025-2026")
    level_cp = LevelFactory(school=school, name="CP", order=1)
    level_ce1 = LevelFactory(school=school, name="CE1", order=2)

    # 1. Création d'une classe
    res_create = client.post(
        "/api/academics/classrooms/",
        {
            "academic_year": str(year.id),
            "level": str(level_cp.id),
            "name": "SIL A",
        },
        format="json",
    )
    assert res_create.status_code == 201
    classroom_id = res_create.json()["id"]
    assert res_create.json()["name"] == "SIL A"
    assert res_create.json()["academic_year_label"] == "2025-2026"
    assert res_create.json()["level_name"] == "CP"
    assert res_create.json()["students_count"] == 0

    # 2. Ajout d'une inscription -> students_count = 1
    classroom = Classroom.objects.get(id=classroom_id)
    EnrollmentFactory(classroom=classroom, academic_year=year, school=school)

    res_detail = client.get(f"/api/academics/classrooms/{classroom_id}/")
    assert res_detail.status_code == 200
    assert res_detail.json()["students_count"] == 1

    # 3. Modification du niveau et du nom
    res_update = client.patch(
        f"/api/academics/classrooms/{classroom_id}/",
        {
            "name": "SIL B",
            "level": str(level_ce1.id),
        },
        format="json",
    )
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "SIL B"
    assert res_update.json()["level_name"] == "CE1"

    # 4. Tentative de modification de academic_year -> 400
    year2 = AcademicYearFactory(school=school, label="2026-2027")
    res_year_change = client.patch(
        f"/api/academics/classrooms/{classroom_id}/",
        {"academic_year": str(year2.id)},
        format="json",
    )
    assert res_year_change.status_code == 400
    assert "academic_year" in res_year_change.json()

    # 5. Unicité du nom par année insensible à la casse
    res_dup = client.post(
        "/api/academics/classrooms/",
        {
            "academic_year": str(year.id),
            "level": str(level_cp.id),
            "name": "sil b",  # Même nom en minuscules
        },
        format="json",
    )
    assert res_dup.status_code == 400
    assert "name" in res_dup.json()

    # 6. Même nom dans une année scolaire différente -> autorisé (201)
    res_diff_year = client.post(
        "/api/academics/classrooms/",
        {
            "academic_year": str(year2.id),
            "level": str(level_cp.id),
            "name": "SIL B",
        },
        format="json",
    )
    assert res_diff_year.status_code == 201

    # 7. Année archivée -> 409 sur création et modification
    archived_year = AcademicYearFactory(school=school, label="2023-2024", is_archived=True)
    res_archived_create = client.post(
        "/api/academics/classrooms/",
        {
            "academic_year": str(archived_year.id),
            "level": str(level_cp.id),
            "name": "Classe Ancienne",
        },
        format="json",
    )
    assert res_archived_create.status_code == 409
    assert res_archived_create.json()["code"] == "year_archived"

    archived_classroom = ClassroomFactory(
        academic_year=archived_year, level=level_cp, name="Archivée", school=school
    )
    res_archived_update = client.patch(
        f"/api/academics/classrooms/{archived_classroom.id}/",
        {"name": "Nouveau Nom"},
        format="json",
    )
    assert res_archived_update.status_code == 409
    assert res_archived_update.json()["code"] == "year_archived"


@pytest.mark.django_db
def test_CLASSROOMS_teacher_visibility(auth_client):
    """Un enseignant ne voit que les classes auxquelles il est affecté."""
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    teacher_user1 = UserFactory(role=User.Role.TEACHER, school=school)
    teacher_user2 = UserFactory(role=User.Role.TEACHER, school=school)

    teacher1 = TeacherFactory(school=school, user=teacher_user1)
    teacher2 = TeacherFactory(school=school, user=teacher_user2)

    year = AcademicYearFactory(school=school)
    level = LevelFactory(school=school)

    c1 = ClassroomFactory(school=school, academic_year=year, level=level, name="Classe 1")
    c2 = ClassroomFactory(school=school, academic_year=year, level=level, name="Classe 2")
    c3 = ClassroomFactory(school=school, academic_year=year, level=level, name="Classe 3")

    # Affectation enseignant 1 -> c1, enseignant 2 -> c2, c3 sans affectation
    ClassroomTeacherFactory(classroom=c1, teacher=teacher1, school=school)
    ClassroomTeacherFactory(classroom=c2, teacher=teacher2, school=school)

    client_t1 = auth_client(teacher_user1)

    # L'enseignant 1 ne voit que c1 dans la liste
    res_list = client_t1.get("/api/academics/classrooms/")
    assert res_list.status_code == 200
    results = res_list.json()["results"]
    assert len(results) == 1
    assert results[0]["id"] == str(c1.id)

    # L'enseignant 1 a accès au détail de c1
    res_c1 = client_t1.get(f"/api/academics/classrooms/{c1.id}/")
    assert res_c1.status_code == 200

    # L'enseignant 1 n'a pas accès à c2 ni c3 (404)
    res_c2 = client_t1.get(f"/api/academics/classrooms/{c2.id}/")
    assert res_c2.status_code == 404

    res_c3 = client_t1.get(f"/api/academics/classrooms/{c3.id}/")
    assert res_c3.status_code == 404

    # L'admin voit les 3 classes
    client_admin = auth_client(admin)
    res_admin_list = client_admin.get("/api/academics/classrooms/")
    assert res_admin_list.status_code == 200
    assert res_admin_list.json()["count"] == 3


@pytest.mark.django_db
def test_CLASSROOMS_delete_protection(auth_client):
    """La suppression d'une classe est protégée contre la présence
    d'inscriptions, matières, affectations et notes.
    """
    school = SchoolFactory()
    admin = UserFactory(role=User.Role.SCHOOL_ADMIN, school=school)
    client = auth_client(admin)

    year = AcademicYearFactory(school=school)
    level = LevelFactory(school=school)

    # 1. Classe vide -> suppression OK (204)
    empty_classroom = ClassroomFactory(school=school, academic_year=year, level=level)
    res_del_ok = client.delete(f"/api/academics/classrooms/{empty_classroom.id}/")
    assert res_del_ok.status_code == 204
    assert not Classroom.objects.filter(id=empty_classroom.id).exists()

    # 2. Classe avec inscriptions -> 409
    c_enroll = ClassroomFactory(school=school, academic_year=year, level=level)
    EnrollmentFactory(classroom=c_enroll, academic_year=year, school=school)
    res_del_enroll = client.delete(f"/api/academics/classrooms/{c_enroll.id}/")
    assert res_del_enroll.status_code == 409
    assert res_del_enroll.json()["code"] == "classroom_has_dependencies"

    # 3. Classe avec matières -> 409
    c_sub = ClassroomFactory(school=school, academic_year=year, level=level)
    SubjectFactory(classroom=c_sub, school=school)
    res_del_sub = client.delete(f"/api/academics/classrooms/{c_sub.id}/")
    assert res_del_sub.status_code == 409
    assert res_del_sub.json()["code"] == "classroom_has_dependencies"

    # 4. Classe avec affectation enseignant -> 409
    c_teach = ClassroomFactory(school=school, academic_year=year, level=level)
    teacher = TeacherFactory(school=school)
    ClassroomTeacherFactory(classroom=c_teach, teacher=teacher, school=school)
    res_del_teach = client.delete(f"/api/academics/classrooms/{c_teach.id}/")
    assert res_del_teach.status_code == 409
    assert res_del_teach.json()["code"] == "classroom_has_dependencies"

    # 5. Classe avec notes -> 409
    grade = GradeFactory(classroom=ClassroomFactory(school=school, academic_year=year, level=level))
    res_del_grade = client.delete(f"/api/academics/classrooms/{grade.subject.classroom.id}/")
    assert res_del_grade.status_code == 409
    assert res_del_grade.json()["code"] == "classroom_has_dependencies"

    # 6. Classe d'une année archivée -> 409 year_archived
    archived_year = AcademicYearFactory(school=school, is_archived=True)
    c_archived = ClassroomFactory(school=school, academic_year=archived_year, level=level)
    res_del_archived = client.delete(f"/api/academics/classrooms/{c_archived.id}/")
    assert res_del_archived.status_code == 409
    assert res_del_archived.json()["code"] == "year_archived"
