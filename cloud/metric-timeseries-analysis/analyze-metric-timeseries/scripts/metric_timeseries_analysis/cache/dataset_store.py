from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from metric_timeseries_analysis.ces.response_parser import extract_series
from metric_timeseries_analysis.constants import NORMALIZATION_VERSION
from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.io.json_files import sha256_file
from metric_timeseries_analysis.io.paths import analysis_root
from metric_timeseries_analysis.series.model import MetricSeriesMap


def persist_dataset(spec: dict[str, Any], raw: dict[str, Any], cache_key: str) -> dict[str, Any]:
    series_by_metric = extract_series(raw, spec["filter"])
    if not series_by_metric:
        raise MetricAnalysisError("invalid_request", "CES response contains no usable datapoints")

    created = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    dataset_id = f"ces_{created}_{cache_key[-8:]}_{uuid4().hex[:8]}"
    dataset_dir = analysis_root() / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    raw_path = dataset_dir / "raw_response.json"
    data_path = dataset_dir / "data.jsonl"
    metadata_path = dataset_dir / "metadata.json"

    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_series_jsonl(data_path, series_by_metric)
    data_sha = sha256_file(data_path)
    point_count = sum(len(series) for series in series_by_metric.values())
    metadata = {
        "dataset_id": dataset_id,
        "source": "huaweicloud_ces",
        "cache_key": cache_key,
        "created_at": _utc_now_iso(),
        "point_count": point_count,
        "metric_count": len(series_by_metric),
        "sha256": data_sha,
        "normalization_version": NORMALIZATION_VERSION,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dataset_bytes = sum(path.stat().st_size for path in (raw_path, data_path, metadata_path))
    dataset_ref = {
        "dataset_id": dataset_id,
        "dataset_path": str(data_path),
        "raw_path": str(raw_path),
        "metadata_path": str(metadata_path),
        "point_count": point_count,
        "metric_count": len(series_by_metric),
        "bytes": dataset_bytes,
        "sha256": data_sha,
        "time_window": spec["time_window"],
    }
    return {"dataset_ref": dataset_ref, "series_by_metric": series_by_metric, "dataset_dir": str(dataset_dir)}


def load_dataset(dataset_ref: dict[str, Any]) -> dict[str, Any]:
    data_path = Path(dataset_ref["dataset_path"])
    series_by_metric: MetricSeriesMap = {}
    with data_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            series_by_metric.setdefault(str(row["metric_name"]), []).append({"timestamp": int(row["timestamp"]), "value": float(row["value"])})
    for series in series_by_metric.values():
        series.sort(key=lambda item: item["timestamp"])
    return {"dataset_ref": dataset_ref, "series_by_metric": series_by_metric, "dataset_dir": str(data_path.parent)}


def _write_series_jsonl(data_path: Path, series_by_metric: MetricSeriesMap) -> None:
    lines = []
    for metric_name, series in sorted(series_by_metric.items()):
        for point in series:
            lines.append(json.dumps({"metric_name": metric_name, "timestamp": point["timestamp"], "value": point["value"]}, ensure_ascii=False, separators=(",", ":")))
    data_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
