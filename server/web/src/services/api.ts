import { USE_MOCK } from "./env";
import { httpJson } from "./http";
import type { WorkerDetail, WorkerSummary, JobDetail, JobSummary, ClusterNode } from "@/types";

type WorkersResp = { workers: WorkerDetail[] };
type JobsResp = { jobs: JobDetail[] };
type ClusterNodesResp = { nodes: ClusterNode[] };

async function mockJson<T>(path: string): Promise<T>{
  const res = await fetch(path);
  if (!res.ok) throw new Error(`mock fetch failed: ${path}`);
  return await res.json() as T;
}

export const api = {
  async health(): Promise<{ok: boolean}>{
    if (USE_MOCK) return { ok: true };
    return await httpJson<{ok:boolean}>("/health", { method: "GET" });
  },

  async listWorkers(): Promise<WorkerSummary[]>{
    if (USE_MOCK){
      const data = await mockJson<WorkersResp>("/mock/workers.json");
      return data.workers.map(w => ({
        worker_id: w.worker_id,
        status: w.status,
        work_state: w.work_state,
        current_job_id: w.current_job_id ?? null,
        last_heartbeat: w.last_heartbeat
      }));
    }
    return await httpJson<WorkerSummary[]>("/admin/workers", { method: "GET" });
  },

  async getWorker(worker_id: string): Promise<WorkerDetail>{
    if (USE_MOCK){
      const data = await mockJson<WorkersResp>("/mock/workers.json");
      const found = data.workers.find(w => w.worker_id === worker_id);
      if (!found) throw new Error("worker not found in mock");
      return found;
    }
    return await httpJson<WorkerDetail>(`/admin/workers/${encodeURIComponent(worker_id)}`, { method: "GET" });
  },

  async listJobs(): Promise<JobSummary[]>{
    if (USE_MOCK){
      const data = await mockJson<JobsResp>("/mock/jobs.json");
      return data.jobs.map(j => ({
        job_id: j.job_id,
        status: j.status,
        model: j.model,
        assigned_worker_id: j.assigned_worker_id,
        created_at: j.created_at,
        updated_at: j.updated_at
      }));
    }
    return await httpJson<JobSummary[]>("/admin/jobs", { method: "GET" });
  },

  async getJob(job_id: string): Promise<JobDetail>{
    if (USE_MOCK){
      const data = await mockJson<JobsResp>("/mock/jobs.json");
      const found = data.jobs.find(j => j.job_id === job_id);
      if (!found) throw new Error("job not found in mock");
      return found;
    }
    return await httpJson<JobDetail>(`/admin/jobs/${encodeURIComponent(job_id)}`, { method: "GET" });
  },

  async listClusterNodes(): Promise<ClusterNode[]>{
    if (USE_MOCK){
      const data = await mockJson<ClusterNodesResp>("/mock/cluster_nodes.json");
      return data.nodes;
    }
    return await httpJson<ClusterNode[]>("/admin/cluster/nodes", { method: "GET" });
  }
};
