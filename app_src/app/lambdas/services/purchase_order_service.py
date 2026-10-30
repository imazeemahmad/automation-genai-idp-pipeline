import json
import os
import time
from datetime import datetime, timezone
from pathlib import PurePosixPath

from aws_lambda_powertools import Logger
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from aws_lambda_powertools.utilities import parameters

from models.po_file import CedlPoFile, PurchaseOrderFile, PurchaseOrderFileStatus
from models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderRecord,
    PurchaseOrderStatus,
)
from parsers.email_parser_factory import parse_email
from repositories.coupa_repository import CoupaRepository
from repositories.execution_repository import ExecutionRepository
from repositories.purchase_order_file_objects_repository import (
    TIMESTAMP_FORMAT,
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.llm_service import LlmService

logger = Logger()
metrics = Metrics()
ssm_provider = parameters.SSMProvider()


class PurchaseOrderService:

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        coupa_repository: CoupaRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
        purchase_order_repository: PurchaseOrderRepository | None = None,
        purchase_order_file_repository: PurchaseOrderFileRepository | None = None,
        purchase_order_file_objects_repository: (
            PurchaseOrderFileObjectsRepository | None
        ) = None,
        llm_service: LlmService | None = None,
    ):
        self._coupa_repository = coupa_repository
        self._execution_repository = execution_repository
        self._purchase_order_repository = purchase_order_repository
        self._purchase_order_file_repository = purchase_order_file_repository
        self._purchase_order_file_objects_repository = (
            purchase_order_file_objects_repository
        )
        self._llm_service = llm_service
        self._ssm_prefix = os.environ.get("SSM_PREFIX", "")
        self._ssm_max_age = int(os.environ.get("SSM_MAX_AGE", "300"))

    def retrieve_pos(
        self,
        hacat: str,
        execution_id: str,
        po_numbers: list[str] | None = None,
    ) -> list[PurchaseOrder]:
        logger.info(
            "Retrieving purchase orders with hacat=%s, po_numbers=%s", hacat, po_numbers
        )

        since = None
        batch_size = None
        if not po_numbers:
            since = self._execution_repository.get_last_execution(hacat)
            batch_size = int(
                ssm_provider.get(
                    f"{self._ssm_prefix}/hacat/{hacat}/batchSize",
                    max_age=self._ssm_max_age,
                )
            )
            logger.info("Batch size for hacat=%s: %d", hacat, batch_size)

        # Load allowed file extensions from SSM
        allowed_extensions = self._load_allowed_extensions(hacat)

        purchase_orders = self._coupa_repository.retrieve_po(
            po_numbers=po_numbers,
            hacat=hacat,
            since=since,
            batch_size=batch_size,
        )

        # Compute the cursor timestamp used to advance lastExecution.
        # We use the max of each PO's earliest file timestamp — this
        # matches the ordering criterion of the sub-query (ORDER BY
        # MIN(T_S3_SOURCE_FILE_TS)) so that the next run with >= will
        # re-include any PO whose MIN was equal to this value (handled
        # by idempotence) without skipping POs that weren't in this batch.
        last_execution_cursor = self._compute_last_execution_cursor(purchase_orders)

        self._filter_files_by_extension(purchase_orders, allowed_extensions, hacat)

        records = [
            PurchaseOrderRecord(
                poNumber=po.po_number,
                hacat=hacat,
                executionId=execution_id,
                status=PurchaseOrderStatus.PENDING,
                nbFiles=len(po.po_files),
            )
            for po in purchase_orders
        ]
        self._purchase_order_repository.batch_create(records)

        # Create PO file records with PENDING status
        po_file_records = [
            PurchaseOrderFile(
                po_number=po.po_number,
                filename=po_file.filename,
                hacat=hacat,
                status=PurchaseOrderFileStatus.PENDING,
                timestamp=po_file.timestamp,
                original_filename=po_file.original_filename,
            )
            for po in purchase_orders
            for po_file in po.po_files
        ]
        if po_file_records:
            self._purchase_order_file_repository.batch_create(po_file_records)

        if not po_numbers:
            # Advance lastExecution so the next run picks up where we left off.
            if last_execution_cursor is not None:
                self._execution_repository.update_last_execution(
                    hacat, last_execution_cursor
                )
                logger.info(
                    "Updated lastExecution to cursor",
                    extra={
                        "hacat": hacat,
                        "last_execution_cursor": str(last_execution_cursor),
                    },
                )
            else:
                logger.info(
                    "No files retrieved — lastExecution not updated",
                    extra={"hacat": hacat},
                )

        metrics.add_metric(
            name="PurchaseOrdersRetrieved",
            unit=MetricUnit.Count,
            value=len(purchase_orders),
        )

        return purchase_orders

    def _load_allowed_extensions(self, hacat: str) -> set[str]:
        """Load the set of allowed file extensions (lowercased) from SSM."""
        allowed_extensions = {
            ext.lower()
            for ext in json.loads(
                ssm_provider.get(
                    f"{self._ssm_prefix}/hacat/{hacat}/allowedFileExtensions",
                    max_age=self._ssm_max_age,
                )
            )
        }
        logger.debug(
            "Loaded allowed extensions for hacat=%s: %s", hacat, allowed_extensions
        )
        return allowed_extensions

    @staticmethod
    def _filter_files_by_extension(
        purchase_orders: list[PurchaseOrder],
        allowed_extensions: set[str],
        hacat: str,
    ) -> None:
        """Remove files whose extension is not in *allowed_extensions* (in-place)."""
        for po in purchase_orders:
            original_count = len(po.po_files)
            kept = []
            for po_file in po.po_files:
                ext = PurePosixPath(po_file.filename).suffix.lower()
                if ext in allowed_extensions:
                    kept.append(po_file)
                else:
                    logger.info(
                        "File ignored: extension not allowed",
                        extra={
                            "ignored_filename": po_file.filename,
                            "extension": ext,
                            "hacat": hacat,
                            "allowed_extensions": sorted(allowed_extensions),
                        },
                    )
            po.po_files = kept
            metrics.add_metric(
                name="FilesFilteredByExtension",
                unit=MetricUnit.Count,
                value=original_count - len(kept),
            )

    @staticmethod
    def _compute_last_execution_cursor(
        purchase_orders: list[PurchaseOrder],
    ) -> datetime | None:
        """Return the timestamp to store as ``lastExecution``.

        For each PO, compute its earliest file timestamp (the ``MIN`` that
        the Snowflake sub-query uses to rank POs). Then return the **maximum**
        of those per-PO minimums.

        This ensures the next run (using ``>=``) will re-include any PO whose
        ``MIN(timestamp)`` equals the cursor (handled by idempotence) without
        jumping over POs that were not part of the current batch.

        Returns ``None`` when *purchase_orders* is empty or contains no files.
        """
        per_po_mins: list[datetime] = []
        for po in purchase_orders:
            if po.po_files:
                per_po_mins.append(min(f.timestamp for f in po.po_files))
        return max(per_po_mins) if per_po_mins else None

    def download_po_files(
        self,
        hacat: str,
        po_number: str,
        po_files: list[CedlPoFile],
        execution_id: str,
    ) -> list[str]:
        """Download PO files from CEDL bucket to data bucket.

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            po_files: List of PO file objects with 'filename' and 's3path' keys.
            execution_id: The Step Function execution ID.

        Returns the list of successfully downloaded filenames.
        """
        if not po_files:
            logger.info("No files to download for PO %s", po_number)
            metrics.add_metric(name="FilesDownloaded", unit=MetricUnit.Count, value=0)
            return []

        # Update PO status to PROCESSING
        self._purchase_order_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            execution_id=execution_id,
            status=PurchaseOrderStatus.PROCESSING,
        )

        downloaded_files: list[str] = []

        for po_file in po_files:
            filename = po_file.filename
            s3path = po_file.s3path
            extension = PurePosixPath(filename).suffix.lower()

            try:
                if extension in (".eml", ".msg"):
                    # Explode email attachments (.eml / .msg) into individual PO files
                    exploded_files = self._process_email_file(hacat, po_number, po_file)
                    downloaded_files.extend(exploded_files)
                    continue

                # Update file status to DOWNLOAD_IN_PROGRESS
                self._purchase_order_file_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    file_name=filename,
                    status=PurchaseOrderFileStatus.DOWNLOAD_IN_PROGRESS,
                )

                # Copy file from CEDL bucket to data bucket
                self._purchase_order_file_objects_repository.copy(
                    source_key=s3path,
                    hacat=hacat,
                    po_number=po_number,
                    filename=filename,
                )

                # Update file status to DOWNLOAD_COMPLETED
                self._purchase_order_file_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    file_name=filename,
                    status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
                )

                downloaded_files.append(filename)

            except Exception as exc:
                logger.error(
                    f"Failed to download file {filename} for PO {po_number}",
                    exc_info=exc,
                )

                # Update file status to DOWNLOAD_FAILED
                self._purchase_order_file_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    file_name=filename,
                    status=PurchaseOrderFileStatus.DOWNLOAD_FAILED,
                )

                # Update PO status to ERROR
                self._purchase_order_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    execution_id=execution_id,
                    status=PurchaseOrderStatus.DOWNLOAD_FAILED,
                )

                metrics.add_metric(
                    name="PurchaseOrderFailed", unit=MetricUnit.Count, value=1
                )
                raise

        metrics.add_metric(
            name="FilesDownloaded",
            unit=MetricUnit.Count,
            value=len(downloaded_files),
        )

        return downloaded_files

    def _process_email_file(
        self, hacat: str, po_number: str, po_file: CedlPoFile
    ) -> list[str]:
        """Download, parse, and extract attachments from an email file.

        Supports both ``.eml`` (MIME, stdlib) and ``.msg`` (Outlook OLE,
        extract-msg). The parser is selected from the file extension.

        Lifecycle for the email PO_FILE record (created as PENDING in
        retrieve_pos): PENDING -> DOWNLOAD_IN_PROGRESS -> DOWNLOAD_COMPLETED.

        The raw email is copied from CEDL to incoming/ for traceability, read
        back from the data bucket, parsed, and each allowed attachment is
        uploaded to incoming/{email}/{attachment} with a matching PO_FILE
        record. The email body is NOT processed.

        Args:
            hacat: The HACAT code.
            po_number: The purchase order number.
            po_file: The email PO file descriptor (.eml or .msg).

        Returns:
            The list of extracted attachment filenames (empty if none).
        """
        filename = po_file.filename

        # 1. Mark the existing email PO_FILE record as DOWNLOAD_IN_PROGRESS
        self._purchase_order_file_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            file_name=filename,
            status=PurchaseOrderFileStatus.DOWNLOAD_IN_PROGRESS,
        )

        # 2. Copy the raw email from CEDL to incoming/ for traceability
        self._purchase_order_file_objects_repository.copy(
            source_key=po_file.s3path,
            hacat=hacat,
            po_number=po_number,
            filename=filename,
        )

        # 3. Read the raw email back from the data bucket to parse it
        raw_content = (
            self._purchase_order_file_objects_repository.download_incoming_file(
                hacat=hacat,
                po_number=po_number,
                filename=filename,
            )
        )

        # 4. Parse (parser chosen by extension) and store allowed attachments
        parsed = parse_email(filename, raw_content)
        attachment_filenames = self._store_email_attachments(
            hacat, po_number, filename, parsed.attachments
        )

        # 5. Mark the email record DOWNLOAD_COMPLETED
        self._purchase_order_file_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            file_name=filename,
            status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
        )

        # 6. Create a PO_FILE record per extracted attachment
        if attachment_filenames:
            now = datetime.now(timezone.utc)
            att_records = [
                PurchaseOrderFile(
                    po_number=po_number,
                    filename=att_path,
                    hacat=hacat,
                    status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
                    timestamp=now,
                    original_filename=att_path,
                )
                for att_path in attachment_filenames
            ]
            self._purchase_order_file_repository.batch_create(att_records)

        logger.info(
            "Email file processed",
            extra={
                "email_filename": filename,
                "attachments_found": len(parsed.attachments),
                "attachments_kept": len(attachment_filenames),
            },
        )

        return attachment_filenames

    def _store_email_attachments(
        self, hacat: str, po_number: str, email_filename: str, attachments: list
    ) -> list[str]:
        """Filter attachments by allowed extensions and upload the kept ones.

        Each kept attachment is uploaded to ``incoming/{email}/{attachment}``.
        Returns the hierarchical paths of the stored attachments.
        """
        allowed_extensions = self._load_allowed_extensions(hacat)
        stored_paths: list[str] = []
        for att in attachments:
            ext = PurePosixPath(att.filename).suffix.lower()
            if ext not in allowed_extensions:
                logger.info(
                    "Email attachment ignored: extension not allowed",
                    extra={
                        "ignored_filename": att.filename,
                        "extension": ext,
                        "email": email_filename,
                        "hacat": hacat,
                    },
                )
                continue

            att_path = f"{email_filename}/{att.filename}"
            self._purchase_order_file_objects_repository.upload_incoming_file(
                hacat=hacat,
                po_number=po_number,
                filename=att_path,
                content=att.content,
                content_type=att.content_type,
            )
            stored_paths.append(att_path)

        return stored_paths

    def _assemble_documents(self, hacat: str, po_number: str) -> list[dict]:
        """Assemble the documents array from OCR outputs for a PO.

        Queries DynamoDB for all file records for the PO and reads each file's
        OCR markdown result. Returns a list of {DOCUMENT_NAME, CONTENT} dicts.
        """
        po_files = self._purchase_order_file_repository.find_by_po_and_status(
            hacat, po_number, PurchaseOrderFileStatus.OCR_COMPLETED
        )

        documents = []
        for po_file in po_files:
            ocr_content = self._purchase_order_file_objects_repository.get_ocr_result(
                hacat=hacat,
                po_number=po_number,
                filename=po_file.filename,
            )
            documents.append(
                {
                    "DOCUMENT_NAME": po_file.original_filename,
                    "CONTENT": ocr_content,
                }
            )

        return documents

    def _resolve_mapping(self, hacat: str) -> str | None:
        """Resolve the optional mapping.json content for a HACAT.

        Reads the `mappingS3Key` SSM parameter (tolerant to a missing
        parameter) and, when it points to a non-empty key, reads the mapping
        file from the data bucket. Returns the mapping content, or None when
        no mapping is configured or the file is absent.
        """
        try:
            mapping_s3_key = ssm_provider.get(
                f"{self._ssm_prefix}/hacat/{hacat}/mappingS3Key",
                max_age=self._ssm_max_age,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.info(
                "mappingS3Key not found — consolidating without mapping",
                extra={"hacat": hacat},
            )
            return None

        if not (mapping_s3_key and mapping_s3_key.strip()):
            return None

        return self._purchase_order_file_objects_repository.get_mapping(
            s3_key=mapping_s3_key.strip(),
        )

    def consolidate(
        self,
        hacat: str,
        po_number: str,
        execution_id: str,
    ) -> tuple[str, str]:
        """Consolidate OCR outputs for a PO via a single Bedrock invocation.

        Reads all OCR markdown files, assembles them into a documents array,
        invokes Bedrock Prompt Management, and stores the consolidated result.

        Returns:
            A tuple of (status, timestamp).

        Raises:
            Exception on any failure (after setting CONSOLIDATE_FAILED status).
        """
        timestamp = datetime.now(timezone.utc)

        # Update PO status to CONSOLIDATE_IN_PROGRESS
        self._purchase_order_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            execution_id=execution_id,
            status=PurchaseOrderStatus.CONSOLIDATE_IN_PROGRESS,
        )

        try:
            # Assemble documents array from OCR outputs
            documents = self._assemble_documents(hacat, po_number)

            if not documents:
                raise ValueError(f"No files found for PO {po_number}")

            # Resolve prompt ARN from SSM
            prompt_arn = ssm_provider.get(
                f"{self._ssm_prefix}/hacat/{hacat}/llmExtractPromptArn",
                max_age=self._ssm_max_age,
            )

            # Assemble prompt variables. "documents" is always present.
            prompt_variables = {"documents": json.dumps(documents)}
            mapping_content = self._resolve_mapping(hacat)
            if mapping_content is not None:
                prompt_variables["mappings"] = mapping_content

            # Invoke LLM for extraction + consolidation
            start_time = time.time()
            consolidated_data = self._llm_service.invoke(
                model_id=prompt_arn,
                prompt_variables=prompt_variables,
            )
            llm_duration_ms = (time.time() - start_time) * 1000
            metrics.add_metric(
                name="LlmDuration", unit=MetricUnit.Milliseconds, value=llm_duration_ms
            )

            # Store consolidated output
            self._purchase_order_file_objects_repository.put_consolidated_data(
                hacat=hacat,
                po_number=po_number,
                timestamp=timestamp,
                data=consolidated_data,
            )

            # Update PO status to CONSOLIDATE_COMPLETED
            self._purchase_order_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                execution_id=execution_id,
                status=PurchaseOrderStatus.CONSOLIDATE_COMPLETED,
            )

            return (
                PurchaseOrderStatus.CONSOLIDATE_COMPLETED.value,
                timestamp.strftime(TIMESTAMP_FORMAT),
            )

        except Exception as original_error:
            logger.error(
                "Consolidation failed",
                exc_info=original_error,
                extra={"hacat": hacat, "po_number": po_number, "step": "consolidation"},
            )
            # Attempt to update PO status to CONSOLIDATE_FAILED
            try:
                self._purchase_order_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    execution_id=execution_id,
                    status=PurchaseOrderStatus.CONSOLIDATE_FAILED,
                )
            except Exception as dynamo_error:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Failed to write CONSOLIDATE_FAILED status to DynamoDB",
                    exc_info=dynamo_error,
                )

            metrics.add_metric(
                name="PurchaseOrderFailed", unit=MetricUnit.Count, value=1
            )
            raise original_error

    def export_to_cedl(
        self,
        hacat: str,
        po_number: str,
        timestamp: str,
        execution_id: str,
    ) -> None:
        """Export consolidated PO data to the CEDL bucket.

        Reads the consolidated JSON from the data bucket, resolves the
        CEDL export path from SSM, derives a date folder from the timestamp,
        and writes the data to the CEDL bucket via cross-account role chain.

        Args:
            hacat: The HACAT category code.
            po_number: The purchase order number.
            timestamp: The formatted timestamp string (YYYYMMDDTHHMMSSz)
                from the consolidation step.
            execution_id: The Step Function execution ID.

        Raises:
            Exception on any failure (after setting EXPORT_FAILED status).
        """
        # Update PO status to EXPORT_IN_PROGRESS
        self._purchase_order_repository.update_status(
            hacat=hacat,
            po_number=po_number,
            execution_id=execution_id,
            status=PurchaseOrderStatus.EXPORT_IN_PROGRESS,
        )

        try:
            # Parse the formatted timestamp string back to a datetime object
            ts = datetime.strptime(timestamp, TIMESTAMP_FORMAT).replace(
                tzinfo=timezone.utc
            )

            # Copy consolidated data from data bucket to CEDL bucket
            self._purchase_order_file_objects_repository.export(
                hacat=hacat,
                po_number=po_number,
                timestamp=ts,
            )

            # Update PO status to EXPORT_COMPLETED
            self._purchase_order_repository.update_status(
                hacat=hacat,
                po_number=po_number,
                execution_id=execution_id,
                status=PurchaseOrderStatus.EXPORT_COMPLETED,
            )

            metrics.add_metric(
                name="PurchaseOrderSucceeded", unit=MetricUnit.Count, value=1
            )

        except Exception as original_error:
            # Attempt to update PO status to EXPORT_FAILED
            try:
                self._purchase_order_repository.update_status(
                    hacat=hacat,
                    po_number=po_number,
                    execution_id=execution_id,
                    status=PurchaseOrderStatus.EXPORT_FAILED,
                )
            except Exception as dynamo_error:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Failed to write EXPORT_FAILED status to DynamoDB",
                    exc_info=dynamo_error,
                )

            metrics.add_metric(
                name="PurchaseOrderFailed", unit=MetricUnit.Count, value=1
            )
            raise original_error
