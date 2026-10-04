"""
YET-211 (OPS-03): nothing created the evidence bucket, so a fresh install failed
with NoSuchBucket on the first browser upload. scripts.ensure_bucket creates it
idempotently. A fake client is used: no real network / S3.
"""

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from scripts.ensure_bucket import ensure_bucket


def _client_error(code: str, op: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "x"}}, op)


class FakeS3:
    def __init__(self, head_errors=(), create_error=None):
        self.head_errors = list(head_errors)
        self.create_error = create_error
        self.created: list[str] = []
        self.head_calls = 0

    def head_bucket(self, Bucket):
        self.head_calls += 1
        if self.head_errors:
            err = self.head_errors.pop(0)
            if err is not None:
                raise err

    def create_bucket(self, Bucket):
        if self.create_error:
            raise self.create_error
        self.created.append(Bucket)


def test_creates_bucket_when_missing():
    s3 = FakeS3(head_errors=[_client_error("404", "HeadBucket")])
    assert ensure_bucket(s3, "b") is True
    assert s3.created == ["b"]


def test_noop_when_bucket_exists():
    s3 = FakeS3()
    assert ensure_bucket(s3, "b") is False
    assert s3.created == []


def test_idempotent_second_run():
    s3 = FakeS3(head_errors=[_client_error("NoSuchBucket", "HeadBucket"), None])
    assert ensure_bucket(s3, "b") is True
    assert ensure_bucket(s3, "b") is False
    assert s3.created == ["b"]


def test_race_already_owned_is_not_an_error():
    s3 = FakeS3(
        head_errors=[_client_error("404", "HeadBucket")],
        create_error=_client_error("BucketAlreadyOwnedByYou", "CreateBucket"),
    )
    assert ensure_bucket(s3, "b") is False


def test_forbidden_is_not_treated_as_missing():
    s3 = FakeS3(head_errors=[_client_error("403", "HeadBucket")])
    with pytest.raises(ClientError):
        ensure_bucket(s3, "b")
    assert s3.created == []


def test_retries_while_endpoint_down_then_succeeds():
    down = EndpointConnectionError(endpoint_url="http://minio:9000")
    s3 = FakeS3(head_errors=[down, down, None])
    sleeps: list[float] = []
    assert ensure_bucket(s3, "b", retries=5, delay=1.0, sleep=sleeps.append) is False
    assert s3.head_calls == 3
    assert sleeps == [1.0, 1.0]


def test_gives_up_when_endpoint_stays_down():
    down = EndpointConnectionError(endpoint_url="http://minio:9000")
    s3 = FakeS3(head_errors=[down] * 3)
    with pytest.raises(EndpointConnectionError):
        ensure_bucket(s3, "b", retries=3, delay=0, sleep=lambda _: None)
    assert s3.created == []


def test_compose_minio_healthcheck_does_not_use_curl():
    """The chainguard minio image ships no curl; a curl healthcheck is always unhealthy."""
    from pathlib import Path

    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(encoding="utf-8")
    minio = compose.split("  minio:")[1].split("\nvolumes:")[0]
    assert "curl" not in minio
    assert "mc" in minio and "ready" in minio
