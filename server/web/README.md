# DistributedLLM Web Admin 部署说明

本说明基于当前仓库实现，覆盖：
- Server 手动部署
- Server Docker 部署
- 不同网络场景下 CORS 配置
- InternalToken 配置
- 生产环境（非测试）在 Server 与 Web 侧必须做的配置

## 1. 基础说明

- Server 进程：`uvicorn server.main:app`
- Server 默认端口：`8000`
- Web 默认开发端口：`5173`
- Server 配置前缀：`DLLM_SERVER_`
- Server 配置文件读取：优先 `.server_env`，其次 `.env`

内部鉴权机制：
- `DLLM_SERVER_INTERNAL_TOKEN` 为空时，`/internal/*` 不校验 token
- 非空时，Worker/Cluster 必须带 `X-Worker-Token: <token>`

## 2. Server 手动部署

### 2.1 安装依赖

仓库根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 准备 `.server_env`

本机最小配置（开发/测试）：

```env
DLLM_SERVER_DB_URL=sqlite:///./server.db
DLLM_SERVER_API_KEYS_BOOTSTRAP=dev-key-123, dev-key-456, dev-key-789, dev-key-abc
DLLM_SERVER_CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
```

### 2.3 启动 Server

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 2.4 启动 Web（开发模式）

在 `server/web` 目录执行：

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Web 本地配置（可选 `.env.local`）：

```env
VITE_API_BASE=http://127.0.0.1:8000
VITE_API_KEY=dev-key-123
VITE_USE_MOCK=false
```

## 3. Server Docker 部署

### 3.1 一键脚本部署（推荐）

项目根目录执行：

Linux/macOS/Git Bash：

```bash
bash scripts/deploy_server_docker.sh
```

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

当前脚本会自动写入：
- `DLLM_SERVER_PORT`（默认 `8000`）
- `DLLM_WEB_PORT`（默认 `5173`）
- `DLLM_SERVER_DB_URL`（默认 `sqlite:///./data/server.db`）
- `DLLM_SERVER_INTERNAL_TOKEN`（若缺失则自动生成）
- `VITE_API_BASE`、`VITE_API_KEY`、`DLLM_SERVER_CORS_ALLOW_ORIGINS`

### 3.2 手工 compose 部署

```bash
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build
```

停止：

```bash
docker compose --env-file .server_env -f docker-compose.server.yml down
```

## 4. 不同网络场景下的 CORS

`DLLM_SERVER_CORS_ALLOW_ORIGINS` 必须与浏览器访问 Web 的 Origin 完全一致（协议/域名或IP/端口）。

### 4.1 同机开发

```env
DLLM_SERVER_CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
```

### 4.2 局域网访问

示例：Server 为 `192.168.1.10`。

```env
DLLM_SERVER_CORS_ALLOW_ORIGINS=http://192.168.1.10:5173,http://127.0.0.1:5173,http://localhost:5173
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
```

### 4.3 公网/反代域名

```env
DLLM_SERVER_CORS_ALLOW_ORIGINS=https://admin.example.com
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
```

## 5. InternalToken 配置方法

### 5.1 Server 端

```env
DLLM_SERVER_INTERNAL_TOKEN=replace-with-strong-random-token
```

### 5.2 Worker 端（必须同值）

```env
DLLM_WORKER_SERVER_URL=http://<server-ip>:8000
DLLM_WORKER_INTERNAL_TOKEN=replace-with-strong-random-token
DLLM_WORKER_OLLAMA_URL=http://127.0.0.1:11434
```

启动 Worker：

```bash
python -m uvicorn worker.main:app --host 0.0.0.0 --port 9001
```

## 6. 生产环境配置（手动部署）

### 6.1 Server 主程序必须调整

```env
DLLM_SERVER_DB_URL=postgresql+psycopg://user:pass@db-host:5432/dllm
DLLM_SERVER_API_KEYS_BOOTSTRAP=replace-with-strong-api-key-or-multiple
DLLM_SERVER_INTERNAL_TOKEN=replace-with-strong-random-token
DLLM_SERVER_CORS_ALLOW_ORIGINS=https://admin.example.com
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
DLLM_SERVER_HEARTBEAT_TIMEOUT_SEC=90
DLLM_SERVER_CLEANUP_INTERVAL_SEC=15
DLLM_SERVER_REQUEST_TIMEOUT_SEC=300
DLLM_SERVER_JOB_MAX_WAIT_SEC=300
```

生产建议：
- 不使用默认 `dev-key-123`
- 不让 `DLLM_SERVER_INTERNAL_TOKEN` 留空
- 当前架构含后台调度任务，生产建议单实例单进程部署 `server.main`，避免多进程重复调度

### 6.2 Web 端调整内容

```env
VITE_API_BASE=https://api.example.com
VITE_API_KEY=<prod-api-key>
VITE_USE_MOCK=false
```

生产建议：
- 不使用 mock
- `VITE_API_BASE` 指向生产 API 域名
- 使用专用生产 API Key，不与开发环境共用

## 7. 生产环境配置（Docker 部署）

### 7.1 Server 主程序配置（`.server_env`）

建议至少覆盖脚本默认值：

```env
DLLM_SERVER_DB_URL=postgresql+psycopg://user:pass@db-host:5432/dllm
DLLM_SERVER_API_KEYS_BOOTSTRAP=<prod-api-key>
DLLM_SERVER_INTERNAL_TOKEN=<strong-random-token>
DLLM_SERVER_CORS_ALLOW_ORIGINS=https://admin.example.com
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false
DLLM_SERVER_PORT=8000
```

若启用集群，再补充：

```env
DLLM_SERVER_CLUSTER_ENABLED=true
DLLM_SERVER_CLUSTER_NODE_ID=node-a
DLLM_SERVER_CLUSTER_SELF_URL=https://api-a.example.com
DLLM_SERVER_CLUSTER_SEED_URLS=https://api-b.example.com,https://api-c.example.com
```

### 7.2 Web 端配置（`.server_env`）

```env
VITE_API_BASE=https://api.example.com
VITE_API_KEY=<prod-api-key> (必须加入到DLLM_SERVER_API_KEYS_BOOTSTRAP)
VITE_USE_MOCK=false
```

注意：
- 当前 `docker-compose.server.yml` 的 `dllm-web` 使用 `npm run dev`（开发服务器）
- 正式生产建议改为 `npm run build` 后由 Nginx/Caddy 提供静态文件服务
- 若继续使用当前 compose，请至少限制来源 IP、加反向代理与 TLS，不建议直接公网裸露

## 8. 快速验证

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/admin/workers -H "Authorization: Bearer <api-key>"
```
