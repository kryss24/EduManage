import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.academics.models import Student
from apps.tenants.models import School
from tests.factories import SchoolFactory

VALID_PASSWORD = "Edu-Manage-Demo-2026!"


@pytest.fixture
def seed_password(monkeypatch):
    monkeypatch.setenv("SEED_USER_PASSWORD", VALID_PASSWORD)
    return VALID_PASSWORD


@pytest.mark.django_db
class TestSeedDemoData:
    @override_settings(DEBUG=True)
    def test_creates_expected_quantities(self, seed_password):
        call_command("seed_demo_data")
        assert School.objects.filter(name__startswith="[DEMO]").count() == 2
        assert Student.objects.filter(school__name__startswith="[DEMO]").count() == 15 * 7 + 15 * 6

    @override_settings(DEBUG=True)
    def test_rerun_creates_no_duplicates(self, seed_password):
        call_command("seed_demo_data")
        before = Student.objects.count()
        call_command("seed_demo_data")
        after = Student.objects.count()
        assert before == after

    def test_refuses_without_password(self, monkeypatch):
        monkeypatch.delenv("SEED_USER_PASSWORD", raising=False)
        with override_settings(DEBUG=True), pytest.raises(CommandError):
            call_command("seed_demo_data")

    def test_refuses_with_placeholder_password(self, monkeypatch):
        monkeypatch.setenv("SEED_USER_PASSWORD", "CHANGE_ME_avant_de_lancer_le_seed")
        with override_settings(DEBUG=True), pytest.raises(CommandError):
            call_command("seed_demo_data")

    def test_refuses_with_weak_password(self, monkeypatch):
        monkeypatch.setenv("SEED_USER_PASSWORD", "1234")
        with override_settings(DEBUG=True), pytest.raises(CommandError):
            call_command("seed_demo_data")

    def test_refuses_when_debug_is_false(self, seed_password):
        with pytest.raises(CommandError):
            call_command("seed_demo_data")

    def test_force_bypasses_debug_check(self, seed_password):
        call_command("seed_demo_data", force=True)
        assert School.objects.filter(name__startswith="[DEMO]").exists()

    @override_settings(DEBUG=True)
    def test_reset_only_removes_demo_data(self, seed_password):
        real_school = SchoolFactory(name="École Réelle")
        call_command("seed_demo_data")
        call_command("seed_demo_data", reset=True)
        assert not School.objects.filter(name__startswith="[DEMO]").exists()
        assert School.objects.filter(pk=real_school.pk).exists()

    @override_settings(DEBUG=True)
    def test_no_data_leaks_between_the_two_schools(self, seed_password):
        call_command("seed_demo_data")
        school_a = School.objects.get(name="[DEMO] École Les Palmiers")
        school_b = School.objects.get(name="[DEMO] École Horizon")
        matricules_a = set(
            Student.objects.filter(school=school_a).values_list("matricule", flat=True)
        )
        matricules_b = set(
            Student.objects.filter(school=school_b).values_list("matricule", flat=True)
        )
        assert matricules_a.isdisjoint(matricules_b)
        assert all(m.startswith("DEMO-A-") for m in matricules_a)
        assert all(m.startswith("DEMO-B-") for m in matricules_b)
