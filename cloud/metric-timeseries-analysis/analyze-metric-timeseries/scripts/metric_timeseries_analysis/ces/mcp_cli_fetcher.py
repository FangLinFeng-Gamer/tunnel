from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence

from metric_timeseries_analysis.ces.response_parser import unwrap_mcp_cli_envelope
from metric_timeseries_analysis.constants import (
    CES_FETCH_TIMEOUT_SECONDS,
    CES_MCP_TOOL_NAME,
    MCP_CLI_COMMAND_PREFIX,
)
from metric_timeseries_analysis.errors import MetricAnalysisError


class McpCliCesFetcher:
    def __init__(
        self,
        tool_name: str = CES_MCP_TOOL_NAME,
        command_prefix: Sequence[str] = MCP_CLI_COMMAND_PREFIX,
        timeout_seconds: int = CES_FETCH_TIMEOUT_SECONDS,
    ) -> None:
        self.tool_name = tool_name.strip()
        self.command_prefix = tuple(command_prefix)
        self.timeout_seconds = timeout_seconds

    def fetch(self, ces_query: dict[str, Any]) -> dict[str, Any]:
        argv = self.render_command(ces_query)
        try:
            completed = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise MetricAnalysisError("data_fetch_failed", f"CES MCP CLI timed out after {self.timeout_seconds}s") from exc
        except OSError as exc:
            raise MetricAnalysisError("data_fetch_failed", f"failed to start CES MCP CLI: {exc}") from exc

        if completed.returncode != 0:
            detail = _failed_cli_detail(completed)
            raise MetricAnalysisError(
                "data_fetch_failed",
                f"CES MCP CLI exited with {completed.returncode}: {detail}",
            )

        payload_text = (completed.stdout or "").strip()
        if not payload_text:
            raise MetricAnalysisError("data_fetch_failed", "CES MCP CLI returned empty output")
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise MetricAnalysisError("data_fetch_failed", f"CES MCP CLI returned non-JSON output: {exc}") from exc
        return unwrap_mcp_cli_envelope(payload, self.tool_name)

    def render_command(self, ces_query: dict[str, Any]) -> list[str]:
        if not self.tool_name:
            raise MetricAnalysisError("data_fetch_failed", "CES MCP tool name is not configured")
        arguments = _mcp_tool_arguments(ces_query)
        arguments_json = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
        return [*self.command_prefix, self.tool_name, "--args", arguments_json]


def _mcp_tool_arguments(ces_query: dict[str, Any]) -> dict[str, Any]:
    body = ces_query["request_body"]
    return {
        "region": ces_query["region"],
        "project_id": ces_query["project_id"],
        "metrics": body["metrics"],
        "from": body["from"],
        "to": body["to"],
        "period": str(body["period"]),
        "filter": body["filter"],
    }


def _failed_cli_detail(completed: subprocess.CompletedProcess[str]) -> str:
    stdout = (completed.stdout or "").strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            return payload["error"][:1000]

    stderr = (completed.stderr or "").strip()
    if stderr:
        return stderr[:1000]
    return "no error detail returned"
