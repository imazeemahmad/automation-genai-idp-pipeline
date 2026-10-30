from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-data-bucket")
    monkeypatch.setenv("CEDL_BUCKET_NAME", "test-cedl-bucket")
    monkeypatch.setenv("COUPA_ACCOUNT", "test_account")
    monkeypatch.setenv("COUPA_WAREHOUSE", "test_warehouse")
    monkeypatch.setenv("COUPA_ACCESS_ROLE_ARN", "test_role")
    monkeypatch.setenv(
        "COUPA_CROSS_ACCOUNT_ROLE_ARN",
        "arn:aws:iam::123456789012:role/test-cross-account-role",
    )
    monkeypatch.setenv(
        "CEDL_CROSS_ACCOUNT_ROLE_ARN", "arn:aws:iam::987654321098:role/test-cedl-role"
    )
    monkeypatch.setenv("COUPA_DATABASE", "test_database")
    monkeypatch.setenv("COUPA_SCHEMA", "test_schema")
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")
    monkeypatch.setenv("SSM_PREFIX", "/test/prefix")
    monkeypatch.setenv("SSM_MAX_AGE", "300")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "test")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.cedl_copy_po_files_handler.purchase_order_service",
        spec=PurchaseOrderService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestCedlCopyPoFilesHandler:
    def test_returns_downloaded_files_for_valid_request(
        self, mock_service, lambda_context
    ):
        # Given
        mock_service.download_po_files.return_value = ["1.pdf", "2.pdf"]

        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1005",
            "poNumber": "E002754388",
            "poFiles": [
                {
                    "filename": "1.pdf",
                    "s3path": "ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
                    "timestamp": "2025-07-09T15:44:16+00:00",
                    "originalFilename": "1.pdf",
                },
                {
                    "filename": "2.pdf",
                    "s3path": "ORDER_HEADER/2025/07/09/attachments/5396937/2.pdf",
                    "timestamp": "2025-07-09T15:44:16+00:00",
                    "originalFilename": "2.pdf",
                },
            ],
            "executionId": EXECUTION_ID,
        }

        # When
        result = handler(event, lambda_context)

        # Then
        assert result["hacat"] == "HC1005"
        assert result["poNumber"] == "E002754388"
        assert len(result["poFiles"]) == 2
        assert result["poFiles"][0] == {"filename": "1.pdf"}
        assert result["poFiles"][1] == {"filename": "2.pdf"}

        mock_service.download_po_files.assert_called_once()
        call_kwargs = mock_service.download_po_files.call_args[1]
        assert call_kwargs["hacat"] == "HC1005"
        assert call_kwargs["po_number"] == "E002754388"
        assert call_kwargs["execution_id"] == EXECUTION_ID

    def test_passes_po_files_with_correct_attributes(
        self, mock_service, lambda_context
    ):
        # Given
        mock_service.download_po_files.return_value = ["doc.pdf"]

        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E000024494",
            "poFiles": [
                {
                    "filename": "doc.pdf",
                    "s3path": "ORDER_HEADER/2025/11/25/attachments/24494/doc.pdf",
                    "timestamp": "2025-11-28T13:05:42+00:00",
                    "originalFilename": "doc.pdf",
                },
            ],
            "executionId": EXECUTION_ID,
        }

        # When
        handler(event, lambda_context)

        # Then
        call_args = mock_service.download_po_files.call_args[1]
        assert len(call_args["po_files"]) == 1
        assert call_args["po_files"][0].filename == "doc.pdf"
        assert (
            call_args["po_files"][0].s3path
            == "ORDER_HEADER/2025/11/25/attachments/24494/doc.pdf"
        )
        assert call_args["po_files"][0].timestamp == datetime(
            2025, 11, 28, 13, 5, 42, tzinfo=timezone.utc
        )

    def test_returns_empty_po_files_when_no_files(self, mock_service, lambda_context):
        # Given
        mock_service.download_po_files.return_value = []

        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1005",
            "poNumber": "E002754388",
            "poFiles": [],
            "executionId": EXECUTION_ID,
        }

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "hacat": "HC1005",
            "poNumber": "E002754388",
            "poFiles": [],
        }

    def test_raises_value_error_on_missing_po_number(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1005",
            "poFiles": [],
            "executionId": EXECUTION_ID,
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.download_po_files.assert_not_called()

    def test_raises_value_error_on_missing_hacat(self, mock_service, lambda_context):
        # Given
        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "poNumber": "E002754388",
            "poFiles": [],
            "executionId": EXECUTION_ID,
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.download_po_files.assert_not_called()

    def test_raises_value_error_on_missing_execution_id(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1005",
            "poNumber": "E002754388",
            "poFiles": [],
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.download_po_files.assert_not_called()

    def test_propagates_service_exception(self, mock_service, lambda_context):
        # Given
        mock_service.download_po_files.side_effect = RuntimeError("S3 copy failed")

        from handlers.cedl_copy_po_files_handler import handler

        event = {
            "hacat": "HC1005",
            "poNumber": "E002754388",
            "poFiles": [
                {
                    "filename": "1.pdf",
                    "s3path": "ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
                    "timestamp": "2025-07-09T15:44:16+00:00",
                    "originalFilename": "1.pdf",
                },
            ],
            "executionId": EXECUTION_ID,
        }

        # When / Then
        with pytest.raises(RuntimeError, match="S3 copy failed"):
            handler(event, lambda_context)
