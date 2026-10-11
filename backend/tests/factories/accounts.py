import factory

from apps.accounts.models import User

from .tenants import SchoolFactory

DEFAULT_TEST_PASSWORD = "Test-Password-123!"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    first_name = "Prénom"
    last_name = factory.Sequence(lambda n: f"Utilisateur{n}")
    role = User.Role.SCHOOL_ADMIN
    school = factory.SubFactory(SchoolFactory)
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_TEST_PASSWORD)

    @factory.post_generation
    def _persist_password(obj, create, extracted, **kwargs):
        if create:
            obj.save(update_fields=["password"])


class SuperAdminFactory(UserFactory):
    role = User.Role.SUPER_ADMIN
    school = None
