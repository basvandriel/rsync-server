import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rsync_server import RsyncModule, RsyncServer


def _rsync_version_ok() -> bool:
    path = shutil.which("rsync")
    if path is None:
        return False

    result = subprocess.run([path, "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        return False

    match = re.search(r"rsync\s+version\s+(\d+)\.(\d+)", result.stdout)
    if not match:
        return False

    major = int(match.group(1))
    minor = int(match.group(2))
    return major > 3 or (major == 3 and minor >= 4)


class TestRsyncServer(unittest.TestCase):
    def test_default_server_config_includes_module(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            server = RsyncServer(root)
            server._prepare_runtime()
            config = server._runtime.config_path.read_text(encoding="utf-8")
            self.assertIn("[data]", config)
            self.assertIn(f"path = {root.resolve()}", config)
            server.cleanup()

    def test_writes_auth_users_and_extra_options(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            module = RsyncModule(
                name="secure",
                path=root,
                auth_users={"alice": "secret"},
                extra_options={"uid": "1000"},
            )
            server = RsyncServer(
                root, modules=[module], extra_config={"motd file": "/dev/null"}
            )
            server._prepare_runtime()

            config = server._runtime.config_path.read_text(encoding="utf-8")
            self.assertIn("[secure]", config)
            self.assertIn("auth users = alice", config)
            self.assertIn("motd file = /dev/null", config)

            secrets = server._runtime.secrets_path.read_text(encoding="utf-8")
            self.assertEqual(secrets, "alice:secret\n")
            server.cleanup()

    def test_cleanup_removes_temporary_runtime(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            server = RsyncServer(root)
            server._prepare_runtime()
            tmpdir = server._runtime.tmpdir
            self.assertIsNotNone(tmpdir)
            self.assertTrue(tmpdir.exists())
            server.cleanup()
            self.assertFalse(tmpdir.exists())

    def test_start_creates_log_directory(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            log_dir = Path(root) / "logs"
            log_file = log_dir / "rsyncd.log"
            server = RsyncServer(root, log_file=log_file, port=0)

            with (
                patch(
                    "rsync_server.server.shutil.which", return_value="/usr/bin/rsync"
                ),
                patch("rsync_server.server.subprocess.run") as mock_run,
                patch("rsync_server.server.subprocess.Popen") as mock_popen,
                patch.object(RsyncServer, "wait_for_ready", return_value=None),
            ):
                process_mock = Mock()
                process_mock.poll.return_value = None
                mock_popen.return_value = process_mock
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "rsync  version 3.4.4  protocol version 31\n"
                mock_run.return_value = mock_result
                server.start()

            self.assertTrue(log_dir.exists())
            self.assertTrue(log_file.exists())
            server.cleanup()

    def test_rsync_version_check_accepts_3_4_plus(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            server = RsyncServer(root)

            result = Mock()
            result.returncode = 0
            result.stdout = "rsync  version 3.4.4  protocol version 31\n"

            with (
                patch(
                    "rsync_server.server.shutil.which", return_value="/usr/bin/rsync"
                ),
                patch("rsync_server.server.subprocess.run", return_value=result),
            ):
                server._ensure_rsync_installed()

    def test_rsync_version_check_rejects_old_version(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            server = RsyncServer(root)

            result = Mock()
            result.returncode = 0
            result.stdout = "rsync  version 3.3.2  protocol version 31\n"

            with (
                patch(
                    "rsync_server.server.shutil.which", return_value="/usr/bin/rsync"
                ),
                patch("rsync_server.server.subprocess.run", return_value=result),
            ):
                with self.assertRaises(RuntimeError):
                    server._ensure_rsync_installed()

    def test_server_start_stop_cycle(self):
        if not _rsync_version_ok():
            self.skipTest("Installed rsync is not version 3.4.x or later")

        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            server = RsyncServer(root, port=0)
            server.start()
            self.assertTrue(server.is_running)
            url = server.module_url()
            self.assertTrue(url.startswith("rsync://"))
            self.assertIn("data", url)
            parsed = server.module_url_parsed()
            self.assertEqual(parsed.scheme, "rsync")
            self.assertIn("data", parsed.path)
            server.cleanup()


if __name__ == "__main__":
    unittest.main()
