import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from tests.factories import SchoolFactory, TeacherFactory, UserFactory


@pytest.mark.django_db
class TestTeacher:
    def test_creation_is_valid(self):
        teacher = TeacherFactory(first_name="Jean", last_name="Mballa")
        assert str(teacher) == "Jean Mballa"

    def test_linked_user_must_have_teacher_role(self):
        school = SchoolFactory()
        user = UserFactory(school=school, role=User.Role.PARENT)
        teacher = TeacherFactory.build(school=school, user=user)
        with pytest.raises(ValidationError):
            teacher.full_clean()

    def test_linked_user_must_belong_to_same_school(self):
        user = UserFactory(role=User.Role.TEACHER)
        other_school = SchoolFactory()
        teacher = TeacherFactory.build(school=other_school, user=user)
        with pytest.raises(ValidationError):
            teacher.full_clean()

    def test_linked_user_with_teacher_role_and_same_school_is_valid(self):
        school = SchoolFactory()
        user = UserFactory(school=school, role=User.Role.TEACHER)
        teacher = TeacherFactory(school=school, user=user)
        assert teacher.user_id == user.id
