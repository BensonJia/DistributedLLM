export type WorkerOnlineStatus = "online" | "offline";
export type WorkerWorkState = "idle" | "busy";

export interface WorkerModelInfo {
  name: string;
  cost_per_token: number;
  avg_power_watts?: number | null;
  speed_tps?: number;
}

export interface WorkerSummary {
  worker_id: string;
  status: WorkerOnlineStatus;
  work_state: WorkerWorkState;
  current_job_id?: string | null;
  last_heartbeat?: string;
}

export interface WorkerDetail extends WorkerSummary {
  models: WorkerModelInfo[];
}

export type JobStatus = "pending" | "running" | "done" | "failed";

export interface JobSummary {
  job_id: string;
  status: JobStatus;
  model: string;
  assigned_worker_id: string;
  created_at?: string;
  updated_at?: string;
}

export interface JobResult {
  output_text?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  avg_power_watts?: number | null;
}

export interface JobDetail extends JobSummary {
  result?: JobResult | null;
  error?: string | null;
}

export interface ClusterNode {
  node_id: string;
  base_url: string;
  revision: number;
  is_self: boolean;
  is_alive: boolean;
  models: string[];
  idle_workers: number;
  busy_workers: number;
  latency_ms?: number | null;
  last_probe_at?: string | null;
  last_seen_at?: string | null;
  state_version: number;
  updated_at?: string | null;
}
