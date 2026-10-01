"""
Storage service for evidence file upload URL generation.

PLAN 2.5 (YET-82, YET-83): MinIO presigned URL generation with content-type
allowlist, file size validation, rate limiting, and error handling.
"""

import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError, EndpointConnectionError

from app.core.config import settings
from app.core.errors import ApiError


# Content-type allowlist (AC-3)
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Extension mapping from content-type to file extension
CONTENT_TYPE_TO_EXT = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/png": "png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

# In-memory rate limiter: {talent_id: [(timestamp1, timestamp2, ...)]}
# Tracks request timestamps within the current minute window.
# Process restart clears this (accepted risk for MVP per atdd.md).
_rate_limit_counters: dict[str, list[float]] = {}


def validate_content_type(content_type: str) -> bool:
    """
    AC-3: Check if content_type is in the allowlist.

    Args:
        content_type: MIME type string (e.g., "application/pdf")

    Returns:
        True if allowed, False otherwise
    """
    return content_type in ALLOWED_CONTENT_TYPES


def validate_file_size(size_bytes: int) -> bool:
    """
    AC-4: Check if file size is within the 10MB limit.

    Args:
        size_bytes: File size in bytes

    Returns:
        True if <= 10MB, False otherwise
    """
    return size_bytes <= settings.evidence_max_size_bytes


def validate_filename(filename: str) -> bool:
    """
    AC-5: Check if filename is valid (non-empty, <= 255 chars).

    Note: Pydantic schema also validates this at request level.
    This function is for unit testing and potential reuse.

    Args:
        filename: File name string

    Returns:
        True if valid, False otherwise
    """
    return 1 <= len(filename) <= 255


def build_object_key(talent_id: str, filename: str, content_type: str) -> str:
    """
    AC-1, AC-S1: Build the object key for MinIO storage.

    Format: evidence/{talent_id}/{uuid}.{ext}
    - talent_id: From auth context, never from request body (AC-S1 elevation defense)
    - uuid: UUIDv7 for uniqueness
    - ext: Derived from content_type allowlist mapping

    Args:
        talent_id: Authenticated user's talent profile ID (from Principal)
        filename: Original filename — NOT used to derive the extension (that
            comes from content_type, see CONTENT_TYPE_TO_EXT) or otherwise
            included in the object key (avoids path traversal from user
            input). Kept as a parameter for API symmetry with the request
            schema and covered by existing tests; not currently read.
        content_type: MIME type (must be in allowlist)

    Returns:
        Object key string in format evidence/{talent_id}/{uuid7}.{ext}
    """
    from uuid6 import uuid7

    # Generate a new UUIDv7
    object_uuid = uuid7()

    # Determine extension from content_type
    ext = CONTENT_TYPE_TO_EXT.get(content_type, "bin")

    # Build the key
    object_key = f"evidence/{talent_id}/{object_uuid}.{ext}"
    return object_key


def check_rate_limit(talent_id: str) -> bool:
    """
    AC-S3: Enforce rate limit of 10 requests per minute per user.

    Maintains an in-memory counter with a sliding minute window.
    Request timestamps older than 60 seconds are purged.

    Args:
        talent_id: User's talent profile ID (from Principal)

    Returns:
        True if within limit (request allowed), False if exceeded (429 reject)

    Note:
        This is a simple in-memory implementation. Process restart clears counters.
        For MVP (single-VPS), this is acceptable per atdd.md Risks section.
    """
    now = time.time()
    window_start = now - 60  # 60-second window

    # Initialize counter for this talent_id if not present
    if talent_id not in _rate_limit_counters:
        _rate_limit_counters[talent_id] = []

    # Clean old timestamps outside the window
    _rate_limit_counters[talent_id] = [
        ts for ts in _rate_limit_counters[talent_id] if ts > window_start
    ]

    # Check if at limit (10 requests)
    if len(_rate_limit_counters[talent_id]) >= 10:
        return False

    # Record this request timestamp
    _rate_limit_counters[talent_id].append(now)
    return True


def generate_presigned_post(
    bucket: str,
    object_key: str,
    content_type: str,
    size_bytes: int,
    ttl: int,
) -> dict:
    """
    AC-1, AC-S2: Generate a presigned POST form data + policy for MinIO/S3.

    The POST policy enforces Content-Type and Content-Length constraints
    (AC-S2 tampering defense). Client must POST with exact content-type
    and size, or the signature will be invalid.

    Args:
        bucket: S3 bucket name
        object_key: Object key (e.g., evidence/{talent_id}/{uuid}.{ext})
        content_type: MIME type (from allowlist)
        size_bytes: Declared file size
        ttl: Time-to-live in seconds (typically 900 = 15 min)

    Returns:
        dict: {
            "url": "https://minio.../bucket",
            "fields": {
                "key": object_key,
                "policy": "...",
                "x-amz-signature": "...",
                "x-amz-credential": "...",
                ...
            }
        }

    Raises:
        botocore.exceptions.EndpointConnectionError: If S3 unreachable (→ 503)
        botocore.exceptions.ConnectTimeoutError: If S3 timeout (→ 503)
    """
    # Create S3 client configured for MinIO
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )

    # Generate presigned POST form data with Content-Type and Content-Length constraints
    # AC-S2: Tampering defense via policy binding to declared values
    # content-length-range enforces exact file size (min == max == size_bytes)
    presigned_post = s3_client.generate_presigned_post(
        Bucket=bucket,
        Key=object_key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", size_bytes, size_bytes],
        ],
        ExpiresIn=ttl,
    )

    return presigned_post


def fetch_object_bytes(bucket: str, object_key: str, max_bytes: int) -> bytes | None:
    """
    YET-195: Read an object (at most max_bytes + 1 bytes) for content inspection.

    Network call — only the outbox worker calls this, never a request handler or
    anything inside an open transaction. Returns None if the object does not exist.
    Other storage errors propagate so the outbox retries the row.
    """
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2}),
    )
    try:
        response = s3_client.get_object(Bucket=bucket, Key=object_key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return None
        raise
    body = response["Body"]
    try:
        # +1 byte so an oversized object is detectable without reading it all.
        return body.read(max_bytes + 1)
    finally:
        body.close()


def generate_presigned_get_url(
    bucket: str,
    object_key: str,
    ttl: int,
) -> str:
    """
    AC-5, AC-10: Generate a presigned GET URL for evidence download.

    Downloads must be short-lived (TTL = 300 seconds, 5 minutes) and require
    ownership/scan_status validation at the endpoint layer (URL generation
    does not substitute for authorization checks).

    Args:
        bucket: S3 bucket name
        object_key: Object key (e.g., evidence/{talent_id}/{uuid}.{ext})
        ttl: Time-to-live in seconds (typically 300 = 5 min)

    Returns:
        str: Presigned GET URL (HTTPS)

    Raises:
        ApiError(503, "STORAGE_UNAVAILABLE") if S3 unreachable or timeout
    """
    # Create S3 client configured for MinIO
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )

    # Generate presigned GET URL with specified TTL
    try:
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=ttl,
        )
    except (EndpointConnectionError, ConnectTimeoutError):
        raise ApiError(
            503,
            "STORAGE_UNAVAILABLE",
            "Dosya depolama servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
        )

    return presigned_url
