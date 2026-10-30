from unittest.mock import MagicMock, patch

import pytest

from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "test")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.cedl_export_po_output_data_handler.purchase_order_service",
        spec=PurchaseOrderService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


def _valid_event():
    return {
        "hacat": "HC1001",
        "poNumber": "E002754388",
        "timestamp": "20250709T154416Z",
        "executionId": EXECUTION_ID,
    }


class TestCedlExportPoOutputDataHandler:
    """Unit tests for the cedl_export_po_output_data_handler."""

    def test_valid_event_delegates_to_service_and_returns_success_response(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        result = handler(_valid_event(), lambda_context)

        assert result == {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "timestamp": "20250709T154416Z",
            "status": "EXPORT_COMPLETED",
        }
        mock_service.export_to_cedl.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250709T154416Z",
            execution_id=EXECUTION_ID,
        )

    def test_missing_hacat_raises_value_error(self, mock_service, lambda_context):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        del event["hacat"]

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_missing_po_number_raises_value_error(self, mock_service, lambda_context):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        del event["poNumber"]

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_missing_timestamp_raises_value_error(self, mock_service, lambda_context):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        del event["timestamp"]

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_missing_execution_id_raises_value_error(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        del event["executionId"]

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_whitespace_only_hacat_raises_value_error(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        event["hacat"] = "   "

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_whitespace_only_po_number_raises_value_error(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        event["poNumber"] = "  \t  "

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_whitespace_only_timestamp_raises_value_error(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        event["timestamp"] = "   "

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_invalid_timestamp_format_raises_value_error(
        self, mock_service, lambda_context
    ):
        from handlers.cedl_export_po_output_data_handler import handler

        event = _valid_event()
        event["timestamp"] = "2025-07-09T15:44:16+00:00"

        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.export_to_cedl.assert_not_called()

    def test_service_exception_raises(self, mock_service, lambda_context):
        from handlers.cedl_export_po_output_data_handler import handler

        mock_service.export_to_cedl.side_effect = RuntimeError("S3 write failed")

        with pytest.raises(RuntimeError, match="S3 write failed"):
            handler(_valid_event(), lambda_context)
