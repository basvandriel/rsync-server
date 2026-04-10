import json
from datetime import datetime
from pathlib import Path

from .server import RsyncModule, RsyncServer

_json = Path(__file__).parent / "_version.json"

if _json.exists():
    _meta = json.loads(_json.read_text(encoding="utf-8"))
    __version__: str = _meta["version"]
    __quality__: str = _meta["quality"]
    __commit__: str = _meta["commit"]
    __branch__: str = _meta["branch"]
    __dirty__: bool = _meta["dirty"]
    __build_date__: datetime = datetime.fromisoformat(_meta["build_date"])
else:
    # Running from source — no build has been run yet.
    __version__ = "dev"
    __quality__ = "dev"
    __commit__ = "unknown"
    __branch__ = "unknown"
    __dirty__ = False
    __build_date__ = datetime.min

__all__ = ["RsyncModule", "RsyncServer"]
