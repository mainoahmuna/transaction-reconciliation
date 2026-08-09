"""Shared helpers bundled into every Step Functions Lambda.

Each Lambda runs in its own container on LocalStack, so it cannot reach the
Django app or its localhost. Instead it talks to LocalStack's S3 (the only
stateful dependency the workflow needs) via the magic hostname
``localhost.localstack.cloud``, which resolves back to the LocalStack gateway.
"""

import json
import os

import boto3

ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost.localstack.cloud:4566")
BUCKET = os.environ.get("S3_BUCKET", "reconciliation-uploads")


def s3():
    return boto3.client("s3", endpoint_url=ENDPOINT)


def get_object(key):
    response = s3().get_object(Bucket=BUCKET, Key=key)
    return response["Body"].read().decode("utf-8")


def get_json(key):
    return json.loads(get_object(key))


def put_json(key, data):
    # Decimal amounts are not JSON-serializable, so str() them (e.g. "150.00").
    s3().put_object(Bucket=BUCKET, Key=key, Body=json.dumps(data, default=str))
