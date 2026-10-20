from unittest.mock import MagicMock, patch

import pytest

from models.procurement import Procurement
from services.procurements_service import ProcurementsService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def mock_service():
    with patch(
        "handlers.process_procurements_handler.procurements_service",
        spec=ProcurementsService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestProcessProcurementsHandler:
    def test_returns_procurements_for_valid_ids(self, mock_service, lambda_context):
        # Given
        mock_service.process_procurements.return_value = [
            Procurement(id="P001", name="Procurement 1"),
            Procurement(id="P002", name="Procurement 2"),
        ]

        from handlers.process_procurements_handler import handler

        event = {"procurementIds": ["P001", "P002"]}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "procurements": [
                {"id": "P001", "name": "Procurement 1"},
                {"id": "P002", "name": "Procurement 2"},
            ],
        }
        mock_service.process_procurements.assert_called_once_with(["P001", "P002"])

    def test_returns_empty_list_when_no_procurements_found(self, mock_service, lambda_context):
        # Given
        mock_service.process_procurements.return_value = []

        from handlers.process_procurements_handler import handler

        event = {"procurementIds": ["P999"]}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "procurements": [],
        }
        mock_service.process_procurements.assert_called_once_with(["P999"])

    def test_handles_none_procurement_ids(self, mock_service, lambda_context):
        # Given
        mock_service.process_procurements.return_value = []

        from handlers.process_procurements_handler import handler

        event = {}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "procurements": [],
        }
        mock_service.process_procurements.assert_called_once_with(None)

    def test_raises_value_error_on_invalid_procurement_ids_type(self, mock_service, lambda_context):
        # Given
        from handlers.process_procurements_handler import handler

        event = {"procurementIds": "not-a-list"}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.process_procurements.assert_not_called()
