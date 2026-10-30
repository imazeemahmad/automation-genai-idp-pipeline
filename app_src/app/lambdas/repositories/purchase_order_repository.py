# pylint: disable=duplicate-code
import os
from datetime import datetime, timezone

import boto3

from models.purchase_order import PurchaseOrderRecord, PurchaseOrderStatus


class PurchaseOrderRepository:
    def __init__(self):
        self._table_name = os.environ["PROCUREMENT_TABLE_NAME"]
        self._dynamodb_client = boto3.resource("dynamodb")
        self._table = self._dynamodb_client.Table(self._table_name)

    def _build_key(self, hacat: str, po_number: str, execution_id: str) -> dict:
        return {
            "PK": f"PO#HACAT#{hacat}#PO#{po_number}",
            "SK": f"EXEC#{execution_id}",
        }

    def batch_create(self, records: list[PurchaseOrderRecord]) -> None:
        """Create initial PO tracking items in DynamoDB with PENDING status."""
        now = datetime.now(timezone.utc).isoformat()
        with self._table.batch_writer() as batch:
            for record in records:
                batch.put_item(
                    Item={
                        **self._build_key(
                            record.hacat, record.po_number, record.execution_id
                        ),
                        "po_number": record.po_number,
                        "hacat": record.hacat,
                        "execution_id": record.execution_id,
                        "status": record.status.value,
                        "nb_files": record.nb_files,
                        "timestamp": now,
                    }
                )

    def update_status(
        self,
        hacat: str,
        po_number: str,
        execution_id: str,
        status: PurchaseOrderStatus,
    ) -> None:
        """Update the status and timestamp fields for a purchase order."""
        now = datetime.now(timezone.utc).isoformat()

        self._table.update_item(
            Key=self._build_key(hacat, po_number, execution_id),
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
