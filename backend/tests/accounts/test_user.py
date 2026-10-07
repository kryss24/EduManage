import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.models import User
from tests.factories import SchoolFactory, UserFactory


@pytest.mark.django_db
class TestUser:
    def test_email_is_normalized_to_lowercase(self):
        user = UserFactory(email="Jane.DOE@Example.TEST")
        assert user.email == "jane.doe@example.test"

    def test_email_uniqueness_is_case_insensitive_at_db_level(self):
        school = SchoolFactory()
        User.objects.bulk_create(
            [
                User(
                    email="person@example.test",
                    first_name="A",
                    last_name="A",
                    role=User.Role.SCHOOL_ADMIN,
                    school=school,
                )
            ]
        )
        with pytest.raises(IntegrityError):
            User.objects.bulk_create(
                [
                    User(
                        email="PERSON@EXAMPLE.TEST",
                        first_name="B",
                        last_name="B",
                        role=User.Role.SCHOOL_ADMIN,
                        school=school,
                    )
                ]
            )

    def test_super_admin_must_not_have_a_school_at_db_level(self):
        school = SchoolFactory()
        with pytest.raises(IntegrityError):
            User.objects.bulk_create(
                [
                    User(
                        email="bad@example.test",
                        first_name="A",
                        last_name="A",
                        role=User.Role.SUPER_ADMIN,
                        school=school,
                    )
                ]
            )

    def test_non_super_admin_must_have_a_school_at_db_level(self):
        with pytest.raises(IntegrityError):
            User.objects.bulk_create(
                [
                    User(
                        email="bad2@example.test",
                        first_name="A",
                        last_name="A",
                        role=User.Role.TEACHER,
                        school=None,
                    )
                ]
            )

    def test_phone_validator_rejects_invalid_numbers(self):
        user = UserFactory(phone="not-a-phone")
        with pytest.raises(ValidationError) as exc:
            user.full_clean()
        assert "phone" in exc.value.message_dict

    def test_phone_validator_accepts_valid_numbers(self):
        user = UserFactory(phone="+237 690010203")
        user.full_clean()

    def test_create_superuser_forces_role_and_no_school(self):
        user = User.objects.create_superuser(email="root@example.test", password="Strong-Pass-123!")
        assert user.role == User.Role.SUPER_ADMIN
        assert user.school is None
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.check_password("Strong-Pass-123!")

    def test_full_name_and_str(self):
        user = UserFactory(first_name="Jean", last_name="Mballa", email="jean@example.test")
        assert user.get_full_name() == "Jean Mballa"
        assert str(user) == "Jean Mballa <jean@example.test>"
