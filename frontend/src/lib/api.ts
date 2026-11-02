export type TunnelState =
  | "stopped"
  | "starting"
  | "connected"
  | "target_unreachable"
  | "ssh_unreachable"
  | "port_conflict"
  | "reconnecting"
  | "error"
  | "stopping";

export type CheckState = "ok" | "warn" | "fail" | "unknown" | "running";

export interface CheckResult {
  key: string;
  label: string;
  state: CheckState;
  detail: string;
  latency_ms: number | null;
}

export interface RemoteProcess {
  pid: number;
  ppid: number | null;
  user: string;
  comm: string;
  args: string;
  is_sshd: boolean;
}

export interface RemoteListener {
  found: boolean;
  address: string | null;
  port: number | null;
  pids: number[];
  processes: RemoteProcess[];
  raw: string;
}

export interface RuntimeView {
  tunnel_id: string;
  state: TunnelState;
  managed: boolean;
  external_tunnel: boolean;
  autossh_pid: number | null;
  ssh_pid: number | null;
  started_at: string | null;
  stable_since: string | null;
  last_error: string | null;
  reconnect_count: number;
  next_retry_at: string | null;
  checks: CheckResult[];
  remote_listener: RemoteListener;
  conflict: Record<string, unknown> | null;
  updated_at: string | null;
  activity: string;
}

export interface TunnelFields {
  name: string;
  ssh_target: string;
  ssh_port: number | null;
  remote_bind_host: string;
  remote_port: number;
  target_host: string;
  target_port: number;
  identity_file: string | null;
  server_alive_interval: number;
  server_alive_count_max: number;
  connect_timeout: number;
  auto_reconnect: boolean;
  auto_start: boolean;
}

export interface Tunnel extends TunnelFields {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface TunnelStatus {
  tunnel: Tunnel;
  runtime: RuntimeView;
}

export interface HealthResponse {
  ok: boolean;
  version: string;
  autossh: string | null;
  time: string;
}

export interface StartResponse {
  started: boolean;
  message: string;
  runtime: RuntimeView;
}

export interface ConflictPreview {
  tunnel_id: string;
  fingerprint: string;
  can_clean: boolean;
  remote_listener: RemoteListener;
  end_to_end_ok: boolean;
  message: string;
  manual_command: string | null;
  expires_at: string;
}

export interface WikiEvent {
  type: "snapshot" | "runtime" | "log" | "log_cleared" | "system";
  tunnel_id?: string;
  runtime?: RuntimeView;
  lines?: string[];
  statuses?: TunnelStatus[];
  message?: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let tokenPromise: Promise<string> | null = null;

export async function sessionToken(): Promise<string> {
  if (!tokenPromise) {
    tokenPromise = fetch("/api/session", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new ApiError("无法建立本地会话", response.status);
        const data = (await response.json()) as { token: string };
        return data.token;
      })
      .catch((error) => {
        tokenPromise = null;
        throw error;
      });
  }
  return tokenPromise;
}

function detailFromPayload(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join("；");
    }
  }
  return "请求失败";
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-WikiTunnel-Token", await sessionToken());
  }
  const response = await fetch(path, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text();
    }
    throw new ApiError(detailFromPayload(payload), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  statuses: () => request<TunnelStatus[]>("/api/tunnels"),
  health: () => request<HealthResponse>("/api/health"),
  logs: async (id: string) => {
    const response = await fetch(`/api/tunnels/${id}/logs`, { cache: "no-store" });
    if (!response.ok) throw new ApiError("无法读取日志", response.status);
    return response.text();
  },
  create: (payload: TunnelFields) =>
    request<TunnelStatus>("/api/tunnels", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: Partial<TunnelFields>) =>
    request<TunnelStatus>(`/api/tunnels/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  remove: (id: string) =>
    request<void>(`/api/tunnels/${id}`, { method: "DELETE" }),
  duplicate: (id: string) =>
    request<TunnelStatus>(`/api/tunnels/${id}/duplicate`, { method: "POST" }),
  start: (id: string) =>
    request<StartResponse>(`/api/tunnels/${id}/start`, { method: "POST" }),
  stop: (id: string) =>
    request<RuntimeView>(`/api/tunnels/${id}/stop`, { method: "POST" }),
  restart: (id: string) =>
    request<StartResponse>(`/api/tunnels/${id}/restart`, { method: "POST" }),
  test: (id: string) =>
    request<{ runtime: RuntimeView }>(`/api/tunnels/${id}/test`, { method: "POST" }),
  clearLogs: (id: string) =>
    request<void>(`/api/tunnels/${id}/logs`, { method: "DELETE" }),
  previewConflict: (id: string) =>
    request<ConflictPreview>(`/api/tunnels/${id}/conflict/preview`, { method: "POST" }),
  cleanConflict: (id: string, fingerprint: string) =>
    request<{ ok: boolean; message: string }>(`/api/tunnels/${id}/conflict/clean`, {
      method: "POST",
      body: JSON.stringify({ fingerprint, confirm: true }),
    }),
};

export function webSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/ws`;
}

