from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.io.paths import cache_index_dir


CACHE_LOCK_TIMEOUT_SECONDS = 75
CACHE_LOCK_STALE_SECONDS = 300
CACHE_LOCK_POLL_SECONDS = 0.05


@contextmanager
def cache_key_lock(cache_key: str) -> Iterator[None]:
    lock_dir = _lock_dir(cache_key)
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + CACHE_LOCK_TIMEOUT_SECONDS

    while True:
        try:
            lock_dir.mkdir()
            (lock_dir / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            _remove_stale_lock(lock_dir)
            if time.monotonic() >= deadline:
                raise MetricAnalysisError("internal_error", f"timed out waiting for cache lock: {cache_key}")
            time.sleep(CACHE_LOCK_POLL_SECONDS)

    try:
        yield
    finally:
        _remove_lock(lock_dir)


def _lock_dir(cache_key: str) -> Path:
    digest = cache_key.split(":", 1)[-1]
    return cache_index_dir() / "locks" / f"{digest}.lock"


def _remove_stale_lock(lock_dir: Path) -> None:
    try:
        age = time.time() - lock_dir.stat().st_mtime
        if age >= CACHE_LOCK_STALE_SECONDS:
            _remove_lock(lock_dir)
    except FileNotFoundError:
        return


def _remove_lock(lock_dir: Path) -> None:
    try:
        for child in lock_dir.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        lock_dir.rmdir()
    except FileNotFoundError:
        return
    except OSError:
        return
