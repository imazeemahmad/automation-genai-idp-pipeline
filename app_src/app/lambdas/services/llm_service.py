import json

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config

logger = Logger()

bedrock_config = Config(read_timeout=600)
bedrock_client = boto3.client("bedrock-runtime", config=bedrock_config)


class LlmService:
    """Service for invoking Bedrock LLM via Prompt Management."""

    def invoke(
        self,
        model_id: str,
        prompt_variables: dict[str, str],
    ) -> str:
        """Invoke a Bedrock managed prompt and return the parsed JSON response.

        Args:
            model_id: The Bedrock prompt ARN (with version) to invoke.
            prompt_variables: Dict of variable name -> value to pass to the prompt.

        Returns:
            The JSON response string from the model (validated and re-serialized).

        Raises:
            ValueError: If the response contains no text block.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        # Build promptVariables in Bedrock format
        bedrock_variables = {
            key: {"text": value} for key, value in prompt_variables.items()
        }

        response = bedrock_client.converse(
            modelId=model_id,
            promptVariables=bedrock_variables,
        )

        # Log response structure for debugging
        content_blocks = response["output"]["message"]["content"]
        logger.info(
            "Bedrock response received",
            extra={
                "model_id": model_id,
                "stop_reason": response.get("stopReason"),
                "content_block_count": len(content_blocks),
                "content_block_types": [list(block.keys()) for block in content_blocks],
            },
        )

        # Extract text block (skip thinking/reasoning blocks)
        response_text = next(
            (block["text"] for block in content_blocks if "text" in block),
            None,
        )

        if response_text is None:
            logger.error(
                "No text block found in Bedrock response",
                extra={"content_blocks": json.dumps(content_blocks, default=str)},
            )
            raise ValueError("Bedrock response contains no text block")

        return self._parse_response(response_text)

    @staticmethod
    def _parse_response(response_text: str) -> str:
        """Parse the Bedrock response text, stripping markdown fences if present.

        Args:
            response_text: Raw text from Bedrock converse response.

        Returns:
            JSON string (validated by parsing then re-serializing).

        Raises:
            json.JSONDecodeError: If the response is not valid JSON after stripping.
        """
        text = response_text.strip()
        if text.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3].rstrip()

        parsed = json.loads(text)
        return json.dumps(parsed)
