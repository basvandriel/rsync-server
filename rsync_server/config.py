from __future__ import annotations

from pathlib import Path


class RsyncConfigBuilder:
    def __init__(
        self,
        modules: list["RsyncModule"],
        host: str,
        max_connections: int,
        extra_config: dict[str, str],
    ) -> None:
        self.modules = modules
        self.host = host
        self.max_connections = max_connections
        self.extra_config = extra_config

    def write_secrets(self, secrets_path: Path) -> None:
        auth_pairs = {
            user: password
            for module in self.modules
            for user, password in module.auth_users.items()
        }
        if not auth_pairs:
            return

        secrets_path.parent.mkdir(parents=True, exist_ok=True)
        secrets_path.write_text(
            "\n".join(
                f"{user}:{password}" for user, password in sorted(auth_pairs.items())
            )
            + "\n",
            encoding="utf-8",
        )
        secrets_path.chmod(0o600)

    def write_config(
        self,
        config_path: Path,
        pid_path: Path,
        log_path: Path,
        secrets_path: Path,
    ) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            self._build(pid_path, log_path, secrets_path), encoding="utf-8"
        )

    def _build(
        self,
        pid_path: Path,
        log_path: Path,
        secrets_path: Path,
    ) -> str:
        lines: list[str] = [
            "[rsyncd]",
            f"    pid file = {pid_path}",
            f"    log file = {log_path}",
            "    use chroot = false",
            "    strict modes = false",
            f"    max connections = {self.max_connections}",
        ]

        if self.host:
            lines.append(f"    address = {self.host}")

        for key, value in sorted(self.extra_config.items()):
            lines.append(f"    {key} = {value}")

        for module in self.modules:
            lines.append("")
            lines.append(f"[{module.name}]")
            lines.append(f"    path = {module.path}")

            if module.comment:
                lines.append(f"    comment = {module.comment}")

            lines.extend(
                [
                    f"    read only = {'yes' if module.read_only else 'no'}",
                    "    list = yes",
                ]
            )

            if module.hosts_allow:
                lines.append(f"    hosts allow = {', '.join(module.hosts_allow)}")
            if module.hosts_deny:
                lines.append(f"    hosts deny = {', '.join(module.hosts_deny)}")
            if module.uid is not None:
                lines.append(f"    uid = {module.uid}")
            if module.gid is not None:
                lines.append(f"    gid = {module.gid}")

            if module.auth_users:
                lines.append(f"    auth users = {', '.join(sorted(module.auth_users))}")
                lines.append(f"    secrets file = {secrets_path}")

            for key, value in sorted(module.extra_options.items()):
                lines.append(f"    {key} = {value}")

        return "\n".join(lines) + "\n"
