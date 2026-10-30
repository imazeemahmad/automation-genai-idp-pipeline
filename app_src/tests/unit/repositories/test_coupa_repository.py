from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models.po_file import CedlPoFile
from models.purchase_order import PurchaseOrder
from repositories.coupa_repository import CoupaRepository


@pytest.fixture
def env_vars():
    with patch.dict(
        "os.environ",
        {
            "COUPA_ACCOUNT": "test_account",
            "COUPA_WAREHOUSE": "test_warehouse",
            "COUPA_ACCESS_ROLE_ARN": "test_role",
            "COUPA_DATABASE": "test_database",
            "COUPA_SCHEMA": "test_schema",
        },
    ):
        yield


@pytest.fixture
def mock_connect():
    with patch("repositories.coupa_repository.snowflake.connector.connect") as mock:
        yield mock


@pytest.fixture
def repository(env_vars):
    return CoupaRepository()


class TestRetrievePo:
    def test_returns_purchase_orders_grouped_by_order_header_id(
        self, repository, mock_connect
    ):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Two rows for same ORDER_HEADER_ID
        mock_cursor.fetchall.return_value = [
            (
                "E002754388",
                "HC1001",
                "1.pdf",
                "ORDER_HEADER/2025/09/08/attachments/2754388/1.pdf",
                datetime(2025, 11, 28, 11, 23, 40, tzinfo=timezone.utc),
                "original_1.pdf",
            ),
            (
                "E002754388",
                "HC1001",
                "2.pdf",
                "ORDER_HEADER/2025/09/08/attachments/2754388/2.pdf",
                datetime(2025, 11, 28, 12, 0, 0, tzinfo=timezone.utc),
                "original_2.pdf",
            ),
            (
                "E000024494",
                "HC1001",
                "3.pdf",
                "ORDER_HEADER/2025/11/25/attachments/24494/3.pdf",
                datetime(2025, 11, 28, 13, 5, 42, tzinfo=timezone.utc),
                "original_3.pdf",
            ),
        ]

        # When
        result = repository.retrieve_po(hacat="HC1001")

        # Then
        assert len(result) == 2
        assert all(isinstance(item, PurchaseOrder) for item in result)

        # Find orders by po_number
        order_map = {po.po_number: po for po in result}

        assert "E002754388" in order_map
        assert order_map["E002754388"].hacat == "HC1001"
        assert len(order_map["E002754388"].po_files) == 2
        assert order_map["E002754388"].po_files[0].filename == "1.pdf"
        assert order_map["E002754388"].po_files[1].filename == "2.pdf"

        assert "E000024494" in order_map
        assert order_map["E000024494"].hacat == "HC1001"
        assert len(order_map["E000024494"].po_files) == 1
        assert order_map["E000024494"].po_files[0].filename == "3.pdf"

    def test_returns_empty_list_for_no_rows(self, repository, mock_connect):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.return_value = []

        # When
        result = repository.retrieve_po(hacat="HC1005")

        # Then
        assert result == []

    def test_closes_connection_after_query(self, repository, mock_connect):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.return_value = []

        # When
        repository.retrieve_po(hacat="HC1005")

        # Then
        mock_conn.close.assert_called_once()

    def test_closes_connection_on_exception(self, repository, mock_connect):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.side_effect = RuntimeError("query failed")

        # When / Then
        with pytest.raises(RuntimeError, match="query failed"):
            repository.retrieve_po(hacat="HC1005")

        mock_conn.close.assert_called_once()

    def test_filters_by_hacat(self, repository, mock_connect):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.return_value = [
            (
                "E000024494",
                "HC1005",
                "2.pdf",
                "some/path/2.pdf",
                datetime(2025, 11, 28, 13, 5, 42, tzinfo=timezone.utc),
                "original_2.pdf",
            ),
        ]

        # When
        result = repository.retrieve_po(hacat="HC1005")

        # Then
        assert len(result) == 1
        assert result[0].hacat == "HC1005"

        # Verify the query contains the hacat filter
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "FK_HACAT_ID = %(hacat)s" in query
        assert params["hacat"] == "HC1005"

    def test_filters_by_po_numbers(self, repository, mock_connect):
        # Given
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.return_value = [
            (
                "E002754388",
                "HC1001",
                "1.pdf",
                "some/path/1.pdf",
                datetime(2025, 11, 28, 11, 23, 40, tzinfo=timezone.utc),
                "original_1.pdf",
            ),
        ]

        # When
        result = repository.retrieve_po(hacat="HC1001", po_numbers=["E002754388"])

        # Then
        assert len(result) == 1
        assert result[0].po_number == "E002754388"

        # Verify the query contains the po_numbers filter
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "ORDER_HEADER_ID IN" in query
        assert params["po_0"] == "E002754388"


class TestBuildQuery:
    def test_hacat_only(self, repository):
        query, params = repository._build_query(hacat="HC1005")
        assert "WHERE" in query
        assert "FK_HACAT_ID = %(hacat)s" in query
        assert "ATTACHMENT_ADJUSTED_NAME IS NOT NULL" in query
        assert "ATTACHMENT_ADJUSTED_NAME != ''" in query
        assert params == {"hacat": "HC1005"}
        assert "ORDER_HEADER_ID" in query
        assert "FK_HACAT_ID" in query
        assert "ATTACHMENT_NAME" in query
        assert "S3_PATH" in query
        assert "T_S3_SOURCE_FILE_TS" in query
        assert "ATTACHMENT_ADJUSTED_NAME" in query
        assert "*" not in query
        assert "test_database.test_schema.S3_ORDER_HEADERS_PATH" in query
        assert "ORDER BY T_S3_SOURCE_FILE_TS ASC" in query

    def test_with_po_numbers(self, repository):
        query, params = repository._build_query(
            hacat="HC1005", po_numbers=["P001", "P002"]
        )
        assert "ORDER_HEADER_ID IN (%(po_0)s, %(po_1)s)" in query
        assert "FK_HACAT_ID = %(hacat)s" in query
        assert params == {"hacat": "HC1005", "po_0": "P001", "po_1": "P002"}
        assert "ORDER BY T_S3_SOURCE_FILE_TS ASC" in query

    def test_with_since(self, repository):
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        query, params = repository._build_query(hacat="HC1005", since=since)
        assert "FK_HACAT_ID = %(hacat)s" in query
        assert "T_S3_SOURCE_FILE_TS > %(since)s" in query
        assert params["hacat"] == "HC1005"
        assert params["since"] == since
        assert "ORDER BY T_S3_SOURCE_FILE_TS ASC" in query

    def test_with_all_filters(self, repository):
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        query, params = repository._build_query(
            hacat="HC1006", po_numbers=["P001"], since=since
        )
        assert "ORDER_HEADER_ID IN (%(po_0)s)" in query
        assert "FK_HACAT_ID = %(hacat)s" in query
        assert "T_S3_SOURCE_FILE_TS > %(since)s" in query
        assert "AND" in query
        assert params["hacat"] == "HC1006"
        assert params["po_0"] == "P001"
        assert params["since"] == since

    def test_with_batch_size(self, repository):
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        query, params = repository._build_query(
            hacat="HC1005", since=since, batch_size=250
        )
        # Should contain the sub-query pattern
        assert "ORDER_HEADER_ID IN (SELECT ORDER_HEADER_ID FROM" in query
        assert "GROUP BY ORDER_HEADER_ID" in query
        assert "ORDER BY MIN(T_S3_SOURCE_FILE_TS) ASC" in query
        assert "LIMIT %(batch_size)s" in query
        assert params["batch_size"] == 250
        # The outer query should also be ordered
        assert query.endswith("ORDER BY T_S3_SOURCE_FILE_TS ASC")

    def test_batch_size_ignored_when_po_numbers_provided(self, repository):
        query, params = repository._build_query(
            hacat="HC1005", po_numbers=["P001"], batch_size=250
        )
        # batch_size should be ignored when po_numbers is provided
        assert "LIMIT" not in query
        assert "GROUP BY" not in query
        assert "batch_size" not in params
        assert "ORDER BY T_S3_SOURCE_FILE_TS ASC" in query

    def test_batch_size_none_does_not_add_limit(self, repository):
        query, params = repository._build_query(hacat="HC1005", batch_size=None)
        assert "LIMIT" not in query
        assert "GROUP BY" not in query
        assert "batch_size" not in params


class TestFormatResults:
    def test_groups_rows_by_order_header_id(self):
        # Given
        rows = [
            (
                "E001",
                "HC1005",
                "file1.pdf",
                "path/1.pdf",
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                "original_file1.pdf",
            ),
            (
                "E001",
                "HC1005",
                "file2.pdf",
                "path/2.pdf",
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                "original_file2.pdf",
            ),
            (
                "E002",
                "HC1006",
                "file3.pdf",
                "path/3.pdf",
                datetime(2025, 1, 3, tzinfo=timezone.utc),
                "original_file3.pdf",
            ),
        ]

        # When
        result = CoupaRepository._format_results(rows)

        # Then
        assert len(result) == 2
        order_map = {po.po_number: po for po in result}

        assert order_map["E001"].hacat == "HC1005"
        assert len(order_map["E001"].po_files) == 2

        assert order_map["E002"].hacat == "HC1006"
        assert len(order_map["E002"].po_files) == 1
        assert order_map["E002"].po_files[0].filename == "file3.pdf"

    def test_returns_empty_list_for_no_rows(self):
        result = CoupaRepository._format_results([])
        assert result == []


class TestConnect:
    def test_uses_environment_variables_for_connection(self, repository, mock_connect):
        # When
        repository._connect()

        # Then
        mock_connect.assert_called_once_with(
            account="test_account",
            authenticator="WORKLOAD_IDENTITY",
            workload_identity_provider="AWS",
            workload_identity_impersonation_path=["test_role"],
            warehouse="test_warehouse",
            database="test_database",
            schema="test_schema",
        )
