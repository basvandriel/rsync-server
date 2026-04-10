# rsync-server

A modern lightweight Python wrapper for running an `rsync` daemon from code.

## Features

- Start and stop a local rsync server from Python
- Expose one or more module directories
- Support read-only or writable modules
- Optional rsync log file and custom module options
- Clean context-manager API for fast server lifecycles

## Quick start

```python
from pathlib import Path
from rsync_server import RsyncModule, RsyncServer

root = Path("/tmp/share")
root.mkdir(parents=True, exist_ok=True)

module = RsyncModule(name="data", path=root, read_only=False)
with RsyncServer(modules=[module], host="127.0.0.1", port=0) as server:
    print(server.module_url("data"))
```

## CLI

Run the server from the command line:

```bash
python main.py /tmp/share --host 127.0.0.1 --port 0
```

## Requirements

- Python 3.10+
- `rsync` installed and available on `PATH`

## Installation

```bash
pip install -e .
```

## API

- `RsyncServer`: start, stop, and manage the daemon lifecycle
- `RsyncModule`: describe an rsync module and access controls

## Testing

```bash
python -m unittest tests.test_server
```
