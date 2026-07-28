from __future__ import annotations

CES_PERIODS_SECONDS = {1, 60, 300, 1200, 3600, 14400, 86400}
CES_MAX_METRICS = 500
CES_MAX_DATAPOINTS = 3000
CES_MAX_REQUEST_BYTES = 512 * 1024
DEFAULT_FILTER = "average"
NORMALIZATION_VERSION = "metric-analysis-normalized-v1"
BACKEND_VERSION = "huaweicloud-ces-batch-list-metric-data-v1"
CES_FETCH_TIMEOUT_SECONDS = 60

DEFAULT_RECENT_TTL_SECONDS = 300
DEFAULT_HISTORICAL_TTL_SECONDS = 86_400
DEFAULT_CACHE_MAX_BYTES = 512 * 1024 * 1024
DEFAULT_CACHE_MAX_ENTRIES = 1024

# The CES tool is registered by the deployment. Keep the CLI shape fixed here
# and set the concrete tool name when registration is complete.
CES_MCP_TOOL_NAME = ""
MCP_CLI_COMMAND_PREFIX = (
    "cli-anything-huaweicloud-mcp",
    "--json",
    "call",
)
