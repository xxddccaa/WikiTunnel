from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]


def _default_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "WikiTunnel"


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
            data_dir=Path(os.environ.get("WIKITUNNEL_DATA_DIR", _default_data_dir())).expanduser(),
            frontend_dist=Path(
                os.environ.get("WIKITUNNEL_FRONTEND_DIST", PROJECT_ROOT / "frontend" / "dist")
            ).expanduser(),
            host=os.environ.get("WIKITUNNEL_HOST", "127.0.0.1"),
            port=int(os.environ.get("WIKITUNNEL_PORT", "8765")),
            instance_lock=os.environ.get("WIKITUNNEL_DISABLE_INSTANCE_LOCK", "").lower()
            not in {"1", "true", "yes"},
            strict_security=os.environ.get("WIKITUNNEL_DISABLE_SECURITY", "").lower()
            not in {"1", "true", "yes"},
            monitor_interval=float(os.environ.get("WIKITUNNEL_MONITOR_INTERVAL", "8")),
            ssh_executable=os.environ.get("WIKITUNNEL_SSH", "/usr/bin/ssh"),
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "wikitunnel.sqlite3"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def records_dir(self) -> Path:
        return self.data_dir / "records"

    @property
    def instance_lock_path(self) -> Path:
        return self.data_dir / "instance.lock"

