from __future__ import annotations

import argparse
import time
from pathlib import Path

from rsync_server import RsyncModule, RsyncServer
from rsync_server.constants import DEFAULT_PORT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start a lightweight rsync server for local directories."
    )
    parser.add_argument(
        "root", nargs="?", default=".", help="Root directory to expose over rsync."
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address for the rsync daemon."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to use (default: {DEFAULT_PORT}; use 0 to select a free port).",
    )
    parser.add_argument(
        "--write", action="store_true", help="Allow write access to the root module."
    )
    parser.add_argument("--log", help="Optional rsync log file path.")
    parser.add_argument(
        "--max-connections",
        type=int,
        default=4,
        help="Maximum concurrent rsync connections.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()

    module = RsyncModule(
        name="data",
        path=root,
        read_only=not args.write,
        comment="Python-powered rsync server module",
    )

    server = RsyncServer(
        modules=[module],
        host=args.host,
        port=args.port,
        log_file=Path(args.log) if args.log else None,
        max_connections=args.max_connections,
    )

    with server:
        print("Rsync server is running")
        print(f"Module URL: {server.module_url(module.name).geturl()}")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("Shutting down rsync server...")


if __name__ == "__main__":
    main()
