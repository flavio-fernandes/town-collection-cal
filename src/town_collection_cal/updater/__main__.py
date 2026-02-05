from __future__ import annotations

import argparse

from town_collection_cal.updater.build_db import main as build_db_main


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Town Collection updater")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_db = subparsers.add_parser("build-db", help="Build town DB from sources")
    build_db.add_argument("--town", required=True, help="Path to town.yaml")
    build_db.add_argument("--out", required=True, help="Output DB JSON path")
    build_db.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    build_db.add_argument("--force-refresh", action="store_true", help="Force re-download sources")
    build_db.add_argument("--validate-only", action="store_true", help="Validate only, no output")
    build_db.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "build-db":
        return build_db_main(
            [
                "--town",
                args.town,
                "--out",
                args.out,
                "--cache-dir",
                args.cache_dir,
            ]
            + (["--force-refresh"] if args.force_refresh else [])
            + (["--validate-only"] if args.validate_only else [])
            + (["--log-level", args.log_level] if args.log_level else [])
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
