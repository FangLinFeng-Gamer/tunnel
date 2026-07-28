from __future__ import annotations

from typing import Any, Protocol


class CesFetcher(Protocol):
    def fetch(self, ces_query: dict[str, Any]) -> dict[str, Any]:
        ...

