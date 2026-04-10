import subprocess
from pathlib import Path

from rsync_server import RsyncModule, RsyncServer


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    share_path = base_dir / "data"
    dest_path = base_dir / "data-received"
    dest_path.mkdir(parents=True, exist_ok=True)

    module = RsyncModule(name="data", path=share_path, read_only=True)

    with RsyncServer(modules=[module], host="127.0.0.1", port=0) as server:
        url = server.module_url("data")
        print("Rsync module URL:", url)
        print("Syncing from server to", dest_path)

        result = subprocess.run(
            ["rsync", "-av", f"{url}/", str(dest_path) + "/"],
            text=True,
        )

        if result.returncode == 0:
            received = (dest_path / "hello.txt").read_text()
            print("Received contents:", received.strip())
            print("Example passed!")
        else:
            print("rsync failed with exit code", result.returncode)
