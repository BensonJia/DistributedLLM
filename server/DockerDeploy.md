# Docker 最小部署教程

本文档提供 `server` 端最小可用部署步骤（含后端 + Web）。

## 1. 前置条件

在项目根目录执行：

```bash
docker --version
docker compose version
```

> 若你的环境只有 `docker-compose`，把文档中的 `docker compose` 替换为 `docker-compose`。

## 2. 最小配置（.server_env）

在项目根目录创建 `.server_env`：

```bash
NODE_IP=你的服务器IP
NODE_INTERNAL_IP=你的内网IP
DLLM_SERVER_API_KEYS_BOOTSTRAP=默认设为dev-key-123  
DLLM_SERVER_INTERNAL_TOKEN=cluster-server-worker管理标识，同一集群公用，默认f7c236ae083058716ae3c91b2824ba237fb4b7ee88a9d8bf
DLLM_SERVER_PORT=8000
DLLM_WEB_PORT=5173
DLLM_SERVER_DB_URL=sqlite:///./data/server.db
DLLM_SERVER_CLUSTER_ENABLED=true
VITE_API_KEY=dev-key-123
```

说明：
- `DLLM_SERVER_INTERNAL_TOKEN`：集群内部通信 token（同一集群保持一致）。
- `VITE_API_KEY`：Web 管理端调用 `/admin/*` 接口时使用的 API Key（默认 `dev-key-123`）。
- 不填写时，部署脚本会自动生成并写回 `.server_env`。
- 脚本会自动补全运行时字段（如 `DLLM_SERVER_CLUSTER_NODE_ID`、`DLLM_SERVER_CLUSTER_SELF_URL`）。

## 3. 一键部署

Linux/macOS/Git Bash：

```bash
bash scripts/deploy_server_docker.sh
```

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

## 4. 验证服务

```bash
docker compose -f docker-compose.server.yml ps
curl http://127.0.0.1:8000/health
```

预期：`/health` 返回 `{"ok": true}`。

## 5. 常用运维命令

```bash
# 查看日志
docker logs -f dllm-server
docker logs -f dllm-web

# 重新部署（重建镜像）
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build

# 停止并删除容器
docker compose --env-file .server_env -f docker-compose.server.yml down
```
