# Server 端设计文档

本文基于当前代码实现整理（目录 `server/` 与 `shared/`），用于帮助理解服务端模块职责、接口、核心函数与关键变量。

## 1. 总体架构

服务端是一个基于 FastAPI + SQLAlchemy + APScheduler 的调度中枢，职责包括：
- 对外提供 OpenAI 兼容接口。
- 对内接收 worker 心跳、派发任务、回收结果。
- 管理 API Key 与管理台查询接口。
- （可选）启用集群节点间 gossip 同步与请求转发。

关键启动流程（`server/main.py`）：
1. 创建 FastAPI 应用并按配置启用 CORS。
2. `startup` 事件中执行：
   - 初始化数据库表（`init_db`）
   - 初始化 API Key（`api_keys_bootstrap`）
   - 启动后台任务：心跳清理、请求分配、集群同步
3. 挂载 API 路由。

## 2. 模块设计

### 2.1 API 层（`server/api`）

- `openai_compat.py`
  - 对外接口：`/v1/models`、`/v1/chat/completions`
  - 功能：鉴权、请求入队、等待分配、创建 Job、轮询结果、超时/失败处理。
  - 集群开启时，支持将请求转发给候选远端节点。

- `worker_mgmt.py`
  - 对内接口：worker 注册、心跳、拉取任务、上报完成。
  - 功能：维护 worker 在线状态和模型能力；将 Job 状态从 pending/running 推进到 done/failed。

- `admin.py`
  - 管理查询接口：workers/jobs/cluster nodes 列表和详情。
  - 功能：聚合数据库字段并转换为前端易读结构（时间 ISO 化、JSON 解析等）。

- `cluster_internal.py`
  - 集群内接口：`/internal/cluster/ping` 与 `/internal/cluster/gossip`。
  - 功能：节点探活、接收和回传增量拓扑状态。

- `auth_middleware.py`
  - 功能：
    - Bearer Token 解析（`get_bearer_token`）
    - API Key 校验（`require_api_key`）
    - 内部 Token 校验（`require_internal_token`，读取 `X-Worker-Token`）

### 2.2 业务域层

每个域采用 `models.py + repository.py + service.py` 分层：
- model：表结构
- repository：DB 读写/事务
- service：业务编排

#### key_manager（API Key）
- `ApiKey`：存储 key、状态、创建时间。
- `ApiKeyRepository`：按 key 查询、缺失时创建。
- `ApiKeyService`：鉴权验证、启动批量导入。

#### worker_registry（Worker 注册表）
- `Worker`：worker 在线信息、当前任务。
- `WorkerModel`：worker 可用模型与单位 token 成本。
- `WorkerRepository`：
  - upsert worker
  - 批量替换 worker 模型能力
  - 查询候选 worker（在线 + 空闲 + 有目标模型）
  - 标记超时 worker 离线
- `WorkerService`：心跳处理和仓储方法封装。

#### request_queue（待分配请求队列）
- `AwaitingRequest`：待分配请求（pending/assigned）。
- `AwaitingRequestRepository`：创建、查询 pending、行级锁分配 worker、删除。
- `AwaitingRequestService`：服务封装。

#### job_queue（任务队列）
- `Job`：任务状态与 payload/result/error。
- `JobRepository`：
  - 创建任务
  - 原子租约（worker 拉取时将 pending -> running）
  - 完成任务（done/failed）
  - 查询任务
- `JobService`：服务封装。

#### scheduler（调度）
- `selector.py`：`greedy_select` 按最低 `cost_per_token` 选 worker。
- `SchedulerService`：基于 `WorkerRepository.get_candidate_workers` 选 worker。

#### cluster（集群）
- `ClusterNode`：节点元数据、模型能力、存活状态、延迟、状态版本。
- `ClusterNeighborSync`：与邻居同步进度（last_sent_state_version）。
- `ClusterRepository`：节点 upsert、离线标记、延迟更新、delta 导出等。
- `ClusterService`：
  - 汇总本地 worker 能力并刷新 self 节点
  - 应用远端 entry（按 revision 去重）
  - 选择 gossip 邻居与转发候选
  - 列出集群已知模型

### 2.3 基础设施层

- `server/db.py`
  - `Base`：SQLAlchemy DeclarativeBase
  - `make_engine(settings)`：按配置创建引擎（SQLite 加 `check_same_thread=False`）
  - `make_session_factory(engine)`：创建 SessionLocal

- `server/deps.py`
  - 全局 `_engine`、`SessionLocal`
  - `init_db()`：导入 model 并 `create_all`
  - `get_db()`：FastAPI 依赖注入，自动关闭会话

- 后台任务（`server/background`）
  - `heartbeat_timeout_checker.py`
    - 定时将超时未心跳 worker 标记为 offline
- `request_assigner.py`
    - 定时扫描候选请求池并批量分配 worker
  - `cluster_sync.py`
    - cluster 启用后定时探活邻居、发送 gossip、应用回传 deltas

## 3. 接口设计

### 3.1 对外 API

- `GET /v1/models`
  - 鉴权：Bearer API Key
  - 返回：模型列表（本地在线 worker + 可选集群节点模型）

- `POST /v1/chat/completions`
  - 鉴权：Bearer API Key
  - 行为：
    1. 写入 `awaiting_reqs`
    2. 等待 request assigner 分配 worker
    3. 分配成功后创建 `jobs`
    4. 轮询 job 状态并返回 OpenAI 兼容响应
    5. 超时/失败抛出 HTTP 错误
    6. finally 中清理 awaiting request + worker current_job
  - 不支持：`stream=true`

### 3.2 Worker 内部 API

- `POST /internal/worker/register`
  - 返回新 worker_id

- `POST /internal/worker/heartbeat`
  - 更新 worker 在线/任务状态与模型能力

- `POST /internal/job/pull`
  - worker 拉取任务
  - 无任务返回 `204 No Content`

- `POST /internal/job/complete`
  - worker 上报任务完成
  - 更新 job 状态并清理 worker 当前 job

### 3.3 管理 API

- `GET /admin/workers`
- `GET /admin/workers/{worker_id}`
- `GET /admin/jobs`
- `GET /admin/jobs/{job_id}`
- `GET /admin/cluster/nodes`

特点：统一走 API Key 鉴权，响应做了适配（时间、枚举状态、结果字段）。

### 3.4 集群内部 API

- `GET /internal/cluster/ping`
  - 节点存活检测

- `POST /internal/cluster/gossip`
  - 交换 sender 状态 + 增量 entries
  - 返回 receiver 视角下的增量状态

## 4. 核心函数设计

### 4.1 请求处理主链路

`chat_completions`（`server/api/openai_compat.py`）是核心编排函数，关键阶段：
1. 参数与流式检查。
2. 创建 `req_id` 并入 `AwaitingRequest`。
3. 在 `request_timeout_sec` 内轮询是否已分配 worker。
4. 若未分配且可转发：根据 hop/seen node 限制选择候选远端并尝试转发。
5. 分配成功后创建 `job_id`，写 `Job`。
6. 在 `job_max_wait_sec` 内轮询 `Job` 状态并转换为 OpenAI 响应。
7. finally 清理状态，降低脏数据风险。

### 4.2 调度相关

- `SchedulerService.pick_worker(model_name)`
  - 输入候选：在线、空闲、支持模型
  - 选择策略：速度容忍分档后按成本择优

- `AwaitingRequestRepository.assign_worker_to_request`
  - 使用 `with_for_update()` 锁请求行，避免并发重复分配

- `JobRepository.lease_next_for_worker`
  - 使用 SQL `update ... returning` 原子抢占单条 pending job

### 4.3 集群同步

- `start_cluster_sync` 周期任务：
  1. 刷新 self node 状态
  2. 种子节点初始化
  3. 邻居 ping 更新 latency/offline
  4. gossip fanout 发送 deltas
  5. 应用回包 entries 并记录 neighbor sync 游标

- `ClusterService.apply_remote_entry`
  - 按 `revision` 比较，拒绝旧版本更新

## 5. 关键变量作用（按业务语义）

### 5.1 请求与任务标识
- `req_id`：待分配请求唯一标识（`req_...`）。
- `job_id`：实际执行任务唯一标识（`job_...`）。
- `assigned_worker_id`：请求/任务最终绑定的 worker。

### 5.2 状态字段
- `AwaitingRequest.status`：`pending | assigned`
- `Job.status`：`pending | running | done | failed`
- `Worker.status`：`online | offline`
- `Worker.current_job_id`：worker 正在执行的任务（空则 idle）

### 5.3 超时与轮询
- `request_timeout_sec`：等待 request 被分配的最长时长。
- `job_poll_interval_ms`：请求侧轮询间隔。
- `job_max_wait_sec`：等待 job 完成的上限。

### 5.4 集群转发控制
- `X-DLLM-Forward-Hop`：当前转发层级。
- `X-DLLM-Seen-Nodes`：已访问节点集合，防循环。
- `cluster_request_max_hops`：最大转发跳数。
- `cluster_request_max_candidates`：每次最多尝试转发节点数。

## 6. 数据流概览

1. 客户端 -> `/v1/chat/completions`
2. Server 将请求写入 `awaiting_reqs`
3. `request_assigner` 按模型 -> 到达时间顺序批量给请求绑定 worker
4. Server 创建 `jobs`
5. Worker `/internal/job/pull` 拉到任务并执行
6. Worker `/internal/job/complete` 回写结果
7. Server 轮询到 `done/failed` 后返回客户端

## 7. predictor 子目录说明

`server/predictor/` 目前更偏离线训练/推理工具（长度桶模型训练、预测），不直接参与主服务实时调度链路。可作为成本/时延预测能力扩展入口。
