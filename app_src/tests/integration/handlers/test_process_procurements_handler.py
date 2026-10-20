"""Integration tests for process_procurements_handler.

Invokes the handler locally against real AWS infrastructure.
The CoupaRepository currently generates data in-memory (no external API),
so these tests validate the full handler → service → repository chain.

Requires:
    - Valid AWS credentials
    - DATA_BUCKET_NAME env var (needed for handler module initialization)
    - POWERTOOLS_TRACE_DISABLED=1 (recommended)
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "integration-test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")
    monkeypatch.setenv("DATA_BUCKET_NAME", os.environ["DATA_BUCKET_NAME"])


@pytest.fixture
def handler():
    """Return a freshly reloaded handler function."""
    import importlib

    import handlers.process_procurements_handler as mod

    importlib.reload(mod)
    return mod.handler


class TestProcessProcurementsHandlerIntegration:
    def test_processes_multiple_ids(self, handler, lambda_context):
        """Handler returns procurement objects for each requested ID."""
        event = {"procurementIds": ["P001", "P002", "P003"]}

        result = handler(event, lambda_context)

        assert result["status"] == "SUCCESS"
        assert len(result["procurements"]) == 3
        assert result["procurements"][0] == {"id": "P001", "name": "P-P001"}
        assert result["procurements"][1] == {"id": "P002", "name": "P-P002"}
        assert result["procurements"][2] == {"id": "P003", "name": "P-P003"}

    def test_processes_single_id(self, handler, lambda_context):
        """Handler works with a single procurement ID."""
        event = {"procurementIds": ["ABC"]}

        result = handler(event, lambda_context)

        assert result["status"] == "SUCCESS"
        assert result["procurements"] == [{"id": "ABC", "name": "P-ABC"}]

    def test_returns_empty_when_no_ids(self, handler, lambda_context):
        """Handler returns empty list when procurementIds is absent."""
        event = {}

        result = handler(event, lambda_context)

        assert result["status"] == "SUCCESS"
        assert result["procurements"] == []

    def test_returns_empty_for_null_ids(self, handler, lambda_context):
        """Handler returns empty list when procurementIds is null."""
        event = {"procurementIds": None}

        result = handler(event, lambda_context)

        assert result["status"] == "SUCCESS"
        assert result["procurements"] == []

    def test_raises_error_on_invalid_type(self, handler, lambda_context):
        """Handler raises ValueError when procurementIds is not a list."""
        event = {"procurementIds": "not-a-list"}

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)
