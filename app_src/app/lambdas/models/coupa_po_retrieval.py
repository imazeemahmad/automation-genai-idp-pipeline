from pydantic import BaseModel, Field

from models.purchase_order import PurchaseOrder


class CoupaPORetrievalRequest(BaseModel):
    po_numbers: list[str] | None = Field(default=None, alias="poNumbers")
    hacat: str = Field(alias="hacat")
    execution_id: str = Field(alias="executionId")


class CoupaPORetrievalResponse(BaseModel):
    status: str
    purchase_orders: list[PurchaseOrder] = Field(alias="purchaseOrders")
