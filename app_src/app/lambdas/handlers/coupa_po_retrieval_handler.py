# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.coupa_po_retrieval import CoupaPORetrievalRequest, CoupaPORetrievalResponse
from repositories.coupa_repository import CoupaRepository
from repositories.execution_repository import ExecutionRepository
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

coupa_repository = CoupaRepository()
execution_repository = ExecutionRepository()
purchase_order_repository = PurchaseOrderRepository()
purchase_order_file_repository = PurchaseOrderFileRepository()
purchase_order_service = PurchaseOrderService(
    coupa_repository=coupa_repository,
    execution_repository=execution_repository,
    purchase_order_repository=purchase_order_repository,
    purchase_order_file_repository=purchase_order_file_repository,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(
    event: dict, context: LambdaContext
) -> dict:  # pylint: disable=unused-argument
    """
    Event coming from Step Function :

    {
        "poNumbers": ["123"],
        "hacat": "HC1005",
        "executionId": "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
    }
    """

    try:
        request = CoupaPORetrievalRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=request.execution_id,
        hacat=request.hacat,
    )

    logger.info("Starting purchase orders retrieval")

    purchase_orders = purchase_order_service.retrieve_pos(
        hacat=request.hacat,
        po_numbers=request.po_numbers,
        execution_id=request.execution_id,
    )

    logger.info("Purchase orders retrieved successfully")

    output = CoupaPORetrievalResponse(
        status="SUCCESS",
        purchaseOrders=purchase_orders,
    )

    return output.model_dump(by_alias=True, mode="json")
