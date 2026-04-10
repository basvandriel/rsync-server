# Examples for rsync-server

This folder contains simple example scripts that show how to use the `rsync_server` library.

## Setup

Install the package in editable mode from the repository root:

```bash
pip install -e .
```

Make sure a compatible `rsync` binary is available on `PATH`. This wrapper requires `rsync 3.4.x` or later.

## Examples

### Basic server

Run a basic server exposing a writable module:

```bash
python examples/basic_server.py
```

This script creates `examples/data/` and starts an rsync daemon exposing that folder as `data`.

### Secure server

Run a server with auth and allowed hosts:

```bash
python examples/secure_server.py
```

This script creates `examples/secure-data/`, starts the daemon, and prints the URL plus credentials.
