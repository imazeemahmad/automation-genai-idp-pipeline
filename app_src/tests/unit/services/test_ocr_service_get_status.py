from unittest.mock import MagicMock, patch

import pytest

from models.po_file import PurchaseOrderFileStatus
from services.ocr_service import OcrService


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv(
        "BDA_PROJECT_ARN", "arn:aws:bedrock:eu-west-1:123456789:project/test"
    )
    monkeypatch.setenv(
        "BDA_PROFILE_ARN", "arn:aws:bedrock:eu-west-1:123456789:profile/test"
    )


class TestOcrServiceGetStatus:
    @patch("services.ocr_service.boto3.client")
    def test_created_maps_to_ocr_processing(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {"status": "Created"}

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_PROCESSING

    @patch("services.ocr_service.boto3.client")
    def test_in_progress_maps_to_ocr_processing(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {"status": "InProgress"}

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_PROCESSING

    @patch("services.ocr_service.boto3.client")
    def test_success_maps_to_ocr_completed(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {"status": "Success"}

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_COMPLETED

    @patch("services.ocr_service.boto3.client")
    def test_service_error_maps_to_ocr_error(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {"status": "ServiceError"}

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_FAILED

    @patch("services.ocr_service.boto3.client")
    def test_client_error_maps_to_ocr_error(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {"status": "ClientError"}

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_FAILED

    @patch("services.ocr_service.boto3.client")
    def test_unknown_status_maps_to_ocr_error(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.return_value = {
            "status": "UnknownStatus"
        }

        service = OcrService()

        # When
        result = service.get_status(
            "arn:aws:bedrock:eu-west-1:123456789:invocation/job-123"
        )

        # Then
        assert result == PurchaseOrderFileStatus.OCR_FAILED

    @patch("services.ocr_service.boto3.client")
    def test_propagates_exception_from_client(self, mock_boto_client, mock_env):
        # Given
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.get_data_automation_status.side_effect = RuntimeError(
            "BDA service unavailable"
        )

        service = OcrService()

        # When / Then
        with pytest.raises(RuntimeError, match="BDA service unavailable"):
            service.get_status("arn:aws:bedrock:eu-west-1:123456789:invocation/job-456")
