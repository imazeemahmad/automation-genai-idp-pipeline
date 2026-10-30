import json
import os

import boto3
from aws_lambda_powertools import Logger

logger = Logger()

lambda_client = boto3.client("lambda")


class ConversionService:
    """Converts documents to PDF by invoking the LibreOffice converter Lambda.

    This service delegates the actual conversion to a dedicated container Lambda
    that runs LibreOffice headless. It sends S3 keys and the converter Lambda
    handles download, conversion, and upload autonomously.
    """

    def __init__(self) -> None:
        self._converter_lambda_arn = os.environ["LIBREOFFICE_CONVERTER_LAMBDA_ARN"]
        self._bucket_name = os.environ["DATA_BUCKET_NAME"]

    def convert_to_pdf(self, source_key: str, destination_key: str) -> None:
        """Convert a document to PDF by invoking the LibreOffice converter Lambda.

        Args:
            source_key: S3 key of the source document.
            destination_key: S3 key where the converted PDF will be uploaded.

        Raises:
            RuntimeError: If the converter Lambda returns an error.
        """
        payload = {
            "source_key": source_key,
            "destination_key": destination_key,
        }

        logger.info(
            "Invoking LibreOffice converter Lambda",
            extra={
                "source_key": source_key,
                "destination_key": destination_key,
                "converter_lambda_arn": self._converter_lambda_arn,
            },
        )

        response = lambda_client.invoke(
            FunctionName=self._converter_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Check for Lambda-level errors (function error, not invocation error)
        if "FunctionError" in response:
            error_payload = json.loads(response["Payload"].read())
            error_message = error_payload.get("errorMessage", "Unknown error")
            raise RuntimeError(
                f"LibreOffice converter Lambda failed for '{source_key}': {error_message}"
            )

        logger.info(
            "File converted to PDF",
            extra={
                "source_key": source_key,
                "destination_key": destination_key,
                "action": "converted",
            },
        )
