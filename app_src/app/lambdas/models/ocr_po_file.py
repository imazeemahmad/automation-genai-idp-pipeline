from pydantic import BaseModel, Field


class OcrPoFileRequest(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    # Original filename — DynamoDB tracking key
    po_file: str = Field(alias="poFile")
    # Physical file to send to BDA (converted PDF, or original if no conversion)
    processed_file: str = Field(alias="processedFile")


class OcrPoFileResponse(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    po_file: str = Field(alias="poFile")
    processed_file: str = Field(alias="processedFile")
    invocation_arn: str = Field(alias="invocationArn")
