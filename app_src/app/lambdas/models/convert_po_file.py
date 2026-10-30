from pydantic import BaseModel, Field


class ConvertPoFileRequest(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    po_file: str = Field(alias="poFile")


class ConvertPoFileResponse(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    # Original filename — used as the DynamoDB tracking key
    po_file: str = Field(alias="poFile")
    # Physical file to process downstream (converted PDF, or original if no conversion)
    processed_file: str = Field(alias="processedFile")
