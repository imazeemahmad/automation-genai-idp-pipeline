"""LibreOffice converter Lambda — generic S3-to-S3 document-to-PDF conversion.

Contract:
    Input event:
        {
            "source_key": "HC1001/incoming/123456/presentation.pptx",
            "destination_key": "HC1001/incoming/123456/presentation.pdf"
        }

    Environment variables:
        S3_BUCKET_NAME  — the S3 bucket for both input and output

    Output:
        {
            "source_key": "...",
            "destination_key": "...",
            "status": "success"
        }

This Lambda has zero business logic. It downloads a file from S3,
converts it to PDF with LibreOffice headless, and uploads the result.
"""

import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from openpyxl import load_workbook

logger = Logger()

s3_client = boto3.client("s3")
BUCKET_NAME = os.environ["S3_BUCKET_NAME"]

# Spreadsheet extensions that benefit from the Calc PDF export filter
CALC_EXTENSIONS = {".xlsx", ".xls", ".ods", ".csv"}

# .xlsx files can be pre-processed with openpyxl for better table layout
OPENPYXL_EXTENSIONS = {".xlsx"}


def _optimize_xlsx_page_setup(file_path: Path) -> None:
    """Set landscape + fit-to-page on all sheets for better table rendering.

    Modifies the .xlsx in-place. Charts will be lost (openpyxl limitation)
    but tabular data will fit on the page width — critical for LLM extraction.
    """
    wb = load_workbook(str(file_path))

    for ws in wb.worksheets:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0  # unlimited pages vertically
        ws.page_setup.paperSize = ws.PAPERSIZE_A4

    wb.save(str(file_path))
    logger.info("Applied fit-to-page landscape layout to .xlsx file")


def _build_convert_command(input_path: str, outdir: str, extension: str) -> list[str]:
    """Build the LibreOffice conversion command with optimal settings per format.

    For spreadsheets, uses the calc_pdf_Export filter to improve page layout.
    For all other formats, uses the default PDF conversion.
    """
    base_cmd = [
        "libreoffice",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--nologo",
        "--nofirststartwizard",
    ]

    if extension in CALC_EXTENSIONS:
        # Use Calc-specific PDF export for better spreadsheet rendering
        base_cmd += ["--convert-to", "pdf:calc_pdf_Export"]
    else:
        base_cmd += ["--convert-to", "pdf"]

    base_cmd += ["--outdir", outdir, input_path]
    return base_cmd


@logger.inject_lambda_context
def handler(
    event: dict, context: LambdaContext
) -> dict:  # pylint: disable=unused-argument
    """Download from S3 → convert to PDF via LibreOffice → upload to S3."""

    source_key = event["source_key"]
    destination_key = event["destination_key"]

    logger.info(
        "Starting conversion",
        extra={"source_key": source_key, "destination_key": destination_key},
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Download source file
        source_filename = PurePosixPath(source_key).name
        input_path = Path(tmp_dir) / source_filename
        s3_client.download_file(BUCKET_NAME, source_key, str(input_path))

        extension = PurePosixPath(source_filename).suffix.lower()

        # 2. Pre-process .xlsx for better table layout (loses charts)
        if extension in OPENPYXL_EXTENSIONS:
            _optimize_xlsx_page_setup(input_path)

        # 3. Convert to PDF with LibreOffice
        cmd = _build_convert_command(str(input_path), tmp_dir, extension)

        logger.info(
            "Running LibreOffice",
            extra={"command": " ".join(cmd), "extension": extension},
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=90,
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LibreOffice conversion failed for '{source_filename}' "
                f"(exit code {result.returncode}): {stderr}"
            )

        # 3. Read converted PDF
        stem = PurePosixPath(source_filename).stem
        output_path = Path(tmp_dir) / f"{stem}.pdf"

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(
                f"LibreOffice produced no output for '{source_filename}'"
            )

        # 4. Upload to S3
        s3_client.upload_file(
            str(output_path),
            BUCKET_NAME,
            destination_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )

    logger.info(
        "Conversion completed",
        extra={"source_key": source_key, "destination_key": destination_key},
    )

    return {
        "source_key": source_key,
        "destination_key": destination_key,
        "status": "success",
    }
