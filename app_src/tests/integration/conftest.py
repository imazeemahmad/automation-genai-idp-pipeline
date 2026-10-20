"""Shared fixtures for integration tests.

These tests invoke the handler code locally (Python) against real AWS services (S3, etc.).
No mocking — requires valid AWS credentials and the following environment variables:
    - AWS_REGION: AWS region (default: eu-west-1)
    - DATA_BUCKET_NAME: The S3 bucket used by the process_procurement handler
"""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _check_env():
    """Skip integration tests if required env vars are not set."""
    if not os.environ.get("DATA_BUCKET_NAME"):
        pytest.skip("DATA_BUCKET_NAME not set — skipping integration tests")


@pytest.fixture
def lambda_context():
    """Minimal Lambda context for local handler invocation."""
    context = MagicMock()
    context.function_name = "integration-test"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:integration-test"
    context.aws_request_id = "integration-test-request-id"
    return context
