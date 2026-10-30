from datetime import datetime

from pydantic import BaseModel, Field


class CedlCopyPoFileItem(BaseModel):
    filename: str
    s3path: str
    timestamp: datetime
    original_filename: str = Field(alias="originalFilename")


class CedlCopyPoFilesRequest(BaseModel):
    hacat: str
    po_number: str = Field(alias="poNumber")
    po_files: list[CedlCopyPoFileItem] = Field(alias="poFiles")
    execution_id: str = Field(alias="executionId")


class CedlCopyPoFilesResponseFile(BaseModel):
    filename: str


class CedlCopyPoFilesResponse(BaseModel):
    hacat: str
    po_number: str = Field(alias="poNumber")
    po_files: list[CedlCopyPoFilesResponseFile] = Field(alias="poFiles")
