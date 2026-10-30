from datetime import datetime, timezone
from unittest.mock import MagicMock

import os

os.environ.setdefault("POWERTOOLS_METRICS_NAMESPACE", "test")

import pytest

from models.purchase_order import PurchaseOrderStatus
from repositories.purchase_order_file_objects_repository import (
    TIMESTAMP_FORMAT,
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture(autouse=True)
def set_metrics_env(monkeypatch):
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def mock_purchase_order_repository():
    return MagicMock(spec=PurchaseOrderRepository)


@pytest.fixture
def mock_purchase_order_file_objects_repository():
    return MagicMock(spec=PurchaseOrderFileObjectsRepository)


@pytest.fixture
def service(
    mock_purchase_order_repository,
    mock_purchase_order_file_objects_repository,
):
    return PurchaseOrderService(
        purchase_order_repository=mock_purchase_order_repository,
        purchase_order_file_objects_repository=mock_purchase_order_file_objects_repository,
    )


class TestExportToCedl:
    def test_writes_export_in_progress_status_to_dynamodb_at_start(
        self,
        service,
        mock_purchase_order_repository,
    ):
        """export_to_cedl writes EXPORT_IN_PROGRESS status to DynamoDB at start."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250709T154416Z",
            execution_id=EXECUTION_ID,
        )

        first_call = mock_purchase_order_repository.update_status.call_args_list[0]
        assert first_call[1]["status"] == PurchaseOrderStatus.EXPORT_IN_PROGRESS
        assert first_call[1]["po_number"] == "E002754388"
        assert first_call[1]["execution_id"] == EXECUTION_ID

    def test_date_folder_derivation_standard_timestamp(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        """Date folder is derived correctly from a standard timestamp."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250709T154416Z",
            execution_id=EXECUTION_ID,
        )

        call_kwargs = (
            mock_purchase_order_file_objects_repository.export.call_args.kwargs
        )
        assert call_kwargs["timestamp"] == datetime(
            2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc
        )

    def test_date_folder_derivation_midnight_timestamp(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        """Date folder is derived correctly from a midnight timestamp."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250101T000000Z",
            execution_id=EXECUTION_ID,
        )

        call_kwargs = (
            mock_purchase_order_file_objects_repository.export.call_args.kwargs
        )
        assert call_kwargs["timestamp"] == datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )

    def test_date_folder_derivation_end_of_year(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        """Date folder is derived correctly from end-of-year timestamp."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20251231T235959Z",
            execution_id=EXECUTION_ID,
        )

        call_kwargs = (
            mock_purchase_order_file_objects_repository.export.call_args.kwargs
        )
        assert call_kwargs["timestamp"] == datetime(
            2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc
        )

    def test_repository_export_called_with_correct_args(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        """Repository export is called with correct computed args."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250709T154416Z",
            execution_id=EXECUTION_ID,
        )

        mock_purchase_order_file_objects_repository.export.assert_called_once_with(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

    def test_writes_export_completed_to_dynamodb_on_success(
        self,
        service,
        mock_purchase_order_repository,
    ):
        """EXPORT_COMPLETED is written to DynamoDB on success."""
        service.export_to_cedl(
            hacat="HC1001",
            po_number="E002754388",
            timestamp="20250709T154416Z",
            execution_id=EXECUTION_ID,
        )

        update_calls = mock_purchase_order_repository.update_status.call_args_list
        assert len(update_calls) == 2

        # Second call: EXPORT_COMPLETED
        assert update_calls[1][1]["status"] == PurchaseOrderStatus.EXPORT_COMPLETED
        assert update_calls[1][1]["po_number"] == "E002754388"
        assert update_calls[1][1]["execution_id"] == EXECUTION_ID

    def test_writes_export_failed_to_dynamodb_on_failure_and_reraises(
        self,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_objects_repository,
    ):
        """EXPORT_FAILED is written to DynamoDB on failure and exception is re-raised."""
        mock_purchase_order_file_objects_repository.export.side_effect = RuntimeError(
            "S3 read failed"
        )

        with pytest.raises(RuntimeError, match="S3 read failed"):
            service.export_to_cedl(
                hacat="HC1001",
                po_number="E002754388",
                timestamp="20250709T154416Z",
                execution_id=EXECUTION_ID,
            )

        # Should have written IN_PROGRESS then FAILED
        update_calls = mock_purchase_order_repository.update_status.call_args_list
        assert len(update_calls) == 2
        assert update_calls[0][1]["status"] == PurchaseOrderStatus.EXPORT_IN_PROGRESS
        assert update_calls[1][1]["status"] == PurchaseOrderStatus.EXPORT_FAILED

    def test_dynamodb_failure_during_failed_status_write_does_not_suppress_original_error(
        self,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_objects_repository,
    ):
        """DynamoDB failure during EXPORT_FAILED write is logged but does not suppress original error."""
        mock_purchase_order_file_objects_repository.export.side_effect = RuntimeError(
            "S3 read failed"
        )

        # First update_status (IN_PROGRESS) succeeds, second (FAILED) also fails
        call_count = [0]

        def update_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # FAILED write
                raise RuntimeError("DynamoDB write failed on EXPORT_FAILED")

        mock_purchase_order_repository.update_status.side_effect = update_side_effect

        # Original error should still be raised
        with pytest.raises(RuntimeError, match="S3 read failed"):
            service.export_to_cedl(
                hacat="HC1001",
                po_number="E002754388",
                timestamp="20250709T154416Z",
                execution_id=EXECUTION_ID,
            )

    def test_export_repository_failure_sets_export_failed_and_reraises(
        self,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_objects_repository,
    ):
        """Repository export failure sets EXPORT_FAILED and re-raises."""
        mock_purchase_order_file_objects_repository.export.side_effect = RuntimeError(
            "S3 write failed"
        )

        with pytest.raises(RuntimeError, match="S3 write failed"):
            service.export_to_cedl(
                hacat="HC1001",
                po_number="E002754388",
                timestamp="20250709T154416Z",
                execution_id=EXECUTION_ID,
            )

        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.EXPORT_FAILED
