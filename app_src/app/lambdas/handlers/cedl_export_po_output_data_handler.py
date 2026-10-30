# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.cedl_export_po_output_data import (
    CedlExportPoOutputDataRequest,
    CedlExportPoOutputDataResponse,
)
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_repository = PurchaseOrderRepository()
purchase_order_file_objects_repository = PurchaseOrderFileObjectsRepository()

purchase_order_service = PurchaseOrderService(
    purchase_order_repository=purchase_order_repository,
    purchase_order_file_objects_repository=purchase_order_file_objects_repository,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(
    event: dict, context: LambdaContext
) -> dict:  # pylint: disable=unused-argument
    """
    Exports consolidated PO output data to CEDL S3 bucket.

    Event coming from Step Function:

    {
        "hacat": "HC1001",
        "poNumber": "E002754388",
        "timestamp": "2025-07-09T15:44:16+00:00",
        "executionId": "arn:aws:states:eu-west-1:123:execution:wf:exec-1"
    }
    """

    try:
        request = CedlExportPoOutputDataRequest.model_validate(event)
    except ValidationError as exc:
        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=request.execution_id,
        hacat=request.hacat,
        po_number=request.po_number,
    )

    logger.info("Starting CEDL export for PO output data")

    purchase_order_service.export_to_cedl(
        hacat=request.hacat,
        po_number=request.po_number,
        timestamp=request.timestamp,
        execution_id=request.execution_id,
    )

    logger.info("CEDL export completed successfully")

    return CedlExportPoOutputDataResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        timestamp=request.timestamp,
        status="EXPORT_COMPLETED",
    ).model_dump(by_alias=True)
