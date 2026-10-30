# pylint: disable=duplicate-code
from unittest.mock import MagicMock, patch

import pytest

from services.purchase_order_file_service import PurchaseOrderFileService


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
    monkeypatch.setenv(
        "LIBREOFFICE_CONVERTER_LAMBDA_ARN",
        "arn:aws:lambda:eu-west-1:123456789:function:converter",
    )


@pytest.fixture
def mock_service():
    with patch(
        "handlers.convert_po_file_handler.purchase_order_file_service",
        spec=PurchaseOrderFileService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestConvertPoFileHandler:
    def test_returns_converted_filename_for_convertible_file(
        self, mock_service, lambda_context
    ):
        # Given
        mock_service.convert_po_file.return_value = "presentation.pdf"

        from handlers.convert_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "presentation.pptx",
        }

        # When
        result = handler(event, lambda_context)

        # Then — poFile stays the ORIGINAL (tracking key), processedFile is the converted PDF
        assert result["hacat"] == "HC1001"
        assert result["poNumber"] == "E002754388"
        assert result["poFile"] == "presentation.pptx"
        assert result["processedFile"] == "presentation.pdf"

        mock_service.convert_po_file.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            po_file="presentation.pptx",
        )

    def test_returns_original_filename_for_bda_compatible_file(
        self, mock_service, lambda_context
    ):
        # Given
        mock_service.convert_po_file.return_value = "document.pdf"

        from handlers.convert_po_file_handler import handler

        event = {
            "hacat": "HC1005",
            "poNumber": "E000024494",
            "poFile": "document.pdf",
        }

        # When
        result = handler(event, lambda_context)

        # Then — no conversion: poFile and processedFile are identical
        assert result["hacat"] == "HC1005"
        assert result["poNumber"] == "E000024494"
        assert result["poFile"] == "document.pdf"
        assert result["processedFile"] == "document.pdf"

        mock_service.convert_po_file.assert_called_once_with(
            hacat="HC1005",
            po_number="E000024494",
            po_file="document.pdf",
        )

    def test_raises_value_error_on_missing_hacat(self, mock_service, lambda_context):
        # Given
        from handlers.convert_po_file_handler import handler

        event = {
            "poNumber": "E002754388",
            "poFile": "presentation.pptx",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.convert_po_file.assert_not_called()

    def test_raises_value_error_on_missing_po_number(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.convert_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poFile": "presentation.pptx",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.convert_po_file.assert_not_called()

    def test_raises_value_error_on_missing_po_file(self, mock_service, lambda_context):
        # Given
        from handlers.convert_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.convert_po_file.assert_not_called()

    def test_propagates_service_exception(self, mock_service, lambda_context):
        # Given
        mock_service.convert_po_file.side_effect = RuntimeError(
            "LibreOffice conversion failed"
        )

        from handlers.convert_po_file_handler import handler

        event = {
            "hacat": "HC1001",
            "poNumber": "E002754388",
            "poFile": "presentation.pptx",
        }

        # When / Then
        with pytest.raises(RuntimeError, match="LibreOffice conversion failed"):
            handler(event, lambda_context)
