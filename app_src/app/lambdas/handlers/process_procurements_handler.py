# pylint: disable=duplicate-code
import os

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from models.process_procurements import ProcessProcurementsRequest
from models.process_procurements import ProcessProcurementsResponse
from repositories.coupa_repository import CoupaRepository
from services.procurements_service import ProcurementsService

logger = Logger()
tracer = Tracer()

s3_client = boto3.client("s3")
bucket_name = os.environ["DATA_BUCKET_NAME"]
coupa_repository = CoupaRepository()
procurements_service = ProcurementsService(
    coupa_repository=coupa_repository,
    s3_client=s3_client,
    bucket_name=bucket_name,
)

@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Event coming from Step Function :

    {
        "procurementIds": ["123"],
    }
    """

    try:
        request = ProcessProcurementsRequest.model_validate(event)

    except ValidationError as exc:
        logger.exception("Invalid input payload")

        raise ValueError(
            f"Payload validation failed: {exc.errors()}"
        ) from exc

    logger.append_keys(
        execution_id=context.aws_request_id
    )

    logger.info("Starting procurements processing")

    procurements = procurements_service.process_procurements(request.procurement_ids)

    logger.info("Procurements processed successfully")

    output = ProcessProcurementsResponse(
        status="SUCCESS",
        procurements=procurements,
    )

    return output.model_dump()
