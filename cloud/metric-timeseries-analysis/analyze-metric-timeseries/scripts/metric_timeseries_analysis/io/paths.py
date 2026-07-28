from __future__ import annotations

import os
from pathlib import Path


def hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home()
    except Exception:
        configured = os.getenv("HERMES_HOME", "").strip()
        return Path(configured).expanduser() if configured else Path.home() / ".hermes"


def analysis_root() -> Path:
    return hermes_home() / "datasets" / "metric-analysis"


def cache_index_dir() -> Path:
    return analysis_root() / "cache" / "ces-timeseries"
