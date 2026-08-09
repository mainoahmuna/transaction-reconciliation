import json

import boto3
from django.conf import settings


def get_sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def get_queue_url():
    client = get_sqs_client()
    return client.get_queue_url(QueueName=settings.AWS_SQS_QUEUE_NAME)["QueueUrl"]


def enqueue_reconciliation(run_id, file_key):
    client = get_sqs_client()
    client.send_message(
        QueueUrl=get_queue_url(),
        MessageBody=json.dumps({"run_id": run_id, "file_key": file_key}),
    )
