import os

import boto3
from aws_lambda_powertools import Logger

from models.po_file import PurchaseOrderFileStatus

logger = Logger()

BDA_STATUS_MAPPING = {
    "Created": PurchaseOrderFileStatus.OCR_PROCESSING,
    "InProgress": PurchaseOrderFileStatus.OCR_PROCESSING,
    "Success": PurchaseOrderFileStatus.OCR_COMPLETED,
    "ServiceError": PurchaseOrderFileStatus.OCR_FAILED,
    "ClientError": PurchaseOrderFileStatus.OCR_FAILED,
}


class OcrService:
    """Abstracts Bedrock Data Automation for OCR processing."""

    def __init__(self):
        self._bda_project_arn = os.environ["BDA_PROJECT_ARN"]
        self._bda_profile_arn = os.environ["BDA_PROFILE_ARN"]
        self._client = boto3.client("bedrock-data-automation-runtime")

    def invoke(self, input_s3_uri: str, output_s3_uri: str) -> str:
        """Invoke Bedrock Data Automation async for OCR processing.

        Args:
            input_s3_uri: S3 URI of the input document.
            output_s3_uri: S3 URI prefix for the output.

        Returns:
            The invocation ARN of the async job.
        """
        logger.info(
            "Invoking Bedrock Data Automation",
            extra={
                "input_s3_uri": input_s3_uri,
                "output_s3_uri": output_s3_uri,
                "bda_project_arn": self._bda_project_arn,
            },
        )

        response = self._client.invoke_data_automation_async(
            inputConfiguration={
                "s3Uri": input_s3_uri,
            },
            outputConfiguration={
                "s3Uri": output_s3_uri,
            },
            dataAutomationConfiguration={
                "dataAutomationProjectArn": self._bda_project_arn,
            },
            dataAutomationProfileArn=self._bda_profile_arn,
        )

        invocation_arn = response["invocationArn"]

        logger.info(
            "Bedrock Data Automation invoked successfully",
            extra={"invocation_arn": invocation_arn},
        )

        return invocation_arn

    def get_status(self, invocation_arn: str) -> PurchaseOrderFileStatus:
        """Get the status of a BDA async invocation mapped to internal status.

        Args:
            invocation_arn: The ARN of the BDA invocation.

        Returns:
            The mapped PurchaseOrderFileStatus.
        """
        logger.info(
            "Getting Bedrock Data Automation async status",
            extra={"invocation_arn": invocation_arn},
        )

        response = self._client.get_data_automation_status(
            invocationArn=invocation_arn,
        )

        bda_status = response["status"]

        internal_status = BDA_STATUS_MAPPING.get(
            bda_status, PurchaseOrderFileStatus.OCR_FAILED
        )

        logger.info(
            f"BDA status '{bda_status}' mapped to '{internal_status.value}'",
            extra={"invocation_arn": invocation_arn},
        )

        return internal_status
