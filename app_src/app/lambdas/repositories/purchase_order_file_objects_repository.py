import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities import parameters
from botocore.exceptions import ClientError

logger = Logger()

ssm_provider = parameters.SSMProvider()

TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


class PurchaseOrderFileObjectsRepository:
    def __init__(self):
        self._source_bucket_name = os.environ.get("CEDL_BUCKET_NAME", "")
        self._source_bucket_prefix = os.environ.get("CEDL_BUCKET_PREFIX", "")
        self._data_bucket_name = os.environ["DATA_BUCKET_NAME"]
        self._intermediate_role_arn = os.environ.get("COUPA_CROSS_ACCOUNT_ROLE_ARN", "")
        self._cross_account_role_arn = os.environ.get("CEDL_CROSS_ACCOUNT_ROLE_ARN", "")
        self._ssm_prefix = os.environ.get("SSM_PREFIX", "")
        self._ssm_max_age = int(os.environ.get("SSM_MAX_AGE", "300"))
        self._s3_client = boto3.client("s3")

    def _get_cross_account_s3_client(self):
        """Assume role chain and return an S3 client with final cross-account credentials.

        1. Assume the intermediate role (same account, grants STS permissions).
        2. From that session, assume the final cross-account role (CEDL account).
        """
        sts_client = boto3.client("sts")

        # Step 1: Assume intermediate role
        intermediate_response = sts_client.assume_role(
            RoleArn=self._intermediate_role_arn,
            RoleSessionName="cedl-copy-po-files",
        )

        intermediate_credentials = intermediate_response["Credentials"]
        intermediate_sts = boto3.client(
            "sts",
            aws_access_key_id=intermediate_credentials["AccessKeyId"],
            aws_secret_access_key=intermediate_credentials["SecretAccessKey"],
            aws_session_token=intermediate_credentials["SessionToken"],
        )

        # Step 2: Assume final cross-account role with external ID
        external_id = ssm_provider.get(
            f"{self._ssm_prefix}/coupa/crossAccountExternalId",
            max_age=self._ssm_max_age,
            decrypt=True,
        )

        logger.info(
            "Assuming final cross-account role",
            extra={
                "role_arn": self._cross_account_role_arn,
                "external_id_length": len(external_id) if external_id else 0,
            },
        )

        final_response = intermediate_sts.assume_role(
            RoleArn=self._cross_account_role_arn,
            RoleSessionName="cedl-cross-account-session",
            ExternalId=external_id,
        )

        final_credentials = final_response["Credentials"]
        return boto3.client(
            "s3",
            aws_access_key_id=final_credentials["AccessKeyId"],
            aws_secret_access_key=final_credentials["SecretAccessKey"],
            aws_session_token=final_credentials["SessionToken"],
        )

    def copy(self, source_key: str, hacat: str, po_number: str, filename: str) -> None:
        """Copy a file from the CEDL bucket to the data bucket.

        Destination: <hacat>/incoming/<po_number>/<filename>.
        """
        destination_key = f"{hacat}/incoming/{po_number}/{filename}"

        full_source_key = (
            f"{self._source_bucket_prefix}/{source_key}"
            if self._source_bucket_prefix
            else source_key
        )

        logger.info(
            "Copying S3 object",
            extra={
                "source_bucket": self._source_bucket_name,
                "source_key": full_source_key,
                "destination_bucket": self._data_bucket_name,
                "destination_key": destination_key,
            },
        )

        # Download from source bucket using cross-account credentials
        cross_account_s3 = self._get_cross_account_s3_client()
        response = cross_account_s3.get_object(
            Bucket=self._source_bucket_name, Key=full_source_key
        )

        # Upload to destination bucket using the Lambda's own credentials
        self._s3_client.put_object(
            Bucket=self._data_bucket_name,
            Key=destination_key,
            Body=response["Body"].read(),
        )

    def get_ocr_result(self, hacat: str, po_number: str, filename: str) -> str:
        """Retrieve the OCR output for a PO file and decode it as UTF-8 text.

        Reads from: <hacat>/ocr-data/<po_number>/<filename>.md

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            filename: The filename of the document (including extension).

        Returns:
            The OCR content as a UTF-8 string.
        """
        key = f"{hacat}/ocr-data/{po_number}/{filename}.md"
        logger.info(
            "Reading OCR result", extra={"bucket": self._data_bucket_name, "key": key}
        )
        response = self._s3_client.get_object(Bucket=self._data_bucket_name, Key=key)
        return response["Body"].read().decode("utf-8")

    def get_mapping(self, s3_key: str) -> str | None:
        """Read a mapping object at the given key from the data bucket.

        Follows the same pattern as `get_ocr_result` but tolerates a missing
        object: if the file does not exist (NoSuchKey / ClientError 404), an
        info message is logged and None is returned. Any other S3 error is re-raised.

        Args:
            s3_key: The S3 key of the mapping object in the data bucket.

        Returns:
            The mapping content as a UTF-8 string, or None if the object
            does not exist.
        """
        logger.info(
            "Reading mapping file",
            extra={"bucket": self._data_bucket_name, "key": s3_key},
        )
        try:
            response = self._s3_client.get_object(
                Bucket=self._data_bucket_name, Key=s3_key
            )
            return response["Body"].read().decode("utf-8")
        except self._s3_client.exceptions.NoSuchKey:
            logger.info("Mapping file not found", extra={"key": s3_key})
            return None
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                logger.info("Mapping file not found (404)", extra={"key": s3_key})
                return None
            raise

    def put_consolidated_data(
        self, hacat: str, po_number: str, timestamp: datetime, data: str
    ) -> None:
        """Store consolidated JSON output in S3.

        Writes to: {hacat}/output/{po_number}/{po_number}_{ts_str}.json

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            timestamp: The UTC datetime for the output filename.
            data: The consolidated JSON string.
        """
        ts_str = timestamp.strftime(TIMESTAMP_FORMAT)
        key = f"{hacat}/output/{po_number}/{po_number}_{ts_str}.json"
        logger.info(
            "Writing consolidated data",
            extra={"bucket": self._data_bucket_name, "key": key},
        )
        self._s3_client.put_object(
            Bucket=self._data_bucket_name,
            Key=key,
            Body=data.encode("utf-8"),
            ContentType="application/json",
        )

    def export(
        self,
        hacat: str,
        po_number: str,
        timestamp: datetime,
    ) -> None:
        """Copy consolidated JSON from data bucket to CEDL bucket via cross-account role chain.

        Reads from: {hacat}/output/{po_number}/{po_number}_{ts_str}.json in data bucket
        Resolves CEDL export path from SSM
        Writes to: {CEDL_Bucket_Prefix}/{cedl_export_path}/{date_folder}/
            {po_number}_{ts_str}.json in CEDL bucket

        This mirrors the `copy()` pattern — the repository handles the full read + write internally.

        Args:
            hacat: The HACAT category code (used to resolve CEDL export path from SSM).
            po_number: The purchase order number.
            timestamp: The UTC datetime object.
        """
        ts_str = timestamp.strftime(TIMESTAMP_FORMAT)
        date_folder = timestamp.strftime("%Y-%m-%d")

        # Read consolidated data from data bucket
        source_key = f"{hacat}/output/{po_number}/{po_number}_{ts_str}.json"
        logger.info(
            "Reading consolidated data for export",
            extra={"bucket": self._data_bucket_name, "key": source_key},
        )
        response = self._s3_client.get_object(
            Bucket=self._data_bucket_name, Key=source_key
        )
        data = response["Body"].read()

        # Resolve CEDL export path from SSM
        cedl_export_path = ssm_provider.get(
            f"{self._ssm_prefix}/hacat/{hacat}/cedlExportPath",
            max_age=self._ssm_max_age,
        )

        # Write to CEDL bucket
        destination_key = (
            f"{self._source_bucket_prefix}/{cedl_export_path}"
            f"/{date_folder}/{po_number}_{ts_str}.json"
        )
        logger.info(
            "Writing export data to CEDL bucket",
            extra={
                "bucket": self._source_bucket_name,
                "key": destination_key,
            },
        )
        cross_account_s3 = self._get_cross_account_s3_client()
        cross_account_s3.put_object(
            Bucket=self._source_bucket_name,
            Key=destination_key,
            Body=data,
            ContentType="application/json",
        )

    def copy_ocr_result(
        self, hacat: str, po_number: str, filename: str, invocation_id: str
    ) -> None:
        """Copy the BDA OCR result to the ocr-data folder.

        Source: <hacat>/ocr-jobs/<po_number>/<invocationId>/0/standard_output/0/result.md
        Destination: <hacat>/ocr-data/<po_number>/<filename>.md

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            filename: The base filename (without extension) for the destination.
            invocation_id: The invocation ID extracted from the BDA ARN.
        """
        source_key = (
            f"{hacat}/ocr-jobs/{po_number}/{invocation_id}"
            f"/0/standard_output/0/result.md"
        )
        destination_key = f"{hacat}/ocr-data/{po_number}/{filename}.md"

        logger.info(
            "Copying OCR result",
            extra={
                "source_bucket": self._data_bucket_name,
                "source_key": source_key,
                "destination_bucket": self._data_bucket_name,
                "destination_key": destination_key,
            },
        )

        self._s3_client.copy_object(
            Bucket=self._data_bucket_name,
            Key=destination_key,
            CopySource={
                "Bucket": self._data_bucket_name,
                "Key": source_key,
            },
        )

    def download_incoming_file(
        self, hacat: str, po_number: str, filename: str
    ) -> bytes:
        """Download an incoming PO file from the data bucket.

        Reads from: {hacat}/incoming/{po_number}/{filename}

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            filename: The filename of the document.

        Returns:
            Raw bytes of the file content.
        """
        key = f"{hacat}/incoming/{po_number}/{filename}"
        logger.info(
            "Downloading incoming file",
            extra={"bucket": self._data_bucket_name, "key": key},
        )
        response = self._s3_client.get_object(Bucket=self._data_bucket_name, Key=key)
        return response["Body"].read()

    def upload_incoming_file(
        self,
        hacat: str,
        po_number: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a file to the incoming folder of the data bucket.

        Writes to: {hacat}/incoming/{po_number}/{filename}

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            filename: The filename for the S3 object.
            content: Raw bytes to upload.
            content_type: MIME type for the S3 object.
        """
        key = f"{hacat}/incoming/{po_number}/{filename}"
        logger.info(
            "Uploading incoming file",
            extra={"bucket": self._data_bucket_name, "key": key},
        )
        self._s3_client.put_object(
            Bucket=self._data_bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
