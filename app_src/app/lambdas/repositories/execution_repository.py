"""Repository for managing execution tracking via SSM Parameter Store."""

import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities import parameters

logger = Logger()

ssm_provider = parameters.SSMProvider()


class ExecutionRepository:

    def __init__(self):
        self._ssm_prefix = os.environ["SSM_PREFIX"]
        self._ssm_client = boto3.client("ssm")

    def get_last_execution(self, hacat: str) -> datetime:
        """Retrieve the lastExecution date from SSM for a given hacat.

        Returns:
            A datetime object parsed from the stored SSM value.

        Raises:
            parameters.exceptions.GetParameterError: If the SSM parameter does not exist.
        """
        param_name = f"{self._ssm_prefix}/hacat/{hacat}/lastExecution"
        value = ssm_provider.get(param_name, max_age=0)
        logger.info(f"Retrieved lastExecution for hacat={hacat}: {value}")
        return datetime.fromisoformat(value)

    def update_last_execution(self, hacat: str, timestamp: datetime) -> None:
        """Update the lastExecution SSM parameter with the given timestamp."""
        param_name = f"{self._ssm_prefix}/hacat/{hacat}/lastExecution"
        self._ssm_client.put_parameter(
            Name=param_name,
            Value=str(timestamp),
            Type="String",
            Overwrite=True,
        )
        logger.info(f"Updated lastExecution for hacat={hacat} to {timestamp}")
