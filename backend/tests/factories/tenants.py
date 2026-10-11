import factory

from apps.tenants.models import School


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    name = factory.Sequence(lambda n: f"École Test {n}")
    city = "Douala"
    plan = School.Plan.STARTER
    currency = "XAF"
    timezone = "Africa/Douala"
    is_active = True
