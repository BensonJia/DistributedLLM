export type WorkerOnlineStatus = "online" | "offline";
export type WorkerWorkState = "idle" | "busy";

export interface WorkerModelInfo {
  name: string;
  cost_per_token: number;
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
}

export interface JobDetail extends JobSummary {
  result?: JobResult | null;
  error?: string | null;
}
