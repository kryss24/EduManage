import datetime

import pytest
from django.db import IntegrityError

from apps.academics.models import AcademicYear
from tests.factories import AcademicYearFactory, SchoolFactory


@pytest.mark.django_db
class TestAcademicYear:
    def test_creation_is_valid(self):
        year = AcademicYearFactory(label="2025-2026")
        assert year.pk
        assert "2025-2026" in str(year)

    def test_label_unique_per_school(self):
        school = SchoolFactory()
        AcademicYearFactory(school=school, label="2025-2026")
        with pytest.raises(IntegrityError):
            AcademicYear.objects.bulk_create(
                [
                    AcademicYear(
                        school=school,
                        label="2025-2026",
                        start_date=datetime.date(2030, 9, 1),
                        end_date=datetime.date(2031, 6, 30),
                    )
                ]
            )

    def test_same_label_allowed_in_different_schools(self):
        AcademicYearFactory(label="2025-2026")
        AcademicYearFactory(label="2025-2026")

    def test_end_date_must_be_after_start_date(self):
        school = SchoolFactory()
        with pytest.raises(IntegrityError):
            AcademicYear.objects.bulk_create(
                [
                    AcademicYear(
                        school=school,
                        label="X",
                        start_date=datetime.date(2025, 9, 1),
                        end_date=datetime.date(2025, 8, 1),
                    )
                ]
            )

    def test_cannot_be_both_active_and_archived(self):
        school = SchoolFactory()
        with pytest.raises(IntegrityError):
            AcademicYear.objects.bulk_create(
                [
                    AcademicYear(
                        school=school,
                        label="X",
                        is_active=True,
                        is_archived=True,
                        start_date=datetime.date(2025, 9, 1),
                        end_date=datetime.date(2026, 6, 30),
                    )
                ]
            )

    def test_only_one_active_year_per_school(self):
        school = SchoolFactory()
        AcademicYearFactory(school=school, label="A", is_active=True)
        with pytest.raises(IntegrityError):
            AcademicYear.objects.bulk_create(
                [
                    AcademicYear(
                        school=school,
                        label="B",
                        is_active=True,
                        start_date=datetime.date(2030, 9, 1),
                        end_date=datetime.date(2031, 6, 30),
                    )
                ]
            )

    def test_two_schools_can_both_have_an_active_year(self):
        AcademicYearFactory(label="A", is_active=True)
        AcademicYearFactory(label="A2", is_active=True)

    def test_no_overlapping_years_within_same_school(self):
        school = SchoolFactory()
        AcademicYearFactory(
            school=school,
            label="A",
            start_date=datetime.date(2025, 9, 1),
            end_date=datetime.date(2026, 6, 30),
        )
        with pytest.raises(IntegrityError):
            AcademicYear.objects.bulk_create(
                [
                    AcademicYear(
                        school=school,
                        label="B",
                        start_date=datetime.date(2026, 1, 1),
                        end_date=datetime.date(2026, 12, 31),
                    )
                ]
            )

    def test_overlapping_dates_allowed_across_different_schools(self):
        start, end = datetime.date(2025, 9, 1), datetime.date(2026, 6, 30)
        AcademicYearFactory(label="A", start_date=start, end_date=end)
        AcademicYearFactory(label="A2", start_date=start, end_date=end)
