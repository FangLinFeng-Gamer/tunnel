from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """所有时序算法共享的内部执行上下文。"""

    granularity_seconds: int

    @classmethod
    def from_period(cls, period: int) -> AnalysisContext:
        if isinstance(period, bool) or not isinstance(period, int) or period <= 0:
            raise ValueError("period must be a positive integer")
        return cls(granularity_seconds=60 if period == 1 else period)
