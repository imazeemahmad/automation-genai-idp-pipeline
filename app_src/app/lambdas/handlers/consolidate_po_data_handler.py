# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.consolidate_po_data import (
    ConsolidatePoDataRequest,
    ConsolidatePoDataResponse,
)
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.llm_service import LlmService
from services.purchase_order_service import PurchaseOrderService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_repository = PurchaseOrderRepository()
purchase_order_file_repository = PurchaseOrderFileRepository()
purchase_order_file_objects_repository = PurchaseOrderFileObjectsRepository()
llm_service = LlmService()
purchase_order_service = PurchaseOrderService(
    purchase_order_repository=purchase_order_repository,
    purchase_order_file_repository=purchase_order_file_repository,
    purchase_order_file_objects_repository=purchase_order_file_objects_repository,
    llm_service=llm_service,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(
    event: dict, context: LambdaContext
) -> dict:  # pylint: disable=unused-argument
    """
    Consolidates extracted data from all PO attachments into a single output.

    The handler queries DynamoDB at runtime to retrieve PO file records,
    rather than receiving them in the event payload.

    Event coming from Step Function:

    {
        "hacat": "HC1001",
        "poNumber": "E002754388",
        "executionId": "arn:aws:states:eu-west-1:123:execution:wf:exec-1"
    }
    """

    try:
        request = ConsolidatePoDataRequest.model_validate(event)
    except ValidationError as exc:
        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=request.execution_id,
        hacat=request.hacat,
        po_number=request.po_number,
    )

    logger.info("Starting PO data consolidation")

    status, timestamp = purchase_order_service.consolidate(
        hacat=request.hacat,
        po_number=request.po_number,
        execution_id=request.execution_id,
    )

    logger.info("PO data consolidation completed successfully")

    return ConsolidatePoDataResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        timestamp=timestamp,
        status=status,
    ).model_dump(by_alias=True)
