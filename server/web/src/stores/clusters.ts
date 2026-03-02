import { defineStore } from "pinia";
import type { ClusterNode } from "@/types";
import { api } from "@/services/api";

export const useClustersStore = defineStore("clusters", {
  state: () => ({
    loading: false,
    nodes: [] as ClusterNode[],
    error: "" as string
  }),
  actions: {
    async refreshList(){
      this.loading = true;
      this.error = "";
      try{
        this.nodes = await api.listClusterNodes();
      }catch(e: any){
        this.error = String(e?.message || e);
        this.nodes = [];
      }finally{
        this.loading = false;
      }
    }
  }
});
