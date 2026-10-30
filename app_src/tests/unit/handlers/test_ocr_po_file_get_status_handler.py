from unittest.mock import MagicMock, patch

import pytest

from models.po_file import PurchaseOrderFileStatus
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
    monkeypatch.setenv("CEDL_BUCKET_NAME", "test-cedl-bucket")
    monkeypatch.setenv(
        "COUPA_CROSS_ACCOUNT_ROLE_ARN", "arn:aws:iam::123456789012:role/test-role"
    )
    monkeypatch.setenv(
        "CEDL_CROSS_ACCOUNT_ROLE_ARN", "arn:aws:iam::987654321098:role/test-cedl-role"
    )
    monkeypatch.setenv("SSM_PREFIX", "/test/prefix")
    monkeypatch.setenv("SSM_MAX_AGE", "300")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.ocr_po_file_get_status_handler.purchase_order_file_service",
        spec=PurchaseOrderFileService,
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
        "poFile": "document.pdf",
        "invocationArn": "arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
    }


class TestOcrPoFileGetStatusHandler:
    def test_returns_ocr_processing_status(self, mock_service, lambda_context):
        # Given
        mock_service.get_ocr_status.return_value = (
            PurchaseOrderFileStatus.OCR_PROCESSING
        )

        from handlers.ocr_po_file_get_status_handler import handler

        event = _valid_event()

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "status": "OCR_PROCESSING",
        }
        mock_service.get_ocr_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        )

    def test_returns_ocr_completed_status(self, mock_service, lambda_context):
        # Given
        mock_service.get_ocr_status.return_value = PurchaseOrderFileStatus.OCR_COMPLETED

        from handlers.ocr_po_file_get_status_handler import handler

        event = _valid_event()

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "status": "OCR_COMPLETED",
        }
        mock_service.get_ocr_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        )

    def test_returns_ocr_error_status(self, mock_service, lambda_context):
        # Given
        mock_service.get_ocr_status.return_value = PurchaseOrderFileStatus.OCR_FAILED

        from handlers.ocr_po_file_get_status_handler import handler

        event = _valid_event()

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "status": "OCR_FAILED",
        }
        mock_service.get_ocr_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        )

    def test_raises_value_error_on_missing_hacat(self, mock_service, lambda_context):
        # Given
        from handlers.ocr_po_file_get_status_handler import handler

        event = {
            "poNumber": "E002754388",
            "poFile": "document.pdf",
            "invocationArn": "arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.get_ocr_status.assert_not_called()

    def test_raises_value_error_on_missing_po_number(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.ocr_po_file_get_status_handler import handler

        event = {
            "hacat": "HC1001",
            "poFile": "document.pdf",
            "invocationArn": "arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.get_ocr_status.assert_not_called()

    def test_raises_value_error_on_missing_po_file(self, mock_service, lambda_context):
        # Given
        from handlers.ocr_po_file_get_status_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "invocationArn": "arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.get_ocr_status.assert_not_called()

    def test_raises_value_error_on_missing_invocation_arn(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.ocr_po_file_get_status_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "document.pdf",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.get_ocr_status.assert_not_called()

    def test_propagates_service_exception(self, mock_service, lambda_context):
        # Given
        mock_service.get_ocr_status.side_effect = RuntimeError("BDA call failed")

        from handlers.ocr_po_file_get_status_handler import handler

        event = _valid_event()

        # When / Then
        with pytest.raises(RuntimeError, match="BDA call failed"):
            handler(event, lambda_context)
