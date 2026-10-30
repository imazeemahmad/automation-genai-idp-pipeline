import os
from pathlib import PurePosixPath

from aws_lambda_powertools import Logger
from aws_lambda_powertools.metrics import Metrics, MetricUnit

from models.po_file import PurchaseOrderFileStatus, OCR_TERMINAL_STATUSES
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from services.conversion_service import ConversionService
from services.ocr_service import OcrService

logger = Logger()
metrics = Metrics()

# Extensions natively supported by BDA (async API) — never need conversion.
# Per AWS docs, the BDA async API supports: PDF, TIFF, JPEG, PNG, DOCX.
# The legacy binary .doc format is NOT supported and must be converted to PDF.
BDA_COMPATIBLE_EXTENSIONS = {
    ".pdf",
    ".tiff",
    ".tif",
    ".jpeg",
    ".jpg",
    ".png",
    ".docx",
}

# Extensions that require conversion to PDF before BDA processing
CONVERTIBLE_EXTENSIONS = {
    ".pptx",
    ".xlsx",
    ".ppt",
    ".xls",
    ".odp",
    ".ods",
    ".doc",
}


class PurchaseOrderFileService:

    def __init__(
        self,
        purchase_order_file_repository: PurchaseOrderFileRepository,
        ocr_service: OcrService | None = None,
        purchase_order_file_objects_repository: (
            PurchaseOrderFileObjectsRepository | None
        ) = None,
        conversion_service: ConversionService | None = None,
    ):
        self._purchase_order_file_repository = purchase_order_file_repository
        self._bucket_name = os.environ["DATA_BUCKET_NAME"]
        self._ocr_service = ocr_service
        self._purchase_order_file_objects_repository = (
            purchase_order_file_objects_repository
        )
        self._conversion_service = conversion_service

    def convert_po_file(self, hacat: str, po_number: str, po_file: str) -> str:
        """Convert a purchase order file to PDF if needed.

        Decision logic:
        1. BDA-compatible extension → passthrough (no conversion, no status change)
        2. Convertible extension → convert via ConversionService with status tracking
        3. Unknown extension → passthrough (no conversion, no status change)

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            po_file: The filename of the document.

        Returns:
            The filename to use for downstream processing (original or converted).
        """
        extension = PurePosixPath(po_file).suffix.lower()

        # 1. BDA-compatible files pass through without status update
        if extension in BDA_COMPATIBLE_EXTENSIONS:
            logger.info(
                f"File {po_file} is BDA-compatible, passing through (hacat={hacat})"
            )
            return po_file

        # 2. Unknown extensions pass through
        if extension not in CONVERTIBLE_EXTENSIONS:
            logger.info(
                f"File {po_file} has unknown extension, passing through (hacat={hacat})"
            )
            return po_file

        # 3. Convertible files — invoke LibreOffice converter Lambda with status tracking.
        # Use with_suffix on the full path so a hierarchical attachment name
        # (e.g. "email1.eml/attach_1_devis.pptx") keeps its directory prefix
        # ("email1.eml/attach_1_devis.pdf") instead of being flattened.
        converted_filename = str(PurePosixPath(po_file).with_suffix(".pdf"))

        logger.info(
            f"Starting conversion for file {po_file} of PO {po_number} (hacat={hacat})"
        )

        self._purchase_order_file_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            file_name=po_file,
            status=PurchaseOrderFileStatus.CONVERSION_IN_PROGRESS,
        )

        try:
            source_key = f"{hacat}/incoming/{po_number}/{po_file}"
            destination_key = f"{hacat}/incoming/{po_number}/{converted_filename}"

            self._conversion_service.convert_to_pdf(
                source_key=source_key,
                destination_key=destination_key,
            )

            self._purchase_order_file_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                file_name=po_file,
                status=PurchaseOrderFileStatus.CONVERSION_COMPLETED,
            )

            logger.info(
                f"Conversion completed for PO {po_number}, file {po_file}",
                extra={"result_filename": converted_filename},
            )

            return converted_filename

        except Exception as exc:
            logger.exception(f"Conversion failed for PO {po_number}, file {po_file}")

            self._purchase_order_file_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                file_name=po_file,
                status=PurchaseOrderFileStatus.CONVERSION_FAILED,
            )

            metrics.add_metric(
                name="FileConversionFailed", unit=MetricUnit.Count, value=1
            )
            raise exc

    def ocr_po_file(
        self, hacat: str, po_number: str, po_file: str, processed_file: str
    ) -> str:
        """Launch OCR processing for a purchase order file via Bedrock Data Automation.

        Status is tracked on the original file (po_file), while the physical file
        sent to BDA is processed_file (the converted PDF, or the original if no
        conversion was needed).

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            po_file: The original filename — used as the DynamoDB tracking key.
            processed_file: The physical file to send to BDA.

        Returns:
            The invocation ARN of the async BDA job.
        """
        logger.info(
            f"Starting OCR for file {processed_file} (tracked as {po_file}) "
            f"of PO {po_number} (hacat={hacat})"
        )

        # Update status to OCR_PROCESSING (tracked on the original file)
        self._purchase_order_file_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            file_name=po_file,
            status=PurchaseOrderFileStatus.OCR_PROCESSING,
        )

        try:
            input_s3_uri = f"s3://{self._bucket_name}/{hacat}/incoming/{po_number}/{processed_file}"
            output_s3_uri = f"s3://{self._bucket_name}/{hacat}/ocr-jobs/{po_number}"

            invocation_arn = self._ocr_service.invoke(
                input_s3_uri=input_s3_uri,
                output_s3_uri=output_s3_uri,
            )

            logger.info(
                f"OCR job launched for PO {po_number}, file {processed_file}",
                extra={"invocation_arn": invocation_arn},
            )

            return invocation_arn

        except Exception as exc:
            logger.exception(
                f"OCR invocation failed for PO {po_number}, file {processed_file}"
            )

            self._purchase_order_file_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                file_name=po_file,
                status=PurchaseOrderFileStatus.OCR_FAILED,
            )

            metrics.add_metric(
                name="FileProcessingFailed", unit=MetricUnit.Count, value=1
            )
            raise exc

    def get_ocr_status(
        self, hacat: str, po_number: str, po_file: str, invocation_arn: str
    ) -> PurchaseOrderFileStatus:
        """Check BDA job status and update PO file status accordingly.

        Only queries ocr_service if the current DB status is not terminal.
        If BDA returns completed, copies the OCR result to ocr-data.

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            po_file: The filename of the document.
            invocation_arn: The ARN of the BDA invocation.

        Returns:
            The current PurchaseOrderFileStatus.
        """
        logger.info(
            f"Checking OCR status for PO {po_number}, file {po_file}",
            extra={"invocation_arn": invocation_arn},
        )

        # Check current status in DB
        po_file_record = self._purchase_order_file_repository.get(
            hacat=hacat,
            po_number=po_number,
            file_name=po_file,
        )

        db_status = po_file_record.status if po_file_record else None

        # If already in a terminal state, return immediately
        if db_status in OCR_TERMINAL_STATUSES:
            logger.info(
                f"Status already terminal ({db_status.value}) "
                f"for PO {po_number}, file {po_file}, skipping BDA call",
            )
            return db_status

        # Query BDA for the current status
        status = self._ocr_service.get_status(invocation_arn)

        logger.info(
            f"OCR status '{status.value}' for PO {po_number}, file {po_file}",
        )

        # Update DB if status has changed
        if status != db_status:
            self._purchase_order_file_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                file_name=po_file,
                status=status,
            )
            logger.info(
                f"DynamoDB updated with status {status.value} "
                f"for PO {po_number}, file {po_file}",
            )

        # If completed, copy OCR result
        if status == PurchaseOrderFileStatus.OCR_COMPLETED:
            invocation_id = invocation_arn.rsplit("/", 1)[-1]
            self._purchase_order_file_objects_repository.copy_ocr_result(
                hacat=hacat,
                po_number=po_number,
                filename=po_file,
                invocation_id=invocation_id,
            )
            logger.info(
                f"OCR result copied for PO {po_number}, file {po_file}",
            )
            metrics.add_metric(
                name="FileProcessingSucceeded", unit=MetricUnit.Count, value=1
            )

        elif status == PurchaseOrderFileStatus.OCR_FAILED:
            metrics.add_metric(
                name="FileProcessingFailed", unit=MetricUnit.Count, value=1
            )

        return status
