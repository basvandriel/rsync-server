"""Manual release script.

Usage:
    uv run python scripts/release.py --type=rc
    uv run python scripts/release.py --type=stable
    uv run python scripts/release.py --type=stable --publish
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and optionally publish a release."
    )
    parser.add_argument(
        "--type",
        choices=["rc", "stable"],
        required=True,
        dest="release_type",
        help="Release type: 'rc' for pre-release, 'stable' for production.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Upload to PyPI after a successful build (requires twine).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = {**os.environ, "RELEASE_TYPE": args.release_type}

    print(f"Building {args.release_type} release...")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
        env=env,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)

    meta = json.loads(Path("rsync_server/_version.json").read_text(encoding="utf-8"))
    print(f"\nBuilt:  {meta['version']}  ({meta['quality']})")
    print(f"Commit: {meta['commit']}  branch: {meta['branch']}  dirty: {meta['dirty']}")

    if args.publish:
        confirm = input("\nPublish to PyPI? [y/N] ").strip().lower()
        if confirm == "y":
            subprocess.run(
                [sys.executable, "-m", "twine", "upload", "dist/*"],
                check=True,
            )
        else:
            print("Publish cancelled.")


if __name__ == "__main__":
    main()
