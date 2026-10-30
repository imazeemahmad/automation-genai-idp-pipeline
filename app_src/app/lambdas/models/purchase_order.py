from enum import Enum

from pydantic import BaseModel, Field

from models.po_file import CedlPoFile


class PurchaseOrderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    CONSOLIDATE_IN_PROGRESS = "CONSOLIDATE_IN_PROGRESS"
    CONSOLIDATE_COMPLETED = "CONSOLIDATE_COMPLETED"
    CONSOLIDATE_FAILED = "CONSOLIDATE_FAILED"
    EXPORT_IN_PROGRESS = "EXPORT_IN_PROGRESS"
    EXPORT_COMPLETED = "EXPORT_COMPLETED"
    EXPORT_FAILED = "EXPORT_FAILED"


class PurchaseOrder(BaseModel):
    po_number: str = Field(alias="poNumber")
    hacat: str
    po_files: list[CedlPoFile] = Field(default_factory=list, alias="poFiles")


class PurchaseOrderRecord(BaseModel):
    """Model used for DynamoDB tracking of purchase order processing."""

    po_number: str = Field(alias="poNumber")
    hacat: str
    execution_id: str = Field(alias="executionId")
    status: PurchaseOrderStatus
    nb_files: int = Field(default=0, alias="nbFiles")
