import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from services.conversion_service import ConversionService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv(
        "LIBREOFFICE_CONVERTER_LAMBDA_ARN",
        "arn:aws:lambda:eu-west-1:123456789:function:converter",
    )
    monkeypatch.setenv("DATA_BUCKET_NAME", "test-data-bucket")


@pytest.fixture(autouse=True)
def mock_logger():
    with patch("services.conversion_service.logger") as mocked:
        yield mocked


@pytest.fixture
def mock_lambda_client():
    with patch("services.conversion_service.lambda_client") as mocked:
        yield mocked


@pytest.fixture
def service():
    return ConversionService()


class TestConvertToPdf:
    def test_invokes_lambda_with_correct_payload(self, service, mock_lambda_client):
        # Given
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": BytesIO(json.dumps({"status": "success"}).encode()),
        }

        # When
        service.convert_to_pdf(
            source_key="HC1001/incoming/P001/presentation.pptx",
            destination_key="HC1001/incoming/P001/presentation.pdf",
        )

        # Then
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName="arn:aws:lambda:eu-west-1:123456789:function:converter",
            InvocationType="RequestResponse",
            Payload=json.dumps(
                {
                    "source_key": "HC1001/incoming/P001/presentation.pptx",
                    "destination_key": "HC1001/incoming/P001/presentation.pdf",
                }
            ),
        )

    def test_returns_none_on_success(self, service, mock_lambda_client):
        # Given
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": BytesIO(json.dumps({"status": "success"}).encode()),
        }

        # When
        result = service.convert_to_pdf(
            source_key="HC1001/incoming/P001/slides.pptx",
            destination_key="HC1001/incoming/P001/slides.pdf",
        )

        # Then
        assert result is None


class TestErrorHandling:
    def test_function_error_raises_runtime_error(self, service, mock_lambda_client):
        # Given
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "FunctionError": "Unhandled",
            "Payload": BytesIO(
                json.dumps(
                    {
                        "errorMessage": "LibreOffice conversion failed for 'presentation.pptx' (exit code 1): error details",
                        "errorType": "RuntimeError",
                    }
                ).encode()
            ),
        }

        # When / Then
        with pytest.raises(RuntimeError, match="LibreOffice converter Lambda failed"):
            service.convert_to_pdf(
                source_key="HC1001/incoming/P001/presentation.pptx",
                destination_key="HC1001/incoming/P001/presentation.pdf",
            )

    def test_function_error_with_unknown_message(self, service, mock_lambda_client):
        # Given
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "FunctionError": "Unhandled",
            "Payload": BytesIO(json.dumps({}).encode()),
        }

        # When / Then
        with pytest.raises(RuntimeError, match="Unknown error"):
            service.convert_to_pdf(
                source_key="HC1001/incoming/P001/presentation.pptx",
                destination_key="HC1001/incoming/P001/presentation.pdf",
            )


class TestStructuredLogging:
    def test_logs_invocation_and_completion(
        self, service, mock_lambda_client, mock_logger
    ):
        # Given
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": BytesIO(json.dumps({"status": "success"}).encode()),
        }

        # When
        service.convert_to_pdf(
            source_key="HC1001/incoming/P001/presentation.pptx",
            destination_key="HC1001/incoming/P001/presentation.pdf",
        )

        # Then — should log both invocation and completion
        assert mock_logger.info.call_count == 2

        # Check invocation log
        invocation_call = mock_logger.info.call_args_list[0]
        assert "Invoking" in invocation_call.args[0]

        # Check completion log
        completion_call = mock_logger.info.call_args_list[1]
        assert completion_call.kwargs["extra"]["action"] == "converted"
