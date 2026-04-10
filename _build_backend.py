"""Custom build backend that injects VCS metadata at build time.

Wraps setuptools.build_meta to write rsync_server/_version.json.
Modelled after VS Code's product.json approach:
  - Running from source → __version__ is 'dev', no git calls at import time
  - Built artifact     → _version.json is baked in with real metadata

Fields written to _version.json:
  version     from VERSION file; quality suffix applied (rc / stable / dev)
  quality     dev | rc | stable  (from RELEASE_TYPE env var, default: dev)
  commit      short SHA from git rev-parse
  branch      current git branch name
  dirty       whether the working tree has uncommitted changes
  build_date  UTC date at the moment the wheel/sdist was built

Version string format:
  stable  →  0.1          (PyPI-publishable)
  rc      →  0.1rc1       (PyPI pre-release)
  dev     →  0.1.dev0     (unofficial build)
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


def _read_base_version() -> str:
    try:
        return Path("VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0"


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _compute_quality() -> str:
    raw = os.environ.get("RELEASE_TYPE", "dev").strip().lower()
    if raw not in ("dev", "rc", "stable"):
        raise ValueError(
            f"RELEASE_TYPE must be 'dev', 'rc', or 'stable' — got: {raw!r}"
        )
    return raw


def _build_version_string(quality: str, base: str) -> str:
    if quality == "stable":
        return base
    if quality == "rc":
        return f"{base}rc1"
    return f"{base}.dev0"


def _write_version_file() -> None:
    commit = _git("rev-parse", "--short", "HEAD")

    # When building a wheel from an extracted sdist there is no .git dir.
    # Reuse the _version.json baked in during the sdist step.
    if commit == "unknown" and _VERSION_FILE.exists():
        return

    quality = _compute_quality()
    base = _read_base_version()
    version = _build_version_string(quality, base)

    dirty_output = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    _VERSION_FILE.write_text(
        json.dumps(
            {
                "version": version,
                "quality": quality,
                "commit": commit,
                "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": bool(dirty_output),
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


from setuptools.build_meta import (
    build_sdist as _build_sdist,
    build_wheel as _build_wheel,
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_wheel as _prepare_wheel,
)
