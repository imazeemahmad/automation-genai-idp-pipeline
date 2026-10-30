# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.ocr_po_file_status import (
    OcrPoFileGetStatusRequest,
    OcrPoFileGetStatusResponse,
)
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.ocr_service import OcrService
from services.purchase_order_file_service import PurchaseOrderFileService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_file_repository = PurchaseOrderFileRepository()
purchase_order_file_objects_repository = PurchaseOrderFileObjectsRepository()
ocr_service = OcrService()
purchase_order_file_service = PurchaseOrderFileService(
    purchase_order_file_repository=purchase_order_file_repository,
    ocr_service=ocr_service,
    purchase_order_file_objects_repository=purchase_order_file_objects_repository,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Checks the status of an OCR job for a purchase order file.

    Event coming from Step Function:

    {
        "hacat": "HC1001",
        "poNumber": "123456",
        "poFile": "document.pdf",
        "invocationArn": "arn:aws:bedrock:eu-west-1:123456789:invocation/abc-123"
    }
    """

    try:
        request = OcrPoFileGetStatusRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=context.aws_request_id,
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
    )

    logger.info("Checking OCR job status")

    status = purchase_order_file_service.get_ocr_status(
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
        invocation_arn=request.invocation_arn,
    )

    logger.info("OCR job status retrieved", extra={"status": status.value})

    output = OcrPoFileGetStatusResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        poFile=request.po_file,
        status=status.value,
    )

    return output.model_dump(by_alias=True)
