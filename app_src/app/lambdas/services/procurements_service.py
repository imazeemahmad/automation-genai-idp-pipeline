from aws_lambda_powertools import Logger

from models.procurement import Procurement
from repositories.coupa_repository import CoupaRepository

logger = Logger()


class ProcurementsService:

    def __init__(
        self,
        coupa_repository: CoupaRepository,
        s3_client,
        bucket_name: str,
    ):
        self._coupa_repository = coupa_repository
        self._s3_client = s3_client
        self._bucket_name = bucket_name

    def process_procurements(self, ids: list[str] | None) -> list[Procurement]:
        logger.info(f"Processing procurements {ids}")
        return self._coupa_repository.search_procurements(ids)

    def process_procurement(self, procurement_id: str) -> list[str]:
        """List procurement attachement in S3 bucket with the procurement id as prefix.

        Args:
            procurement_id: The procurement identifier used as S3 key prefix.

        Returns:
            List procurement attachment.
        """
        logger.info(f"Processing procurement {procurement_id}")

        attachments: list[str] = []
        paginator = self._s3_client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=procurement_id):
            for obj in page.get("Contents", []):
                if not obj["Key"].endswith("/"):
                    attachments.append(obj["Key"])

        logger.info(
            f"Found {len(attachments)} attachments for procurement {procurement_id}"
        )
        return attachments
