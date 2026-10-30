from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models.po_file import PurchaseOrderFile, PurchaseOrderFileStatus
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")


@pytest.fixture
def mock_table():
    with patch("repositories.purchase_order_file_repository.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def repository(mock_table):
    return PurchaseOrderFileRepository()


class TestInit:
    def test_reads_table_name_from_env(self, mock_table):
        repo = PurchaseOrderFileRepository()
        assert repo._table_name == "test-table"

    def test_raises_key_error_when_env_not_set(self):
        with patch("repositories.purchase_order_file_repository.boto3"):
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(KeyError):
                    PurchaseOrderFileRepository()


class TestBuildKey:
    def test_builds_correct_key_structure(self, repository):
        key = repository._build_key("HC1001", "E002754388", "document.pdf")
        assert key == {
            "PK": "PO_FILE#HACAT#HC1001#PO#E002754388",
            "SK": "PO_FILE#document.pdf",
        }


class TestGet:
    def test_returns_purchase_order_file_when_item_exists(self, repository, mock_table):
        # Given
        mock_table.get_item.return_value = {
            "Item": {
                "PK": "PO_FILE#PO#E002754388",
                "SK": "PO_FILE#sow_v1.pdf",
                "po_number": "E002754388",
                "filename": "sow_v1.pdf",
                "hacat": "HC1001",
                "status": "OCR_COMPLETED",
                "timestamp": "2025-01-15T10:30:00Z",
                "original_filename": "Statement of Work v1.pdf",
            }
        }

        # When
        result = repository.get("HC1001", "E002754388", "sow_v1.pdf")

        # Then
        assert result is not None
        assert result.po_number == "E002754388"
        assert result.filename == "sow_v1.pdf"
        assert result.hacat == "HC1001"
        assert result.status == PurchaseOrderFileStatus.OCR_COMPLETED
        assert result.original_filename == "Statement of Work v1.pdf"

    def test_returns_none_when_item_not_found(self, repository, mock_table):
        # Given
        mock_table.get_item.return_value = {}

        # When
        result = repository.get("HC1001", "NONEXISTENT", "file.pdf")

        # Then
        assert result is None

    def test_queries_with_correct_key(self, repository, mock_table):
        # Given
        mock_table.get_item.return_value = {}

        # When
        repository.get("HC1001", "E002754388", "doc.pdf")

        # Then
        mock_table.get_item.assert_called_once_with(
            Key={
                "PK": "PO_FILE#HACAT#HC1001#PO#E002754388",
                "SK": "PO_FILE#doc.pdf",
            }
        )

    def test_strips_pk_sk_from_returned_item(self, repository, mock_table):
        # Given
        mock_table.get_item.return_value = {
            "Item": {
                "PK": "PO_FILE#PO#P001",
                "SK": "PO_FILE#file.pdf",
                "po_number": "P001",
                "filename": "file.pdf",
                "hacat": "HC1005",
                "status": "PENDING",
                "timestamp": "2025-06-01T08:00:00Z",
                "original_filename": "Original File.pdf",
            }
        }

        # When
        result = repository.get("HC1005", "P001", "file.pdf")

        # Then
        assert result is not None
        assert result.po_number == "P001"
        assert result.status == PurchaseOrderFileStatus.PENDING

    def test_propagates_dynamodb_error(self, repository, mock_table):
        # Given
        mock_table.get_item.side_effect = Exception("DynamoDB error")

        # When / Then
        with pytest.raises(Exception, match="DynamoDB error"):
            repository.get("HC1005", "P001", "file.pdf")


class TestUpdateStatus:
    @patch("repositories.purchase_order_file_repository.datetime")
    def test_updates_status_and_timestamp(self, mock_datetime, repository, mock_table):
        # Given
        fake_now = datetime(2025, 7, 10, 14, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now

        # When
        repository.update_status(
            "HC1001", "E002754388", "sow_v1.pdf", PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # Then
        mock_table.update_item.assert_called_once_with(
            Key={
                "PK": "PO_FILE#HACAT#HC1001#PO#E002754388",
                "SK": "PO_FILE#sow_v1.pdf",
            },
            UpdateExpression="SET #s = :status, #t = :timestamp",
            ExpressionAttributeNames={
                "#s": "status",
                "#t": "timestamp",
            },
            ExpressionAttributeValues={
                ":status": "OCR_COMPLETED",
                ":timestamp": fake_now.isoformat(),
            },
        )

    @patch("repositories.purchase_order_file_repository.datetime")
    def test_propagates_dynamodb_error(self, mock_datetime, repository, mock_table):
        # Given
        mock_datetime.now.return_value = datetime(
            2025, 7, 10, 14, 0, 0, tzinfo=timezone.utc
        )
        mock_table.update_item.side_effect = Exception("DynamoDB error")

        # When / Then
        with pytest.raises(Exception, match="DynamoDB error"):
            repository.update_status(
                "HC1001", "E002754388", "file.pdf", PurchaseOrderFileStatus.OCR_FAILED
            )


class TestBatchCreate:
    def test_writes_all_items_to_dynamodb(self, repository, mock_table):
        # Given
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        po_files = [
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
            PurchaseOrderFile(
                po_number="E002754388",
                filename="invoice.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
                original_filename="Invoice.pdf",
            ),
        ]

        # When
        repository.batch_create(po_files)

        # Then
        assert mock_batch.put_item.call_count == 2

    def test_builds_correct_item_structure(self, repository, mock_table):
        # Given
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        po_files = [
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
        ]

        # When
        repository.batch_create(po_files)

        # Then
        mock_batch.put_item.assert_called_once_with(
            Item={
                "PK": "PO_FILE#HACAT#HC1001#PO#E002754388",
                "SK": "PO_FILE#sow_v1.pdf",
                "po_number": "E002754388",
                "filename": "sow_v1.pdf",
                "hacat": "HC1001",
                "status": "PENDING",
                "timestamp": "2025-01-15 10:30:00+00:00",
                "original_filename": "Statement of Work v1.pdf",
            }
        )

    def test_deduplicates_items_with_same_key(self, repository, mock_table):
        # Given — two records with same po_number + filename (duplicate key)
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        po_files = [
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
        ]

        # When
        repository.batch_create(po_files)

        # Then — only one put_item call (deduplicated)
        assert mock_batch.put_item.call_count == 1

    def test_deduplication_keeps_last_occurrence(self, repository, mock_table):
        # Given — duplicate key, second has different timestamp
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        po_files = [
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
                original_filename="First occurrence.pdf",
            ),
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
                original_filename="Second occurrence.pdf",
            ),
        ]

        # When
        repository.batch_create(po_files)

        # Then — the item written should be the last occurrence
        call_args = mock_batch.put_item.call_args
        assert call_args[1]["Item"]["original_filename"] == "Second occurrence.pdf"
        assert call_args[1]["Item"]["timestamp"] == "2025-01-15 12:00:00+00:00"

    def test_deduplication_across_different_pos(self, repository, mock_table):
        # Given — same filename but different po_numbers (different keys, no dedup)
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        po_files = [
            PurchaseOrderFile(
                po_number="E002754388",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
            PurchaseOrderFile(
                po_number="E002754389",
                filename="sow_v1.pdf",
                hacat="HC1001",
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
                original_filename="Statement of Work v1.pdf",
            ),
        ]

        # When
        repository.batch_create(po_files)

        # Then — both are written (different PK)
        assert mock_batch.put_item.call_count == 2

    def test_handles_empty_list(self, repository, mock_table):
        # Given
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        # When
        repository.batch_create([])

        # Then
        mock_batch.put_item.assert_not_called()


class TestFindByPoAndStatus:
    def test_queries_dynamodb_with_partition_key_and_status_filter(
        self, repository, mock_table
    ):
        # Given
        mock_table.query.return_value = {"Items": []}
        po_number = "E002754388"

        # When
        repository.find_by_po_and_status(
            "HC1001", po_number, PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # Then
        mock_table.query.assert_called_once_with(
            KeyConditionExpression="PK = :pk",
            FilterExpression="#s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":pk": "PO_FILE#HACAT#HC1001#PO#E002754388",
                ":status": "OCR_COMPLETED",
            },
        )

    def test_maps_returned_items_to_purchase_order_file_objects(
        self, repository, mock_table
    ):
        # Given
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "PO_FILE#PO#E002754388",
                    "SK": "PO_FILE#sow_v1.pdf",
                    "po_number": "E002754388",
                    "filename": "sow_v1.pdf",
                    "hacat": "HC1001",
                    "status": "PENDING",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "original_filename": "sow_v1.pdf",
                },
                {
                    "PK": "PO_FILE#PO#E002754388",
                    "SK": "PO_FILE#invoice.pdf",
                    "po_number": "E002754388",
                    "filename": "invoice.pdf",
                    "hacat": "HC1001",
                    "status": "OCR_COMPLETED",
                    "timestamp": "2024-01-15T11:00:00Z",
                    "original_filename": "invoice.pdf",
                },
            ]
        }

        # When
        result = repository.find_by_po_and_status(
            "HC1001", "E002754388", PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # Then
        assert len(result) == 2

        assert result[0].po_number == "E002754388"
        assert result[0].filename == "sow_v1.pdf"
        assert result[0].hacat == "HC1001"
        assert result[0].status == PurchaseOrderFileStatus.PENDING
        assert result[0].timestamp == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

        assert result[1].po_number == "E002754388"
        assert result[1].filename == "invoice.pdf"
        assert result[1].hacat == "HC1001"
        assert result[1].status == PurchaseOrderFileStatus.OCR_COMPLETED
        assert result[1].timestamp == datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)

    def test_returns_empty_list_when_no_items_found(self, repository, mock_table):
        # Given
        mock_table.query.return_value = {"Items": []}

        # When
        result = repository.find_by_po_and_status(
            "HC1001", "NONEXISTENT", PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # Then
        assert result == []

    def test_propagates_dynamodb_query_error(self, repository, mock_table):
        # Given
        mock_table.query.side_effect = Exception("DynamoDB query failed")

        # When / Then
        with pytest.raises(Exception, match="DynamoDB query failed"):
            repository.find_by_po_and_status(
                "HC1001", "E002754388", PurchaseOrderFileStatus.OCR_COMPLETED
            )

    def test_returns_purchase_order_file_instances(self, repository, mock_table):
        # Given
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "PO_FILE#PO#P001",
                    "SK": "PO_FILE#doc.pdf",
                    "po_number": "P001",
                    "filename": "doc.pdf",
                    "hacat": "HC1005",
                    "status": "OCR_COMPLETED",
                    "timestamp": "2025-03-01T09:00:00Z",
                    "original_filename": "doc.pdf",
                },
            ]
        }

        # When
        result = repository.find_by_po_and_status(
            "HC1005", "P001", PurchaseOrderFileStatus.OCR_COMPLETED
        )

        # Then
        assert all(isinstance(item, PurchaseOrderFile) for item in result)
