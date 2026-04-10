# Shim used by setuptools to resolve __version__ via
# {attr = "rsync_server._version.__version__"} in pyproject.toml.
# Running from source -> "dev". Built artifact -> reads _version.json baked in.
import json
from pathlib import Path

_json = Path(__file__).parent / "_version.json"
__version__: str = (
    json.loads(_json.read_text(encoding="utf-8"))["version"]
    if _json.exists()
    else "0.0.0.dev0"
)
