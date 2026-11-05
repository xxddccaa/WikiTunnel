# `remote port forwarding failed` 故障说明

## 现象

OpenVPN 中断后，autossh/ssh 会退出并尝试重连。远端主机上旧的 SSH 会话可能没有同步释放：

```text
Error: remote port forwarding failed for listen port 15432
```

此时新的 SSH 会话认证成功，但远端主机上 `127.0.0.1:15432` 仍由旧 sshd 会话监听。`ExitOnForwardFailure=yes` 会让当前转发启动失败，避免出现“SSH 已连接但端口没有转发”的假成功。

## 先判断链路是否健康

```bash
ssh remote-host "ss -ltnp 'sport = :15432'"
ssh remote-host "nc -z -w 3 127.0.0.1 15432"
```

第二条命令成功时，说明已有隧道可以接受 TCP 连接。AutoSSH Desk 会把它标记为“已有健康隧道”，不会启动第二个 autossh。

第二条命令失败或超时时，才属于疑似残留监听。

## 安全清理

检查精确端口、PID 和进程：

```bash
ssh remote-host "ss -ltnp 'sport = :15432'"
ssh remote-host "ps -o pid,ppid,user,comm,args -p <PID>"
```

只有在以下条件全部满足时才终止该 PID：

- 监听地址和端口与本隧道完全一致：`127.0.0.1:15432`
- PID 来自该端口的 `ss` 输出
- 进程名是 `sshd`
- 不是当前 SSH 会话本身

```bash
ssh remote-host "kill -TERM <PID>"
```

随后再次检查端口。不要使用 `killall ssh`、`pkill ssh` 或按名称批量终止进程，它们会破坏其他 SSH 会话。

AutoSSH Desk 的“清理端口”按钮会重新读取监听信息，并把诊断结果绑定到 120 秒有效的一次性确认令牌。若 PID 变化、端到端已经恢复、存在多个 PID 或无法确认进程为 sshd，则只显示手工命令，不自动执行。

## 防止反复刷日志

AutoSSH Desk 检测到冲突后会停止本次由它启动的 autossh，并进入“远端端口冲突”状态；在用户测试或清理前不会继续密集重试。目标网络或 SSH 断开时使用 1、2、5、10、20、30、60 秒指数退避，并在网络恢复后提前诊断。

