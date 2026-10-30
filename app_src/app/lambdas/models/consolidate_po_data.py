from pydantic import BaseModel, Field, field_validator


class ConsolidatePoDataRequest(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    execution_id: str = Field(alias="executionId")

    @field_validator("hacat", "po_number", "execution_id")
    @classmethod
    def must_be_non_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return v


class ConsolidatePoDataResponse(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    timestamp: str = Field(alias="timestamp")
    status: str = Field(alias="status")
