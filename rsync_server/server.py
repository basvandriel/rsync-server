from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Optional
from urllib.parse import ParseResult

from .config import RsyncConfigBuilder
from .constants import DEFAULT_MODULE_NAME, SUPPORTED_RSYNC_VERSION
from .runtime import RsyncRuntime


@dataclass(slots=True)
class RsyncModule:
    name: str
    path: Path
    read_only: bool = True
    comment: str = ""
    hosts_allow: list[str] = field(default_factory=list)
    hosts_deny: list[str] = field(default_factory=list)
    auth_users: dict[str, str] = field(default_factory=dict)
    extra_options: dict[str, str] = field(default_factory=dict)
    uid: Optional[int] = None
    gid: Optional[int] = None

    def __post_init__(self) -> None:
        self.path = Path(self.path).resolve()
        if not self.name or any(c.isspace() for c in self.name):
            raise ValueError(
                "Module name must be a non-empty string without whitespace"
            )
        if self.uid is not None and self.uid < 0:
            raise ValueError("uid must be a non-negative integer")
        if self.gid is not None and self.gid < 0:
            raise ValueError("gid must be a non-negative integer")


class RsyncServer:
    def __init__(
        self,
        root: Path = Path("."),
        *,
        modules: Optional[list[RsyncModule]] = None,
        host: str = "127.0.0.1",
        port: int = 0,
        rsync_executable: Path = Path("rsync"),
        log_file: Optional[Path] = None,
        max_connections: int = 4,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        extra_config: Optional[dict[str, str]] = None,
    ):
        self.root = Path(root).resolve()
        self.modules = modules or [
            RsyncModule(DEFAULT_MODULE_NAME, self.root, read_only=False)
        ]
        self.host = host or "127.0.0.1"
        self.port = port
        self.rsync_executable = Path(rsync_executable)
        self.log_file = Path(log_file).resolve() if log_file else None
        self.max_connections = max_connections
        self.uid = uid
        self.gid = gid
        self.extra_config = extra_config or {}

        self._runtime = RsyncRuntime(self.log_file)
        self._config_builder = RsyncConfigBuilder(
            modules=self.modules,
            host=self.host,
            max_connections=self.max_connections,
            extra_config=self.extra_config,
        )
        self._log_handle: Optional[IO[str]] = None
        self._process: Optional[subprocess.Popen[bytes]] = None

        self._ensure_module_paths()

    def _ensure_module_paths(self) -> None:
        for module in self.modules:
            if not module.path.exists():
                raise FileNotFoundError(
                    f"Rsync module path does not exist: {module.path}"
                )

    def _ensure_rsync_installed(self) -> None:
        executable_path = self.rsync_executable

        if not self.rsync_executable.is_absolute():
            resolved = shutil.which(str(self.rsync_executable))
            if resolved is None:
                raise RuntimeError(
                    f"Unable to find rsync executable: {self.rsync_executable}. "
                    "Install rsync or provide a valid path."
                )
            executable_path = Path(resolved)

        if not executable_path.exists() or not os.access(executable_path, os.X_OK):
            raise RuntimeError(
                f"Unable to execute rsync at path: {executable_path}. "
                "Install rsync or provide a valid executable."
            )

        self._check_rsync_version(executable_path)

    def _check_rsync_version(self, executable_path: Path) -> None:
        major, minor, patch = self._get_rsync_version(executable_path)
        if major < 3 or (major == 3 and minor < 4):
            raise RuntimeError(
                f"Unsupported rsync version {major}.{minor}.{patch}. "
                f"This wrapper requires rsync {SUPPORTED_RSYNC_VERSION} or later."
            )

    def _get_rsync_version(self, executable_path: Path) -> tuple[int, int, int]:
        result = subprocess.run(
            [str(executable_path), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to execute rsync for version check: {executable_path}"
            )

        match = re.search(r"rsync\s+version\s+(\d+)\.(\d+)\.(\d+)", result.stdout)
        if not match:
            raise RuntimeError(
                f"Unable to parse rsync version from output: {result.stdout.splitlines()[0]}"
            )

        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    def _prepare_runtime(self) -> None:
        if self._runtime.tmpdir is not None:
            return

        self._runtime.prepare()
        self._write_secrets()
        self._write_config()

    def _write_secrets(self) -> None:
        if self._runtime.secrets_path is None:
            raise RuntimeError("Secrets path is not initialized")
        self._config_builder.write_secrets(self._runtime.secrets_path)

    def _write_config(self) -> None:
        if (
            self._runtime.config_path is None
            or self._runtime.pid_path is None
            or self._runtime.log_path is None
            or self._runtime.secrets_path is None
        ):
            raise RuntimeError("Runtime paths are not initialized")

        self._config_builder.write_config(
            config_path=self._runtime.config_path,
            pid_path=self._runtime.pid_path,
            log_path=self._runtime.log_path,
            secrets_path=self._runtime.secrets_path,
        )

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _ensure_log_file(self) -> None:
        if self._runtime.log_path is None:
            raise RuntimeError("Log path is not initialized")
        self._runtime.log_path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, timeout: float = 5.0) -> None:
        if self._process is not None:
            return

        self._ensure_rsync_installed()
        self._prepare_runtime()

        if self.port == 0:
            self.port = self._find_free_port()

        if self._runtime.log_path is None or self._runtime.config_path is None:
            raise RuntimeError("Runtime paths are not initialized")

        self._ensure_log_file()
        self._log_handle = open(self._runtime.log_path, "a", encoding="utf-8")

        command = [
            str(self.rsync_executable),
            "--daemon",
            "--no-detach",
            "--config",
            str(self._runtime.config_path),
            "--port",
            str(self.port),
        ]
        if self.host:
            command.extend(["--address", self.host])

        self._process = subprocess.Popen(
            command, stdout=self._log_handle, stderr=subprocess.STDOUT
        )

        try:
            self.wait_for_ready(timeout=timeout)
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        if self._process is None:
            return

        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)

        self._process = None
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def cleanup(self) -> None:
        self.stop()
        self._runtime.cleanup()

    def wait_for_ready(self, timeout: float = 5.0) -> None:
        if self._process is None:
            raise RuntimeError("Rsync server is not running")

        deadline = time.time() + timeout
        connect_host = "127.0.0.1" if self.host in {"0.0.0.0", ""} else self.host

        while time.time() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError("Rsync daemon terminated unexpectedly")

            try:
                with socket.create_connection((connect_host, self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)

        raise TimeoutError(
            f"Failed to start rsync daemon on {self.host}:{self.port} within {timeout} seconds"
        )

    def module_url(self, module_name: Optional[str] = None) -> ParseResult:
        name = module_name or self.modules[0].name
        host = "localhost" if self.host in {"0.0.0.0", ""} else self.host
        return ParseResult(
            scheme="rsync",
            netloc=f"{host}:{self.port}",
            path=f"/{name}",
            params="",
            query="",
            fragment="",
        )

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def close(self) -> None:
        self.cleanup()

    def __enter__(self) -> "RsyncServer":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: object,
    ) -> None:
        self.cleanup()
