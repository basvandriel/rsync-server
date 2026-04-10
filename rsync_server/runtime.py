from pathlib import Path
import shutil
import tempfile
from typing import Optional


class RsyncRuntime:
    def __init__(self, log_file: Optional[Path] = None) -> None:
        self.log_file = Path(log_file).resolve() if log_file else None
        self.tmpdir: Optional[Path] = None
        self.config_path: Optional[Path] = None
        self.secrets_path: Optional[Path] = None
        self.pid_path: Optional[Path] = None
        self.log_path: Optional[Path] = None

    def prepare(self) -> None:
        if self.tmpdir is not None:
            return

        self.tmpdir = Path(tempfile.mkdtemp(prefix="py_rsync_server_"))
        self.config_path = self.tmpdir / "rsyncd.conf"
        self.secrets_path = self.tmpdir / "rsyncd.secrets"
        self.pid_path = self.tmpdir / "rsyncd.pid"
        self.log_path = self.log_file or self.tmpdir / "rsyncd.log"

    def cleanup(self) -> None:
        if self.tmpdir is None:
            return

        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.tmpdir = None
        self.config_path = None
        self.secrets_path = None
        self.pid_path = None
        self.log_path = None
