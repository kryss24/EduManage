"""Restrictions de visibilité au sein d'une école.

Réutilisées par les permissions et par les futurs CRUD métier (élèves,
classes...). `school` doit être fourni explicitement pour un
`SUPER_ADMIN` (qui n'a pas d'école propre) : en pratique, le résultat de
`apps.core.tenancy.get_request_school(request)`. Pour les autres rôles,
`school` par défaut à `user.school`.
"""

from apps.academics.models import (
    Classroom,
    ClassroomTeacher,
    Enrollment,
    Student,
    StudentGuardian,
    Teacher,
)
from apps.accounts.models import User


def classrooms_visible_to(user, school=None):
    school = school if school is not None else user.school
    queryset = Classroom.objects.for_school(school)

    if user.role in (User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN):
        return queryset

    if user.role == User.Role.TEACHER:
        teacher_ids = Teacher.objects.filter(user=user, school=school).values_list("id", flat=True)
        classroom_ids = ClassroomTeacher.objects.filter(teacher_id__in=teacher_ids).values_list(
            "classroom_id", flat=True
        )
        return queryset.filter(id__in=classroom_ids)

    # PARENT et CASHIER : aucun accès aux classes (matrice "classrooms" = "-").
    return queryset.none()


def students_visible_to(user, school=None):
    school = school if school is not None else user.school
    queryset = Student.objects.for_school(school)

    if user.role in (User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN, User.Role.CASHIER):
        return queryset

    if user.role == User.Role.PARENT:
        student_ids = StudentGuardian.objects.filter(
            guardian__user=user, school=school
        ).values_list("student_id", flat=True)
        return queryset.filter(id__in=student_ids)

    if user.role == User.Role.TEACHER:
        classroom_ids = classrooms_visible_to(user, school).values_list("id", flat=True)
        student_ids = Enrollment.objects.filter(classroom_id__in=classroom_ids).values_list(
            "student_id", flat=True
        )
        return queryset.filter(id__in=student_ids)

    return queryset.none()
