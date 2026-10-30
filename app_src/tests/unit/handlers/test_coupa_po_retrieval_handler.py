from unittest.mock import MagicMock, patch

import pytest

from models.purchase_order import PurchaseOrder
from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("COUPA_ACCOUNT", "test_account")
    monkeypatch.setenv("COUPA_WAREHOUSE", "test_warehouse")
    monkeypatch.setenv("COUPA_ACCESS_ROLE_ARN", "test_role")
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
        "handlers.coupa_po_retrieval_handler.purchase_order_service",
        spec=PurchaseOrderService,
    ) as mock:
        yield mock


@pytest.fixture
def lambda_context():
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    return context


class TestProcessPurchaseOrdersHandler:
    def test_returns_purchase_orders_for_valid_ids(self, mock_service, lambda_context):
        # Given
        mock_service.retrieve_pos.return_value = [
            PurchaseOrder(poNumber="P001", hacat="HC1005"),
            PurchaseOrder(poNumber="P002", hacat="HC1005"),
        ]

        from handlers.coupa_po_retrieval_handler import handler

        event = {
            "poNumbers": ["P001", "P002"],
            "hacat": "HC1005",
            "executionId": EXECUTION_ID,
        }

        # When
        result = handler(event, lambda_context)

        # Then
        assert result["status"] == "SUCCESS"
        assert len(result["purchaseOrders"]) == 2
        assert result["purchaseOrders"][0]["poNumber"] == "P001"
        assert result["purchaseOrders"][1]["poNumber"] == "P002"
        mock_service.retrieve_pos.assert_called_once_with(
            hacat="HC1005", po_numbers=["P001", "P002"], execution_id=EXECUTION_ID
        )

    def test_returns_empty_list_when_no_purchase_orders_found(
        self, mock_service, lambda_context
    ):
        # Given
        mock_service.retrieve_pos.return_value = []

        from handlers.coupa_po_retrieval_handler import handler

        event = {"poNumbers": ["P999"], "hacat": "HC1005", "executionId": EXECUTION_ID}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "purchaseOrders": [],
        }
        mock_service.retrieve_pos.assert_called_once_with(
            hacat="HC1005", po_numbers=["P999"], execution_id=EXECUTION_ID
        )

    def test_handles_none_po_numbers(self, mock_service, lambda_context):
        # Given
        mock_service.retrieve_pos.return_value = []

        from handlers.coupa_po_retrieval_handler import handler

        event = {"hacat": "HC1005", "executionId": EXECUTION_ID}

        # When
        result = handler(event, lambda_context)

        # Then
        assert result == {
            "status": "SUCCESS",
            "purchaseOrders": [],
        }
        mock_service.retrieve_pos.assert_called_once_with(
            hacat="HC1005", po_numbers=None, execution_id=EXECUTION_ID
        )

    def test_raises_value_error_on_invalid_po_numbers_type(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.coupa_po_retrieval_handler import handler

        event = {
            "poNumbers": "not-a-list",
            "hacat": "HC1005",
            "executionId": EXECUTION_ID,
        }

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.retrieve_pos.assert_not_called()

    def test_raises_value_error_on_missing_execution_id(
        self, mock_service, lambda_context
    ):
        # Given
        from handlers.coupa_po_retrieval_handler import handler

        event = {"poNumbers": ["P001"], "hacat": "HC1005"}

        # When / Then
        with pytest.raises(ValueError, match="Payload validation failed"):
            handler(event, lambda_context)

        mock_service.retrieve_pos.assert_not_called()
