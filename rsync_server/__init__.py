import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .server import RsyncModule, RsyncServer

_json = Path(__file__).parent / "_version.json"
_git_dir = Path(__file__).parent.parent / ".git"

if _git_dir.exists():
    # Running inside a git checkout (source or editable install) — always
    # compute live so the metadata reflects the actual current commit.
    def _git(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return "unknown"

    _base = (
        (Path(__file__).parent.parent / "VERSION").read_text(encoding="utf-8").strip()
    )
    _sha = _git("rev-parse", "--short", "HEAD")
    __version__ = f"{_base}+g{_sha}" if _sha != "unknown" else f"{_base}.dev0"
    __quality__: str = "dev"
    __commit__: str = _sha
    __build_date__: Optional[datetime] = None
else:
    # Installed artifact (wheel / sdist) — read the metadata baked in at build time.
    _meta = json.loads(_json.read_text(encoding="utf-8"))
    __version__: str = _meta["version"]
    __quality__ = _meta["quality"]
    __commit__ = _meta["commit"]
    __build_date__ = datetime.fromisoformat(_meta["build_date"])

__all__ = ["RsyncModule", "RsyncServer"]
