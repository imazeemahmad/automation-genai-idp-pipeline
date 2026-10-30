# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.convert_po_file import ConvertPoFileRequest, ConvertPoFileResponse
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.conversion_service import ConversionService
from services.purchase_order_file_service import PurchaseOrderFileService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_file_repository = PurchaseOrderFileRepository()
conversion_service = ConversionService()
purchase_order_file_service = PurchaseOrderFileService(
    purchase_order_file_repository=purchase_order_file_repository,
    conversion_service=conversion_service,
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(
    event: dict, context: LambdaContext
) -> dict:  # pylint: disable=unused-argument
    """
    Event coming from Step Function:

    {
        "hacat": "HC1001",
        "poNumber": "123456",
        "poFile": "presentation.pptx"
    }
    """

    try:
        request = ConvertPoFileRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=context.aws_request_id,
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
    )

    logger.info("Starting file conversion check")

    processed_filename = purchase_order_file_service.convert_po_file(
        hacat=request.hacat,
        po_number=request.po_number,
        po_file=request.po_file,
    )

    output = ConvertPoFileResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        poFile=request.po_file,
        processedFile=processed_filename,
    )

    return output.model_dump(by_alias=True)
