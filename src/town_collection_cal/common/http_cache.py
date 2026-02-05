from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class CacheResult:
    path: Path
    sha256: str
    updated: bool
    status_code: int
    url: str
    etag: str | None
    last_modified: str | None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_with_cache(
    url: str,
    cache_dir: Path,
    filename: str,
    *,
    force_refresh: bool = False,
    timeout: int = 30,
) -> CacheResult:
    cache_dir.mkdir(parents=True, exist_ok=True)
    content_path = cache_dir / filename
    meta_path = cache_dir / f"{filename}.meta.json"

    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}

    headers: dict[str, str] = {}
    if not force_refresh:
        if etag := meta.get("etag"):
            headers["If-None-Match"] = etag
        if last_modified := meta.get("last_modified"):
            headers["If-Modified-Since"] = last_modified

    response = requests.get(url, headers=headers, timeout=timeout)

    if response.status_code == 304 and content_path.exists():
        sha = meta.get("sha256") or _sha256_file(content_path)
        return CacheResult(
            path=content_path,
            sha256=sha,
            updated=False,
            status_code=304,
            url=url,
            etag=meta.get("etag"),
            last_modified=meta.get("last_modified"),
        )

    response.raise_for_status()
    data = response.content
    sha = _sha256_bytes(data)

    tmp_path = content_path.with_suffix(content_path.suffix + ".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(content_path)

    new_meta = {
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "sha256": sha,
        "url": url,
    }
    meta_path.write_text(json.dumps(new_meta, indent=2, sort_keys=True), encoding="utf-8")

    return CacheResult(
        path=content_path,
        sha256=sha,
        updated=True,
        status_code=response.status_code,
        url=url,
        etag=new_meta.get("etag"),
        last_modified=new_meta.get("last_modified"),
    )
