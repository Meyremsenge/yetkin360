"""
Create the evidence bucket in MinIO/S3 if it does not exist (YET-211).

Presigned POST URLs are signed offline, so a missing bucket only surfaces when
the browser uploads (NoSuchBucket). Run this once after `docker compose up -d`.
Idempotent: safe to run repeatedly. No bucket content or credentials are printed.

Usage: python -m scripts.ensure_bucket
"""

import sys
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.config import settings

_MISSING_CODES = {"404", "NoSuchBucket", "NotFound"}
_RACE_CODES = {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}


def ensure_bucket(client, bucket: str, retries: int = 5, delay: float = 2.0, sleep=time.sleep) -> bool:
    """Create `bucket` if missing. Returns True if created, False if it already existed.

    Retries only while the endpoint is unreachable (MinIO still starting).
    Other errors (e.g. 403 bad credentials) propagate: they are not "missing".
    """
    for attempt in range(retries):
        try:
            client.head_bucket(Bucket=bucket)
            return False
        except EndpointConnectionError:
            if attempt == retries - 1:
                raise
            sleep(delay)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in _MISSING_CODES:
                raise
            break
    try:
        client.create_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in _RACE_CODES:
            return False
        raise
    return True


def main() -> int:
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        # Fail fast: a wrong endpoint must not hang the setup script.
        config=Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}),
    )
    try:
        created = ensure_bucket(client, settings.s3_bucket)
    except (ClientError, EndpointConnectionError) as exc:
        print(f"HATA: bucket hazirlanamadi ({type(exc).__name__}).", file=sys.stderr)
        return 1
    print("Bucket olusturuldu." if created else "Bucket zaten var.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
