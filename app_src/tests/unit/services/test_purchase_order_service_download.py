from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models.cedl_copy_po_files import CedlCopyPoFileItem
from models.po_file import PurchaseOrderFileStatus
from models.purchase_order import PurchaseOrderStatus
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


class TestDownloadPoFiles:
    def test_updates_po_status_to_processing(
        self,
        service,
        mock_purchase_order_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        mock_purchase_order_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            execution_id=EXECUTION_ID,
            status=PurchaseOrderStatus.PROCESSING,
        )

    def test_creates_file_record_with_downloading_status_before_copy(
        self,
        service,
        mock_purchase_order_file_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="1.pdf",
            status=PurchaseOrderFileStatus.DOWNLOAD_IN_PROGRESS,
        )

    def test_copies_file_from_cedl_to_data_bucket(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        mock_purchase_order_file_objects_repository.copy.assert_called_once_with(
            source_key="ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
            hacat="HC1005",
            po_number="E002754388",
            filename="1.pdf",
        )

    def test_updates_file_record_to_downloaded_after_copy(
        self,
        service,
        mock_purchase_order_file_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="1.pdf",
            status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
        )

    def test_returns_list_of_downloaded_filenames(
        self,
        service,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
            CedlCopyPoFileItem(
                filename="2.pdf",
                s3path="path/2.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="2.pdf",
            ),
        ]

        # When
        result = service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        assert result == ["1.pdf", "2.pdf"]

    def test_processes_multiple_files_sequentially(
        self,
        service,
        mock_purchase_order_file_objects_repository,
        mock_purchase_order_file_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="a.pdf",
                s3path="path/a.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="a.pdf",
            ),
            CedlCopyPoFileItem(
                filename="b.pdf",
                s3path="path/b.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="b.pdf",
            ),
        ]

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        assert mock_purchase_order_file_objects_repository.copy.call_count == 2
        # 2 files × 2 update_status each (DOWNLOAD_IN_PROGRESS + DOWNLOAD_COMPLETED) = 4 calls
        assert mock_purchase_order_file_repository.update_status.call_count == 4

    def test_sets_file_status_to_error_on_copy_failure(
        self,
        service,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
    ):
        # Given
        mock_purchase_order_file_objects_repository.copy.side_effect = RuntimeError(
            "S3 error"
        )

        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When / Then
        with pytest.raises(RuntimeError, match="S3 error"):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=po_files,
                execution_id=EXECUTION_ID,
            )

        # File status should be set to DOWNLOAD_FAILED
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="1.pdf",
            status=PurchaseOrderFileStatus.DOWNLOAD_FAILED,
        )

    def test_sets_po_status_to_error_on_copy_failure(
        self,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_objects_repository,
    ):
        # Given
        mock_purchase_order_file_objects_repository.copy.side_effect = RuntimeError(
            "S3 error"
        )

        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When / Then
        with pytest.raises(RuntimeError, match="S3 error"):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=po_files,
                execution_id=EXECUTION_ID,
            )

        # PO status should be set to DOWNLOAD_FAILED
        mock_purchase_order_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            execution_id=EXECUTION_ID,
            status=PurchaseOrderStatus.DOWNLOAD_FAILED,
        )

    def test_re_raises_exception_after_error_handling(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        # Given
        mock_purchase_order_file_objects_repository.copy.side_effect = RuntimeError(
            "Network error"
        )

        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        # When / Then
        with pytest.raises(RuntimeError, match="Network error"):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=po_files,
                execution_id=EXECUTION_ID,
            )

    def test_correct_call_order_for_each_file(
        self,
        service,
        mock_purchase_order_repository,
        mock_purchase_order_file_repository,
        mock_purchase_order_file_objects_repository,
    ):
        # Given
        po_files = [
            CedlCopyPoFileItem(
                filename="1.pdf",
                s3path="path/1.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="1.pdf",
            ),
        ]

        call_order = []
        mock_purchase_order_repository.update_status.side_effect = (
            lambda **kwargs: call_order.append(f"po_update:{kwargs['status'].value}")
        )
        mock_purchase_order_file_repository.update_status.side_effect = (
            lambda **kwargs: call_order.append(f"file_update:{kwargs['status'].value}")
        )
        mock_purchase_order_file_objects_repository.copy.side_effect = (
            lambda **kwargs: call_order.append("copy")
        )

        # When
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then
        assert call_order == [
            "po_update:PROCESSING",
            "file_update:DOWNLOAD_IN_PROGRESS",
            "copy",
            "file_update:DOWNLOAD_COMPLETED",
        ]

    def test_returns_empty_list_when_po_files_is_empty(self, service):
        """download_po_files returns [] immediately when po_files is empty."""
        result = service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=[],
            execution_id=EXECUTION_ID,
        )

        assert result == []

    def test_does_not_update_po_status_when_po_files_is_empty(
        self, service, mock_purchase_order_repository
    ):
        """download_po_files does not write any PO records when po_files is empty."""
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=[],
            execution_id=EXECUTION_ID,
        )

        mock_purchase_order_repository.update_status.assert_not_called()

    def test_does_not_copy_files_when_po_files_is_empty(
        self, service, mock_purchase_order_file_objects_repository
    ):
        """download_po_files does not call copy when po_files is empty."""
        service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=[],
            execution_id=EXECUTION_ID,
        )

        mock_purchase_order_file_objects_repository.copy.assert_not_called()


class _FakeAttachment:
    """Lightweight stand-in for parsers.email_eml_parser.Attachment."""

    def __init__(self, filename, content, content_type):
        self.filename = filename
        self.content = content
        self.content_type = content_type


class _FakeParsedEmail:
    """Lightweight stand-in for parsers.email_eml_parser.ParsedEmail."""

    def __init__(self, attachments):
        self.attachments = attachments


class TestDownloadPoFilesEml:
    @pytest.fixture
    def allowed_extensions(self, service):
        """Patch _load_allowed_extensions to a fixed allowed set."""
        with patch.object(
            service,
            "_load_allowed_extensions",
            return_value={".pdf", ".png"},
        ) as mocked:
            yield mocked

    @pytest.fixture
    def eml_po_file(self):
        return CedlCopyPoFileItem(
            filename="email1.eml",
            s3path="ORDER_HEADER/2025/07/09/attachments/5396937/email1.eml",
            timestamp="2025-07-01T00:00:00+00:00",
            originalFilename="email1.eml",
        )

    def test_eml_routed_to_process_eml_not_plain_copy(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_objects_repository,
    ):
        # Given a parsed email with two allowed attachments
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [
                    _FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf"),
                    _FakeAttachment("attach_2_specs.png", b"png", "image/png"),
                ]
            ),
        ):
            # When
            result = service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        # Then — raw .eml copied, read back, attachments uploaded
        mock_purchase_order_file_objects_repository.copy.assert_called_once_with(
            source_key="ORDER_HEADER/2025/07/09/attachments/5396937/email1.eml",
            hacat="HC1005",
            po_number="E002754388",
            filename="email1.eml",
        )
        mock_purchase_order_file_objects_repository.download_incoming_file.assert_called_once_with(
            hacat="HC1005",
            po_number="E002754388",
            filename="email1.eml",
        )
        assert result == [
            "email1.eml/attach_1_devis.pdf",
            "email1.eml/attach_2_specs.png",
        ]

    def test_non_eml_uses_existing_copy_path(
        self,
        service,
        mock_purchase_order_file_objects_repository,
    ):
        # Given a regular pdf
        po_files = [
            CedlCopyPoFileItem(
                filename="doc.pdf",
                s3path="path/doc.pdf",
                timestamp="2025-07-01T00:00:00+00:00",
                originalFilename="doc.pdf",
            ),
        ]

        # When
        result = service.download_po_files(
            hacat="HC1005",
            po_number="E002754388",
            po_files=po_files,
            execution_id=EXECUTION_ID,
        )

        # Then — plain copy path, no eml download/upload
        assert result == ["doc.pdf"]
        mock_purchase_order_file_objects_repository.download_incoming_file.assert_not_called()
        mock_purchase_order_file_objects_repository.upload_incoming_file.assert_not_called()

    def test_eml_record_status_transitions(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [_FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf")]
            ),
        ):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="email1.eml",
            status=PurchaseOrderFileStatus.DOWNLOAD_IN_PROGRESS,
        )
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="email1.eml",
            status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
        )

    def test_copy_before_download_before_parse(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_objects_repository,
    ):
        call_order = []
        mock_purchase_order_file_objects_repository.copy.side_effect = (
            lambda **kwargs: call_order.append("copy")
        )
        mock_purchase_order_file_objects_repository.download_incoming_file.side_effect = (
            lambda **kwargs: call_order.append("download") or b"raw"
        )

        def fake_parse(_filename, _raw):
            call_order.append("parse")
            return _FakeParsedEmail([])

        with patch(
            "services.purchase_order_service.parse_email", side_effect=fake_parse
        ):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        assert call_order == ["copy", "download", "parse"]

    def test_attachments_uploaded_with_hierarchical_path(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_objects_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [_FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf")]
            ),
        ):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        mock_purchase_order_file_objects_repository.upload_incoming_file.assert_called_once_with(
            hacat="HC1005",
            po_number="E002754388",
            filename="email1.eml/attach_1_devis.pdf",
            content=b"pdf",
            content_type="application/pdf",
        )

    def test_attachment_records_created_with_full_hierarchical_original_filename(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [
                    _FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf"),
                    _FakeAttachment("attach_2_specs.png", b"png", "image/png"),
                ]
            ),
        ):
            service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        mock_purchase_order_file_repository.batch_create.assert_called_once()
        created = mock_purchase_order_file_repository.batch_create.call_args[0][0]
        assert len(created) == 2
        for record, expected in zip(
            created,
            ["email1.eml/attach_1_devis.pdf", "email1.eml/attach_2_specs.png"],
        ):
            assert record.filename == expected
            assert record.original_filename == expected
            assert record.status == PurchaseOrderFileStatus.DOWNLOAD_COMPLETED

    def test_only_attachment_filenames_returned(
        self,
        service,
        allowed_extensions,
        eml_po_file,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [_FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf")]
            ),
        ):
            result = service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        # The .eml container itself is NOT in the returned list
        assert result == ["email1.eml/attach_1_devis.pdf"]

    def test_no_attachments_returns_empty_but_eml_completed(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail([]),
        ):
            result = service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        assert result == []
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="email1.eml",
            status=PurchaseOrderFileStatus.DOWNLOAD_COMPLETED,
        )
        mock_purchase_order_file_repository.batch_create.assert_not_called()

    def test_attachments_filtered_by_allowed_extensions(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_objects_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [
                    _FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf"),
                    _FakeAttachment(
                        "attach_2_macro.exe", b"exe", "application/octet-stream"
                    ),
                ]
            ),
        ):
            result = service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[eml_po_file],
                execution_id=EXECUTION_ID,
            )

        # Only the allowed .pdf attachment is kept and uploaded
        assert result == ["email1.eml/attach_1_devis.pdf"]
        assert (
            mock_purchase_order_file_objects_repository.upload_incoming_file.call_count
            == 1
        )

    def test_malformed_eml_sets_download_failed_and_reraises(
        self,
        service,
        allowed_extensions,
        eml_po_file,
        mock_purchase_order_file_repository,
        mock_purchase_order_repository,
    ):
        with patch(
            "services.purchase_order_service.parse_email",
            side_effect=ValueError("malformed MIME"),
        ):
            with pytest.raises(ValueError, match="malformed MIME"):
                service.download_po_files(
                    hacat="HC1005",
                    po_number="E002754388",
                    po_files=[eml_po_file],
                    execution_id=EXECUTION_ID,
                )

        # .eml file record set to DOWNLOAD_FAILED
        mock_purchase_order_file_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            file_name="email1.eml",
            status=PurchaseOrderFileStatus.DOWNLOAD_FAILED,
        )
        # PO status set to DOWNLOAD_FAILED
        mock_purchase_order_repository.update_status.assert_any_call(
            hacat="HC1005",
            po_number="E002754388",
            execution_id=EXECUTION_ID,
            status=PurchaseOrderStatus.DOWNLOAD_FAILED,
        )

    @pytest.fixture
    def msg_po_file(self):
        return CedlCopyPoFileItem(
            filename="email1.msg",
            s3path="ORDER_HEADER/2025/07/09/attachments/5396937/email1.msg",
            timestamp="2025-07-01T00:00:00+00:00",
            originalFilename="email1.msg",
        )

    def test_msg_routed_through_parse_email_with_msg_filename(
        self,
        service,
        allowed_extensions,
        msg_po_file,
        mock_purchase_order_file_objects_repository,
    ):
        # The service delegates parser selection to parse_email (the factory),
        # passing the .msg filename. Extension-based routing is covered in the
        # factory's own tests.
        with patch(
            "services.purchase_order_service.parse_email",
            return_value=_FakeParsedEmail(
                [_FakeAttachment("attach_1_devis.pdf", b"pdf", "application/pdf")]
            ),
        ) as mock_parse_email:
            # When
            result = service.download_po_files(
                hacat="HC1005",
                po_number="E002754388",
                po_files=[msg_po_file],
                execution_id=EXECUTION_ID,
            )

        # Then — parse_email called with the .msg filename and its raw bytes
        mock_parse_email.assert_called_once()
        assert mock_parse_email.call_args.args[0] == "email1.msg"
        mock_purchase_order_file_objects_repository.copy.assert_called_once_with(
            source_key="ORDER_HEADER/2025/07/09/attachments/5396937/email1.msg",
            hacat="HC1005",
            po_number="E002754388",
            filename="email1.msg",
        )
        assert result == ["email1.msg/attach_1_devis.pdf"]
