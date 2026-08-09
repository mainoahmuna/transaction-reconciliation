"""Standalone worker that consumes SQS messages.

Simulates a Lambda-triggered-by-SQS or an ECS worker in real AWS.

Run it in its own terminal:

    python worker.py

It bootstraps Django so it can reuse the app's settings and models, then
polls the queue forever with the classic SQS loop:

    receive_message -> process -> delete_message
"""

import json
import os
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reconciler.settings")
django.setup()

from django.utils import timezone

from core.models import ReconciliationRun
from core.sqs import get_queue_url, get_sqs_client


def process_message(body):
    run_id = body["run_id"]
    file_key = body["file_key"]
    print(f"[worker] received message: run_id={run_id} file_key={file_key}", flush=True)

    run = ReconciliationRun.objects.get(id=run_id)
    run.status = "processing"
    run.save(update_fields=["status"])

    time.sleep(2)  # simulate the heavy reconciliation work

    run.status = "complete"
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at"])
    print(f"[worker] finished run_id={run_id} -> status={run.status}", flush=True)


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
                print("[worker] leaving message in queue for retry", flush=True)
            else:
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                print("[worker] deleted message from queue", flush=True)


if __name__ == "__main__":
    main()
