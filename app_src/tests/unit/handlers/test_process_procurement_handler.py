from unittest.mock import MagicMock, patch

import pytest

from services.procurements_service import ProcurementsService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.process_procurement_handler.procurements_service",
        spec=ProcurementsService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestProcessProcurementHandler:
    def test_returns_attachments_for_valid_procurement_id(self, mock_service, lambda_context):
        # Given
        mock_service.process_procurement.return_value = [
            "P001/file1.pdf",
            "P001/file2.csv",
        ]

        from handlers.process_procurement_handler import handler

        event = {"procurementId": "P001"}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "procurementId": "P001",
            "attachments": ["P001/file1.pdf", "P001/file2.csv"],
        }
        mock_service.process_procurement.assert_called_once_with("P001")

    def test_returns_empty_attachments_when_no_s3_objects(self, mock_service, lambda_context):
        # Given
        mock_service.process_procurement.return_value = []

        from handlers.process_procurement_handler import handler

        event = {"procurementId": "P999"}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "procurementId": "P999",
            "attachments": [],
        }
        mock_service.process_procurement.assert_called_once_with("P999")

    def test_raises_value_error_on_missing_procurement_id(self, mock_service, lambda_context):
        # Given
        from handlers.process_procurement_handler import handler

        event = {}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.process_procurement.assert_not_called()

    def test_raises_value_error_on_invalid_type(self, mock_service, lambda_context):
        # Given
        from handlers.process_procurement_handler import handler

        event = {"procurementId": 123}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.process_procurement.assert_not_called()
