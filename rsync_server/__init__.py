import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .server import RsyncModule, RsyncServer

_json = Path(__file__).parent / "_version.json"

if _json.exists():
    _meta = json.loads(_json.read_text(encoding="utf-8"))
    __version__: str = _meta["version"]
    __quality__: str = _meta["quality"]
    __commit__: str = _meta["commit"]
    __build_date__: Optional[datetime] = datetime.fromisoformat(_meta["build_date"])
else:
    # Running from source — compute live from git.
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
    __quality__ = "dev"
    __commit__ = _sha
    __build_date__: Optional[datetime] = None

__all__ = ["RsyncModule", "RsyncServer"]
