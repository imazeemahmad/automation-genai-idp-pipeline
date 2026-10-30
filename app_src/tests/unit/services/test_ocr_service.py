from unittest.mock import MagicMock, patch

import pytest

from services.ocr_service import OcrService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv(
        "BDA_PROJECT_ARN",
        "arn:aws:bedrock:us-east-1:123456789012:data-automation-project/test-project",
    )
    monkeypatch.setenv(
        "BDA_PROFILE_ARN",
        "arn:aws:bedrock:us-east-1:123456789012:data-automation-profile/test-profile",
    )


@pytest.fixture
def mock_bda_client():
    with patch("services.ocr_service.boto3.client") as mock_boto_client:
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def ocr_service(mock_bda_client):
    return OcrService()


class TestOcrService:
    def test_invoke_returns_invocation_arn(self, ocr_service, mock_bda_client):
        # Given
        mock_bda_client.invoke_data_automation_async.return_value = {
            "invocationArn": "arn:aws:bedrock:us-east-1:123:invocation/job-456"
        }

        input_uri = "s3://test-bucket/HC1001/incoming/P001/doc.pdf"
        output_uri = "s3://test-bucket/HC1001/ocr-jobs/P001/"

        # When
        result = ocr_service.invoke(input_s3_uri=input_uri, output_s3_uri=output_uri)

        # Then
        assert result == "arn:aws:bedrock:us-east-1:123:invocation/job-456"
        mock_bda_client.invoke_data_automation_async.assert_called_once_with(
            inputConfiguration={
                "s3Uri": input_uri,
            },
            outputConfiguration={
                "s3Uri": output_uri,
            },
            dataAutomationConfiguration={
                "dataAutomationProjectArn": "arn:aws:bedrock:us-east-1:123456789012:data-automation-project/test-project",
            },
            dataAutomationProfileArn="arn:aws:bedrock:us-east-1:123456789012:data-automation-profile/test-profile",
        )

    def test_invoke_raises_on_bda_error(self, ocr_service, mock_bda_client):
        # Given
        mock_bda_client.invoke_data_automation_async.side_effect = Exception(
            "BDA service error"
        )

        input_uri = "s3://test-bucket/HC1001/incoming/P001/doc.pdf"
        output_uri = "s3://test-bucket/HC1001/ocr-jobs/P001/"

        # When / Then
        with pytest.raises(Exception, match="BDA service error"):
            ocr_service.invoke(input_s3_uri=input_uri, output_s3_uri=output_uri)
