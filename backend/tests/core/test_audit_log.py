import pytest
from django.core.exceptions import ValidationError

from apps.core.models import AuditLog
from tests.factories import SchoolFactory, UserFactory


@pytest.mark.django_db
class TestAuditLog:
    def test_creation_is_valid(self):
        school = SchoolFactory()
        user = UserFactory(school=school)
        log = AuditLog.objects.create(
            school=school,
            user=user,
            action="create",
            entity_type="Student",
            entity_id="123",
        )
        assert log.pk
        assert "create" in str(log)

    def test_cannot_be_modified(self):
        log = AuditLog.objects.create(action="create", entity_type="Student", entity_id="1")
        log.action = "update"
        with pytest.raises(ValidationError):
            log.save()

    def test_cannot_be_deleted(self):
        log = AuditLog.objects.create(action="create", entity_type="Student", entity_id="1")
        with pytest.raises(ValidationError):
            log.delete()
