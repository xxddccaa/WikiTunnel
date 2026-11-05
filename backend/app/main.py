from __future__ import annotations

import asyncio
import fcntl
import os
import secrets
import threading
import time
import urllib.request
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import select

from .config import Settings, env_setting
from .conflict import ConflictError
from .database import Database
from .diagnostics import Diagnostics
from .events import EventBroker
from .models import Tunnel
from .schemas import (
    ConflictCleanRequest,
    ConflictPreview,
    DiagnosticsResponse,
    RuntimeView,
    SessionResponse,
    StartResponse,
    TunnelInput,
    TunnelPatch,
    TunnelStatus,
)
from .supervisor import SupervisorError, TunnelBusyError, TunnelSupervisor


class InstanceLock:
    def __init__(self, path: Path):
        self.path = path
        self.descriptor: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise RuntimeError("AutoSSH Desk 已有实例运行") from exc
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        os.chmod(self.path, 0o600)
        self.descriptor = descriptor

    def release(self) -> None:
        if self.descriptor is None:
            return
        try:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self.descriptor)
            self.descriptor = None


def _local_hostname(value: str) -> str | None:
    parsed = urlsplit(f"//{value}")
    return parsed.hostname


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    config.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(config.data_dir, 0o700)
    config.records_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    config.logs_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(config.records_dir, 0o700)
    os.chmod(config.logs_dir, 0o700)

    database = Database(config.database_path)
    broker = EventBroker()
    diagnostics = Diagnostics(config)
    supervisor = TunnelSupervisor(database, config, diagnostics, broker)
    lock = InstanceLock(config.instance_lock_path) if config.instance_lock else None
    api_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if lock is not None:
            lock.acquire()
        await supervisor.start_background()
        try:
            yield
        finally:
            await supervisor.shutdown()
            database.engine.dispose()
            if lock is not None:
                lock.release()

    app = FastAPI(
        title="AutoSSH Desk",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.database = database
    app.state.supervisor = supervisor
    app.state.broker = broker
    app.state.diagnostics = diagnostics
    app.state.api_token = api_token

    if config.strict_security:
        @app.middleware("http")
        async def local_security(request: Request, call_next):
            host = _local_hostname(request.headers.get("host", ""))
            allowed_hosts = {"127.0.0.1", "localhost", "::1", config.host}
            if host not in allowed_hosts:
                return JSONResponse({"detail": "仅允许本机访问"}, status_code=403)
            origin = request.headers.get("origin")
            if origin:
                origin_host = urlsplit(origin).hostname
                if origin_host not in allowed_hosts:
                    return JSONResponse({"detail": "Origin 被拒绝"}, status_code=403)
            if (
                request.url.path.startswith("/api/")
                and request.method not in {"GET", "HEAD", "OPTIONS"}
                and request.url.path != "/api/session"
            ):
                supplied = request.headers.get(
                    "x-autossh-desk-token", request.headers.get("x-wikitunnel-token", "")
                )
                if not secrets.compare_digest(supplied, api_token):
                    return JSONResponse({"detail": "无效的本地会话令牌"}, status_code=403)
            return await call_next(request)

    def require_not_managed(tunnel_id: str) -> TunnelStatus:
        status = supervisor.status(tunnel_id)
        if status.runtime.managed:
            raise HTTPException(status_code=409, detail="请先停止该隧道再修改或删除配置")
        return status

    def ensure_unique(
        session,
        validated: dict,
        *,
        exclude_id: str | None = None,
    ) -> None:
        query = select(Tunnel.id).where(
            Tunnel.ssh_target == validated["ssh_target"],
            Tunnel.remote_bind_host == validated["remote_bind_host"],
            Tunnel.remote_port == validated["remote_port"],
        )
        if exclude_id:
            query = query.where(Tunnel.id != exclude_id)
        if session.scalar(query.limit(1)) is not None:
            raise HTTPException(
                status_code=409,
                detail="同一 SSH 端点和监听地址下，远端端口不能重复",
            )

    @app.get("/api/health")
    async def health():
        return {
            "ok": True,
            "version": "0.1.0",
            "autossh": diagnostics.find_autossh(),
            "time": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/session", response_model=SessionResponse)
    async def session_token():
        return SessionResponse(token=api_token)

    @app.get("/api/tunnels", response_model=list[TunnelStatus])
    async def list_tunnels():
        return supervisor.statuses()

    @app.post("/api/tunnels", response_model=TunnelStatus, status_code=201)
    async def create_tunnel(payload: TunnelInput):
        validated = payload.model_dump()
        with database.session() as session:
            ensure_unique(session, validated)
            tunnel = Tunnel(**validated)
            session.add(tunnel)
            session.commit()
            session.refresh(tunnel)
            session.expunge(tunnel)
        return supervisor.status(tunnel.id)

    @app.get("/api/tunnels/{tunnel_id}", response_model=TunnelStatus)
    async def get_tunnel(tunnel_id: str):
        try:
            return supervisor.status(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/tunnels/{tunnel_id}", response_model=TunnelStatus)
    async def update_tunnel(tunnel_id: str, payload: TunnelPatch):
        require_not_managed(tunnel_id)
        try:
            await supervisor.suspend_for_config_change(tunnel_id)
        except TunnelBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        with database.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if tunnel is None:
                raise HTTPException(status_code=404, detail="隧道不存在")
            current = TunnelInput.model_validate(tunnel).model_dump()
            current.update(payload.model_dump(exclude_unset=True))
            validated = TunnelInput.model_validate(current).model_dump()
            ensure_unique(session, validated, exclude_id=tunnel_id)
            for key, value in validated.items():
                setattr(tunnel, key, value)
            tunnel.updated_at = datetime.now(timezone.utc)
            session.commit()
        return supervisor.status(tunnel_id)

    @app.post("/api/tunnels/{tunnel_id}/duplicate", response_model=TunnelStatus, status_code=201)
    async def duplicate_tunnel(tunnel_id: str):
        with database.session() as session:
            source = session.get(Tunnel, tunnel_id)
            if source is None:
                raise HTTPException(status_code=404, detail="隧道不存在")
            values = TunnelInput.model_validate(source).model_dump()
            used_ports = set(
                session.scalars(
                    select(Tunnel.remote_port).where(Tunnel.ssh_target == source.ssh_target)
                ).all()
            )
            port = source.remote_port
            for _ in range(65535):
                port = port + 1 if port < 65535 else 1024
                if port not in used_ports:
                    break
            else:
                raise HTTPException(status_code=409, detail="没有可用的远端端口")
            values["name"] = f"{source.name} 副本"[:80]
            values["remote_port"] = port
            values["auto_start"] = False
            ensure_unique(session, values)
            tunnel = Tunnel(**values, manually_stopped=True)
            session.add(tunnel)
            session.commit()
            session.refresh(tunnel)
            session.expunge(tunnel)
        return supervisor.status(tunnel.id)

    @app.delete("/api/tunnels/{tunnel_id}", status_code=204)
    async def delete_tunnel(tunnel_id: str):
        require_not_managed(tunnel_id)
        try:
            await supervisor.suspend_for_config_change(tunnel_id)
        except TunnelBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        with database.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if tunnel is None:
                raise HTTPException(status_code=404, detail="隧道不存在")
            session.delete(tunnel)
            session.commit()
        supervisor.forget_tunnel(tunnel_id)
        return None

    @app.post("/api/tunnels/{tunnel_id}/start", response_model=StartResponse)
    async def start_tunnel(tunnel_id: str):
        try:
            return await supervisor.start_tunnel(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tunnels/{tunnel_id}/stop", response_model=RuntimeView)
    async def stop_tunnel(tunnel_id: str):
        try:
            return await supervisor.stop_tunnel(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tunnels/{tunnel_id}/restart", response_model=StartResponse)
    async def restart_tunnel(tunnel_id: str):
        try:
            return await supervisor.restart_tunnel(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tunnels/{tunnel_id}/test", response_model=DiagnosticsResponse)
    async def test_tunnel(tunnel_id: str):
        try:
            runtime = await supervisor.diagnose_tunnel(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return DiagnosticsResponse(runtime=runtime, checks=runtime.checks)

    @app.get("/api/tunnels/{tunnel_id}/logs", response_class=PlainTextResponse)
    async def tunnel_logs(tunnel_id: str):
        try:
            return PlainTextResponse(
                supervisor.get_log(tunnel_id),
                headers={"Cache-Control": "no-store"},
            )
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/tunnels/{tunnel_id}/logs", status_code=204)
    async def clear_tunnel_logs(tunnel_id: str):
        try:
            supervisor.clear_log(tunnel_id)
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return None

    @app.post("/api/tunnels/{tunnel_id}/conflict/preview", response_model=ConflictPreview)
    async def preview_conflict(tunnel_id: str):
        try:
            return await supervisor.preview_conflict(tunnel_id)
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tunnels/{tunnel_id}/conflict/clean")
    async def clean_conflict(tunnel_id: str, payload: ConflictCleanRequest):
        try:
            listener, message = await supervisor.clean_conflict(tunnel_id, payload)
            return {"ok": True, "message": message, "remote_listener": listener}
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SupervisorError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.websocket("/api/ws")
    async def events(websocket: WebSocket):
        if config.strict_security:
            origin = websocket.headers.get("origin")
            allowed_hosts = {"127.0.0.1", "localhost", "::1", config.host}
            if origin and urlsplit(origin).hostname not in allowed_hosts:
                await websocket.close(code=4403)
                return
        await websocket.accept()
        if config.strict_security:
            try:
                auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            except (asyncio.TimeoutError, ValueError, RuntimeError, WebSocketDisconnect):
                await websocket.close(code=4401)
                return
            token = auth_message.get("token", "") if isinstance(auth_message, dict) else ""
            if not secrets.compare_digest(str(token), api_token):
                await websocket.close(code=4401)
                return
        try:
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "statuses": [item.model_dump(mode="json") for item in supervisor.statuses()],
                }
            )
            async for event in broker.subscribe():
                await websocket.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            return

    frontend_index = config.frontend_dist / "index.html"
    assets_dir = config.frontend_dist / "assets"
    if assets_dir.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}")
    async def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if frontend_index.is_file():
            return FileResponse(frontend_index)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "前端尚未构建",
                "next": "在项目目录执行 ./setup.sh，或使用 pnpm --dir frontend dev",
            },
        )

    return app


def _open_when_ready(url: str) -> None:
    health_url = f"{url}/api/health"
    for _ in range(40):
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.25)


def launch() -> None:
    import uvicorn

    config = Settings.from_env()
    if not (config.frontend_dist / "index.html").is_file():
        raise SystemExit("前端尚未构建，请先执行 ./setup.sh")
    app = create_app(config)
    url = f"http://{config.host}:{config.port}"
    if env_setting("NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
        threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
    print(f"AutoSSH Desk: {url}")
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")

