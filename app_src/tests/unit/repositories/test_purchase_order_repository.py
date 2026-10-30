from unittest.mock import MagicMock, patch

import pytest

from models.purchase_order import PurchaseOrderRecord, PurchaseOrderStatus
from repositories.purchase_order_repository import PurchaseOrderRepository


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")


@pytest.fixture
def mock_table():
    with patch("repositories.purchase_order_repository.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def repository(mock_table):
    return PurchaseOrderRepository()


class TestBatchCreate:
    def test_batch_creates_items_with_correct_key_and_attributes(
        self, repository, mock_table
    ):
        # Given
        mock_batch_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        records = [
            PurchaseOrderRecord(
                poNumber="P001",
                hacat="HC1001",
                executionId="f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
                status=PurchaseOrderStatus.PENDING,
                nbFiles=3,
            ),
            PurchaseOrderRecord(
                poNumber="P002",
                hacat="HC1001",
                executionId="f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
                status=PurchaseOrderStatus.PENDING,
                nbFiles=1,
            ),
        ]

        # When
        repository.batch_create(records)

        # Then
        assert mock_batch_writer.put_item.call_count == 2
        first_call = mock_batch_writer.put_item.call_args_list[0]
        item = first_call[1]["Item"]
        assert item["PK"] == "PO#HACAT#HC1001#PO#P001"
        assert item["SK"] == "EXEC#f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
        assert item["po_number"] == "P001"
        assert item["hacat"] == "HC1001"
        assert item["execution_id"] == "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
        assert item["status"] == "PENDING"
        assert item["nb_files"] == 3
        assert "timestamp" in item

    def test_batch_create_with_empty_list(self, repository, mock_table):
        # Given
        mock_batch_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        # When
        repository.batch_create([])

        # Then
        mock_batch_writer.put_item.assert_not_called()


class TestUpdateStatus:
    def test_updates_status_with_correct_expression(self, repository, mock_table):
        # When
        repository.update_status(
            hacat="HC1001",
            po_number="E002754388",
            execution_id="f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
            status=PurchaseOrderStatus.PROCESSING,
        )

        # Then
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args[1]
        assert call_kwargs["Key"] == {
            "PK": "PO#HACAT#HC1001#PO#E002754388",
            "SK": "EXEC#f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
        }
        assert call_kwargs["UpdateExpression"] == "SET #s = :status, #t = :timestamp"
        assert call_kwargs["ExpressionAttributeNames"] == {
            "#s": "status",
            "#t": "timestamp",
        }
        assert call_kwargs["ExpressionAttributeValues"][":status"] == "PROCESSING"
        assert ":timestamp" in call_kwargs["ExpressionAttributeValues"]

    def test_propagates_dynamodb_error(self, repository, mock_table):
        # Given
        mock_table.update_item.side_effect = Exception("DynamoDB error")

        # When / Then
        with pytest.raises(Exception, match="DynamoDB error"):
            repository.update_status(
                hacat="HC1001",
                po_number="P001",
                execution_id="exec-1",
                status=PurchaseOrderStatus.EXPORT_COMPLETED,
            )


class TestInit:
    def test_reads_table_name_from_env(self, mock_table):
        # When
        repo = PurchaseOrderRepository()

        # Then
        assert repo._table_name == "test-table"
