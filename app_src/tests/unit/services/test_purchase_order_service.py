from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models.po_file import CedlPoFile
from models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderRecord,
    PurchaseOrderStatus,
)
from repositories.coupa_repository import CoupaRepository
from repositories.execution_repository import ExecutionRepository
from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)
from repositories.purchase_order_file_repository import PurchaseOrderFileRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

EXECUTION_ID = "f8a2b1c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c"


@pytest.fixture
def mock_coupa_repository():
    return MagicMock(spec=CoupaRepository)


@pytest.fixture
def mock_execution_repository():
    repo = MagicMock(spec=ExecutionRepository)
    repo.get_last_execution.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return repo


@pytest.fixture
def mock_purchase_order_repository():
    return MagicMock(spec=PurchaseOrderRepository)


@pytest.fixture
def mock_purchase_order_file_repository():
    return MagicMock(spec=PurchaseOrderFileRepository)


@pytest.fixture
def mock_purchase_order_file_objects_repository():
    return MagicMock(spec=PurchaseOrderFileObjectsRepository)


@pytest.fixture(autouse=True)
def _set_ssm_prefix(monkeypatch):
    monkeypatch.setenv("SSM_PREFIX", "/test/prefix")
    monkeypatch.setenv("SSM_MAX_AGE", "300")


@pytest.fixture(autouse=True)
def _mock_ssm_get_parameter():
    def _side_effect(param_name, **kwargs):
        if param_name.endswith("/batchSize"):
            return "250"
        if param_name.endswith("/allowedFileExtensions"):
            return '[".pdf", ".jpeg", ".png"]'
        raise ValueError(f"Unexpected SSM param: {param_name}")

    with patch(
        "services.purchase_order_service.ssm_provider.get",
        side_effect=_side_effect,
    ) as mock_get_param:
        yield mock_get_param


@pytest.fixture
def service(
    mock_coupa_repository,
    mock_execution_repository,
    mock_purchase_order_repository,
    mock_purchase_order_file_repository,
    mock_purchase_order_file_objects_repository,
):
    return PurchaseOrderService(
        coupa_repository=mock_coupa_repository,
        execution_repository=mock_execution_repository,
        purchase_order_repository=mock_purchase_order_repository,
        purchase_order_file_repository=mock_purchase_order_file_repository,
        purchase_order_file_objects_repository=mock_purchase_order_file_objects_repository,
    )


class TestProcessPurchaseOrders:
    def test_delegates_to_coupa_repository(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(poNumber="P001", hacat="HC1001"),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=["P001"]
        )

        # Then
        assert len(result) == 1
        assert result[0].po_number == "P001"
        mock_execution_repository.get_last_execution.assert_not_called()
        mock_coupa_repository.retrieve_po.assert_called_once_with(
            po_numbers=["P001"], hacat="HC1001", since=None, batch_size=None
        )
        mock_execution_repository.update_last_execution.assert_not_called()

    def test_passes_none_when_no_ids(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = []

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert result == []
        mock_coupa_repository.retrieve_po.assert_called_once_with(
            po_numbers=None,
            hacat="HC1001",
            since=datetime(2025, 1, 1, tzinfo=timezone.utc),
            batch_size=250,
        )
        mock_purchase_order_repository.batch_create.assert_called_once_with([])
        # No files returned → lastExecution should NOT be updated
        mock_execution_repository.update_last_execution.assert_not_called()

    def test_passes_hacat_filter(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given — PO with a file so lastExecution gets updated
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P002",
                hacat="HC1005",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp=datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
                        originalFilename="doc.pdf",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1005", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result) == 1
        assert result[0].hacat == "HC1005"
        mock_execution_repository.get_last_execution.assert_called_once_with("HC1005")
        mock_coupa_repository.retrieve_po.assert_called_once_with(
            po_numbers=None,
            hacat="HC1005",
            since=datetime(2025, 1, 1, tzinfo=timezone.utc),
            batch_size=250,
        )
        mock_execution_repository.update_last_execution.assert_called_once_with(
            "HC1005", datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        )

    def test_batch_creates_po_records_with_pending_status(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(poNumber="P001", hacat="HC1001"),
            PurchaseOrder(poNumber="P002", hacat="HC1001"),
        ]

        # When
        service.retrieve_pos(hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None)

        # Then
        mock_purchase_order_repository.batch_create.assert_called_once()
        records = mock_purchase_order_repository.batch_create.call_args[0][0]

        assert len(records) == 2

        assert records[0].po_number == "P001"
        assert records[0].hacat == "HC1001"
        assert records[0].status == PurchaseOrderStatus.PENDING
        assert records[0].execution_id == EXECUTION_ID
        assert records[0].nb_files == 0

        assert records[1].po_number == "P002"
        assert records[1].hacat == "HC1001"
        assert records[1].status == PurchaseOrderStatus.PENDING
        assert records[1].execution_id == EXECUTION_ID
        assert records[1].nb_files == 0

    def test_batch_create_called_before_updating_last_execution(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given — PO must have a file so that lastExecution actually gets updated
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp=datetime(2025, 3, 1, tzinfo=timezone.utc),
                        originalFilename="doc.pdf",
                    ),
                ],
            ),
        ]
        call_order = []
        mock_purchase_order_repository.batch_create.side_effect = (
            lambda r: call_order.append("batch_create")
        )
        mock_execution_repository.update_last_execution.side_effect = (
            lambda h, t: call_order.append("update_last_execution")
        )

        # When
        service.retrieve_pos(hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None)

        # Then
        assert call_order == ["batch_create", "update_last_execution"]

    def test_does_not_use_last_execution_when_po_numbers_provided(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(poNumber="P001", hacat="HC1001"),
        ]

        # When
        service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=["P001"]
        )

        # Then
        mock_execution_repository.get_last_execution.assert_not_called()
        mock_coupa_repository.retrieve_po.assert_called_once_with(
            po_numbers=["P001"], hacat="HC1001", since=None, batch_size=None
        )
        mock_execution_repository.update_last_execution.assert_not_called()

    def test_last_execution_uses_max_of_per_po_min_timestamps(
        self,
        service,
        mock_coupa_repository,
        mock_execution_repository,
        mock_purchase_order_repository,
    ):
        """lastExecution cursor should be the max of each PO's earliest file
        timestamp (not the global max), so that POs not in the current batch
        are not skipped.

        PO1: files at 06-03, 06-05  → min = 06-03
        PO2: files at 06-04, 06-05  → min = 06-04
        cursor = max(06-03, 06-04) = 06-04  (NOT 06-05)
        """
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="PO1",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="f1.pdf",
                        s3path="p/f1.pdf",
                        timestamp=datetime(2026, 6, 3, tzinfo=timezone.utc),
                        originalFilename="f1.pdf",
                    ),
                    CedlPoFile(
                        filename="f2.pdf",
                        s3path="p/f2.pdf",
                        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
                        originalFilename="f2.pdf",
                    ),
                ],
            ),
            PurchaseOrder(
                poNumber="PO2",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="f3.pdf",
                        s3path="p/f3.pdf",
                        timestamp=datetime(2026, 6, 4, tzinfo=timezone.utc),
                        originalFilename="f3.pdf",
                    ),
                    CedlPoFile(
                        filename="f4.pdf",
                        s3path="p/f4.pdf",
                        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
                        originalFilename="f4.pdf",
                    ),
                ],
            ),
        ]

        # When
        service.retrieve_pos(hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None)

        # Then — cursor should be 06-04 (max of per-PO mins), NOT 06-05
        mock_execution_repository.update_last_execution.assert_called_once_with(
            "HC1001", datetime(2026, 6, 4, tzinfo=timezone.utc)
        )


class TestFileExtensionFiltering:
    def test_keeps_files_with_allowed_extensions(
        self, service, mock_coupa_repository, mock_purchase_order_repository
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp="2025-01-01",
                        originalFilename="doc.pdf",
                    ),
                    CedlPoFile(
                        filename="img.jpeg",
                        s3path="path/img.jpeg",
                        timestamp="2025-01-01",
                        originalFilename="img.jpeg",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result[0].po_files) == 2
        assert result[0].po_files[0].filename == "doc.pdf"
        assert result[0].po_files[1].filename == "img.jpeg"

    def test_excludes_files_with_non_allowed_extensions(
        self, service, mock_coupa_repository, mock_purchase_order_repository
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp="2025-01-01",
                        originalFilename="doc.pdf",
                    ),
                    CedlPoFile(
                        filename="data.csv",
                        s3path="path/data.csv",
                        timestamp="2025-01-01",
                        originalFilename="data.csv",
                    ),
                    CedlPoFile(
                        filename="script.py",
                        s3path="path/script.py",
                        timestamp="2025-01-01",
                        originalFilename="script.py",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result[0].po_files) == 1
        assert result[0].po_files[0].filename == "doc.pdf"

    def test_case_insensitive_matching(
        self, service, mock_coupa_repository, mock_purchase_order_repository
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="DOC.PDF",
                        s3path="path/DOC.PDF",
                        timestamp="2025-01-01",
                        originalFilename="DOC.PDF",
                    ),
                    CedlPoFile(
                        filename="img.JPEG",
                        s3path="path/img.JPEG",
                        timestamp="2025-01-01",
                        originalFilename="img.JPEG",
                    ),
                    CedlPoFile(
                        filename="pic.Png",
                        s3path="path/pic.Png",
                        timestamp="2025-01-01",
                        originalFilename="pic.Png",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result[0].po_files) == 3

    def test_excludes_files_without_extension(
        self, service, mock_coupa_repository, mock_purchase_order_repository
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp="2025-01-01",
                        originalFilename="doc.pdf",
                    ),
                    CedlPoFile(
                        filename="noextension",
                        s3path="path/noextension",
                        timestamp="2025-01-01",
                        originalFilename="noextension",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result[0].po_files) == 1
        assert result[0].po_files[0].filename == "doc.pdf"

    def test_po_with_all_files_filtered_has_empty_list(
        self, service, mock_coupa_repository, mock_purchase_order_repository
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="data.csv",
                        s3path="path/data.csv",
                        timestamp="2025-01-01",
                        originalFilename="data.csv",
                    ),
                    CedlPoFile(
                        filename="script.py",
                        s3path="path/script.py",
                        timestamp="2025-01-01",
                        originalFilename="script.py",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result) == 1
        assert result[0].po_number == "P001"
        assert result[0].po_files == []

    def test_reads_ssm_parameter_with_correct_path(
        self,
        service,
        mock_coupa_repository,
        mock_purchase_order_repository,
        _mock_ssm_get_parameter,
    ):
        # Given
        mock_coupa_repository.retrieve_po.return_value = []

        # When
        service.retrieve_pos(hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None)

        # Then — two SSM calls: batchSize and allowedFileExtensions
        assert _mock_ssm_get_parameter.call_count == 2
        _mock_ssm_get_parameter.assert_any_call(
            "/test/prefix/hacat/HC1001/batchSize", max_age=300
        )
        _mock_ssm_get_parameter.assert_any_call(
            "/test/prefix/hacat/HC1001/allowedFileExtensions", max_age=300
        )

    def test_get_parameter_error_propagates(
        self, service, mock_coupa_repository, _mock_ssm_get_parameter
    ):
        # Given
        from aws_lambda_powertools.utilities.parameters.exceptions import (
            GetParameterError,
        )

        _mock_ssm_get_parameter.side_effect = GetParameterError("Parameter not found")

        # When / Then
        with pytest.raises(GetParameterError):
            service.retrieve_pos(
                hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
            )

    def test_extensions_from_ssm_are_lowercased(
        self,
        service,
        mock_coupa_repository,
        mock_purchase_order_repository,
        _mock_ssm_get_parameter,
    ):
        # Given — SSM returns uppercase extensions
        _mock_ssm_get_parameter.return_value = '[".PDF", ".JPEG"]'
        mock_coupa_repository.retrieve_po.return_value = [
            PurchaseOrder(
                poNumber="P001",
                hacat="HC1001",
                poFiles=[
                    CedlPoFile(
                        filename="doc.pdf",
                        s3path="path/doc.pdf",
                        timestamp="2025-01-01",
                        originalFilename="doc.pdf",
                    ),
                    CedlPoFile(
                        filename="img.jpeg",
                        s3path="path/img.jpeg",
                        timestamp="2025-01-01",
                        originalFilename="img.jpeg",
                    ),
                    CedlPoFile(
                        filename="data.csv",
                        s3path="path/data.csv",
                        timestamp="2025-01-01",
                        originalFilename="data.csv",
                    ),
                ],
            ),
        ]

        # When
        result = service.retrieve_pos(
            hacat="HC1001", execution_id=EXECUTION_ID, po_numbers=None
        )

        # Then
        assert len(result[0].po_files) == 2
        filenames = [f.filename for f in result[0].po_files]
        assert "doc.pdf" in filenames
        assert "img.jpeg" in filenames
