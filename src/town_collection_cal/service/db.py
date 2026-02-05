from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from town_collection_cal.common.db_model import Database


def load_db(path: Path) -> Database:
    if not path.exists():
        raise FileNotFoundError(f"DB file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return Database.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid DB format: {exc}") from exc


@dataclass
class DbLoader:
    path: Path
    reload_interval_seconds: int
    _cached: Database | None = None
    _cached_mtime: float | None = None
    _last_check: float = 0.0

    def get_db(self) -> Database:
        now = time.monotonic()
        if self._cached is None:
            self._reload()
            return self._cached  # type: ignore[return-value]

        if now - self._last_check >= self.reload_interval_seconds:
            self._last_check = now
            mtime = self.path.stat().st_mtime
            if self._cached_mtime is None or mtime > self._cached_mtime:
                self._reload()

        return self._cached  # type: ignore[return-value]

    def _reload(self) -> None:
        db = load_db(self.path)
        self._cached = db
        self._cached_mtime = self.path.stat().st_mtime
        self._last_check = time.monotonic()
