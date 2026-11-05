from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]


def _default_data_dir() -> Path:
    support_dir = Path.home() / "Library" / "Application Support"
    data_dir = support_dir / "AutoSSH Desk"
    legacy_dir = support_dir / "WikiTunnel"
    if (data_dir / "autossh-desk.sqlite3").exists():
        return data_dir
    if (legacy_dir / "wikitunnel.sqlite3").exists():
        return legacy_dir
    return data_dir


def env_setting(name: str, default: str) -> str:
    return os.environ.get(
        f"AUTOSSH_DESK_{name}", os.environ.get(f"WIKITUNNEL_{name}", default)
    )


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    frontend_dist: Path
    host: str = "127.0.0.1"
    port: int = 8765
    instance_lock: bool = True
    strict_security: bool = True
    monitor_interval: float = 8.0
    ssh_executable: str = "/usr/bin/ssh"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(env_setting("DATA_DIR", str(_default_data_dir()))).expanduser(),
            frontend_dist=Path(
                env_setting("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
            ).expanduser(),
            host=env_setting("HOST", "127.0.0.1"),
            port=int(env_setting("PORT", "8765")),
            instance_lock=env_setting("DISABLE_INSTANCE_LOCK", "").lower()
            not in {"1", "true", "yes"},
            strict_security=env_setting("DISABLE_SECURITY", "").lower()
            not in {"1", "true", "yes"},
            monitor_interval=float(env_setting("MONITOR_INTERVAL", "8")),
            ssh_executable=env_setting("SSH", "/usr/bin/ssh"),
        )

    @property
    def database_path(self) -> Path:
        legacy_path = self.data_dir / "wikitunnel.sqlite3"
        return legacy_path if legacy_path.exists() else self.data_dir / "autossh-desk.sqlite3"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def records_dir(self) -> Path:
        return self.data_dir / "records"

    @property
    def instance_lock_path(self) -> Path:
        return self.data_dir / "instance.lock"

