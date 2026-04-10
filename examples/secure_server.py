from pathlib import Path

from rsync_server import RsyncModule, RsyncServer


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    share_path = base_dir / "secure-data"
    share_path.mkdir(parents=True, exist_ok=True)

    module = RsyncModule(
        name="secure",
        path=share_path,
        read_only=False,
        auth_users={"alice": "secret"},
        hosts_allow=["127.0.0.1"],
        extra_options={"comment": "Secure example module"},
    )

    with RsyncServer(
        modules=[module],
        host="127.0.0.1",
        port=0,
        log_file=Path("examples/rsyncd.log"),
    ) as server:
        print("Secure rsync module URL:", server.module_url("secure"))
        print("Credentials: alice / secret")
        print("Press Enter to stop the server")
        input()
