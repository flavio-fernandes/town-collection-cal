from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated DB")
    parser.add_argument("--db", required=True, help="Path to DB JSON")
    args = parser.parse_args()

    path = Path(args.db)
    if not path.exists():
        raise SystemExit(f"DB not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    routes = data.get("routes", [])
    if not routes:
        raise SystemExit("DB has no routes")

    anchors = data.get("calendar_policy", {})
    if anchors.get("recycling_mode") == "alternating_week":
        if not anchors.get("anchor_week_sunday") or not anchors.get("anchor_color"):
            raise SystemExit("DB missing anchor_week_sunday or anchor_color")

    street_names = [r.get("street", "") for r in routes]
    if not any("boston" in s.lower() for s in street_names):
        raise SystemExit("Expected to find a Boston street in routes")

    print("DB sanity check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
