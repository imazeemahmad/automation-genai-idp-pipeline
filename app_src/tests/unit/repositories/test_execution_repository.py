from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from repositories.execution_repository import ExecutionRepository


@pytest.fixture
def env_vars():
    with patch.dict("os.environ", {"SSM_PREFIX": "/my-app/dev"}):
        yield


@pytest.fixture
def mock_ssm_client():
    with patch("repositories.execution_repository.boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def mock_ssm_provider():
    with patch("repositories.execution_repository.ssm_provider") as mock_provider:
        yield mock_provider


@pytest.fixture
def repository(env_vars, mock_ssm_client):
    return ExecutionRepository()


class TestGetLastExecution:
    def test_returns_value_from_ssm(self, repository, mock_ssm_provider):
        # Given
        mock_ssm_provider.get.return_value = "2025-06-15T10:30:00+00:00"

        # When
        result = repository.get_last_execution("HC1005")

        # Then
        assert result == datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        mock_ssm_provider.get.assert_called_once_with(
            "/my-app/dev/hacat/HC1005/lastExecution", max_age=0
        )

    def test_builds_param_name_from_prefix_and_hacat(
        self, repository, mock_ssm_provider
    ):
        # Given
        mock_ssm_provider.get.return_value = "2025-01-01T00:00:00+00:00"

        # When
        repository.get_last_execution("HC1006")

        # Then
        mock_ssm_provider.get.assert_called_once_with(
            "/my-app/dev/hacat/HC1006/lastExecution", max_age=0
        )

    def test_propagates_exception_when_parameter_not_found(
        self, repository, mock_ssm_provider
    ):
        # Given
        mock_ssm_provider.get.side_effect = Exception("Parameter not found")

        # When / Then
        with pytest.raises(Exception, match="Parameter not found"):
            repository.get_last_execution("UNKNOWN")


class TestUpdateLastExecution:
    def test_puts_given_timestamp_to_ssm(self, repository, mock_ssm_client):
        # When
        ts = datetime(2025, 7, 1, 14, 30, tzinfo=timezone.utc)
        repository.update_last_execution("HC1005", ts)

        # Then
        mock_ssm_client.put_parameter.assert_called_once_with(
            Name="/my-app/dev/hacat/HC1005/lastExecution",
            Value=str(ts),
            Type="String",
            Overwrite=True,
        )

    def test_builds_param_name_from_prefix_and_hacat(self, repository, mock_ssm_client):
        # When
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repository.update_last_execution("HC1006", ts)

        # Then
        call_args = mock_ssm_client.put_parameter.call_args
        assert call_args[1]["Name"] == "/my-app/dev/hacat/HC1006/lastExecution"

    def test_propagates_exception_on_put_failure(self, repository, mock_ssm_client):
        # Given
        mock_ssm_client.put_parameter.side_effect = RuntimeError("SSM error")

        # When / Then
        ts = datetime(2025, 7, 1, tzinfo=timezone.utc)
        with pytest.raises(RuntimeError, match="SSM error"):
            repository.update_last_execution("HC1005", ts)


class TestInit:
    def test_reads_ssm_prefix_from_env(self, env_vars, mock_ssm_client):
        repo = ExecutionRepository()
        assert repo._ssm_prefix == "/my-app/dev"

    def test_defaults_to_empty_prefix_when_env_not_set(self, mock_ssm_client):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(KeyError):
                ExecutionRepository()
