# Server 配置项说明（可选变量与作用）

配置由 `shared/config.py` 中 `ServerSettings` 定义，读取规则：
- 环境变量前缀：`DLLM_SERVER_`
- env 文件：优先 `.server_env`，其次 `.env`
- 未配置时使用默认值。

示例：`db_url` 对应环境变量 `DLLM_SERVER_DB_URL`。

## 1. 基础配置

- `db_url`（默认：`sqlite:///./server.db`）
  - 数据库连接 URL。
  - SQLite 默认落在项目根目录 `server.db`。

- `api_keys_bootstrap`（默认：空字符串）
  - 启动时自动导入的 API Key 列表，逗号分隔。
  - 仅导入不存在的 key。

- `internal_token`（默认：空字符串）
  - 内部接口共享令牌。
  - 设置后，worker/cluster 内部接口需提供请求头 `X-Worker-Token`。

## 2. Worker 存活与清理

- `heartbeat_timeout_sec`（默认：`60`）
  - 超过该秒数未收到心跳，worker 会被标记离线。

- `cleanup_interval_sec`（默认：`30`）
  - 心跳清理任务执行周期（秒）。

## 3. 请求/任务等待参数

- `request_timeout_sec`（默认：`600`）
  - `/v1/chat/completions` 等待请求分配的最长时间（秒）。

- `job_poll_interval_ms`（默认：`300`）
  - 请求端轮询 job 状态间隔（毫秒）。

- `job_max_wait_sec`（默认：`600`）
  - 请求端等待 job 完成的最大时长（秒）。

- `dispatch_interval_sec`（默认：`2.0`）
  - 请求池批量分配任务的调度间隔（秒）。
  - 在该间隔内到达的请求会先进入候选请求池，等待下一轮批量分配。

- `scheduler_speed_tolerance_ratio`（默认：`0.1`）
  - worker 选择时的速度容忍比例（0 表示严格按速度优先）。
  - 例如 `0.1` 表示在最高推理速度 90% 以上的 worker 视为同一速度档，再按成本择优。

## 4. CORS 配置

- `cors_allow_origins`（默认：空字符串）
  - 逗号分隔来源白名单，例如：
    - `http://localhost:5173,https://your.domain.com`
  - 为空时不添加 CORS 中间件。

- `cors_allow_credentials`（默认：`False`）
  - 是否允许跨域携带凭据（cookies/authorization 等）。

## 5. 集群开关与节点标识

- `cluster_enabled`（默认：`False`）
  - 是否启用集群同步与请求转发。

- `cluster_node_id`（默认：`node-local`）
  - 当前节点唯一 ID。

- `cluster_self_url`（默认：`http://127.0.0.1:8000`）
  - 当前节点对外可访问地址。

- `cluster_seed_urls`（默认：空字符串）
  - 种子节点 URL，逗号分隔。
  - 启动后同步任务会将其写入邻居候选。

## 6. Gossip 与探活参数

- `cluster_neighbor_count`（默认：`3`）
  - 每轮探活时选择的邻居数量。

- `cluster_gossip_fanout`（默认：`2`）
  - 每轮 gossip 发送目标数量。

- `cluster_gossip_interval_sec`（默认：`3`）
  - cluster 同步任务调度周期（秒）。

- `cluster_gossip_timeout_sec`（默认：`2.5`）
  - gossip HTTP 调用超时（秒）。

- `cluster_probe_timeout_sec`（默认：`1.5`）
  - ping 探活请求超时（秒）。

- `cluster_delta_batch_size`（默认：`200`）
  - 单次 gossip 发送的最大增量条数。

## 7. 集群请求转发参数

- `cluster_request_forward_after_sec`（默认：`2.0`）
  - 本地有候选 worker 时，先本地等待该时长后再尝试转发。
  - 本地完全无模型时可立即转发。

- `cluster_request_forward_timeout_sec`（默认：`20.0`）
  - 转发到远端节点时的 HTTP 超时。

- `cluster_request_max_hops`（默认：`2`）
  - 最大转发跳数，防止无限传递。

- `cluster_request_max_candidates`（默认：`3`）
  - 单次最多尝试转发到多少候选节点。

## 8. 推荐配置模板

### 8.1 单机最小配置

```env
DLLM_SERVER_DB_URL=sqlite:///./server.db
DLLM_SERVER_API_KEYS_BOOTSTRAP=sk-local-test
```

### 8.2 生产建议（带内部鉴权）

```env
DLLM_SERVER_DB_URL=postgresql+psycopg://user:pass@db-host:5432/dllm
DLLM_SERVER_API_KEYS_BOOTSTRAP=sk-prod-a,sk-prod-b
DLLM_SERVER_INTERNAL_TOKEN=replace-with-strong-random-token
DLLM_SERVER_HEARTBEAT_TIMEOUT_SEC=90
DLLM_SERVER_CLEANUP_INTERVAL_SEC=15
DLLM_SERVER_REQUEST_TIMEOUT_SEC=300
DLLM_SERVER_JOB_MAX_WAIT_SEC=300
DLLM_SERVER_CORS_ALLOW_ORIGINS=https://console.example.com
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=true
```

### 8.3 集群节点示例

```env
DLLM_SERVER_CLUSTER_ENABLED=true
DLLM_SERVER_CLUSTER_NODE_ID=node-a
DLLM_SERVER_CLUSTER_SELF_URL=http://10.0.0.11:8000
DLLM_SERVER_CLUSTER_SEED_URLS=http://10.0.0.12:8000,http://10.0.0.13:8000
DLLM_SERVER_CLUSTER_NEIGHBOR_COUNT=3
DLLM_SERVER_CLUSTER_GOSSIP_FANOUT=2
DLLM_SERVER_CLUSTER_GOSSIP_INTERVAL_SEC=3
DLLM_SERVER_CLUSTER_PROBE_TIMEOUT_SEC=1.5
DLLM_SERVER_CLUSTER_GOSSIP_TIMEOUT_SEC=2.5
DLLM_SERVER_CLUSTER_REQUEST_MAX_HOPS=2
DLLM_SERVER_CLUSTER_REQUEST_MAX_CANDIDATES=3
```

## 9. 变量命名映射规则

`ServerSettings` 字段名转环境变量规则：
- 字段：`cluster_request_max_hops`
- 环境变量：`DLLM_SERVER_CLUSTER_REQUEST_MAX_HOPS`

布尔值可使用：`true/false`、`1/0`（由 pydantic 解析）。
