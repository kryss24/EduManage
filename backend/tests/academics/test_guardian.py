import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from tests.factories import GuardianFactory, SchoolFactory, UserFactory


@pytest.mark.django_db
class TestGuardian:
    def test_creation_is_valid(self):
        guardian = GuardianFactory(first_name="Marie", last_name="Nkomo")
        assert "Marie Nkomo" in str(guardian)

    def test_linked_user_must_have_parent_role(self):
        school = SchoolFactory()
        user = UserFactory(school=school, role=User.Role.TEACHER)
        guardian = GuardianFactory.build(school=school, user=user)
        with pytest.raises(ValidationError):
            guardian.full_clean()

    def test_linked_user_must_belong_to_same_school(self):
        user = UserFactory(role=User.Role.PARENT)
        other_school = SchoolFactory()
        guardian = GuardianFactory.build(school=other_school, user=user)
        with pytest.raises(ValidationError):
            guardian.full_clean()

    def test_linked_user_with_parent_role_and_same_school_is_valid(self):
        school = SchoolFactory()
        user = UserFactory(school=school, role=User.Role.PARENT)
        guardian = GuardianFactory(school=school, user=user)
        assert guardian.user_id == user.id
