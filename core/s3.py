import boto3
from django.conf import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def upload_file(file_obj, key):
    client = get_s3_client()
    client.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=file_obj.read(),
    )
    return key


def download_file(key):
    client = get_s3_client()
    response = client.get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
    )
    return response["Body"].read().decode("utf-8")
