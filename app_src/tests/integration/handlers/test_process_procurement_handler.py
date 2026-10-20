"""Integration tests for process_procurement_handler.

Invokes the handler locally against real AWS S3.
Requires:
    - Valid AWS credentials
    - DATA_BUCKET_NAME env var pointing to an existing bucket
    - POWERTOOLS_TRACE_DISABLED=1 (recommended to avoid X-Ray errors locally)
"""

import os

import boto3
import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "integration-test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def s3_client():
    region = os.environ.get("AWS_REGION", "eu-west-1")
    return boto3.client("s3", region_name=region)


@pytest.fixture
def bucket_name():
    return os.environ["DATA_BUCKET_NAME"]


@pytest.fixture
def _upload_test_files(s3_client, bucket_name):
    """Upload test files to S3 before the test, clean up after."""
    test_keys = [
        "integration-test/P001/file1.pdf",
        "integration-test/P001/file2.csv",
    ]

    for key in test_keys:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"test content")

    yield test_keys

    # Cleanup
    for key in test_keys:
        s3_client.delete_object(Bucket=bucket_name, Key=key)


class TestProcessProcurementHandlerIntegration:
    def test_returns_files_from_s3(self, _upload_test_files, lambda_context, monkeypatch):
        """Handler lists real S3 objects matching the procurement prefix."""
        monkeypatch.setenv("DATA_BUCKET_NAME", os.environ["DATA_BUCKET_NAME"])

        # Reimport to pick up env
        import importlib

        import handlers.process_procurement_handler as mod

        importlib.reload(mod)

        event = {"procurementId": "integration-test/P001"}

        # When
        result = mod.handler(event, lambda_context)

        # Then
        assert result["status"] == "SUCCESS"
        assert result["procurementId"] == "integration-test/P001"
        assert sorted(result["attachments"]) == [
            "integration-test/P001/file1.pdf",
            "integration-test/P001/file2.csv",
        ]

    def test_returns_empty_when_no_matching_objects(self, lambda_context, monkeypatch):
        """Handler returns empty list when no S3 objects match the prefix."""
        monkeypatch.setenv("DATA_BUCKET_NAME", os.environ["DATA_BUCKET_NAME"])

        import importlib

        import handlers.process_procurement_handler as mod

        importlib.reload(mod)

        event = {"procurementId": "integration-test/nonexistent-prefix"}

        # When
        result = mod.handler(event, lambda_context)

        # Then
        assert result["status"] == "SUCCESS"
        assert result["attachments"] == []

    def test_raises_error_on_invalid_input(self, lambda_context, monkeypatch):
        """Handler raises ValueError on invalid payload."""
        monkeypatch.setenv("DATA_BUCKET_NAME", os.environ["DATA_BUCKET_NAME"])

        import importlib

        import handlers.process_procurement_handler as mod

        importlib.reload(mod)

        event = {}

        with pytest.raises(ValueError, match="Payload validation failed"):
            mod.handler(event, lambda_context)
