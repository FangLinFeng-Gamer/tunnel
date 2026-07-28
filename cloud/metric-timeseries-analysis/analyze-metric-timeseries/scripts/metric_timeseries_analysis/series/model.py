from __future__ import annotations

from typing import TypedDict


class DataPoint(TypedDict):
    timestamp: int
    value: float


MetricSeriesMap = dict[str, list[DataPoint]]

