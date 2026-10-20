from unittest.mock import MagicMock, patch

import pytest

from repositories.coupa_repository import CoupaRepository
from services.procurements_service import ProcurementsService


@pytest.fixture
def mock_s3_client():
    return MagicMock()


@pytest.fixture
def service(mock_s3_client):
    return ProcurementsService(
        coupa_repository=CoupaRepository(),
        s3_client=mock_s3_client,
        bucket_name="test-bucket",
    )


class TestProcessProcurement:
    def test_returns_files_matching_prefix(self, service, mock_s3_client):
        # Given
        paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "P001/file1.pdf"}, {"Key": "P001/file2.csv"}]},
            {"Contents": [{"Key": "P001/subdir/file3.json"}]},
        ]

        # When
        result = service.process_procurement("P001")

        # Then
        assert result == ["P001/file1.pdf", "P001/file2.csv", "P001/subdir/file3.json"]
        mock_s3_client.get_paginator.assert_called_once_with("list_objects_v2")
        paginator.paginate.assert_called_once_with(
            Bucket="test-bucket", Prefix="P001"
        )

    def test_returns_empty_list_when_no_files(self, service, mock_s3_client):
        # Given
        paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [{}]

        # When
        result = service.process_procurement("P999")

        # Then
        assert result == []

    def test_handles_multiple_pages(self, service, mock_s3_client):
        # Given
        paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "P002/a.txt"}]},
            {"Contents": [{"Key": "P002/b.txt"}]},
            {"Contents": [{"Key": "P002/c.txt"}]},
        ]

        # When
        result = service.process_procurement("P002")

        # Then
        assert result == ["P002/a.txt", "P002/b.txt", "P002/c.txt"]
