"""Repository for retrieving purchase orders from Coupa."""

import logging
import os
from collections import defaultdict
from datetime import datetime

import snowflake.connector

from models.po_file import CedlPoFile
from models.purchase_order import PurchaseOrder

logger = logging.getLogger(__name__)

# Connection defaults
_AUTHENTICATOR = "WORKLOAD_IDENTITY"
_WORKLOAD_IDENTITY_PROVIDER = "AWS"

_COLUMNS = [
    "ORDER_HEADER_ID",
    "FK_HACAT_ID",
    "ATTACHMENT_NAME",
    "S3_PATH",
    "T_S3_SOURCE_FILE_TS",
    "ATTACHMENT_ADJUSTED_NAME",
]


class CoupaRepository:

    def __init__(self):
        """Initialize the repository.

        Connection parameters are read from environment variables:
            - COUPA_ACCOUNT: Account identifier
            - COUPA_WAREHOUSE: Warehouse to use
            - COUPA_ACCESS_ROLE_ARN: IAM role ARN to assume via impersonation
            - COUPA_DATABASE: Database name
            - COUPA_SCHEMA: Schema name
        """

        self._account = os.environ["COUPA_ACCOUNT"]
        self._warehouse = os.environ["COUPA_WAREHOUSE"]
        self._access_role_arn = os.environ["COUPA_ACCESS_ROLE_ARN"]
        self._database = os.environ["COUPA_DATABASE"]
        self._schema = os.environ["COUPA_SCHEMA"]

    def _connect(self):
        """Build and return a database connection using workload identity with impersonation."""

        connect_kwargs = {
            "account": self._account,
            "authenticator": _AUTHENTICATOR,
            "workload_identity_provider": _WORKLOAD_IDENTITY_PROVIDER,
            "workload_identity_impersonation_path": [self._access_role_arn],
            "warehouse": self._warehouse,
            "database": self._database,
            "schema": self._schema,
        }
        logger.debug(
            "Connecting to account '%s' with impersonation via '%s'",
            self._account,
            self._access_role_arn,
        )
        conn = snowflake.connector.connect(**connect_kwargs)
        logger.info("Connected to Coupa data source.")
        return conn

    def retrieve_po(
        self,
        hacat: str,
        po_numbers: list[str] | None = None,
        since: datetime | None = None,
        batch_size: int | None = None,
    ) -> list[PurchaseOrder]:
        """Retrieve purchase orders from Coupa.

        Connects to the data source and executes the retrieval query,
        filtering by HACAT code and optionally by PO numbers. Results are grouped
        by ORDER_HEADER_ID.

        Args:
            hacat: HACAT code (FK_HACAT_ID) to filter on.
            po_numbers: Optional list of ORDER_HEADER_ID values to filter on.
            since: Optional datetime to filter only records newer than this date.
            batch_size: Optional max number of distinct POs to return (oldest first).

        Returns:
            List of PurchaseOrder instances grouped by ORDER_HEADER_ID.
        """

        conn = self._connect()
        try:
            query, params = self._build_query(hacat, po_numbers, since, batch_size)
            logger.debug("Executing query: %s with params: %s", query, params)

            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

            logger.debug("Raw Snowflake response: %s", rows)
            logger.info("Query returned %d row(s).", len(rows))
            return self._format_results(rows)
        finally:
            conn.close()

    def _build_query(
        self,
        hacat: str,
        po_numbers: list[str] | None = None,
        since: datetime | None = None,
        batch_size: int | None = None,
    ) -> tuple[str, dict]:
        """Build the SQL query with optional filters.

        When *batch_size* is provided the query orders rows by
        ``T_S3_SOURCE_FILE_TS ASC`` and limits the result set so that at most
        *batch_size* **complete purchase orders** are returned (no PO is split
        across batches).

        Returns:
            Tuple of (query_string, bind_parameters).
        """
        columns = ", ".join(_COLUMNS)
        table = f"{self._database}.{self._schema}.S3_ORDER_HEADERS_PATH"

        conditions: list[str] = [
            "FK_HACAT_ID = %(hacat)s",
            "ATTACHMENT_ADJUSTED_NAME IS NOT NULL",
            "ATTACHMENT_ADJUSTED_NAME != ''",
        ]
        params: dict = {"hacat": hacat}

        if po_numbers:
            placeholders = ", ".join([f"%(po_{i})s" for i in range(len(po_numbers))])
            conditions.append(f"ORDER_HEADER_ID IN ({placeholders})")
            for i, po in enumerate(po_numbers):
                params[f"po_{i}"] = po

        if since:
            conditions.append("T_S3_SOURCE_FILE_TS > %(since)s")
            params["since"] = since

        where_clause = " WHERE " + " AND ".join(conditions)

        if batch_size is not None and not po_numbers:
            # Sub-query: pick the first *batch_size* distinct POs ordered by
            # their earliest file timestamp, then fetch all rows for those POs.
            params["batch_size"] = batch_size
            base_query = (
                f"SELECT {columns} FROM {table}"
                f"{where_clause}"
                " AND ORDER_HEADER_ID IN ("
                f"SELECT ORDER_HEADER_ID FROM {table}"
                f"{where_clause}"
                " GROUP BY ORDER_HEADER_ID"
                " ORDER BY MIN(T_S3_SOURCE_FILE_TS) ASC"
                " LIMIT %(batch_size)s"
                ")"
                " ORDER BY T_S3_SOURCE_FILE_TS ASC"
            )
        else:
            base_query = f"SELECT {columns} FROM {table}{where_clause}"
            base_query += " ORDER BY T_S3_SOURCE_FILE_TS ASC"

        return base_query, params

    @staticmethod
    def _format_results(rows: list[tuple]) -> list[PurchaseOrder]:
        """Convert raw rows into a list of PurchaseOrder models grouped by ORDER_HEADER_ID."""
        if not rows:
            return []

        # Group rows by ORDER_HEADER_ID
        grouped: dict[str, dict] = defaultdict(lambda: {"hacat": None, "po_files": []})

        for row in rows:
            order_header_id = row[0]
            fk_hacat_id = row[1]
            attachment_name = row[2]
            s3_path = row[3]
            t_s3_source_file_ts = row[4]
            attachment_adjusted_name = row[5]

            grouped[order_header_id]["hacat"] = fk_hacat_id
            grouped[order_header_id]["po_files"].append(
                CedlPoFile(
                    filename=attachment_name,
                    s3path=s3_path,
                    timestamp=t_s3_source_file_ts,
                    originalFilename=attachment_adjusted_name,
                )
            )

        purchase_orders: list[PurchaseOrder] = []
        for order_header_id, data in grouped.items():
            purchase_orders.append(
                PurchaseOrder(
                    poNumber=order_header_id,
                    hacat=data["hacat"],
                    poFiles=data["po_files"],
                )
            )

        return purchase_orders
