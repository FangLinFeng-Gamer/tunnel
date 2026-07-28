from __future__ import annotations

import importlib
import io
import logging
import warnings
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, Protocol, cast

import pandas as pd

from metric_timeseries_analysis.errors import MetricAnalysisError


class TrendForecaster(Protocol):
    def forecast(
        self,
        history: pd.DataFrame,
        *,
        periods: int,
    ) -> pd.DataFrame:
        ...


class ProphetModel(Protocol):
    def fit(self, history: pd.DataFrame) -> Any:
        ...

    def make_future_dataframe(
        self,
        *,
        periods: int,
        freq: str,
        include_history: bool,
    ) -> pd.DataFrame:
        ...

    def predict(self, future: pd.DataFrame) -> pd.DataFrame:
        ...


ModelFactory = Callable[..., ProphetModel]


class ProphetForecaster:
    """使用固定的原服务配置执行 Prophet 小时级预测。"""

    def __init__(self, model_factory: ModelFactory | None = None) -> None:
        self._model_factory = model_factory

    def forecast(
        self,
        history: pd.DataFrame,
        *,
        periods: int,
    ) -> pd.DataFrame:
        output = io.StringIO()
        previous_logging_disable = logging.root.manager.disable
        try:
            with (
                redirect_stdout(output),
                redirect_stderr(output),
                warnings.catch_warnings(),
            ):
                warnings.simplefilter("ignore")
                logging.disable(logging.CRITICAL)
                model_factory = self._model_factory or _load_prophet_factory()
                model = model_factory(
                    growth="linear",
                    changepoint_range=0.9,
                )
                model.fit(history)
                future = model.make_future_dataframe(
                    periods=periods,
                    freq="H",
                    include_history=False,
                )
                forecast = model.predict(future)
        finally:
            logging.disable(previous_logging_disable)

        required_columns = {"ds", "yhat"}
        if not required_columns.issubset(forecast.columns):
            raise MetricAnalysisError(
                "internal_error",
                "Prophet forecast is missing required columns",
            )
        return forecast[["ds", "yhat"]].copy()


def _load_prophet_factory() -> ModelFactory:
    try:
        module = importlib.import_module("prophet")
    except ImportError as exc:
        raise MetricAnalysisError(
            "internal_error",
            "Prophet dependency is not installed",
        ) from exc

    factory = getattr(module, "Prophet", None)
    if factory is None:
        raise MetricAnalysisError(
            "internal_error",
            "Prophet dependency does not expose Prophet",
        )
    return cast(ModelFactory, factory)
