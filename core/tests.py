from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Mismatch, ReconciliationRun, Transaction


class TransactionModelTests(TestCase):
    def test_str_representation(self):
        tx = Transaction.objects.create(
            source="bank",
            external_id="TXN-1001",
            amount=Decimal("99.99"),
            date="2026-08-01",
        )
        self.assertEqual(str(tx), "bank - TXN-1001 (99.99)")

    def test_defaults(self):
        tx = Transaction.objects.create(
            source="ledger",
            external_id="TXN-1002",
            amount=Decimal("10.00"),
            date="2026-08-02",
        )
        self.assertEqual(tx.description, "")
        self.assertIsNotNone(tx.created_at)


class ReconciliationRunModelTests(TestCase):
    def test_default_status_is_pending(self):
        run = ReconciliationRun.objects.create()
        self.assertEqual(run.status, "pending")

    def test_str_representation(self):
        run = ReconciliationRun.objects.create(status="complete")
        self.assertEqual(str(run), f"Run {run.id} - complete")

    def test_source_file_key_defaults_to_blank(self):
        run = ReconciliationRun.objects.create()
        self.assertEqual(run.source_file_key, "")


class MismatchModelTests(TestCase):
    def test_str_representation(self):
        run = ReconciliationRun.objects.create()
        mismatch = Mismatch.objects.create(run=run, reason="amount mismatch")
        self.assertEqual(str(mismatch), f"Mismatch in {run.id}: amount mismatch")


class TransactionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/transactions/"

    def test_create_transaction(self):
        response = self.client.post(
            self.url,
            {
                "source": "bank",
                "external_id": "TXN-1001",
                "amount": "99.99",
                "date": "2026-08-01",
                "description": "coffee",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["external_id"], "TXN-1001")
        self.assertEqual(Transaction.objects.count(), 1)

    def test_create_transaction_requires_amount(self):
        response = self.client.post(
            self.url,
            {"source": "bank", "external_id": "TXN-1001", "date": "2026-08-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_transactions(self):
        Transaction.objects.create(
            source="bank", external_id="TXN-1001", amount="99.99", date="2026-08-01"
        )
        Transaction.objects.create(
            source="ledger", external_id="TXN-1002", amount="99.99", date="2026-08-01"
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_transaction(self):
        tx = Transaction.objects.create(
            source="bank", external_id="TXN-1001", amount="99.99", date="2026-08-01"
        )
        response = self.client.get(f"{self.url}{tx.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["external_id"], "TXN-1001")

    def test_update_transaction(self):
        tx = Transaction.objects.create(
            source="bank", external_id="TXN-1001", amount="99.99", date="2026-08-01"
        )
        response = self.client.patch(
            f"{self.url}{tx.id}/", {"amount": "199.99"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.amount, Decimal("199.99"))

    def test_delete_transaction(self):
        tx = Transaction.objects.create(
            source="bank", external_id="TXN-1001", amount="99.99", date="2026-08-01"
        )
        response = self.client.delete(f"{self.url}{tx.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Transaction.objects.count(), 0)


class ReconciliationRunAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/runs/"

    def test_list_runs(self):
        ReconciliationRun.objects.create()
        ReconciliationRun.objects.create(status="complete")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_runs_are_read_only(self):
        response = self.client.post(self.url, {"status": "complete"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MismatchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/mismatches/"

    def test_list_mismatches(self):
        run = ReconciliationRun.objects.create()
        Mismatch.objects.create(run=run, reason="amount mismatch")
        Mismatch.objects.create(run=run, reason="missing in ledger")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_mismatches_are_read_only(self):
        response = self.client.post(self.url, {"reason": "amount mismatch"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UploadFileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/upload/"

    def test_upload_requires_file(self):
        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("core.views.upload_file")
    def test_upload_creates_reconciliation_run(self, mock_upload):
        csv_file = SimpleUploadedFile("bank.csv", b"csv data", content_type="text/csv")
        response = self.client.post(self.url, {"file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_upload.called)
        self.assertEqual(ReconciliationRun.objects.count(), 1)
        run = ReconciliationRun.objects.get()
        self.assertEqual(response.data["id"], run.id)
        self.assertEqual(response.data["source_file_key"], run.source_file_key)
        self.assertTrue(run.source_file_key.startswith("uploads/"))
