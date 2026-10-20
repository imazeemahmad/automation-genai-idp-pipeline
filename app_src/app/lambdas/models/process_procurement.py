from pydantic import BaseModel, Field


class ProcessProcurementRequest(BaseModel):
    procurement_id: str = Field(alias="procurementId")


class ProcessProcurementResponse(BaseModel):
    status: str
    procurement_id: str = Field(serialization_alias="procurementId")
    attachments: list[str] = Field(serialization_alias="attachments")
