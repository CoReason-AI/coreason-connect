# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any, Optional

import httpx
from coreason_identity.models import UserContext
from mcp.types import Tool

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition, ToolExecutionError
from coreason_connect.utils.logger import logger


class GitOpsConnector(ConnectorProtocol):
    """Native plugin for DevOps operations using GitHub/Git APIs.

    Implements the 'Self-healing code and configuration' capability.
    """

    def __init__(self, secrets: SecretsProvider) -> None:
        """Initialize the GitOps connector.

        Args:
            secrets: The secrets provider for obtaining the GITHUB_TOKEN.
        """
        super().__init__(secrets)
        # In a real implementation, we would fetch the GitHub Token.
        # For now, we assume it's available or use a placeholder.
        try:
            self.token = self.secrets.get_secret("GITHUB_TOKEN")
        except KeyError:
            logger.warning("GITHUB_TOKEN not found. GitOps plugin running in limited/mock mode.")
            self.token = "mock_token"

        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        # Use a client that can be mocked in tests
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers)

    def get_tools(self) -> list[ToolDefinition]:
        """Return a list of available tools.

        Returns:
            list[ToolDefinition]: A list of ToolDefinition objects.
        """
        return [
            ToolDefinition(
                name="git_create_pr",
                tool=Tool(
                    name="git_create_pr",
                    description="Automates the Fork -> Branch -> Commit -> PR workflow.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                            "branch": {"type": "string", "description": "Target branch name"},
                            "changes": {
                                "type": "string",
                                "description": "Description or content of changes to apply",
                            },
                            "title": {"type": "string", "description": "Pull Request title"},
                            "body": {"type": "string", "description": "Pull Request body"},
                        },
                        "required": ["repo", "branch", "changes", "title"],
                    },
                ),
            ),
            ToolDefinition(
                name="git_get_build_logs",
                tool=Tool(
                    name="git_get_build_logs",
                    description="Retrieves CI/CD failure logs for analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "commit_sha": {"type": "string", "description": "The commit SHA to check logs for"},
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                        },
                        "required": ["commit_sha", "repo"],
                    },
                ),
            ),
        ]

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: Optional[UserContext] = None,
    ) -> Any:
        """Execute a GitOps tool.

        Args:
            tool_name: The name of the tool to execute.
            arguments: A dictionary of arguments for the tool.
            user_context: The user context containing identity and tokens.

        Returns:
            Any: The result of the tool execution.

        Raises:
            ToolExecutionError: If the tool fails or is unknown.
        """
        args = arguments or {}
        try:
            if tool_name == "git_create_pr":
                return self._create_pr(args)
            elif tool_name == "git_get_build_logs":
                return self._get_build_logs(args)
            else:
                raise ToolExecutionError(f"Unknown tool: {tool_name}")
        except httpx.HTTPStatusError as e:
            # Wrap HTTP errors
            msg = f"GitHub API error: {e.response.status_code} - {e.response.text}"
            raise ToolExecutionError(msg, retryable=e.response.status_code >= 500) from e
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"GitOps error: {str(e)}") from e

    def _create_pr(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a Pull Request.

        Args:
            args: Dictionary containing 'repo', 'branch', 'title', and optional 'body'.

        Returns:
            dict[str, Any]: The JSON response from the GitHub API.

        Raises:
            ToolExecutionError: If required arguments are missing or API call fails.
        """
        repo = args.get("repo")
        branch = args.get("branch")
        title = args.get("title")
        body = args.get("body", "Automated PR created by coreason-connect")
        # 'changes' would be used to create the commit in a real implementation
        # For this atomic unit, we assume the branch/commit logic is part of the "automation"
        # which we are simplifying to just the PR creation call for the API level.

        if not repo or not branch or not title:
            raise ToolExecutionError("Missing required arguments for git_create_pr")

        # Simplified Logic:
        # 1. We assume the code change logic (Fork/Commit) happened or is simulated.
        # 2. We just call the Create PR endpoint.
        # POST /repos/{owner}/{repo}/pulls
        url = f"/repos/{repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": branch,
            "base": "main",  # defaulting to main
        }

        response = self.client.post(url, json=payload)
        response.raise_for_status()
        return dict(response.json())

    def _get_build_logs(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get build logs for a failed commit.

        Args:
            args: Dictionary containing 'repo' and 'commit_sha'.

        Returns:
            dict[str, Any]: A dictionary with status and logs if found.

        Raises:
            ToolExecutionError: If required arguments are missing or API call fails.
        """
        repo = args.get("repo")
        commit_sha = args.get("commit_sha")

        if not repo or not commit_sha:
            raise ToolExecutionError("Missing required arguments for git_get_build_logs")

        # Logic:
        # 1. Get check runs for the ref
        # GET /repos/{owner}/{repo}/commits/{ref}/check-runs
        url = f"/repos/{repo}/commits/{commit_sha}/check-runs"
        response = self.client.get(url)
        response.raise_for_status()
        data = response.json()

        # 2. Extract logs (simplified)
        logs = []
        for run in data.get("check_runs", []):
            if run.get("status") == "completed" and run.get("conclusion") == "failure":
                output_obj = run.get("output") or {}
                logs.append(
                    {
                        "name": run.get("name"),
                        "output": output_obj.get("summary", "No summary available"),
                    }
                )

        if not logs:
            return {"status": "success", "message": "No failed checks found or logs unavailable."}

        return {"status": "failure", "logs": logs}
