import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.academics.models import Sequence
from tests.factories import AcademicYearFactory, SequenceFactory


@pytest.mark.django_db
class TestSequence:
    def test_creation_is_valid_and_trimester_is_computed(self):
        year = AcademicYearFactory()
        seq = SequenceFactory(
            academic_year=year,
            number=3,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=10),
        )
        assert seq.trimester == 2

    @pytest.mark.parametrize("number,trimester", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3)])
    def test_trimester_for_each_sequence_number(self, number, trimester):
        year = AcademicYearFactory()
        seq = Sequence(
            school=year.school,
            academic_year=year,
            number=number,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=1),
        )
        assert seq.trimester == trimester

    def test_number_unique_per_academic_year(self):
        year = AcademicYearFactory()
        SequenceFactory(
            academic_year=year,
            number=1,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=10),
        )
        with pytest.raises(IntegrityError):
            Sequence.objects.bulk_create(
                [
                    Sequence(
                        school=year.school,
                        academic_year=year,
                        number=1,
                        start_date=year.start_date + datetime.timedelta(days=50),
                        end_date=year.start_date + datetime.timedelta(days=60),
                    )
                ]
            )

    def test_number_must_be_between_1_and_6(self):
        year = AcademicYearFactory()
        with pytest.raises(IntegrityError):
            Sequence.objects.bulk_create(
                [
                    Sequence(
                        school=year.school,
                        academic_year=year,
                        number=7,
                        start_date=year.start_date,
                        end_date=year.start_date + datetime.timedelta(days=5),
                    )
                ]
            )

    def test_end_date_must_be_after_start_date(self):
        year = AcademicYearFactory()
        with pytest.raises(IntegrityError):
            Sequence.objects.bulk_create(
                [
                    Sequence(
                        school=year.school,
                        academic_year=year,
                        number=1,
                        start_date=year.start_date + datetime.timedelta(days=10),
                        end_date=year.start_date,
                    )
                ]
            )

    def test_no_overlap_within_same_academic_year(self):
        year = AcademicYearFactory()
        SequenceFactory(
            academic_year=year,
            number=1,
            start_date=year.start_date,
            end_date=year.start_date + datetime.timedelta(days=30),
        )
        with pytest.raises(IntegrityError):
            Sequence.objects.bulk_create(
                [
                    Sequence(
                        school=year.school,
                        academic_year=year,
                        number=2,
                        start_date=year.start_date + datetime.timedelta(days=20),
                        end_date=year.start_date + datetime.timedelta(days=40),
                    )
                ]
            )

    def test_overlap_allowed_across_different_academic_years(self):
        year1 = AcademicYearFactory()
        year2 = AcademicYearFactory()
        SequenceFactory(
            academic_year=year1,
            number=1,
            start_date=year1.start_date,
            end_date=year1.start_date + datetime.timedelta(days=30),
        )
        SequenceFactory(
            academic_year=year2,
            number=1,
            start_date=year2.start_date,
            end_date=year2.start_date + datetime.timedelta(days=30),
        )

    def test_dates_must_be_within_academic_year(self):
        year = AcademicYearFactory()
        seq = Sequence(
            school=year.school,
            academic_year=year,
            number=1,
            start_date=year.start_date - datetime.timedelta(days=5),
            end_date=year.start_date + datetime.timedelta(days=5),
        )
        with pytest.raises(ValidationError):
            seq.full_clean()
