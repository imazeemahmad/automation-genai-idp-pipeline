from unittest.mock import MagicMock, patch

import pytest

from services.purchase_order_file_service import PurchaseOrderFileService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")
    monkeypatch.setenv(
        "BDA_PROJECT_ARN",
        "arn:aws:bedrock:us-east-1:123456789012:data-automation-project/test",
    )
    monkeypatch.setenv(
        "BDA_PROFILE_ARN",
        "arn:aws:bedrock:us-east-1:123456789012:data-automation-profile/test",
    )
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.ocr_po_file_handler.purchase_order_file_service",
        spec=PurchaseOrderFileService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestOcrPoFileHandler:
    def test_returns_invocation_arn_on_success(self, mock_service, lambda_context):
        # Given
        mock_service.ocr_po_file.return_value = (
            "arn:aws:bedrock:us-east-1:123:invocation/abc-123"
        )

        from handlers.ocr_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "processedFile": "document.pdf",
        }

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "processedFile": "document.pdf",
            "invocationArn": "arn:aws:bedrock:us-east-1:123:invocation/abc-123",
        }
        mock_service.ocr_po_file.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            processed_file="document.pdf",
        )

    def test_raises_value_error_on_missing_hacat(self, mock_service, lambda_context):
        # Given
        from handlers.ocr_po_file_handler import handler

        event = {"poNumber": "E002754388", "poFile": "document.pdf"}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.ocr_po_file.assert_not_called()

    def test_raises_value_error_on_missing_po_number(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.ocr_po_file_handler import handler

        event = {"hacat": "HC1001", "poFile": "document.pdf"}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.ocr_po_file.assert_not_called()

    def test_raises_value_error_on_missing_po_file(self, mock_service, lambda_context):
        # Given
        from handlers.ocr_po_file_handler import handler

        event = {"hacat": "HC1001", "poNumber": "E002754388"}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.ocr_po_file.assert_not_called()

    def test_propagates_service_exception(self, mock_service, lambda_context):
        # Given
        mock_service.ocr_po_file.side_effect = RuntimeError("BDA call failed")

        from handlers.ocr_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "processedFile": "document.pdf",
        }

        # When / Then
        with pytest.raises(RuntimeError, match="BDA call failed"):
            handler(event, lambda_context)
