from datetime import datetime

from pydantic import BaseModel, Field, field_validator

TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


class CedlExportPoOutputDataRequest(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    timestamp: str = Field(alias="timestamp")
    execution_id: str = Field(alias="executionId")

    @field_validator("hacat", "po_number", "timestamp", "execution_id")
    @classmethod
    def must_be_non_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return v

    @field_validator("timestamp")
    @classmethod
    def must_be_valid_timestamp(cls, v: str) -> str:
        try:
            datetime.strptime(v, TIMESTAMP_FORMAT)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"timestamp must be in format YYYYMMDDTHHMMSSz, got: {v}"
            ) from exc
        return v


class CedlExportPoOutputDataResponse(BaseModel):
    hacat: str = Field(alias="hacat")
    po_number: str = Field(alias="poNumber")
    timestamp: str = Field(alias="timestamp")
    status: str = Field(alias="status")
