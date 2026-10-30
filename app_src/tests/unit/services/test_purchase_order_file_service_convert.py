from unittest.mock import MagicMock, call, patch

import pytest

from models.po_file import PurchaseOrderFileStatus
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.conversion_service import ConversionService
from services.purchase_order_file_service import (
    BDA_COMPATIBLE_EXTENSIONS,
    CONVERTIBLE_EXTENSIONS,
    PurchaseOrderFileService,
)


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-data-bucket")


@pytest.fixture
def mock_file_repo():
    return MagicMock(spec=PurchaseOrderFileRepository)


@pytest.fixture
def mock_conversion_service():
    return MagicMock(spec=ConversionService)


@pytest.fixture(autouse=True)
def mock_logger():
    with patch("services.purchase_order_file_service.logger") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_metrics():
    with patch("services.purchase_order_file_service.metrics") as mocked:
        yield mocked


@pytest.fixture
def service(mock_file_repo, mock_conversion_service):
    return PurchaseOrderFileService(
        purchase_order_file_repository=mock_file_repo,
        conversion_service=mock_conversion_service,
    )


class TestExtensionConstants:
    def test_convertible_extensions_contains_expected_set(self):
        assert CONVERTIBLE_EXTENSIONS == {
            ".pptx",
            ".xlsx",
            ".ppt",
            ".xls",
            ".odp",
            ".ods",
            ".doc",
        }

    def test_bda_compatible_extensions_contains_expected_set(self):
        assert BDA_COMPATIBLE_EXTENSIONS == {
            ".pdf",
            ".tiff",
            ".tif",
            ".jpeg",
            ".jpg",
            ".png",
            ".docx",
        }


class TestPassthrough:
    @pytest.mark.parametrize(
        "filename",
        [
            "report.pdf",
            "scan.tiff",
            "scan.tif",
            "photo.jpeg",
            "photo.jpg",
            "image.png",
            "letter.docx",
        ],
    )
    def test_bda_compatible_passthrough_no_conversion(
        self, service, mock_file_repo, mock_conversion_service, filename
    ):
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file=filename
        )

        # Then
        assert result == filename
        mock_file_repo.update_status.assert_not_called()
        mock_conversion_service.convert_to_pdf.assert_not_called()

    def test_unknown_extension_passthrough(
        self, service, mock_file_repo, mock_conversion_service
    ):
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file="data.csv"
        )

        # Then
        assert result == "data.csv"
        mock_file_repo.update_status.assert_not_called()
        mock_conversion_service.convert_to_pdf.assert_not_called()


class TestCaseInsensitiveExtension:
    @pytest.mark.parametrize(
        "filename",
        [
            "report.PDF",
            "report.Pdf",
        ],
    )
    def test_bda_compatible_uppercase_passthrough(
        self, service, mock_file_repo, mock_conversion_service, filename
    ):
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file=filename
        )

        assert result == filename
        mock_file_repo.update_status.assert_not_called()
        mock_conversion_service.convert_to_pdf.assert_not_called()

    def test_convertible_uppercase_triggers_conversion(
        self, service, mock_conversion_service
    ):
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file="PRESENTATION.PPTX"
        )

        # Then
        assert result == "PRESENTATION.pdf"
        mock_conversion_service.convert_to_pdf.assert_called_once()


class TestConversionWithStatusTracking:
    def test_success_flow_full_orchestration(
        self, service, mock_file_repo, mock_conversion_service
    ):
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file="presentation.pptx"
        )

        # Then
        assert result == "presentation.pdf"

        # Verify converter Lambda was invoked with S3 keys
        mock_conversion_service.convert_to_pdf.assert_called_once_with(
            source_key="HC1001/incoming/P001/presentation.pptx",
            destination_key="HC1001/incoming/P001/presentation.pdf",
        )

        # Verify status update order: IN_PROGRESS then COMPLETED
        assert mock_file_repo.update_status.call_count == 2
        mock_file_repo.update_status.assert_has_calls(
            [
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="presentation.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_IN_PROGRESS,
                ),
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="presentation.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_COMPLETED,
                ),
            ]
        )

    def test_failure_flow_sets_conversion_failed_and_reraises(
        self, service, mock_file_repo, mock_conversion_service, mock_metrics
    ):
        # Given
        mock_conversion_service.convert_to_pdf.side_effect = RuntimeError(
            "LibreOffice converter Lambda failed"
        )

        # When / Then
        with pytest.raises(RuntimeError, match="LibreOffice converter Lambda failed"):
            service.convert_po_file(
                hacat="HC1001", po_number="P001", po_file="presentation.pptx"
            )

        # Verify status update order: IN_PROGRESS then FAILED
        assert mock_file_repo.update_status.call_count == 2
        mock_file_repo.update_status.assert_has_calls(
            [
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="presentation.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_IN_PROGRESS,
                ),
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="presentation.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_FAILED,
                ),
            ]
        )

        # Verify metric was emitted
        mock_metrics.add_metric.assert_called_once()

    @pytest.mark.parametrize(
        "filename,expected_pdf",
        [
            ("report.xlsx", "report.pdf"),
            ("slides.ppt", "slides.pdf"),
            ("data.xls", "data.pdf"),
            ("deck.odp", "deck.pdf"),
            ("sheet.ods", "sheet.pdf"),
            ("letter.doc", "letter.pdf"),
        ],
    )
    def test_other_convertible_extensions_trigger_conversion(
        self, service, mock_conversion_service, filename, expected_pdf
    ):
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file=filename
        )

        # Then
        assert result == expected_pdf
        mock_conversion_service.convert_to_pdf.assert_called_once_with(
            source_key=f"HC1001/incoming/P001/{filename}",
            destination_key=f"HC1001/incoming/P001/{expected_pdf}",
        )

    def test_hierarchical_attachment_preserves_email_prefix(
        self, service, mock_conversion_service
    ):
        # Given a convertible EML attachment with a hierarchical filename
        # When
        result = service.convert_po_file(
            hacat="HC1001",
            po_number="P001",
            po_file="email1.eml/attach_1_devis.pptx",
        )

        # Then the directory prefix is preserved and only the suffix changes
        assert result == "email1.eml/attach_1_devis.pdf"
        mock_conversion_service.convert_to_pdf.assert_called_once_with(
            source_key="HC1001/incoming/P001/email1.eml/attach_1_devis.pptx",
            destination_key="HC1001/incoming/P001/email1.eml/attach_1_devis.pdf",
        )

    def test_flat_filename_conversion_unchanged(self, service, mock_conversion_service):
        # Given a convertible flat (non-email) filename
        # When
        result = service.convert_po_file(
            hacat="HC1001", po_number="P001", po_file="report.pptx"
        )

        # Then behavior is unchanged — flat name, no prefix
        assert result == "report.pdf"
        mock_conversion_service.convert_to_pdf.assert_called_once_with(
            source_key="HC1001/incoming/P001/report.pptx",
            destination_key="HC1001/incoming/P001/report.pdf",
        )

    def test_converter_lambda_failure_sets_conversion_failed(
        self, service, mock_file_repo, mock_conversion_service
    ):
        # Given
        mock_conversion_service.convert_to_pdf.side_effect = RuntimeError(
            "LibreOffice converter Lambda failed for 'missing.pptx': timeout"
        )

        # When / Then
        with pytest.raises(RuntimeError, match="timeout"):
            service.convert_po_file(
                hacat="HC1001", po_number="P001", po_file="missing.pptx"
            )

        # Status should go IN_PROGRESS then FAILED
        assert mock_file_repo.update_status.call_count == 2
        mock_file_repo.update_status.assert_has_calls(
            [
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="missing.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_IN_PROGRESS,
                ),
                call(
                    hacat="HC1001",
                    po_number="P001",
                    file_name="missing.pptx",
                    status=PurchaseOrderFileStatus.CONVERSION_FAILED,
                ),
            ]
        )
