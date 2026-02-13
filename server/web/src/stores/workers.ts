import { defineStore } from "pinia";
import type { WorkerDetail, WorkerSummary } from "@/types";
import { api } from "@/services/api";

export const useWorkersStore = defineStore("workers", {
  state: () => ({
    loading: false,
    workers: [] as WorkerSummary[],
    selectedId: "" as string,
    selected: null as WorkerDetail | null,
    error: "" as string
  }),
  actions: {
    async refreshList(){
      this.loading = true;
      this.error = "";
      try{
        this.workers = await api.listWorkers();
      }catch(e: any){
        this.error = String(e?.message || e);
        this.workers = [];
      }finally{
        this.loading = false;
      }
    },
    async select(worker_id: string){
      this.selectedId = worker_id;
      this.selected = null;
      try{
        this.selected = await api.getWorker(worker_id);
      }catch(e: any){
        this.error = String(e?.message || e);
      }
    }
  }
});
