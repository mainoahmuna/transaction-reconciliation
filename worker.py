"""Standalone worker that consumes SQS messages.

Simulates a Lambda-triggered-by-SQS or an ECS worker in real AWS.

Run it in its own terminal:

    python worker.py

It bootstraps Django so it can reuse the app's settings and models, then
polls the queue forever with the classic SQS loop:

    receive_message -> process -> delete_message

The business logic itself lives in core/reconcile.py (pure Python, no AWS),
so the same code is reused by the Step Functions Lambdas.
"""

import json
import os
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reconciler.settings")
django.setup()

from django.utils import timezone

from core.models import Mismatch, ReconciliationRun, Transaction
from core.reconcile import parse_transactions_csv, reconcile, source_from_filename
from core.s3 import download_file
from core.sqs import get_queue_url, get_sqs_client


def persist_transactions(parsed):
    """Upsert parsed transaction dicts so re-runs don't duplicate rows."""
    for txn in parsed:
        Transaction.objects.update_or_create(
            source=txn["source"],
            external_id=txn["external_id"],
            defaults={
                "amount": txn["amount"],
                "date": date.fromisoformat(txn["date"]),
                "description": txn["description"],
            },
        )


def process_message(body):
    run_id = body["run_id"]
    file_key = body["file_key"]
    print(f"[worker] received message: run_id={run_id} file_key={file_key}", flush=True)

    run = ReconciliationRun.objects.get(id=run_id)
    run.status = "processing"
    run.save(update_fields=["status"])

    try:
        text = download_file(file_key)
        source = source_from_filename(file_key)
        parsed = parse_transactions_csv(text, source)
        print(f"[worker] parsed {len(parsed)} {source} transactions", flush=True)

        persist_transactions(parsed)

        bank_txns = list(Transaction.objects.filter(source="bank"))
        ledger_txns = list(Transaction.objects.filter(source="ledger"))
        mismatches = reconcile(bank_txns, ledger_txns)
        for txn, reason in mismatches:
            Mismatch.objects.create(run=run, transaction=txn, reason=reason)

        run.status = "complete"
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at"])
        print(
            f"[worker] finished run_id={run_id}: {len(parsed)} parsed, "
            f"{len(mismatches)} mismatches -> status={run.status}",
            flush=True,
        )
        return {"parsed": len(parsed), "mismatches": len(mismatches)}
    except Exception as exc:
        run.status = "failed"
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at"])
        print(f"[worker] run_id={run_id} failed: {exc}", flush=True)
        raise


def main():
    client = get_sqs_client()
    queue_url = get_queue_url()
    print(f"[worker] polling {queue_url}", flush=True)

    while True:
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )
        messages = response.get("Messages", [])
        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                process_message(json.loads(message["Body"]))
            except Exception as exc:
                print(f"[worker] ERROR processing message: {exc}", flush=True)
            finally:
                # Delete on success AND on handled failure (the run is marked
                # failed so there is nothing left to retry). Only a hard crash
                # before this line leaves the message for SQS to redeliver.
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                print("[worker] deleted message from queue", flush=True)


if __name__ == "__main__":
    main()
