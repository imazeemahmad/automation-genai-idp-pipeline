from unittest.mock import MagicMock

import pytest

from models.po_file import PurchaseOrderFile, PurchaseOrderFileStatus
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
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
def mock_po_file_objects_repository():
    return MagicMock(spec=PurchaseOrderFileObjectsRepository)


@pytest.fixture
def service(
    mock_po_file_repository,
    mock_ocr_service,
    mock_po_file_objects_repository,
    monkeypatch,
):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    return PurchaseOrderFileService(
        purchase_order_file_repository=mock_po_file_repository,
        ocr_service=mock_ocr_service,
        purchase_order_file_objects_repository=mock_po_file_objects_repository,
    )


def _make_po_file(status: PurchaseOrderFileStatus) -> PurchaseOrderFile:
    return PurchaseOrderFile(
        po_number="E002754388",
        filename="document.pdf",
        hacat="HC1001",
        status=status,
        timestamp="2025-07-09T00:00:00+00:00",
        original_filename="document.pdf",
    )


class TestGetOcrStatus:
    """Tests for PurchaseOrderFileService.get_ocr_status"""

    def test_db_terminal_completed_skips_bda_call(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Si le statut en base est OCR_COMPLETED, on ne call pas BDA."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_COMPLETED
        mock_ocr_service.get_status.assert_not_called()
        mock_po_file_repository.update_status.assert_not_called()

    def test_db_terminal_error_skips_bda_call(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Si le statut en base est OCR_ERROR, on ne call pas BDA."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_FAILED
        )

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_FAILED
        mock_ocr_service.get_status.assert_not_called()
        mock_po_file_repository.update_status.assert_not_called()

    def test_non_terminal_queries_bda_and_updates_on_change(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Si le statut en base est OCR_PROCESSING et BDA retourne OCR_ERROR, update DB."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_PROCESSING
        )
        mock_ocr_service.get_status.return_value = PurchaseOrderFileStatus.OCR_FAILED

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_FAILED
        mock_po_file_repository.update_status.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            file_name="document.pdf",
            status=PurchaseOrderFileStatus.OCR_FAILED,
        )

    def test_non_terminal_no_change_skips_update(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Si le statut en base est OCR_PROCESSING et BDA retourne aussi OCR_PROCESSING, pas d'update."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_PROCESSING
        )
        mock_ocr_service.get_status.return_value = (
            PurchaseOrderFileStatus.OCR_PROCESSING
        )

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_PROCESSING
        mock_po_file_repository.update_status.assert_not_called()

    def test_completed_calls_copy_ocr_result(
        self,
        service,
        mock_po_file_repository,
        mock_ocr_service,
        mock_po_file_objects_repository,
    ):
        """Si BDA retourne OCR_COMPLETED, appelle copy_ocr_result avec invocation_id extrait."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_PROCESSING
        )
        mock_ocr_service.get_status.return_value = PurchaseOrderFileStatus.OCR_COMPLETED

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:AWSACCNNNNNN:data-automation-invocation/ff79603c-591b-4e46-baf0-3823df3371d2",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_COMPLETED
        mock_po_file_objects_repository.copy_ocr_result.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            filename="document.pdf",
            invocation_id="ff79603c-591b-4e46-baf0-3823df3371d2",
        )

    def test_error_does_not_call_copy_ocr_result(
        self,
        service,
        mock_po_file_repository,
        mock_ocr_service,
        mock_po_file_objects_repository,
    ):
        """Si BDA retourne OCR_ERROR, ne copie pas le résultat."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_PROCESSING
        )
        mock_ocr_service.get_status.return_value = PurchaseOrderFileStatus.OCR_FAILED

        # When
        service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        mock_po_file_objects_repository.copy_ocr_result.assert_not_called()

    def test_ocr_service_exception_propagates(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Exception OcrService → exception propagée."""
        # Given
        mock_po_file_repository.get.return_value = _make_po_file(
            PurchaseOrderFileStatus.OCR_PROCESSING
        )
        mock_ocr_service.get_status.side_effect = RuntimeError(
            "BDA service unavailable"
        )

        # When / Then
        with pytest.raises(RuntimeError, match="BDA service unavailable"):
            service.get_ocr_status(
                hacat="HC1001",
                po_number="E002754388",
                po_file="document.pdf",
                invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
            )

        mock_po_file_repository.update_status.assert_not_called()

    def test_db_record_none_queries_bda(
        self, service, mock_po_file_repository, mock_ocr_service
    ):
        """Si pas d'enregistrement en base, on query BDA normalement."""
        # Given
        mock_po_file_repository.get.return_value = None
        mock_ocr_service.get_status.return_value = (
            PurchaseOrderFileStatus.OCR_PROCESSING
        )

        # When
        result = service.get_ocr_status(
            hacat="HC1001",
            po_number="E002754388",
            po_file="document.pdf",
            invocation_arn="arn:aws:bedrock:eu-west-1:123:invocation/abc-123",
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_PROCESSING
        mock_ocr_service.get_status.assert_called_once()
