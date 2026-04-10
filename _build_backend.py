"""Custom build backend that injects VCS metadata at build time.

Wraps setuptools.build_meta to write rsync_server/_version.json.
Modelled after VS Code's product.json approach:
  - Running from source (.git present) → __init__.py computes live from git
  - Built artifact (.git absent)       → _version.json is baked in

The wheel version comes from the VERSION file directly (via pyproject.toml).
_version.json carries runtime metadata only: quality, commit, build_date,
and the full version string (which may include a quality suffix for display).

Fields written to _version.json:
  version     VERSION + quality suffix (0.1 / 0.1rc1 / 0.1.dev0)
  quality     dev | rc | stable  (from RELEASE_TYPE env var, default: dev)
  commit      short SHA from git rev-parse
  build_date  UTC datetime at the moment the wheel/sdist was built
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from setuptools.build_meta import (
    build_sdist as _build_sdist,
    build_wheel as _build_wheel,
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_wheel as _prepare_wheel,
)

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
]

_VERSION_FILE = Path("rsync_server/_version.json")


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _write_version_file() -> None:
    commit = _git("rev-parse", "--short", "HEAD")

    # When building a wheel from an extracted sdist there is no .git dir.
    # Reuse the _version.json baked in during the sdist step.
    if commit == "unknown" and _VERSION_FILE.exists():
        return

    base = Path("VERSION").read_text(encoding="utf-8").strip()
    raw = os.environ.get("RELEASE_TYPE", "dev").strip().lower()
    if raw not in ("dev", "rc", "stable"):
        raise ValueError(
            f"RELEASE_TYPE must be 'dev', 'rc', or 'stable' — got: {raw!r}"
        )
    if raw == "stable":
        version = base
    elif raw == "rc":
        version = f"{base}rc1"
    else:
        version = f"{base}.dev0"

    _VERSION_FILE.write_text(
        json.dumps(
            {
                "version": version,
                "quality": raw,
                "commit": commit,
                "build_date": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# --- PEP 517 hooks -----------------------------------------------------------


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    _write_version_file()
    return _prepare_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _write_version_file()
    return _build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    _write_version_file()
    return _build_sdist(sdist_directory, config_settings)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    from setuptools.build_meta import (
        prepare_metadata_for_build_editable as _prepare_editable,
    )

    _write_version_file()
    return _prepare_editable(metadata_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    from setuptools.build_meta import build_editable as _build_editable

    _write_version_file()
    return _build_editable(wheel_directory, config_settings, metadata_directory)
