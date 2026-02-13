import { defineStore } from "pinia";
import type { JobDetail, JobSummary } from "@/types";
import { api } from "@/services/api";

export const useJobsStore = defineStore("jobs", {
  state: () => ({
    loading: false,
    jobs: [] as JobSummary[],
    selectedId: "" as string,
    selected: null as JobDetail | null,
    error: "" as string
  }),
  actions: {
    async refreshList(){
      this.loading = true;
      this.error = "";
      try{
        this.jobs = await api.listJobs();
      }catch(e: any){
        this.error = String(e?.message || e);
        this.jobs = [];
      }finally{
        this.loading = false;
      }
    },
    async select(job_id: string){
      this.selectedId = job_id;
      this.selected = null;
      try{
        this.selected = await api.getJob(job_id);
      }catch(e: any){
        this.error = String(e?.message || e);
      }
    }
  }
});
