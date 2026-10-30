from unittest.mock import MagicMock, call, patch

import pytest

from models.po_file import PurchaseOrderFileStatus
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.ocr_service import OcrService
from services.purchase_order_file_service import PurchaseOrderFileService


@pytest.fixture
def mock_po_file_repository():
    return MagicMock(spec=PurchaseOrderFileRepository)


@pytest.fixture
def mock_ocr_service():
    return MagicMock(spec=OcrService)


@pytest.fixture
def service(mock_po_file_repository, mock_ocr_service, monkeypatch):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    return PurchaseOrderFileService(
        purchase_order_file_repository=mock_po_file_repository,
        ocr_service=mock_ocr_service,
    )


class TestOcrPoFile:
    def test_nominal_case_updates_status_and_invokes_ocr(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        # Given
        mock_ocr_service.invoke.return_value = (
            "arn:aws:bedrock:us-east-1:123:invocation/job-789"
        )

        # When
        result = service.ocr_po_file(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            processed_file="document.pdf",
        )

        # Then
        assert result == "arn:aws:bedrock:us-east-1:123:invocation/job-789"

        mock_po_file_repository.update_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            file_name="document.pdf",
            status=PurchaseOrderFileStatus.OCR_PROCESSING,
        )

        mock_ocr_service.invoke.assert_called_once_with(
            input_s3_uri="s3://test-bucket/HC1001/incoming/E002754388/document.pdf",
            output_s3_uri="s3://test-bucket/HC1001/ocr-jobs/E002754388",
        )

    def test_tracks_original_but_sends_converted_file_to_bda(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """When a file was converted, status is tracked on the original
        filename while BDA receives the converted PDF."""
        # Given
        mock_ocr_service.invoke.return_value = (
            "arn:aws:bedrock:us-east-1:123:invocation/job-abc"
        )

        # When — original is .pptx, physical file is .pdf
        service.ocr_po_file(
            hacat="HC1001",
            po_number="E002754388",
            po_file="presentation.pptx",
            processed_file="presentation.pdf",
        )

        # Then — tracking uses the ORIGINAL filename
        mock_po_file_repository.update_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            file_name="presentation.pptx",
            status=PurchaseOrderFileStatus.OCR_PROCESSING,
        )

        # BDA receives the CONVERTED file
        mock_ocr_service.invoke.assert_called_once_with(
            input_s3_uri="s3://test-bucket/HC1001/incoming/E002754388/presentation.pdf",
            output_s3_uri="s3://test-bucket/HC1001/ocr-jobs/E002754388",
        )

    def test_updates_status_to_ocr_error_on_invocation_failure(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        # Given
        mock_ocr_service.invoke.side_effect = RuntimeError("BDA invocation failed")

        # When / Then
        with pytest.raises(RuntimeError, match="BDA invocation failed"):
            service.ocr_po_file(
                hacat="HC1001",
                po_number="E002754388",
                po_file="document.pdf",
                processed_file="document.pdf",
            )

        # Status should first be set to OCR_PROCESSING, then OCR_ERROR
        assert mock_po_file_repository.update_status.call_count == 2

        calls = mock_po_file_repository.update_status.call_args_list
        assert calls[0] == call(
            hacat="HC1001",
            po_number="E002754388",
            file_name="document.pdf",
            status=PurchaseOrderFileStatus.OCR_PROCESSING,
        )
        assert calls[1] == call(
            hacat="HC1001",
            po_number="E002754388",
            file_name="document.pdf",
            status=PurchaseOrderFileStatus.OCR_FAILED,
        )

    def test_constructs_correct_s3_uris(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        # Given
        mock_ocr_service.invoke.return_value = (
            "arn:aws:bedrock:us-east-1:123:invocation/job-001"
        )

        # When
        service.ocr_po_file(
            hacat="HC1005",
            po_number="P999",
            po_file="invoice.pdf",
            processed_file="invoice.pdf",
        )

        # Then
        mock_ocr_service.invoke.assert_called_once_with(
            input_s3_uri="s3://test-bucket/HC1005/incoming/P999/invoice.pdf",
            output_s3_uri="s3://test-bucket/HC1005/ocr-jobs/P999",
        )
