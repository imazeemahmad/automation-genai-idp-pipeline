# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.ocr_po_file import OcrPoFileRequest, OcrPoFileResponse
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.ocr_service import OcrService
from services.purchase_order_file_service import PurchaseOrderFileService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_file_repository = PurchaseOrderFileRepository()
ocr_service = OcrService()
purchase_order_file_service = PurchaseOrderFileService(
    purchase_order_file_repository=purchase_order_file_repository,
    ocr_service=ocr_service,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Event coming from Step Function:

    {
        "hacat": "HC1001",
        "poNumber": "123456",
        "poFile": "document.pdf"
    }
    """

    try:
        request = OcrPoFileRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=context.aws_request_id,
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
    )

    logger.info("Starting OCR processing for purchase order file")

    invocation_arn = purchase_order_file_service.ocr_po_file(
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
        processed_file=request.processed_file,
    )

    logger.info("OCR processing initiated successfully")

    output = OcrPoFileResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        poFile=request.po_file,
        processedFile=request.processed_file,
        invocationArn=invocation_arn,
    )

    return output.model_dump(by_alias=True)
