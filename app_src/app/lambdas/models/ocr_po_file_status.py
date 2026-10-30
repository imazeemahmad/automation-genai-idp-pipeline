from pydantic import BaseModel, Field


class OcrPoFileGetStatusRequest(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    po_file: str = Field(alias="poFile")
    invocation_arn: str = Field(alias="invocationArn")


class OcrPoFileGetStatusResponse(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    po_file: str = Field(alias="poFile")
    status: str = Field(alias="status")
