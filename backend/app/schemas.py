from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


HOST_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SSH_TARGET_RE = re.compile(r"^[^\s]+$")


def validate_host(value: str, field_name: str) -> str:
    value = value.strip()
    if not value or not HOST_RE.fullmatch(value):
        raise ValueError(f"{field_name} 包含不支持的字符")
    return value


class TunnelFields(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    ssh_target: str = Field(min_length=1, max_length=255)
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    remote_bind_host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    remote_port: int = Field(default=15432, ge=1, le=65535)
    target_host: str = Field(min_length=1, max_length=255)
    target_port: int = Field(default=5432, ge=1, le=65535)
    identity_file: str | None = Field(default=None, max_length=1024)
    server_alive_interval: int = Field(default=30, ge=1, le=3600)
    server_alive_count_max: int = Field(default=3, ge=1, le=10)
    connect_timeout: int = Field(default=10, ge=1, le=120)
    auto_reconnect: bool = True
    auto_start: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("名称不能为空")
        return value

    @field_validator("ssh_target")
    @classmethod
    def clean_ssh_target(cls, value: str) -> str:
        value = value.strip()
        if not SSH_TARGET_RE.fullmatch(value) or value.startswith("-"):
            raise ValueError("SSH 目标不能包含空白或以 - 开头")
        return value

    @field_validator("remote_bind_host")
    @classmethod
    def clean_bind_host(cls, value: str) -> str:
        return validate_host(value, "远端监听地址")

    @field_validator("target_host")
    @classmethod
    def clean_target_host(cls, value: str) -> str:
        return validate_host(value, "目标主机")

    @field_validator("identity_file")
    @classmethod
    def clean_identity_file(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TunnelInput(TunnelFields):
    pass


class TunnelPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    ssh_target: str | None = Field(default=None, min_length=1, max_length=255)
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    remote_bind_host: str | None = Field(default=None, min_length=1, max_length=255)
    remote_port: int | None = Field(default=None, ge=1, le=65535)
    target_host: str | None = Field(default=None, min_length=1, max_length=255)
    target_port: int | None = Field(default=None, ge=1, le=65535)
    identity_file: str | None = Field(default=None, max_length=1024)
    server_alive_interval: int | None = Field(default=None, ge=1, le=3600)
    server_alive_count_max: int | None = Field(default=None, ge=1, le=10)
    connect_timeout: int | None = Field(default=None, ge=1, le=120)
    auto_reconnect: bool | None = None
    auto_start: bool | None = None

    @field_validator("name", "ssh_target", "remote_bind_host", "target_host", "identity_file")
    @classmethod
    def clean_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

class TunnelRead(TunnelFields):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


CheckState = Literal["ok", "warn", "fail", "unknown", "running"]


class CheckResult(BaseModel):
    key: str
    label: str
    state: CheckState
    detail: str = ""
    latency_ms: int | None = None


class RemoteListener(BaseModel):
    found: bool = False
    address: str | None = None
    port: int | None = None
    pids: list[int] = Field(default_factory=list)
    processes: list[dict[str, Any]] = Field(default_factory=list)
    raw: str = ""


class RuntimeView(BaseModel):
    tunnel_id: str
    state: Literal[
        "stopped",
        "starting",
        "connected",
        "target_unreachable",
        "ssh_unreachable",
        "port_conflict",
        "reconnecting",
        "error",
        "stopping",
    ] = "stopped"
    managed: bool = False
    external_tunnel: bool = False
    autossh_pid: int | None = None
    ssh_pid: int | None = None
    started_at: datetime | None = None
    stable_since: datetime | None = None
    last_error: str | None = None
    reconnect_count: int = 0
    next_retry_at: datetime | None = None
    checks: list[CheckResult] = Field(default_factory=list)
    remote_listener: RemoteListener = Field(default_factory=RemoteListener)
    conflict: dict[str, Any] | None = None
    updated_at: datetime | None = None
    activity: str = ""


class TunnelStatus(BaseModel):
    tunnel: TunnelRead
    runtime: RuntimeView


class DiagnosticsResponse(BaseModel):
    runtime: RuntimeView
    checks: list[CheckResult]


class StartResponse(BaseModel):
    started: bool
    message: str
    runtime: RuntimeView


class ConflictPreview(BaseModel):
    tunnel_id: str
    fingerprint: str
    can_clean: bool
    remote_listener: RemoteListener
    end_to_end_ok: bool
    message: str
    manual_command: str | None = None
    expires_at: datetime


class ConflictCleanRequest(BaseModel):
    fingerprint: str
    confirm: bool = False


class SessionResponse(BaseModel):
    token: str

