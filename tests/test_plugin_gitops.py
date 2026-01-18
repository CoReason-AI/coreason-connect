# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from unittest.mock import MagicMock, Mock

import httpx
import pytest
from coreason_connect.interfaces import SecretsProvider
from coreason_connect.plugins.gitops import GitOpsConnector
from coreason_connect.types import ToolExecutionError


@pytest.fixture
def mock_secrets() -> MagicMock:
    secrets = MagicMock(spec=SecretsProvider)
    secrets.get_secret.return_value = "mock_token"
    return secrets


@pytest.fixture
def gitops_plugin(mock_secrets: MagicMock) -> GitOpsConnector:
    return GitOpsConnector(secrets=mock_secrets)


def test_initialization(gitops_plugin: GitOpsConnector) -> None:
    assert gitops_plugin.token == "mock_token"
    assert isinstance(gitops_plugin.client, httpx.Client)


def test_get_tools(gitops_plugin: GitOpsConnector) -> None:
    tools = gitops_plugin.get_tools()
    assert len(tools) == 2
    names = [t.name for t in tools]
    assert "git_create_pr" in names
    assert "git_get_build_logs" in names

    pr_tool = next(t for t in tools if t.name == "git_create_pr")
    assert "repo" in pr_tool.tool.inputSchema["properties"]  # type: ignore
    assert "branch" in pr_tool.tool.inputSchema["properties"]  # type: ignore


def test_create_pr_success(gitops_plugin: GitOpsConnector) -> None:
    # Mock the httpx client
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"html_url": "https://github.com/owner/repo/pull/1"}
    mock_response.raise_for_status = Mock()

    gitops_plugin.client.post = Mock(return_value=mock_response)  # type: ignore

    args = {
        "repo": "owner/repo",
        "branch": "feature-branch",
        "changes": "fix: bug",
        "title": "Fix bug",
    }
    result = gitops_plugin.execute("git_create_pr", args)

    assert result["html_url"] == "https://github.com/owner/repo/pull/1"
    gitops_plugin.client.post.assert_called_once()
    call_args = gitops_plugin.client.post.call_args
    assert call_args[0][0] == "/repos/owner/repo/pulls"
    assert call_args[1]["json"]["title"] == "Fix bug"
    assert call_args[1]["json"]["head"] == "feature-branch"


def test_create_pr_missing_args(gitops_plugin: GitOpsConnector) -> None:
    with pytest.raises(ToolExecutionError) as excinfo:
        gitops_plugin.execute("git_create_pr", {"repo": "owner/repo"})
    assert "Missing required arguments" in str(excinfo.value)


def test_create_pr_api_error(gitops_plugin: GitOpsConnector) -> None:
    # Mock failure
    mock_response = Mock()
    mock_response.status_code = 422
    mock_response.text = "Validation Failed"

    # raise_for_status should raise an HTTPStatusError
    error = httpx.HTTPStatusError("422 Client Error", request=Mock(), response=mock_response)
    mock_response.raise_for_status.side_effect = error

    gitops_plugin.client.post = Mock(return_value=mock_response)  # type: ignore

    args = {
        "repo": "owner/repo",
        "branch": "bad-branch",
        "changes": "stuff",
        "title": "Bad PR",
    }

    with pytest.raises(ToolExecutionError) as excinfo:
        gitops_plugin.execute("git_create_pr", args)

    assert "GitHub API error: 422" in str(excinfo.value)
    assert not excinfo.value.retryable


def test_get_build_logs_success(gitops_plugin: GitOpsConnector) -> None:
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "check_runs": [
            {
                "status": "completed",
                "conclusion": "failure",
                "name": "build",
                "output": {"summary": "Error: build failed"},
            },
            {
                "status": "completed",
                "conclusion": "success",
                "name": "lint",
            }
        ]
    }
    mock_response.raise_for_status = Mock()

    gitops_plugin.client.get = Mock(return_value=mock_response)  # type: ignore

    args = {"repo": "owner/repo", "commit_sha": "abcdef123456"}
    result = gitops_plugin.execute("git_get_build_logs", args)

    assert result["status"] == "failure"
    assert len(result["logs"]) == 1
    assert result["logs"][0]["name"] == "build"
    assert "Error: build failed" in result["logs"][0]["output"]


def test_unknown_tool(gitops_plugin: GitOpsConnector) -> None:
    with pytest.raises(ToolExecutionError) as excinfo:
        gitops_plugin.execute("unknown_tool", {})
    assert "Unknown tool" in str(excinfo.value)


def test_init_missing_token() -> None:
    mock_secrets = MagicMock(spec=SecretsProvider)
    mock_secrets.get_secret.side_effect = KeyError("Missing")

    plugin = GitOpsConnector(secrets=mock_secrets)
    assert plugin.token == "mock_token"


def test_execute_generic_error(gitops_plugin: GitOpsConnector) -> None:
    gitops_plugin.client.post = Mock(side_effect=Exception("Boom"))  # type: ignore

    with pytest.raises(ToolExecutionError) as excinfo:
        gitops_plugin.execute("git_create_pr", {"repo": "a", "branch": "b", "title": "c", "changes": "d"})

    assert "GitOps error: Boom" in str(excinfo.value)


def test_get_build_logs_missing_args(gitops_plugin: GitOpsConnector) -> None:
    with pytest.raises(ToolExecutionError) as excinfo:
        gitops_plugin.execute("git_get_build_logs", {"repo": "owner/repo"})
    assert "Missing required arguments" in str(excinfo.value)


def test_get_build_logs_no_failures(gitops_plugin: GitOpsConnector) -> None:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "check_runs": [
            {
                "status": "completed",
                "conclusion": "success",
                "name": "build",
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    gitops_plugin.client.get = Mock(return_value=mock_response)  # type: ignore

    args = {"repo": "owner/repo", "commit_sha": "abcdef123456"}
    result = gitops_plugin.execute("git_get_build_logs", args)

    assert result["status"] == "success"
    assert "No failed checks" in result["message"]
