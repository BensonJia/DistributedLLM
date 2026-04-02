# Power Host 部署

这是一个跑在宿主机上的独立功耗采样服务，不放进 worker 容器。

## 1. 作用

- 采样宿主机 CPU/GPU 功耗
- 向 worker 提供实时 websocket 功耗流
- 向 worker 提供最新功耗快照

## 2. 默认端口

- `9002`

## 3. 启动方式

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_power_host.ps1
```

Linux/macOS/Git Bash：

```bash
bash scripts/run_power_host.sh
```

## 4. Worker 侧配置

```env
DLLM_WORKER_POWER_SERVICE_HTTP_URL=http://host.docker.internal:9002
DLLM_WORKER_POWER_SERVICE_WS_URL=ws://host.docker.internal:9002/internal/power/ws
```

## 5. 验证

```bash
curl http://127.0.0.1:9002/health
curl http://127.0.0.1:9002/internal/power/latest
```
