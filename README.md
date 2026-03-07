# DistributedLLM

基于 FastAPI + Ollama 的分布式推理系统：
- `server`：OpenAI 兼容接口、任务调度、集群同步
- `worker`：模型探测、心跳上报、主动拉取任务执行
- `web`：管理界面（与 server 同机 Docker 部署）

## 1. 目录结构

- `server/`：API、调度、集群逻辑
- `worker/`：Worker 运行逻辑
- `shared/`：配置与公共 schema
- `scripts/`：Docker 一键部署脚本
- `docker-compose.server.yml`：`dllm-server + dllm-web` 编排

## 2. 推荐部署方式（Docker，一键）

### 2.1 前置条件

1. Docker
2. Docker Compose（`docker compose`）
3. 服务器开放端口（默认）：
- `8000`：Server API
- `5173`：Web

### 2.2 最小部署步骤

1. 在仓库根目录准备 `.server_env`（见第 4 节模板）
2. 执行脚本：

Linux/macOS/Git Bash
```bash
bash scripts/deploy_server_docker.sh
```

PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

3. 验证：
```bash
curl http://127.0.0.1:8000/health
```

访问 Web：
- `http://<服务器IP>:5173`

## 3. 新服务器部署前要先设计的信息

1. 认证与密钥
- `DLLM_SERVER_API_KEYS_BOOTSTRAP`：Server Bearer Key（可多个，逗号分隔）
- `DLLM_SERVER_INTERNAL_TOKEN`：Worker/Cluster 内部令牌
- `VITE_API_KEY`：Web 调 `/admin/*` 的 Key（建议与 Server Key 一致）

2. 网络与 CORS
- Web 默认调用 `VITE_API_BASE=/api`（同源路径）
- Web 容器默认代理到 `VITE_PROXY_TARGET=http://dllm-server:8000`（容器内服务名通信，不依赖公网 IP）
- `DLLM_SERVER_CORS_ALLOW_ORIGINS` 必须覆盖你实际访问 Web 的 Origin（协议 + 主机 + 端口）

3. 数据持久化
- 推荐 `DLLM_SERVER_DB_URL=sqlite:///./data/server.db`
- 宿主机目录 `./data/server` 会挂载到容器 `/app/data`

4. 集群（可选）
- `DLLM_SERVER_CLUSTER_ENABLED` 是否启用
- `NODE_IP` 用于生成 `cluster_self_url`
- 多节点时建议手工维护 `DLLM_SERVER_CLUSTER_SEED_URLS`

## 4. `.server_env` 推荐模板（单机）

```env
# ===== Required in production =====
DLLM_SERVER_API_KEYS_BOOTSTRAP=replace-with-strong-api-key
DLLM_SERVER_INTERNAL_TOKEN=replace-with-strong-internal-token
VITE_API_KEY=replace-with-strong-api-key

# ===== Server =====
DLLM_SERVER_DB_URL=sqlite:///./data/server.db
DLLM_SERVER_PORT=8000

# ===== Web =====
DLLM_WEB_PORT=5173
VITE_API_BASE=/api
VITE_PROXY_TARGET=http://dllm-server:8000
VITE_USE_MOCK=false

# ===== Network/CORS =====
NODE_IP=127.0.0.1
NODE_INTERNAL_IP=127.0.0.1
DLLM_SERVER_CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false

# ===== Cluster =====
DLLM_SERVER_CLUSTER_ENABLED=true
```

## 5. 如何在部署时手动指定 token

Linux/macOS/Git Bash：
```bash
DLLM_SERVER_API_KEYS_BOOTSTRAP="your-server-api-key" \
DLLM_SERVER_INTERNAL_TOKEN="your-internal-token" \
VITE_API_KEY="your-web-api-key" \
bash scripts/deploy_server_docker.sh
```

PowerShell：
```powershell
$env:DLLM_SERVER_API_KEYS_BOOTSTRAP="your-server-api-key"
$env:DLLM_SERVER_INTERNAL_TOKEN="your-internal-token"
$env:VITE_API_KEY="your-web-api-key"
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

说明：
- 如果你没传，脚本会用默认值/自动值（例如 `dev-key-123`、随机内部 token）。
- 脚本执行完成后会打印配置摘要（包含原始认证字段）。

## 6. 手工 Compose 部署

```bash
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build
docker compose --env-file .server_env -f docker-compose.server.yml down
```

## 7. 非 Docker Server 启动（开发）

### 7.1 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 7.2 启动

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

## 8. Worker 部署

1. 确保本机可访问 Ollama（默认 `http://127.0.0.1:11434`）
2. 设置最小环境变量：

```bash
export DLLM_WORKER_SERVER_URL=http://<server-ip>:8000
export DLLM_WORKER_OLLAMA_URL=http://127.0.0.1:11434
export DLLM_WORKER_INTERNAL_TOKEN=<same-as-server-internal-token>
(optional) export DLLM_WORKER_STREAM_INTERVAL_SEC=2
```

3. 启动 Worker：

```bash
python -m uvicorn worker.main:app --host 0.0.0.0 --port 9001
```

## 9. 常用验证与运维命令

健康检查：
```bash
curl http://127.0.0.1:8000/health
```

查看容器状态：
```bash
docker compose -f docker-compose.server.yml ps
```

查看日志：
```bash
docker logs -f dllm-server
docker logs -f dllm-web
```

验证 OpenAI 兼容接口：
```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen3:8b",
    "messages":[{"role":"user","content":"1+1等于几，分析下为什么"}],
    "stream": true
  }'
```

## 10. 关键参数速查

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `DLLM_SERVER_DB_URL` | `sqlite:///./server.db` | Server 数据库 |
| `DLLM_SERVER_API_KEYS_BOOTSTRAP` | `""`（代码）/`dev-key-123`（脚本） | 启动导入 API Keys |
| `DLLM_SERVER_INTERNAL_TOKEN` | `""`（代码）/脚本可自动生成 | 内部鉴权 token |
| `DLLM_SERVER_CORS_ALLOW_ORIGINS` | `""` | CORS 来源白名单 |
| `DLLM_SERVER_CORS_ALLOW_CREDENTIALS` | `false` | 是否允许携带凭据 |
| `DLLM_SERVER_CLUSTER_ENABLED` | `false`（代码）/`true`（脚本） | 是否启用集群 |
| `DLLM_SERVER_CLUSTER_SELF_URL` | `http://127.0.0.1:8000` | 节点自身地址 |
| `DLLM_SERVER_CLUSTER_SEED_URLS` | `""` | 种子节点列表 |
| `DLLM_SERVER_PORT` | `8000` | 主机映射端口 |
| `DLLM_WEB_PORT` | `5173` | Web 映射端口 |
| `VITE_API_BASE` | `/api`（脚本） | Web 侧 API 基础路径 |
| `VITE_PROXY_TARGET` | `http://dllm-server:8000`（脚本） | Web 容器内代理目标 |
| `VITE_API_KEY` | `dev-key-123`（脚本） | Web 管理接口调用 key |
| `VITE_USE_MOCK` | `false` | 是否开启 Web mock |
