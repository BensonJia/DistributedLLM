import { defineStore } from "pinia";
import type { JobDetail, JobSummary } from "@/types";
import { api } from "@/services/api";

function normalizeJobSummary(j: JobSummary){
  return {
    job_id: j.job_id,
    source: j.source,
    status: j.status,
    model: j.model,
    assigned_worker_id: j.assigned_worker_id ?? null,
    created_at: j.created_at ?? "",
    updated_at: j.updated_at ?? ""
  };
}

function sameJobSummary(a: JobSummary, b: JobSummary): boolean{
  return JSON.stringify(normalizeJobSummary(a)) === JSON.stringify(normalizeJobSummary(b));
}

function normalizeJobDetail(j: JobDetail){
  return {
    ...normalizeJobSummary(j),
    error: j.error ?? null,
    result: {
      output_text: j.result?.output_text ?? "",
      prompt_tokens: j.result?.prompt_tokens ?? 0,
      completion_tokens: j.result?.completion_tokens ?? 0,
      total_tokens: j.result?.total_tokens ?? 0,
      avg_power_watts: j.result?.avg_power_watts ?? null
    }
  };
}

function sameJobDetail(a: JobDetail, b: JobDetail): boolean{
  return JSON.stringify(normalizeJobDetail(a)) === JSON.stringify(normalizeJobDetail(b));
}

function sameJobResult(a: JobDetail, b: JobDetail): boolean{
  return JSON.stringify(normalizeJobDetail(a).result) === JSON.stringify(normalizeJobDetail(b).result);
}

export const useJobsStore = defineStore("jobs", {
  state: () => ({
    loading: false,
    loadedOnce: false,
    jobs: [] as JobSummary[],
    selectedId: "" as string,
    selected: null as JobDetail | null,
    error: "" as string,
    updatedJobIds: {} as Record<string, boolean>,
    updatedJobTimers: {} as Record<string, number>,
    selectedMetaUpdated: false,
    selectedResultUpdated: false,
    selectedMetaTimer: 0 as number,
    selectedResultTimer: 0 as number
  }),
  actions: {
    markJobUpdated(jobId: string, durationMs = 1300){
      const prevTimer = this.updatedJobTimers[jobId];
      if (prevTimer) window.clearTimeout(prevTimer);
      this.updatedJobIds = { ...this.updatedJobIds, [jobId]: true };
      const timer = window.setTimeout(() => {
        const next = { ...this.updatedJobIds };
        delete next[jobId];
        this.updatedJobIds = next;
        const timers = { ...this.updatedJobTimers };
        delete timers[jobId];
        this.updatedJobTimers = timers;
      }, durationMs);
      this.updatedJobTimers = { ...this.updatedJobTimers, [jobId]: timer };
    },
    markSelectedMetaUpdated(durationMs = 1300){
      if (this.selectedMetaTimer) window.clearTimeout(this.selectedMetaTimer);
      this.selectedMetaUpdated = true;
      this.selectedMetaTimer = window.setTimeout(() => {
        this.selectedMetaUpdated = false;
        this.selectedMetaTimer = 0;
      }, durationMs);
    },
    markSelectedResultUpdated(durationMs = 1300){
      if (this.selectedResultTimer) window.clearTimeout(this.selectedResultTimer);
      this.selectedResultUpdated = true;
      this.selectedResultTimer = window.setTimeout(() => {
        this.selectedResultUpdated = false;
        this.selectedResultTimer = 0;
      }, durationMs);
    },
    async refreshList(background = false){
      if (!background) this.loading = true;
      if (!background) this.error = "";
      try{
        const [jobs, awaiting] = await Promise.all([api.listJobs(), api.listAwaitingRequests()]);
        const incoming = [...awaiting, ...jobs];
        const existingMap = new Map(this.jobs.map(j => [j.job_id, j]));
        const nextJobs = incoming.map((j) => {
          const existing = existingMap.get(j.job_id);
          if (existing && sameJobSummary(existing, j)) return existing;
          if (this.loadedOnce) this.markJobUpdated(j.job_id);
          return j;
        });

        const prevIds = new Set(this.jobs.map(j => j.job_id));
        for (const j of incoming) prevIds.delete(j.job_id);
        for (const removed of prevIds){
          const next = { ...this.updatedJobIds };
          delete next[removed];
          this.updatedJobIds = next;
        }

        this.jobs = nextJobs;
        if (this.selectedId && !nextJobs.some(j => j.job_id === this.selectedId)){
          this.selectedId = "";
          this.selected = null;
        }
        this.loadedOnce = true;
      }catch(e: any){
        this.error = String(e?.message || e);
        if (!background) this.jobs = [];
      }finally{
        if (!background) this.loading = false;
      }
    },
    async select(job_id: string){
      this.selectedId = job_id;
      this.selected = null;
      await this.refreshSelected(false);
    },
    async refreshSelected(background = true){
      if (!this.selectedId) return;
      try{
        const selectedSummary = this.jobs.find((j) => j.job_id === this.selectedId);
        const incoming = selectedSummary?.source === "awaiting"
          ? await api.getAwaitingRequest(this.selectedId)
          : await api.getJob(this.selectedId);
        if (!this.selected){
          this.selected = incoming;
          this.markSelectedMetaUpdated();
          this.markSelectedResultUpdated();
          return;
        }

        if (!sameJobDetail(this.selected, incoming)){
          if (!sameJobSummary(this.selected, incoming) || (this.selected.error ?? null) !== (incoming.error ?? null)){
            this.markSelectedMetaUpdated();
          }
          if (!sameJobResult(this.selected, incoming)) this.markSelectedResultUpdated();
          this.selected = incoming;
        }
      }catch(e: any){
        this.error = String(e?.message || e);
        if (!background) this.selected = null;
      }
    }
  }
});
