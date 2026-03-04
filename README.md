# DistributedLLM

基于 FastAPI + Ollama 的分布式推理系统：
- `server` 提供 OpenAI 兼容接口（`/v1/models`、`/v1/chat/completions`）
- `worker` 通过心跳 + 主动拉取任务执行推理（NAT 友好）
- 可选 Docker 一键部署 `server + web`

## 1. 目录说明

- `server/`：调度、队列、API、集群逻辑
- `worker/`：模型探测、推理执行、心跳上报、任务拉取
- `shared/`：配置与公共 schema
- `scripts/`：Docker 部署脚本
- `docker-compose.server.yml`：Server + Web 的 Compose 编排

## 2. Server 手动部署

### 2.1 前置条件

1. Python 3.10+（建议 3.12）
2. 可写数据库路径（默认 SQLite）

### 2.2 安装依赖

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

### 2.3 配置 `.server_env`

在仓库根目录创建 `.server_env`（至少建议填这两项）：

```env
DLLM_SERVER_DB_URL=sqlite:///./server.db
DLLM_SERVER_API_KEYS_BOOTSTRAP=dev-key-123
```

如果你启用了内部鉴权，还要加：

```env
DLLM_SERVER_INTERNAL_TOKEN=replace-with-a-strong-token
```

### 2.4 启动 Server

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 2.5 验证

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models -H "Authorization: Bearer dev-key-123"
```

## 3. Server Docker 部署

### 3.1 前置条件

1. Docker
2. Docker Compose（`docker compose`）

### 3.2 方式 A：使用脚本一键部署（推荐）

Linux/macOS/Git Bash：

```bash
bash scripts/deploy_server_docker.sh
```

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

脚本会自动生成或更新根目录 `.server_env`，并执行：

```bash
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build
```

脚本写入 `.server_env` 时的关键行为：
- 默认将 `DLLM_SERVER_CLUSTER_ENABLED` 设为 `true`
- 自动生成 `DLLM_SERVER_CLUSTER_NODE_ID`
- 自动设置 `DLLM_SERVER_CLUSTER_SELF_URL=http://<NODE_IP>:<DLLM_SERVER_PORT>`
- 自动合并 `DLLM_SERVER_CLUSTER_SEED_URLS`，并包含默认邻居 `http://111.230.32.219:8000`

### 3.3 方式 B：手工执行 compose

1. 先准备 `.server_env`（至少应包含 `DLLM_SERVER_API_KEYS_BOOTSTRAP`，建议同时设置 `DLLM_SERVER_DB_URL=sqlite:///./data/server.db`）
2. 启动：

```bash
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build
```

3. 停止：

```bash
docker compose --env-file .server_env -f docker-compose.server.yml down
```

### 3.4 Docker 部署验证

```bash
docker compose -f docker-compose.server.yml ps
curl http://127.0.0.1:8000/health
```

## 4. Worker 部署

### 4.1 前置条件

1. 与 Server 相同版本的代码和 Python 依赖
2. 本机可访问 Ollama（默认 `http://127.0.0.1:11434`）
3. Ollama 已下载至少一个模型（例如 `qwen3:8b`）

### 4.2 启动 Ollama（示例）

```bash
ollama serve
ollama pull qwen3:8b
```

### 4.3 配置 Worker 环境变量

最小配置：

```bash
export DLLM_WORKER_SERVER_URL=http://<server-ip>:8000
export DLLM_WORKER_OLLAMA_URL=http://127.0.0.1:11434
```

若 Server 设置了 `DLLM_SERVER_INTERNAL_TOKEN`，Worker 必须配置同值：

```bash
export DLLM_WORKER_INTERNAL_TOKEN=replace-with-the-same-token
```

### 4.4 启动 Worker

```bash
python -m uvicorn worker.main:app --host 0.0.0.0 --port 9001
```

Worker 启动后会自动：
1. 注册 worker_id
2. 定时上报心跳
3. 循环拉取并执行任务

### 4.5 验证 Worker 是否接入

```bash
curl http://127.0.0.1:8000/admin/workers -H "Authorization: Bearer <your-api-key>"
```

## 5. `.server_env` 允许参数与默认值

说明：
- `ServerSettings` 读取 `.server_env` 和 `.env`（优先 `.server_env`），变量前缀为 `DLLM_SERVER_`
- Docker Compose 也会读取 `.server_env`，用于端口映射和 Web 环境变量
- 下表中的“代码默认值”来自 `shared/config.py`；“脚本默认值”来自 `scripts/deploy_server_docker.sh/.ps1`

### 5.1 Server 核心参数（`DLLM_SERVER_*`）

| 参数 | 代码默认值 | 用途 |
| --- | --- | --- |
| `DLLM_SERVER_DB_URL` | `sqlite:///./server.db` | 数据库连接串 |
| `DLLM_SERVER_API_KEYS_BOOTSTRAP` | `""` | 启动时导入 API Key（逗号分隔） |
| `DLLM_SERVER_INTERNAL_TOKEN` | `""` | Worker/Cluster 内部接口令牌（`X-Worker-Token`） |
| `DLLM_SERVER_HEARTBEAT_TIMEOUT_SEC` | `60` | 心跳超时判离线 |
| `DLLM_SERVER_CLEANUP_INTERVAL_SEC` | `30` | 心跳清理任务周期 |
| `DLLM_SERVER_REQUEST_TIMEOUT_SEC` | `600` | 请求分配等待超时 |
| `DLLM_SERVER_JOB_POLL_INTERVAL_MS` | `300` | 请求端轮询间隔 |
| `DLLM_SERVER_JOB_MAX_WAIT_SEC` | `600` | Job 完成等待超时 |
| `DLLM_SERVER_CORS_ALLOW_ORIGINS` | `""` | CORS 来源白名单（逗号分隔） |
| `DLLM_SERVER_CORS_ALLOW_CREDENTIALS` | `false` | 是否允许跨域携带凭据 |
| `DLLM_SERVER_CLUSTER_ENABLED` | `false` | 是否启用集群 |
| `DLLM_SERVER_CLUSTER_NODE_ID` | `node-local` | 当前节点 ID |
| `DLLM_SERVER_CLUSTER_SELF_URL` | `http://127.0.0.1:8000` | 当前节点对外地址 |
| `DLLM_SERVER_CLUSTER_SEED_URLS` | `""` | 种子节点列表（逗号分隔） |
| `DLLM_SERVER_CLUSTER_NEIGHBOR_COUNT` | `3` | 探活邻居数 |
| `DLLM_SERVER_CLUSTER_GOSSIP_FANOUT` | `2` | 每轮 gossip 扇出 |
| `DLLM_SERVER_CLUSTER_GOSSIP_INTERVAL_SEC` | `3` | gossip 周期 |
| `DLLM_SERVER_CLUSTER_GOSSIP_TIMEOUT_SEC` | `2.5` | gossip HTTP 超时 |
| `DLLM_SERVER_CLUSTER_PROBE_TIMEOUT_SEC` | `1.5` | 探活超时 |
| `DLLM_SERVER_CLUSTER_DELTA_BATCH_SIZE` | `200` | gossip 增量批大小 |
| `DLLM_SERVER_CLUSTER_REQUEST_FORWARD_AFTER_SEC` | `2.0` | 本地等待后触发转发 |
| `DLLM_SERVER_CLUSTER_REQUEST_FORWARD_TIMEOUT_SEC` | `20.0` | 转发请求超时 |
| `DLLM_SERVER_CLUSTER_REQUEST_MAX_HOPS` | `2` | 最大转发跳数 |
| `DLLM_SERVER_CLUSTER_REQUEST_MAX_CANDIDATES` | `3` | 单次最大候选转发数 |

### 5.2 Docker/脚本相关参数（同样放在 `.server_env`）

| 参数 | 脚本默认值 | 用途 |
| --- | --- | --- |
| `DLLM_SERVER_PORT` | `8000` | 容器内 `8000` 对外映射端口 |
| `DLLM_WEB_PORT` | `5173` | Web 容器端口映射 |
| `DOCKER_IMAGE_NAME` | `dllm-server:latest` | Server 镜像名 |
| `DOCKER_CONTAINER_NAME` | `dllm-server` | Server 容器名 |
| `DOCKER_WEB_CONTAINER_NAME` | `dllm-web` | Web 容器名 |
| `NODE_IP` | `127.0.0.1` | 脚本生成 `cluster_self_url` 与 `VITE_API_BASE` |
| `NODE_INTERNAL_IP` | `127.0.0.1` | 脚本生成 CORS 白名单 |
| `VITE_API_BASE` | `http://<NODE_IP>:<DLLM_SERVER_PORT>` | Web 调用后端地址 |
| `VITE_API_KEY` | `dev-key-123` | Web 调用 `/admin/*` 时的 Bearer Key |
| `VITE_USE_MOCK` | `false` | Web 是否启用 mock |

注意：
- Docker 脚本默认会把 `DLLM_SERVER_DB_URL` 写成 `sqlite:///./data/server.db`（落在挂载卷 `./data/server`）
- 如果你手动 compose 且未设置 `DLLM_SERVER_DB_URL`，代码默认将使用 `sqlite:///./server.db`（容器内路径）

## 6. 常用接口验证

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role":"user","content":"用中文回答：1+1等于几？"}],
    "temperature": 0.2
  }'
```
