import subprocess
from pathlib import Path

from rsync_server import RsyncServer


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    share_path = base_dir / "data"
    dest_path = base_dir / "data-received"
    dest_path.mkdir(parents=True, exist_ok=True)

    with RsyncServer(root=share_path, host="127.0.0.1", port=0) as server:
        url = server.module_url()
        print("Rsync module URL:", url.geturl())
        print("Syncing from server to", dest_path)

        result = subprocess.run(
            ["rsync", "-av", url.geturl() + "/", str(dest_path) + "/"],
            text=True,
        )

        if result.returncode == 0:
            received = (dest_path / "hello.txt").read_text()
            print("Received contents:", received.strip())
            print("Example passed!")
        else:
            print("rsync failed with exit code", result.returncode)
