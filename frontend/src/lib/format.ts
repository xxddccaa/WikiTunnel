import type { TunnelState } from "./api";

export const stateMeta: Record<
  TunnelState,
  { label: string; tone: "green" | "amber" | "red" | "gray"; description: string }
> = {
  stopped: { label: "未启动", tone: "gray", description: "隧道当前停止" },
  starting: { label: "正在启动", tone: "amber", description: "正在检查并建立连接" },
  connected: { label: "已连接", tone: "green", description: "反向隧道工作正常" },
  target_unreachable: {
    label: "VPN / 目标不可达",
    tone: "red",
    description: "目标数据库或 VPN 网络不可达",
  },
  ssh_unreachable: {
    label: "SSH 不可达",
    tone: "red",
    description: "远端主机的 SSH 端点不可达",
  },
  port_conflict: {
    label: "远端端口冲突",
    tone: "red",
    description: "远端监听被旧会话占用",
  },
  reconnecting: {
    label: "正在自动重连",
    tone: "amber",
    description: "等待下一次重试",
  },
  error: { label: "错误", tone: "red", description: "需要人工处理" },
  stopping: { label: "停止中", tone: "gray", description: "正在安全终止进程" },
};

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  if (seconds < 60) return `${Math.floor(seconds)} 秒`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) return `${hours} 小时 ${remainingMinutes} 分`;
  const days = Math.floor(hours / 24);
  return `${days} 天 ${hours % 24} 小时`;
}

export function elapsedSince(value: string | null, now = Date.now()): number {
  if (!value) return 0;
  return Math.max(0, (now - new Date(value).getTime()) / 1000);
}

export function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export function copyText(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function dbeaverText(tunnel: {
  ssh_target: string;
  ssh_port: number | null;
  identity_file: string | null;
  remote_bind_host: string;
  remote_port: number;
}): string {
  const sshPort = tunnel.ssh_port ? ` -p ${tunnel.ssh_port}` : "";
  const identity = tunnel.identity_file ? ` -i "${tunnel.identity_file}"` : "";
  return [
    `远端 DBeaver: 主机 127.0.0.1，端口 ${tunnel.remote_port}，类型 PostgreSQL`,
    "",
    "Mac 端临时本地转发命令（不要同时运行 AutoSSH Desk 的同端口本地监听）：",
    `ssh -N -L ${tunnel.remote_port}:${tunnel.remote_bind_host}:${tunnel.remote_port}${sshPort}${identity} ${tunnel.ssh_target}`,
    "",
    "数据库账号和密码未包含在复制内容中。",
  ].join("\n");
}

