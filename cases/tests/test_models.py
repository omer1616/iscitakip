from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from cases.models import CaseFile, Worker


class WorkerModelTests(TestCase):
    def test_employment_end_cannot_precede_start(self):
        worker = Worker(
            first_name="Ali",
            last_name="Kaya",
            employment_start=date(2025, 5, 1),
            employment_end=date(2025, 4, 1),
        )
        with self.assertRaises(ValidationError):
            worker.full_clean()


class CaseFileModelTests(TestCase):
    def test_total_receivables_ignores_empty_values(self):
        case_file = CaseFile(
            severance_amount=Decimal("1000.25"),
            notice_amount=None,
            other_receivables=Decimal("250.75"),
        )
        self.assertEqual(case_file.total_receivables, Decimal("1251.00"))

