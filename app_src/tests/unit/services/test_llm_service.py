import json
from unittest.mock import patch

import pytest

from services.llm_service import LlmService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "1")


@pytest.fixture
def service():
    return LlmService()


class TestInvoke:
    @patch("services.llm_service.bedrock_client")
    def test_success_with_text_block(self, mock_bedrock, service):
        """Successful invocation returns parsed JSON."""
        mock_bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": '{"result": "ok"}'}]}},
            "stopReason": "end_turn",
        }

        result = service.invoke(
            model_id="arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            prompt_variables={"documents": '[{"doc": "content"}]'},
        )

        assert json.loads(result) == {"result": "ok"}
        mock_bedrock.converse.assert_called_once_with(
            modelId="arn:aws:bedrock:eu-west-1:123:prompt/ABC:1",
            promptVariables={"documents": {"text": '[{"doc": "content"}]'}},
        )

    @patch("services.llm_service.bedrock_client")
    def test_success_with_reasoning_and_text_blocks(self, mock_bedrock, service):
        """Response with reasoning block + text block returns the text."""
        mock_bedrock.converse.return_value = {
            "output": {
                "message": {
                    "content": [
                        {
                            "reasoningContent": {
                                "reasoningText": {"text": "thinking..."}
                            }
                        },
                        {"text": '{"supplier": "ACME"}'},
                    ]
                }
            },
            "stopReason": "end_turn",
        }

        result = service.invoke(
            model_id="arn:prompt:1",
            prompt_variables={"data": "test"},
        )

        assert json.loads(result) == {"supplier": "ACME"}

    @patch("services.llm_service.bedrock_client")
    def test_no_text_block_raises_value_error(self, mock_bedrock, service):
        """Response with no text block raises ValueError."""
        mock_bedrock.converse.return_value = {
            "output": {
                "message": {
                    "content": [
                        {
                            "reasoningContent": {
                                "reasoningText": {"text": "only thinking"}
                            }
                        },
                    ]
                }
            },
            "stopReason": "end_turn",
        }

        with pytest.raises(ValueError, match="no text block"):
            service.invoke(model_id="arn:prompt:1", prompt_variables={"x": "y"})

    @patch("services.llm_service.bedrock_client")
    def test_invalid_json_raises_decode_error(self, mock_bedrock, service):
        """Invalid JSON in text block raises JSONDecodeError."""
        mock_bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "not valid json {{"}]}},
            "stopReason": "end_turn",
        }

        with pytest.raises(json.JSONDecodeError):
            service.invoke(model_id="arn:prompt:1", prompt_variables={"x": "y"})

    @patch("services.llm_service.bedrock_client")
    def test_strips_markdown_fences(self, mock_bedrock, service):
        """JSON wrapped in markdown fences is parsed correctly."""
        mock_bedrock.converse.return_value = {
            "output": {
                "message": {"content": [{"text": '```json\n{"key": "value"}\n```'}]}
            },
            "stopReason": "end_turn",
        }

        result = service.invoke(model_id="arn:prompt:1", prompt_variables={"x": "y"})
        assert json.loads(result) == {"key": "value"}

    @patch("services.llm_service.bedrock_client")
    def test_bedrock_exception_propagates(self, mock_bedrock, service):
        """Bedrock client exception propagates to caller."""
        mock_bedrock.converse.side_effect = RuntimeError("Throttled")

        with pytest.raises(RuntimeError, match="Throttled"):
            service.invoke(model_id="arn:prompt:1", prompt_variables={"x": "y"})
