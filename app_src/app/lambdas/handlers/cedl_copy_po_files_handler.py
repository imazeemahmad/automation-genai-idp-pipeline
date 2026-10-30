# pylint: disable=duplicate-code
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.cedl_copy_po_files import (
    CedlCopyPoFilesRequest,
    CedlCopyPoFilesResponse,
    CedlCopyPoFilesResponseFile,
)
from models.po_file import CedlPoFile
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

purchase_order_repository = PurchaseOrderRepository()
purchase_order_file_repository = PurchaseOrderFileRepository()
purchase_order_file_objects_repository = PurchaseOrderFileObjectsRepository()

purchase_order_service = PurchaseOrderService(
    purchase_order_repository=purchase_order_repository,
    purchase_order_file_repository=purchase_order_file_repository,
    purchase_order_file_objects_repository=purchase_order_file_objects_repository,
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
        "hacat": "HC1005",
        "poNumber": "E002754388",
        "poFiles": [
            {
                "filename": "1.pdf",
                "s3path": "ORDER_HEADER/2025/07/09/154416/attachments/5396937/1.pdf",
                "timestamp": "2025-07-09T15:44:16+00:00"
            }
        ],
        "executionId": "arn:aws:states:eu-west-1:123:execution:wf:exec-1"
    }
    """

    try:
        request = CedlCopyPoFilesRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(f"Payload validation failed: {exc.errors()}") from exc

    logger.append_keys(
        execution_id=request.execution_id,
        po_number=request.po_number,
        hacat=request.hacat,
    )

    logger.info("Starting PO files download from CEDL")

    po_files_input = [
        CedlPoFile(
            filename=f.filename,
            s3path=f.s3path,
            timestamp=f.timestamp,
            originalFilename=f.original_filename,
        )
        for f in request.po_files
    ]

    downloaded_files = purchase_order_service.download_po_files(
        hacat=request.hacat,
        po_number=request.po_number,
        po_files=po_files_input,
        execution_id=request.execution_id,
    )

    logger.info("PO files downloaded successfully")

    output = CedlCopyPoFilesResponse(
        hacat=request.hacat,
        poNumber=request.po_number,
        poFiles=[CedlCopyPoFilesResponseFile(filename=f) for f in downloaded_files],
    )

    return output.model_dump(by_alias=True, mode="json")
