from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_ces_query(ces_query: dict[str, Any]) -> str:
    return json.dumps(ces_query, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cache_key_for(ces_query: dict[str, Any]) -> str:
    canonical = canonical_ces_query(ces_query)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

