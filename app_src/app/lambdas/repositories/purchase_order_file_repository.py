import os
from datetime import datetime, timezone

import boto3

from models.po_file import PurchaseOrderFile, PurchaseOrderFileStatus


class PurchaseOrderFileRepository:
    def __init__(self):
        self._table_name = os.environ["PROCUREMENT_TABLE_NAME"]
        self._dynamodb_client = boto3.resource("dynamodb")
        self._table = self._dynamodb_client.Table(self._table_name)

    def _build_key(self, hacat: str, po_number: str, file_name: str) -> dict:
        return {
            "PK": f"PO_FILE#HACAT#{hacat}#PO#{po_number}",
            "SK": f"PO_FILE#{file_name}",
        }

    def get(
        self, hacat: str, po_number: str, file_name: str
    ) -> PurchaseOrderFile | None:
        response = self._table.get_item(
            Key=self._build_key(hacat, po_number, file_name)
        )
        item = response.get("Item")

        if item is None:
            return None

        item.pop("PK", None)
        item.pop("SK", None)

        return PurchaseOrderFile(
            po_number=item["po_number"],
            filename=item["filename"],
            hacat=item["hacat"],
            status=item["status"],
            timestamp=item["timestamp"],
            original_filename=item["original_filename"],
        )

    def find_by_po_and_status(
        self, hacat: str, po_number: str, status: PurchaseOrderFileStatus
    ) -> list[PurchaseOrderFile]:
        """Retrieve PO file records for a PO/HACAT filtered by status.

        Executes a DynamoDB Query on PK=PO_FILE#HACAT#{hacat}#PO#{po_number}
        and applies a FilterExpression on the status attribute (status is a
        DynamoDB reserved word, so it is aliased via ExpressionAttributeNames).

        Args:
            hacat: The HACAT category code.
            po_number: The purchase order number.
            status: Only records with this status are returned.

        Returns:
            List of PurchaseOrderFile objects. Empty list if no records match.
        """
        response = self._table.query(
            KeyConditionExpression="PK = :pk",
            FilterExpression="#s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":pk": f"PO_FILE#HACAT#{hacat}#PO#{po_number}",
                ":status": status.value,
            },
        )

        items = response.get("Items", [])

        return [
            PurchaseOrderFile(
                po_number=item["po_number"],
                filename=item["filename"],
                hacat=item["hacat"],
                status=item["status"],
                timestamp=item["timestamp"],
                original_filename=item["original_filename"],
            )
            for item in items
        ]

    def batch_create(self, po_files: list[PurchaseOrderFile]) -> None:
        """Create multiple PO file records in DynamoDB using batch_writer.

        Uses DynamoDB batch_writer which automatically handles chunking into
        25-item batches and retries for unprocessed items.

        Deduplicates items by (PK, SK) to avoid DynamoDB BatchWriteItem
        ValidationException when duplicate keys are present. The last
        occurrence wins.

        Args:
            po_files: List of PurchaseOrderFile objects to persist.
        """
        # Deduplicate by composite key — last occurrence wins
        seen: dict[tuple[str, str, str], PurchaseOrderFile] = {}
        for po_file in po_files:
            key = (po_file.hacat, po_file.po_number, po_file.filename)
            seen[key] = po_file

        with self._table.batch_writer() as batch:
            for po_file in seen.values():
                batch.put_item(
                    Item={
                        **self._build_key(
                            po_file.hacat, po_file.po_number, po_file.filename
                        ),
                        "po_number": po_file.po_number,
                        "filename": po_file.filename,
                        "hacat": po_file.hacat,
                        "status": po_file.status.value,
                        "timestamp": str(po_file.timestamp),
                        "original_filename": po_file.original_filename,
                    }
                )

    def update_status(
        self,
        hacat: str,
        po_number: str,
        file_name: str,
        status: "PurchaseOrderFileStatus",
    ) -> None:
        """Update only the status and timestamp fields for a purchase order file."""
        now = datetime.now(timezone.utc).isoformat()

        self._table.update_item(
            Key=self._build_key(hacat, po_number, file_name),
            UpdateExpression="SET #s = :status, #t = :timestamp",
            ExpressionAttributeNames={
                "#s": "status",
                "#t": "timestamp",
            },
            ExpressionAttributeValues={
                ":status": status.value,
                ":timestamp": now,
            },
        )
