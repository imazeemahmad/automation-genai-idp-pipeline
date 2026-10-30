from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from repositories.purchase_order_file_objects_repository import (
    PurchaseOrderFileObjectsRepository,
)


@pytest.fixture
def env_vars():
    with patch.dict(
        "os.environ",
        {
            "CEDL_BUCKET_NAME": "my-cedl-bucket",
            "CEDL_BUCKET_PREFIX": "DUMMY_UNSTRUCTURED_DATA",
            "DATA_BUCKET_NAME": "my-data-bucket",
            "COUPA_CROSS_ACCOUNT_ROLE_ARN": "arn:aws:iam::123456789012:role/test-intermediate-role",
            "CEDL_CROSS_ACCOUNT_ROLE_ARN": "arn:aws:iam::987654321098:role/test-cross-account-role",
            "SSM_PREFIX": "/test/prefix",
            "SSM_MAX_AGE": "300",
        },
    ):
        yield


@pytest.fixture
def mock_s3_client():
    with patch(
        "repositories.purchase_order_file_objects_repository.boto3.client"
    ) as mock_client:
        yield mock_client.return_value


@pytest.fixture
def mock_ssm_provider():
    with patch(
        "repositories.purchase_order_file_objects_repository.ssm_provider"
    ) as mock_provider:
        mock_provider.get.return_value = "GEN_AI/BIOMARKER"
        yield mock_provider


@pytest.fixture
def repository(env_vars, mock_s3_client):
    repo = PurchaseOrderFileObjectsRepository()
    # Patch _get_cross_account_s3_client to return the same mock S3 client
    # so that copy() tests don't hit real SSM/STS
    repo._get_cross_account_s3_client = lambda: mock_s3_client
    return repo


@pytest.fixture
def repository_with_ssm(env_vars, mock_s3_client, mock_ssm_provider):
    repo = PurchaseOrderFileObjectsRepository()
    repo._get_cross_account_s3_client = lambda: mock_s3_client
    return repo


class TestCopy:
    def test_copies_object_to_correct_destination(self, repository, mock_s3_client):
        # Given
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"file-content")
        }

        # When
        repository.copy(
            source_key="ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
            hacat="HC1005",
            po_number="E002754388",
            filename="1.pdf",
        )

        # Then - source key is prefixed with CEDL_BUCKET_PREFIX
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="my-cedl-bucket",
            Key="DUMMY_UNSTRUCTURED_DATA/ORDER_HEADER/2025/07/09/attachments/5396937/1.pdf",
        )
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1005/incoming/E002754388/1.pdf",
            Body=b"file-content",
        )

    def test_builds_destination_key_from_hacat_po_number_filename(
        self, repository, mock_s3_client
    ):
        # Given
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"data")
        }

        # When
        repository.copy(
            source_key="some/path/doc.pdf",
            hacat="HC1001",
            po_number="E000024494",
            filename="doc.pdf",
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Key"] == "HC1001/incoming/E000024494/doc.pdf"
        assert call_args["Bucket"] == "my-data-bucket"

    def test_uses_cedl_bucket_as_source(self, repository, mock_s3_client):
        # Given
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"data")
        }

        # When
        repository.copy(
            source_key="path/file.pdf",
            hacat="HC1005",
            po_number="E002754388",
            filename="file.pdf",
        )

        # Then
        get_call_args = mock_s3_client.get_object.call_args[1]
        assert get_call_args["Bucket"] == "my-cedl-bucket"

    def test_propagates_s3_exception(self, repository, mock_s3_client):
        # Given
        mock_s3_client.get_object.side_effect = RuntimeError("Access denied")

        # When / Then
        with pytest.raises(RuntimeError, match="Access denied"):
            repository.copy(
                source_key="path/1.pdf",
                hacat="HC1005",
                po_number="E002754388",
                filename="1.pdf",
            )


class TestInit:
    def test_reads_bucket_names_from_env(self, env_vars, mock_s3_client):
        repo = PurchaseOrderFileObjectsRepository()
        assert repo._source_bucket_name == "my-cedl-bucket"
        assert repo._data_bucket_name == "my-data-bucket"

    def test_reads_role_arns_from_env(self, env_vars, mock_s3_client):
        repo = PurchaseOrderFileObjectsRepository()
        assert (
            repo._intermediate_role_arn
            == "arn:aws:iam::123456789012:role/test-intermediate-role"
        )
        assert (
            repo._cross_account_role_arn
            == "arn:aws:iam::987654321098:role/test-cross-account-role"
        )

    def test_cedl_bucket_defaults_to_empty_when_not_set(self, mock_s3_client):
        with patch.dict("os.environ", {"DATA_BUCKET_NAME": "bucket"}, clear=True):
            repo = PurchaseOrderFileObjectsRepository()
            assert repo._source_bucket_name == ""

    def test_raises_key_error_when_data_bucket_not_set(self, mock_s3_client):
        with patch.dict("os.environ", {"CEDL_BUCKET_NAME": "bucket"}, clear=True):
            with pytest.raises(KeyError):
                PurchaseOrderFileObjectsRepository()


class TestGetOcrResult:
    def test_reads_from_correct_s3_key(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"OCR content"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        result = repository.get_ocr_result(
            hacat="HC1001",
            po_number="E002754388",
            filename="document.pdf",
        )

        # Then
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/ocr-data/E002754388/document.pdf.md",
        )
        assert result == "OCR content"

    def test_key_pattern_uses_hacat_po_number_filename(
        self, repository, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"data"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository.get_ocr_result(
            hacat="HC1005", po_number="P999", filename="invoice.pdf"
        )

        # Then
        call_args = mock_s3_client.get_object.call_args[1]
        assert call_args["Key"] == "HC1005/ocr-data/P999/invoice.pdf.md"
        assert call_args["Bucket"] == "my-data-bucket"

    def test_decodes_body_as_utf8(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = "OCR output with special chars: 100mg/mL".encode(
            "utf-8"
        )
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        result = repository.get_ocr_result(
            hacat="HC1001", po_number="E002754388", filename="doc.pdf"
        )

        # Then
        assert result == "OCR output with special chars: 100mg/mL"

    def test_propagates_s3_client_error(self, repository, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The key does not exist"}},
            "GetObject",
        )

        # When / Then
        with pytest.raises(ClientError) as exc_info:
            repository.get_ocr_result(
                hacat="HC1001", po_number="E002754388", filename="document.pdf"
            )
        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_propagates_unicode_decode_error(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"\x80\x81\x82\x83"  # invalid UTF-8
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When / Then
        with pytest.raises(UnicodeDecodeError):
            repository.get_ocr_result(
                hacat="HC1001", po_number="E002754388", filename="document.pdf"
            )


class TestPutConsolidatedData:
    def test_writes_to_correct_s3_key(self, repository, mock_s3_client):
        # When
        repository.put_consolidated_data(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            data='[{"field": "value"}]',
        )

        # Then
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/output/E002754388/E002754388_20240115T103000Z.json",
            Body=b'[{"field": "value"}]',
            ContentType="application/json",
        )

    def test_key_pattern_uses_hacat_po_number_timestamp(
        self, repository, mock_s3_client
    ):
        # When
        repository.put_consolidated_data(
            hacat="HC1005",
            po_number="P999",
            timestamp=datetime(2025, 6, 1, 8, 0, 0, tzinfo=timezone.utc),
            data="[]",
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Key"] == "HC1005/output/P999/P999_20250601T080000Z.json"
        assert call_args["Bucket"] == "my-data-bucket"

    def test_encodes_data_as_utf8(self, repository, mock_s3_client):
        # When
        repository.put_consolidated_data(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            data='[{"résumé": "données"}]',
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Body"] == '[{"résumé": "données"}]'.encode("utf-8")

    def test_sets_content_type_to_application_json(self, repository, mock_s3_client):
        # When
        repository.put_consolidated_data(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            data="[]",
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["ContentType"] == "application/json"

    def test_propagates_s3_client_error(self, repository, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )

        # When / Then
        with pytest.raises(ClientError) as exc_info:
            repository.put_consolidated_data(
                hacat="HC1001",
                po_number="E002754388",
                timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                data="[]",
            )
        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


class TestCopyOcrResult:
    def test_copies_result_to_ocr_data_folder(self, repository, mock_s3_client):
        # When
        repository.copy_ocr_result(
            hacat="HC1001",
            po_number="E002754388",
            filename="document.pdf",
            invocation_id="ff79603c-591b-4e46-baf0-3823df3371d2",
        )

        # Then
        mock_s3_client.copy_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/ocr-data/E002754388/document.pdf.md",
            CopySource={
                "Bucket": "my-data-bucket",
                "Key": "HC1001/ocr-jobs/E002754388/ff79603c-591b-4e46-baf0-3823df3371d2/0/standard_output/0/result.md",
            },
        )

    def test_builds_correct_source_key(self, repository, mock_s3_client):
        # When
        repository.copy_ocr_result(
            hacat="HC1005",
            po_number="P999",
            filename="invoice.pdf",
            invocation_id="abcd-1234",
        )

        # Then
        call_args = mock_s3_client.copy_object.call_args[1]
        assert call_args["CopySource"]["Key"] == (
            "HC1005/ocr-jobs/P999/abcd-1234/0/standard_output/0/result.md"
        )

    def test_propagates_s3_exception(self, repository, mock_s3_client):
        # Given
        mock_s3_client.copy_object.side_effect = RuntimeError("NoSuchKey")

        # When / Then
        with pytest.raises(RuntimeError, match="NoSuchKey"):
            repository.copy_ocr_result(
                hacat="HC1001",
                po_number="E002754388",
                filename="document.pdf",
                invocation_id="abc-123",
            )


class TestGetCrossAccountS3Client:
    """Tests for the _get_cross_account_s3_client role-chaining logic (lines 32-70)."""

    def test_assumes_intermediate_role_first(self, env_vars):
        with patch(
            "repositories.purchase_order_file_objects_repository.boto3.client"
        ) as mock_boto_client:
            # Setup: regular S3 client for __init__
            mock_s3 = MagicMock()
            mock_sts = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return mock_s3
                if service == "sts":
                    return mock_sts
                return MagicMock()

            mock_boto_client.side_effect = client_factory

            # STS assume_role returns credentials for intermediate
            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "INTERMEDIATE_KEY",
                    "SecretAccessKey": "INTERMEDIATE_SECRET",
                    "SessionToken": "INTERMEDIATE_TOKEN",
                }
            }

            # Patch the intermediate STS client creation
            mock_intermediate_sts = MagicMock()
            mock_intermediate_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "FINAL_KEY",
                    "SecretAccessKey": "FINAL_SECRET",
                    "SessionToken": "FINAL_TOKEN",
                }
            }

            # boto3.client calls: s3 (init), sts (step1), sts (intermediate), s3 (final)
            call_count = [0]
            original_side_effect = mock_boto_client.side_effect

            def enhanced_client_factory(service, **kwargs):
                call_count[0] += 1
                if (
                    service == "sts"
                    and kwargs.get("aws_access_key_id") == "INTERMEDIATE_KEY"
                ):
                    return mock_intermediate_sts
                if service == "s3" and kwargs.get("aws_access_key_id") == "FINAL_KEY":
                    return MagicMock(name="final_s3_client")
                return original_side_effect(service, **kwargs)

            mock_boto_client.side_effect = enhanced_client_factory

            with patch(
                "repositories.purchase_order_file_objects_repository.ssm_provider"
            ) as mock_ssm:
                mock_ssm.get.return_value = "external-id-123"

                repo = PurchaseOrderFileObjectsRepository()
                result = repo._get_cross_account_s3_client()

                # Verify intermediate role was assumed
                mock_sts.assume_role.assert_called_once_with(
                    RoleArn="arn:aws:iam::123456789012:role/test-intermediate-role",
                    RoleSessionName="cedl-copy-po-files",
                )

    def test_assumes_final_cross_account_role_with_external_id(self, env_vars):
        with patch(
            "repositories.purchase_order_file_objects_repository.boto3.client"
        ) as mock_boto_client:
            mock_s3 = MagicMock()
            mock_sts = MagicMock()

            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "INTERMEDIATE_KEY",
                    "SecretAccessKey": "INTERMEDIATE_SECRET",
                    "SessionToken": "INTERMEDIATE_TOKEN",
                }
            }

            mock_intermediate_sts = MagicMock()
            mock_intermediate_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "FINAL_KEY",
                    "SecretAccessKey": "FINAL_SECRET",
                    "SessionToken": "FINAL_TOKEN",
                }
            }

            def client_factory(service, **kwargs):
                if service == "s3" and not kwargs:
                    return mock_s3
                if service == "sts" and not kwargs.get("aws_access_key_id"):
                    return mock_sts
                if (
                    service == "sts"
                    and kwargs.get("aws_access_key_id") == "INTERMEDIATE_KEY"
                ):
                    return mock_intermediate_sts
                if service == "s3" and kwargs.get("aws_access_key_id") == "FINAL_KEY":
                    return MagicMock(name="final_s3_client")
                return MagicMock()

            mock_boto_client.side_effect = client_factory

            with patch(
                "repositories.purchase_order_file_objects_repository.ssm_provider"
            ) as mock_ssm:
                mock_ssm.get.return_value = "my-external-id"

                repo = PurchaseOrderFileObjectsRepository()
                repo._get_cross_account_s3_client()

                # Verify final role assumed with external ID
                mock_intermediate_sts.assume_role.assert_called_once_with(
                    RoleArn="arn:aws:iam::987654321098:role/test-cross-account-role",
                    RoleSessionName="cedl-cross-account-session",
                    ExternalId="my-external-id",
                )

    def test_returns_s3_client_with_final_credentials(self, env_vars):
        with patch(
            "repositories.purchase_order_file_objects_repository.boto3.client"
        ) as mock_boto_client:
            mock_s3 = MagicMock()
            mock_sts = MagicMock()

            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "INTERMEDIATE_KEY",
                    "SecretAccessKey": "INTERMEDIATE_SECRET",
                    "SessionToken": "INTERMEDIATE_TOKEN",
                }
            }

            mock_intermediate_sts = MagicMock()
            mock_intermediate_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "FINAL_KEY",
                    "SecretAccessKey": "FINAL_SECRET",
                    "SessionToken": "FINAL_TOKEN",
                }
            }

            final_s3_mock = MagicMock(name="final_s3_client")

            def client_factory(service, **kwargs):
                if service == "s3" and not kwargs:
                    return mock_s3
                if service == "sts" and not kwargs.get("aws_access_key_id"):
                    return mock_sts
                if (
                    service == "sts"
                    and kwargs.get("aws_access_key_id") == "INTERMEDIATE_KEY"
                ):
                    return mock_intermediate_sts
                if service == "s3" and kwargs.get("aws_access_key_id") == "FINAL_KEY":
                    return final_s3_mock
                return MagicMock()

            mock_boto_client.side_effect = client_factory

            with patch(
                "repositories.purchase_order_file_objects_repository.ssm_provider"
            ) as mock_ssm:
                mock_ssm.get.return_value = "ext-id"

                repo = PurchaseOrderFileObjectsRepository()
                result = repo._get_cross_account_s3_client()

                # Verify the returned client uses final credentials
                assert result is final_s3_mock

    def test_fetches_external_id_from_ssm_with_decrypt(self, env_vars):
        with patch(
            "repositories.purchase_order_file_objects_repository.boto3.client"
        ) as mock_boto_client:
            mock_s3 = MagicMock()
            mock_sts = MagicMock()

            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "KEY1",
                    "SecretAccessKey": "SECRET1",
                    "SessionToken": "TOKEN1",
                }
            }

            mock_intermediate_sts = MagicMock()
            mock_intermediate_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "KEY2",
                    "SecretAccessKey": "SECRET2",
                    "SessionToken": "TOKEN2",
                }
            }

            def client_factory(service, **kwargs):
                if service == "s3" and not kwargs:
                    return mock_s3
                if service == "sts" and not kwargs.get("aws_access_key_id"):
                    return mock_sts
                if service == "sts" and kwargs.get("aws_access_key_id") == "KEY1":
                    return mock_intermediate_sts
                return MagicMock()

            mock_boto_client.side_effect = client_factory

            with patch(
                "repositories.purchase_order_file_objects_repository.ssm_provider"
            ) as mock_ssm:
                mock_ssm.get.return_value = "secret-external-id"

                repo = PurchaseOrderFileObjectsRepository()
                repo._get_cross_account_s3_client()

                # Verify SSM called with correct path and decrypt=True
                mock_ssm.get.assert_called_once_with(
                    "/test/prefix/coupa/crossAccountExternalId",
                    max_age=300,
                    decrypt=True,
                )

    def test_propagates_sts_error(self, env_vars):
        with patch(
            "repositories.purchase_order_file_objects_repository.boto3.client"
        ) as mock_boto_client:
            mock_s3 = MagicMock()
            mock_sts = MagicMock()
            mock_sts.assume_role.side_effect = RuntimeError("STS unavailable")

            def client_factory(service, **kwargs):
                if service == "s3":
                    return mock_s3
                if service == "sts":
                    return mock_sts
                return MagicMock()

            mock_boto_client.side_effect = client_factory

            repo = PurchaseOrderFileObjectsRepository()

            with pytest.raises(RuntimeError, match="STS unavailable"):
                repo._get_cross_account_s3_client()


class TestExportToCedl:
    def test_reads_from_data_bucket_with_correct_source_key(
        self, repository_with_ssm, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b'{"consolidated": "data"}'
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/output/E002754388/E002754388_20250709T154416Z.json",
        )

    def test_constructs_correct_destination_key(
        self, repository_with_ssm, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b'{"consolidated": "data"}'
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Key"] == (
            "DUMMY_UNSTRUCTURED_DATA/GEN_AI/BIOMARKER"
            "/2025-07-09/E002754388_20250709T154416Z.json"
        )

    def test_uses_cross_account_s3_client(
        self, env_vars, mock_s3_client, mock_ssm_provider
    ):
        # Given - create a separate mock for the cross-account client
        cross_account_mock = MagicMock()
        body_mock = MagicMock()
        body_mock.read.return_value = b"{}"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        repo = PurchaseOrderFileObjectsRepository()
        repo._get_cross_account_s3_client = lambda: cross_account_mock

        # When
        repo.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then - cross-account client is used for put, not the regular S3 client
        cross_account_mock.put_object.assert_called_once()
        mock_s3_client.put_object.assert_not_called()

    def test_passes_raw_bytes_without_decode_encode(
        self, repository_with_ssm, mock_s3_client
    ):
        # Given
        raw_bytes = '{"résumé": "données spéciales"}'.encode("utf-8")
        body_mock = MagicMock()
        body_mock.read.return_value = raw_bytes
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then - raw bytes passed through without decode/encode
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Body"] is raw_bytes

    def test_calls_put_object_with_correct_params(
        self, repository_with_ssm, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b'{"field": "value"}'
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="my-cedl-bucket",
            Key="DUMMY_UNSTRUCTURED_DATA/GEN_AI/BIOMARKER/2025-07-09/E002754388_20250709T154416Z.json",
            Body=b'{"field": "value"}',
            ContentType="application/json",
        )

    def test_sets_content_type_to_application_json(
        self, repository_with_ssm, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"{}"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["ContentType"] == "application/json"

    def test_propagates_s3_read_exception(self, repository_with_ssm, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The key does not exist"}},
            "GetObject",
        )

        # When / Then
        with pytest.raises(ClientError) as exc_info:
            repository_with_ssm.export(
                hacat="HC1001",
                po_number="E002754388",
                timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
            )
        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_propagates_s3_write_exception(self, repository_with_ssm, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"{}"
        mock_s3_client.get_object.return_value = {"Body": body_mock}
        mock_s3_client.put_object.side_effect = RuntimeError("Access denied")

        # When / Then
        with pytest.raises(RuntimeError, match="Access denied"):
            repository_with_ssm.export(
                hacat="HC1001",
                po_number="E002754388",
                timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
            )

    def test_ssm_called_with_correct_key_and_max_age(
        self, repository_with_ssm, mock_s3_client, mock_ssm_provider
    ):
        """SSM parameter is fetched with correct key and max_age=300."""
        body_mock = MagicMock()
        body_mock.read.return_value = b"{}"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        repository_with_ssm.export(
            hacat="HC1001",
            po_number="E002754388",
            timestamp=datetime(2025, 7, 9, 15, 44, 16, tzinfo=timezone.utc),
        )

        mock_ssm_provider.get.assert_called_once_with(
            "/test/prefix/hacat/HC1001/cedlExportPath",
            max_age=300,
        )


class TestDownloadIncomingFile:
    def test_calls_get_object_with_correct_bucket_and_key(
        self, repository, mock_s3_client
    ):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"file-content"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository.download_incoming_file(
            hacat="HC1001", po_number="E002754388", filename="presentation.pptx"
        )

        # Then
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/incoming/E002754388/presentation.pptx",
        )

    def test_returns_raw_bytes(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"\x89PNG\r\n\x1a\nraw-binary-content"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        result = repository.download_incoming_file(
            hacat="HC1005", po_number="P999", filename="report.xlsx"
        )

        # Then
        assert result == b"\x89PNG\r\n\x1a\nraw-binary-content"

    def test_builds_key_from_hacat_po_number_filename(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = b"data"
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        repository.download_incoming_file(
            hacat="HC1005", po_number="E000024494", filename="doc.pdf"
        )

        # Then
        call_args = mock_s3_client.get_object.call_args[1]
        assert call_args["Key"] == "HC1005/incoming/E000024494/doc.pdf"

    def test_propagates_s3_exception(self, repository, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The key does not exist"}},
            "GetObject",
        )

        # When / Then
        with pytest.raises(ClientError) as exc_info:
            repository.download_incoming_file(
                hacat="HC1001", po_number="E002754388", filename="missing.pptx"
            )
        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"


class TestUploadIncomingFile:
    def test_calls_put_object_with_correct_params(self, repository, mock_s3_client):
        # When
        repository.upload_incoming_file(
            hacat="HC1001",
            po_number="E002754388",
            filename="presentation.pdf",
            content=b"pdf-bytes",
            content_type="application/pdf",
        )

        # Then
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/incoming/E002754388/presentation.pdf",
            Body=b"pdf-bytes",
            ContentType="application/pdf",
        )

    def test_builds_key_from_hacat_po_number_filename(self, repository, mock_s3_client):
        # When
        repository.upload_incoming_file(
            hacat="HC1005",
            po_number="P999",
            filename="report.pdf",
            content=b"data",
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["Key"] == "HC1005/incoming/P999/report.pdf"

    def test_uses_default_content_type(self, repository, mock_s3_client):
        # When
        repository.upload_incoming_file(
            hacat="HC1005",
            po_number="P999",
            filename="report.pdf",
            content=b"data",
        )

        # Then
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args["ContentType"] == "application/octet-stream"

    def test_propagates_s3_exception(self, repository, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )

        # When / Then
        with pytest.raises(ClientError) as exc_info:
            repository.upload_incoming_file(
                hacat="HC1001",
                po_number="E002754388",
                filename="presentation.pdf",
                content=b"pdf-bytes",
                content_type="application/pdf",
            )
        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


class TestGetMapping:
    """Tests for get_mapping (Composant 6ter, Req 7.4).

    get_mapping reads a mapping object from the data bucket using the repository's
    own S3 client. A missing object (NoSuchKey / ClientError 404) yields None; any
    other S3 error is propagated.
    """

    def test_returns_utf8_content_when_object_present(self, repository, mock_s3_client):
        # Given
        body_mock = MagicMock()
        body_mock.read.return_value = '{"map": "données spéciales"}'.encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        # When
        result = repository.get_mapping(s3_key="HC1001/mappings/mapping.json")

        # Then - content decoded as UTF-8 and returned as-is
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="my-data-bucket",
            Key="HC1001/mappings/mapping.json",
        )
        assert result == '{"map": "données spéciales"}'

    def test_returns_none_when_nosuchkey_raised(self, repository, mock_s3_client):
        # Given - s3_client.exceptions.NoSuchKey is a real exception class the
        # SUT catches via `except self._s3_client.exceptions.NoSuchKey`.
        class NoSuchKey(Exception):
            pass

        mock_s3_client.exceptions.NoSuchKey = NoSuchKey
        mock_s3_client.get_object.side_effect = NoSuchKey(
            "The specified key does not exist"
        )

        # When
        result = repository.get_mapping(s3_key="HC1001/mappings/missing.json")

        # Then
        assert result is None

    def test_returns_none_on_client_error_404(self, repository, mock_s3_client):
        # Given - a NoSuchKey exceptions attribute distinct from ClientError so
        # the SUT falls through to the ClientError handler.
        from botocore.exceptions import ClientError

        class NoSuchKey(Exception):
            pass

        mock_s3_client.exceptions.NoSuchKey = NoSuchKey
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "GetObject",
        )

        # When
        result = repository.get_mapping(s3_key="HC1001/mappings/missing.json")

        # Then
        assert result is None

    def test_propagates_client_error_non_404(self, repository, mock_s3_client):
        # Given
        from botocore.exceptions import ClientError

        class NoSuchKey(Exception):
            pass

        mock_s3_client.exceptions.NoSuchKey = NoSuchKey
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Access Denied"}},
            "GetObject",
        )

        # When / Then - non-404 errors are propagated
        with pytest.raises(ClientError) as exc_info:
            repository.get_mapping(s3_key="HC1001/mappings/forbidden.json")
        assert exc_info.value.response["Error"]["Code"] == "403"
