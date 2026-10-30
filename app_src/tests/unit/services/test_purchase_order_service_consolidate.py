import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest
from botocore.exceptions import ClientError

from models.po_file import PurchaseOrderFile, PurchaseOrderFileStatus
from models.purchase_order import PurchaseOrderRecord, PurchaseOrderStatus
from repositories.purchase_order_file_objects_repository import (
    TIMESTAMP_FORMAT,
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.llm_service import LlmService
from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PROCUREMENT_TABLE_NAME", "test-table")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")
    monkeypatch.setenv("SSM_PREFIX", "/pdb/sbx")
    monkeypatch.setenv("SSM_MAX_AGE", "300")


@pytest.fixture
def mock_purchase_order_repository():
    return MagicMock(spec=PurchaseOrderRepository)


@pytest.fixture
def mock_purchase_order_file_repository():
    return MagicMock(spec=PurchaseOrderFileRepository)


@pytest.fixture
def mock_purchase_order_file_objects_repository():
    return MagicMock(spec=PurchaseOrderFileObjectsRepository)


@pytest.fixture
def mock_llm_service():
    return MagicMock(spec=LlmService)


@pytest.fixture
def service(
    mock_purchase_order_repository,
    mock_purchase_order_file_repository,
    mock_purchase_order_file_objects_repository,
    mock_llm_service,
):
    return PurchaseOrderService(
        purchase_order_repository=mock_purchase_order_repository,
        purchase_order_file_repository=mock_purchase_order_file_repository,
        purchase_order_file_objects_repository=mock_purchase_order_file_objects_repository,
        llm_service=mock_llm_service,
    )


@pytest.fixture
def po_file_records():
    return [
        PurchaseOrderFile(
            po_number="E002754388",
            filename="sow_v1.pdf",
            hacat="HC1001",
            status=PurchaseOrderFileStatus.OCR_COMPLETED,
            timestamp="2025-01-15T10:30:00Z",
            original_filename="Statement of Work v1.pdf",
        ),
        PurchaseOrderFile(
            po_number="E002754388",
            filename="amendment_1.pdf",
            hacat="HC1001",
            status=PurchaseOrderFileStatus.OCR_COMPLETED,
            timestamp="2025-01-15T11:00:00Z",
            original_filename="Amendment #1.pdf",
        ),
    ]


def _no_such_key_error():
    """Create a ClientError with NoSuchKey code."""
    return ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
    )


class TestConsolidate:
    """Tests for the consolidate() method using LlmService."""

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_success_path_invokes_llm_and_stores_result(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """Success: reads OCR for 2 files, calls LlmService, stores result, returns COMPLETED."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = (
            po_file_records
        )

        mock_purchase_order_file_objects_repository.get_ocr_result.side_effect = [
            "# OCR content for SOW",
            "# OCR content for Amendment",
        ]

        # Two SSM lookups now occur: the prompt ARN, then the mappingS3Key.
        # Return the ARN for the first and an empty string for the mapping so
        # this happy-path test stays documents-only.
        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            "",
        ]

        mock_llm_service.invoke.return_value = '{"supplier": "ACME", "total": 1000}'

        result = service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        assert result == ("CONSOLIDATE_COMPLETED", "20250701T120000Z")

        # Verify status transitions
        update_calls = mock_purchase_order_repository.update_status.call_args_list
        assert len(update_calls) == 2
        assert (
            update_calls[0][1]["status"] == PurchaseOrderStatus.CONSOLIDATE_IN_PROGRESS
        )
        assert update_calls[1][1]["status"] == PurchaseOrderStatus.CONSOLIDATE_COMPLETED

        # Verify LlmService called with correct arguments
        mock_llm_service.invoke.assert_called_once()
        invoke_kwargs = mock_llm_service.invoke.call_args.kwargs
        assert invoke_kwargs["model_id"] == "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1"
        documents = json.loads(invoke_kwargs["prompt_variables"]["documents"])
        assert len(documents) == 2
        assert documents[0]["DOCUMENT_NAME"] == "Statement of Work v1.pdf"
        assert documents[0]["CONTENT"] == "# OCR content for SOW"
        assert documents[1]["DOCUMENT_NAME"] == "Amendment #1.pdf"
        assert documents[1]["CONTENT"] == "# OCR content for Amendment"
        # Empty mappingS3Key -> no "mappings" injected
        assert "mappings" not in invoke_kwargs["prompt_variables"]

        # Verify SSM was queried for both the prompt ARN and the mappingS3Key.
        ssm_get_calls = mock_ssm.get.call_args_list
        assert len(ssm_get_calls) == 2
        assert ssm_get_calls[0] == call(
            "/pdb/sbx/hacat/HC1001/llmExtractPromptArn", max_age=300
        )
        assert ssm_get_calls[1] == call(
            "/pdb/sbx/hacat/HC1001/mappingS3Key", max_age=300
        )
        # Empty mapping value -> get_mapping never called
        mock_purchase_order_file_objects_repository.get_mapping.assert_not_called()

        # Verify put_consolidated_data called
        mock_purchase_order_file_objects_repository.put_consolidated_data.assert_called_once()
        put_kwargs = (
            mock_purchase_order_file_objects_repository.put_consolidated_data.call_args.kwargs
        )
        assert put_kwargs["hacat"] == "HC1001"
        assert put_kwargs["po_number"] == "E002754388"
        assert put_kwargs["timestamp"] == fake_now
        stored_data = json.loads(put_kwargs["data"])
        assert stored_data == {"supplier": "ACME", "total": 1000}

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_ocr_missing_raises_and_sets_failed(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """OCR output missing (NoSuchKey) -> raises ClientError, CONSOLIDATE_FAILED set."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = (
            po_file_records
        )
        mock_purchase_order_file_objects_repository.get_ocr_result.side_effect = (
            _no_such_key_error()
        )

        with pytest.raises(ClientError):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        # LlmService should NOT have been called
        mock_llm_service.invoke.assert_not_called()

        # Final status should be FAILED
        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_partial_ocr_failure_raises_and_sets_failed(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """Partial OCR: first file succeeds, second raises NoSuchKey -> error propagated."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = (
            po_file_records
        )

        mock_purchase_order_file_objects_repository.get_ocr_result.side_effect = [
            "# SOW content",
            _no_such_key_error(),
        ]

        with pytest.raises(ClientError):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        # Final status should be FAILED
        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

        # LlmService should NOT have been called
        mock_llm_service.invoke.assert_not_called()

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_llm_service_failure_sets_failed_and_reraises(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """LlmService.invoke raises RuntimeError -> CONSOLIDATE_FAILED, exception re-raised."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = (
            po_file_records
        )
        mock_purchase_order_file_objects_repository.get_ocr_result.return_value = (
            "# OCR text"
        )
        mock_ssm.get.return_value = "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1"
        mock_llm_service.invoke.side_effect = RuntimeError("Bedrock throttled")

        with pytest.raises(RuntimeError, match="Bedrock throttled"):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_dynamodb_find_by_po_error_sets_failed_and_reraises(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
    ):
        """DynamoDB find_by_po failure -> CONSOLIDATE_FAILED, exception re-raised."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.side_effect = (
            RuntimeError("DynamoDB Query failed")
        )

        with pytest.raises(RuntimeError, match="DynamoDB Query failed"):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

        # LlmService should NOT have been called
        mock_llm_service.invoke.assert_not_called()

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_invalid_json_from_llm_sets_failed_and_reraises(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """LlmService returns invalid JSON -> JSONDecodeError propagated, CONSOLIDATE_FAILED."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = (
            po_file_records
        )
        mock_purchase_order_file_objects_repository.get_ocr_result.return_value = (
            "# OCR text"
        )
        mock_ssm.get.return_value = "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1"

        mock_llm_service.invoke.side_effect = json.JSONDecodeError("err", "doc", 0)

        with pytest.raises(json.JSONDecodeError):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_empty_file_list_raises_value_error_and_sets_failed(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
    ):
        """find_by_po returns empty list -> raises ValueError('No files found'), CONSOLIDATE_FAILED set."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        mock_purchase_order_file_repository.find_by_po_and_status.return_value = []

        with pytest.raises(ValueError, match="No files found for PO E002754388"):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )

        # LlmService should NOT have been called
        mock_llm_service.invoke.assert_not_called()

        # Final status should be FAILED
        last_call = mock_purchase_order_repository.update_status.call_args_list[-1]
        assert last_call[1]["status"] == PurchaseOrderStatus.CONSOLIDATE_FAILED

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_dynamo_failure_during_consolidate_failed_write_does_not_suppress_original_error(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
    ):
        """DynamoDB failure during CONSOLIDATE_FAILED write is logged but does not suppress original error."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        # find_by_po returns empty -> ValueError
        mock_purchase_order_file_repository.find_by_po_and_status.return_value = []

        # First update_status (IN_PROGRESS) succeeds, second (FAILED) raises
        call_count = [0]

        def update_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # CONSOLIDATE_FAILED write
                raise RuntimeError("DynamoDB write failed on CONSOLIDATE_FAILED")

        mock_purchase_order_repository.update_status.side_effect = update_side_effect

        # Original ValueError should still be raised, not the DynamoDB error
        with pytest.raises(ValueError, match="No files found for PO E002754388"):
            service.consolidate(
                hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
            )


class TestConsolidateMapping:
    """Tests for the conditional mappingS3Key behavior in consolidate().

    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.6, 7.7
    """

    @staticmethod
    def _prime_ocr(mock_file_repository, mock_objects_repository, po_file_records):
        """Set up find_by_po and OCR reads for a successful documents assembly."""
        mock_file_repository.find_by_po_and_status.return_value = po_file_records
        mock_objects_repository.get_ocr_result.side_effect = [
            "# OCR content for SOW",
            "# OCR content for Amendment",
        ]

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_mapping_present_injects_mappings_variable(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """mappingS3Key non-empty + get_mapping returns content -> invoke gets documents AND mappings."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            "HC1001/mappings/mappings.json",
        ]
        mock_purchase_order_file_objects_repository.get_mapping.return_value = (
            '{"supplier_codes": {"ACME": "S1"}}'
        )
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        # get_mapping called with the stripped S3 key
        mock_purchase_order_file_objects_repository.get_mapping.assert_called_once_with(
            s3_key="HC1001/mappings/mappings.json"
        )

        invoke_kwargs = mock_llm_service.invoke.call_args.kwargs
        prompt_variables = invoke_kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert prompt_variables["mappings"] == '{"supplier_codes": {"ACME": "S1"}}'

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_empty_mapping_parameter_skips_mapping(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """mappingS3Key = '' -> get_mapping NOT called, invoke gets documents only."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            "",
        ]
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        mock_purchase_order_file_objects_repository.get_mapping.assert_not_called()

        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert "mappings" not in prompt_variables

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_missing_mapping_parameter_is_treated_as_no_mapping(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """ssm_provider.get raises on mappingS3Key -> no mapping, documents only, success."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        # First get (prompt ARN) succeeds, second get (mappingS3Key) raises.
        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            RuntimeError("ParameterNotFound"),
        ]
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        result = service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        # Consolidation still succeeds
        assert result == ("CONSOLIDATE_COMPLETED", "20250701T120000Z")

        mock_purchase_order_file_objects_repository.get_mapping.assert_not_called()
        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert "mappings" not in prompt_variables

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_mapping_file_not_found_skips_mapping(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """mappingS3Key non-empty but get_mapping returns None -> documents only."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            "HC1001/mappings/mappings.json",
        ]
        mock_purchase_order_file_objects_repository.get_mapping.return_value = None
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        mock_purchase_order_file_objects_repository.get_mapping.assert_called_once_with(
            s3_key="HC1001/mappings/mappings.json"
        )
        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert "mappings" not in prompt_variables

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_whitespace_only_mapping_value_skips_mapping(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """mappingS3Key of only whitespace -> get_mapping NOT called, documents only."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            "   \t  ",
        ]
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        service.consolidate(
            hacat="HC1001", po_number="E002754388", execution_id=EXECUTION_ID
        )

        mock_purchase_order_file_objects_repository.get_mapping.assert_not_called()
        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert "mappings" not in prompt_variables

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_default_lnd_mapping_present_injects_mappings(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """lnd default mappingS3Key 'HC1003/mappings/mappings.json' + file present -> mappings injected."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/LND:1",
            "HC1003/mappings/mappings.json",
        ]
        mock_purchase_order_file_objects_repository.get_mapping.return_value = (
            '{"HC1003": "mapping-data"}'
        )
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        service.consolidate(
            hacat="HC1003", po_number="E002754388", execution_id=EXECUTION_ID
        )

        # SSM queried for the lnd mappingS3Key under the HC1003 HACAT path
        assert mock_ssm.get.call_args_list[1] == call(
            "/pdb/sbx/hacat/HC1003/mappingS3Key", max_age=300
        )
        mock_purchase_order_file_objects_repository.get_mapping.assert_called_once_with(
            s3_key="HC1003/mappings/mappings.json"
        )
        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert prompt_variables["mappings"] == '{"HC1003": "mapping-data"}'

    @patch("services.purchase_order_service.ssm_provider")
    @patch("services.purchase_order_service.datetime")
    def test_default_lnd_mapping_file_absent_falls_back_to_documents_only(
        self,
        mock_datetime,
        mock_ssm,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
        mock_llm_service,
        po_file_records,
    ):
        """lnd default mappingS3Key non-empty but file absent (None) -> documents only (fallback)."""
        fake_now = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        self._prime_ocr(
            mock_purchase_order_file_repository,
            mock_purchase_order_file_objects_repository,
            po_file_records,
        )

        mock_ssm.get.side_effect = [
            "arn:aws:bedrock:eu-west-1:123:prompt/LND:1",
            "HC1003/mappings/mappings.json",
        ]
        mock_purchase_order_file_objects_repository.get_mapping.return_value = None
        mock_llm_service.invoke.return_value = '{"supplier": "ACME"}'

        result = service.consolidate(
            hacat="HC1003", po_number="E002754388", execution_id=EXECUTION_ID
        )

        assert result == ("CONSOLIDATE_COMPLETED", "20250701T120000Z")
        mock_purchase_order_file_objects_repository.get_mapping.assert_called_once_with(
            s3_key="HC1003/mappings/mappings.json"
        )
        prompt_variables = mock_llm_service.invoke.call_args.kwargs["prompt_variables"]
        assert "documents" in prompt_variables
        assert "mappings" not in prompt_variables


class TestParseBedrockResponse:
    """Tests for LlmService._parse_response (moved from PurchaseOrderService)."""

    def test_plain_json_string(self):
        """Plain JSON string -> returns valid JSON (same content)."""
        input_text = '{"supplier": "ACME", "total": 42}'
        result = LlmService._parse_response(input_text)
        assert json.loads(result) == {"supplier": "ACME", "total": 42}

    def test_json_wrapped_in_json_fences(self):
        """JSON wrapped in ```json ... ``` fences -> returns valid JSON."""
        input_text = '```json\n{"supplier": "ACME", "total": 42}\n```'
        result = LlmService._parse_response(input_text)
        assert json.loads(result) == {"supplier": "ACME", "total": 42}

    def test_json_wrapped_in_plain_fences(self):
        """JSON wrapped in ``` ... ``` fences (no language tag) -> returns valid JSON."""
        input_text = '```\n{"supplier": "ACME", "total": 42}\n```'
        result = LlmService._parse_response(input_text)
        assert json.loads(result) == {"supplier": "ACME", "total": 42}

    def test_invalid_json_raises_decode_error(self):
        """Invalid JSON -> raises json.JSONDecodeError."""
        input_text = "this is not valid json {{"
        with pytest.raises(json.JSONDecodeError):
            LlmService._parse_response(input_text)

    def test_json_with_leading_trailing_whitespace(self):
        """JSON with leading/trailing whitespace -> returns valid JSON."""
        input_text = '   \n  {"supplier": "ACME", "total": 42}  \n  '
        result = LlmService._parse_response(input_text)
        assert json.loads(result) == {"supplier": "ACME", "total": 42}
