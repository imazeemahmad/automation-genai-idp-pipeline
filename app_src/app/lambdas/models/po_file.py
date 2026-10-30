from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CedlPoFile(BaseModel):
    filename: str
    s3path: str
    timestamp: datetime
    original_filename: str = Field(alias="originalFilename")


class PurchaseOrderFileStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOAD_IN_PROGRESS = "DOWNLOAD_IN_PROGRESS"
    DOWNLOAD_COMPLETED = "DOWNLOAD_COMPLETED"
    CONVERSION_IN_PROGRESS = "CONVERSION_IN_PROGRESS"
    CONVERSION_COMPLETED = "CONVERSION_COMPLETED"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    OCR_PROCESSING = "OCR_PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    OCR_FAILED = "OCR_FAILED"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"


class PurchaseOrderFile(BaseModel):
    po_number: str
    filename: str
    hacat: str
    status: PurchaseOrderFileStatus
    timestamp: datetime
    original_filename: str


OCR_TERMINAL_STATUSES = {
    PurchaseOrderFileStatus.OCR_COMPLETED,
    PurchaseOrderFileStatus.OCR_FAILED,
}
