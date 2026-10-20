from pydantic import BaseModel, Field

from models.procurement import Procurement


class ProcessProcurementsRequest(BaseModel):
    procurement_ids: list[str] | None = Field(default=None, alias="procurementIds")


class ProcessProcurementsResponse(BaseModel):
    status: str
    procurements: list[Procurement]
