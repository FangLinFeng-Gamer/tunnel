from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from metric_timeseries_analysis.cache.config import cache_config
from metric_timeseries_analysis.io.json_files import sha256_file, write_json_atomic
from metric_timeseries_analysis.io.paths import analysis_root, cache_index_dir


def cache_get(cache_key: str) -> dict[str, Any] | None:
    path = _cache_index_path(cache_key)
    if not path.exists():
        return None
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        quarantine_cache_entry(path)
        return None

    lifecycle = index.get("lifecycle") or {}
    dataset_ref = index.get("dataset_ref")
    dataset_dir = _managed_dataset_dir(dataset_ref)
    dataset_path = dataset_dir / "data.jsonl" if dataset_dir is not None else None
    expires_at = parse_epoch(lifecycle.get("expires_at"))
    invalid = (
        index.get("schema_version") != 1
        or lifecycle.get("state") != "ready"
        or dataset_path is None
        or not dataset_path.exists()
        or (expires_at is not None and expires_at <= time.time())
    )
    if not invalid:
        expected_sha = (index.get("data_summary") or {}).get("sha256")
        invalid = bool(expected_sha and sha256_file(dataset_path) != expected_sha)
    if invalid:
        delete_cache_entry(path)
        return None

    index["lifecycle"]["last_accessed_at"] = utc_now_iso()
    try:
        write_json_atomic(path, index)
    except OSError:
        pass
    return index


def cache_put(cache_key: str, spec: dict[str, Any], dataset: dict[str, Any]) -> bool:
    path = _cache_index_path(cache_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        now_epoch = time.time()
        ttl = ttl_for(spec)
        index = {
            "schema_version": 1,
            "cache_key": cache_key,
            "query_summary": {
                "region": spec["region"],
                "project_id": spec["project_id"],
                "namespace": spec["metric"]["namespace"],
                "metric_name": spec["metric"]["metric_name"],
                "dimensions": spec["metric"]["dimensions"],
                "from": spec["time_window"]["from"],
                "to": spec["time_window"]["to"],
                "period": spec["period"],
                "statistics": [spec["filter"]],
            },
            "dataset_ref": dataset["dataset_ref"],
            "data_summary": {
                "point_count": dataset["dataset_ref"]["point_count"],
                "bytes": dataset["dataset_ref"]["bytes"],
                "sha256": dataset["dataset_ref"]["sha256"],
                "time_window": spec["time_window"],
            },
            "lifecycle": {
                "state": "ready",
                "created_at": format_epoch(now_epoch),
                "last_accessed_at": format_epoch(now_epoch),
                "expires_at": format_epoch(now_epoch + ttl),
            },
        }
        write_json_atomic(path, index)
    except Exception:
        _delete_managed_dataset(dataset.get("dataset_ref"))
        return False
    try:
        evict_cache_if_needed(protected_cache_key=cache_key)
    except Exception:
        delete_cache_entry(path)
        return False
    return True


def ttl_for(spec: dict[str, Any]) -> int:
    cfg = cache_config()
    now_ms = int(time.time() * 1000)
    return cfg["recent_ttl_seconds"] if spec["time_window"]["to"] >= now_ms - 15 * 60 * 1000 else cfg["historical_ttl_seconds"]


def evict_cache_if_needed(protected_cache_key: str | None = None) -> None:
    cfg = cache_config()
    entries = []
    total = 0
    now = time.time()
    for path in cache_index_dir().glob("*.json"):
        try:
            index = json.loads(path.read_text(encoding="utf-8"))
            lifecycle = index.get("lifecycle") or {}
            size = int((index.get("data_summary") or {}).get("bytes") or 0)
            total += size
            entries.append(
                {
                    "path": path,
                    "cache_key": index.get("cache_key"),
                    "size": size,
                    "last_accessed": parse_epoch(lifecycle.get("last_accessed_at")) or 0,
                    "expires_at": parse_epoch(lifecycle.get("expires_at")) or float("inf"),
                    "ready": lifecycle.get("state") == "ready",
                }
            )
        except Exception:
            quarantine_cache_entry(path)

    for entry in list(entries):
        if entry["cache_key"] == protected_cache_key:
            continue
        if entry["expires_at"] <= now:
            delete_cache_entry(entry["path"])
            total -= entry["size"]
            entries.remove(entry)

    if total <= cfg["max_bytes"] and len(entries) <= cfg["max_entries"]:
        return

    entries.sort(key=lambda item: item["last_accessed"])
    for entry in list(entries):
        if not entry["ready"] or entry["cache_key"] == protected_cache_key:
            continue
        delete_cache_entry(entry["path"])
        total -= entry["size"]
        entries.remove(entry)
        if total <= cfg["max_bytes"] and len(entries) <= cfg["max_entries"]:
            break


def delete_cache_entry(path: Path) -> None:
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
        _delete_managed_dataset(index.get("dataset_ref"))
        path.unlink(missing_ok=True)
    except Exception:
        quarantine_cache_entry(path)


def quarantine_cache_entry(path: Path) -> None:
    try:
        if path.exists():
            path.replace(path.with_suffix(path.suffix + ".bad"))
    except Exception:
        pass


def utc_now_iso() -> str:
    return format_epoch(time.time())


def format_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_epoch(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _cache_index_path(cache_key: str) -> Path:
    return cache_index_dir() / f"{cache_key.split(':', 1)[1]}.json"


def _managed_dataset_dir(dataset_ref: Any) -> Path | None:
    if not isinstance(dataset_ref, dict):
        return None
    raw_path = dataset_ref.get("dataset_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        dataset_path = Path(raw_path).expanduser().resolve(strict=False)
        root = analysis_root().resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    dataset_dir = dataset_path.parent
    if dataset_path.name != "data.jsonl":
        return None
    if dataset_dir.parent != root or not dataset_dir.name.startswith("ces_"):
        return None
    return dataset_dir


def _delete_managed_dataset(dataset_ref: Any) -> None:
    dataset_dir = _managed_dataset_dir(dataset_ref)
    if dataset_dir is None or not dataset_dir.exists():
        return
    for child in dataset_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
    try:
        dataset_dir.rmdir()
    except OSError:
        pass
