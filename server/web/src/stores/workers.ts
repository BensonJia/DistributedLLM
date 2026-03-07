import { defineStore } from "pinia";
import type { WorkerDetail, WorkerSummary } from "@/types";
import { api } from "@/services/api";

function sameWorkerSummary(a: WorkerSummary, b: WorkerSummary): boolean{
  return (
    a.worker_id === b.worker_id &&
    a.status === b.status &&
    a.work_state === b.work_state &&
    (a.current_job_id ?? null) === (b.current_job_id ?? null) &&
    (a.last_heartbeat ?? "") === (b.last_heartbeat ?? "")
  );
}

function normalizeModels(models: WorkerDetail["models"]): WorkerDetail["models"]{
  return [...(models || [])]
    .map(m => ({
      name: m.name,
      cost_per_token: Number(m.cost_per_token),
      avg_power_watts: m.avg_power_watts ?? null,
      speed_tps: m.speed_tps ?? null
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function sameWorkerDetail(a: WorkerDetail, b: WorkerDetail): boolean{
  if (!sameWorkerSummary(a, b)) return false;
  return JSON.stringify(normalizeModels(a.models)) === JSON.stringify(normalizeModels(b.models));
}

function sameWorkerModels(a: WorkerDetail, b: WorkerDetail): boolean{
  return JSON.stringify(normalizeModels(a.models)) === JSON.stringify(normalizeModels(b.models));
}

export const useWorkersStore = defineStore("workers", {
  state: () => ({
    loading: false,
    loadedOnce: false,
    workers: [] as WorkerSummary[],
    selectedId: "" as string,
    selected: null as WorkerDetail | null,
    error: "" as string,
    updatedWorkerIds: {} as Record<string, boolean>,
    updatedWorkerTimers: {} as Record<string, number>,
    selectedMetaUpdated: false,
    selectedModelsUpdated: false,
    selectedMetaTimer: 0 as number,
    selectedModelsTimer: 0 as number
  }),
  actions: {
    markWorkerUpdated(workerId: string, durationMs = 1300){
      const prevTimer = this.updatedWorkerTimers[workerId];
      if (prevTimer) window.clearTimeout(prevTimer);
      this.updatedWorkerIds = { ...this.updatedWorkerIds, [workerId]: true };
      const timer = window.setTimeout(() => {
        const next = { ...this.updatedWorkerIds };
        delete next[workerId];
        this.updatedWorkerIds = next;
        const timers = { ...this.updatedWorkerTimers };
        delete timers[workerId];
        this.updatedWorkerTimers = timers;
      }, durationMs);
      this.updatedWorkerTimers = { ...this.updatedWorkerTimers, [workerId]: timer };
    },
    markSelectedMetaUpdated(durationMs = 1300){
      if (this.selectedMetaTimer) window.clearTimeout(this.selectedMetaTimer);
      this.selectedMetaUpdated = true;
      this.selectedMetaTimer = window.setTimeout(() => {
        this.selectedMetaUpdated = false;
        this.selectedMetaTimer = 0;
      }, durationMs);
    },
    markSelectedModelsUpdated(durationMs = 1300){
      if (this.selectedModelsTimer) window.clearTimeout(this.selectedModelsTimer);
      this.selectedModelsUpdated = true;
      this.selectedModelsTimer = window.setTimeout(() => {
        this.selectedModelsUpdated = false;
        this.selectedModelsTimer = 0;
      }, durationMs);
    },
    async refreshList(background = false){
      if (!background) this.loading = true;
      if (!background) this.error = "";
      try{
        const incoming = await api.listWorkers();
        const existingMap = new Map(this.workers.map(w => [w.worker_id, w]));
        const nextWorkers = incoming.map((w) => {
          const existing = existingMap.get(w.worker_id);
          if (existing && sameWorkerSummary(existing, w)) return existing;
          if (this.loadedOnce) this.markWorkerUpdated(w.worker_id);
          return w;
        });

        const prevIds = new Set(this.workers.map(w => w.worker_id));
        for (const w of incoming) prevIds.delete(w.worker_id);
        for (const removed of prevIds){
          const next = { ...this.updatedWorkerIds };
          delete next[removed];
          this.updatedWorkerIds = next;
        }

        this.workers = nextWorkers;
        if (this.selectedId && !nextWorkers.some(w => w.worker_id === this.selectedId)){
          this.selectedId = "";
          this.selected = null;
        }
        this.loadedOnce = true;
      }catch(e: any){
        this.error = String(e?.message || e);
        if (!background) this.workers = [];
      }finally{
        if (!background) this.loading = false;
      }
    },
    async select(worker_id: string){
      this.selectedId = worker_id;
      this.selected = null;
      await this.refreshSelected(false);
    },
    async refreshSelected(background = true){
      if (!this.selectedId) return;
      try{
        const incoming = await api.getWorker(this.selectedId);
        if (!this.selected){
          this.selected = incoming;
          this.markSelectedMetaUpdated();
          this.markSelectedModelsUpdated();
          return;
        }

        if (!sameWorkerDetail(this.selected, incoming)){
          if (!sameWorkerSummary(this.selected, incoming)) this.markSelectedMetaUpdated();
          if (!sameWorkerModels(this.selected, incoming)) this.markSelectedModelsUpdated();
          this.selected = incoming;
        }
      }catch(e: any){
        this.error = String(e?.message || e);
        if (!background) this.selected = null;
      }
    }
  }
});
