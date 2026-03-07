import { defineStore } from "pinia";
import type { ClusterNode } from "@/types";
import { api } from "@/services/api";

function normalizeClusterNode(n: ClusterNode){
  return {
    node_id: n.node_id,
    base_url: n.base_url,
    revision: n.revision,
    is_self: n.is_self,
    is_alive: n.is_alive,
    models: [...(n.models || [])].sort(),
    idle_workers: n.idle_workers,
    busy_workers: n.busy_workers,
    latency_ms: n.latency_ms ?? null,
    last_probe_at: n.last_probe_at ?? null,
    last_seen_at: n.last_seen_at ?? null,
    state_version: n.state_version,
    updated_at: n.updated_at ?? null
  };
}

function sameClusterNode(a: ClusterNode, b: ClusterNode): boolean{
  return JSON.stringify(normalizeClusterNode(a)) === JSON.stringify(normalizeClusterNode(b));
}

function clusterSummary(nodes: ClusterNode[]){
  const remote = nodes.filter(n => !n.is_self);
  const alive = remote.filter(n => n.is_alive).length;
  return `${remote.length}:${alive}`;
}

export const useClustersStore = defineStore("clusters", {
  state: () => ({
    loading: false,
    nodes: [] as ClusterNode[],
    loadedOnce: false,
    error: "" as string,
    updatedNodeIds: {} as Record<string, boolean>,
    updatedNodeTimers: {} as Record<string, number>,
    summaryUpdated: false,
    summaryUpdatedTimer: 0 as number
  }),
  actions: {
    markNodeUpdated(nodeId: string, durationMs = 1300){
      const prevTimer = this.updatedNodeTimers[nodeId];
      if (prevTimer) window.clearTimeout(prevTimer);
      this.updatedNodeIds = { ...this.updatedNodeIds, [nodeId]: true };
      const timer = window.setTimeout(() => {
        const next = { ...this.updatedNodeIds };
        delete next[nodeId];
        this.updatedNodeIds = next;
        const timers = { ...this.updatedNodeTimers };
        delete timers[nodeId];
        this.updatedNodeTimers = timers;
      }, durationMs);
      this.updatedNodeTimers = { ...this.updatedNodeTimers, [nodeId]: timer };
    },
    markSummaryUpdated(durationMs = 1300){
      if (this.summaryUpdatedTimer) window.clearTimeout(this.summaryUpdatedTimer);
      this.summaryUpdated = true;
      this.summaryUpdatedTimer = window.setTimeout(() => {
        this.summaryUpdated = false;
        this.summaryUpdatedTimer = 0;
      }, durationMs);
    },
    async refreshList(background = false){
      if (!background) this.loading = true;
      if (!background) this.error = "";
      try{
        const incoming = await api.listClusterNodes();
        const prevSummary = clusterSummary(this.nodes);
        const existingMap = new Map(this.nodes.map(n => [n.node_id, n]));
        const nextNodes = incoming.map((n) => {
          const existing = existingMap.get(n.node_id);
          if (existing && sameClusterNode(existing, n)) return existing;
          if (this.loadedOnce) this.markNodeUpdated(n.node_id);
          return n;
        });

        const prevIds = new Set(this.nodes.map(n => n.node_id));
        for (const n of incoming) prevIds.delete(n.node_id);
        for (const removed of prevIds){
          const next = { ...this.updatedNodeIds };
          delete next[removed];
          this.updatedNodeIds = next;
        }

        this.nodes = nextNodes;
        if (prevSummary !== clusterSummary(nextNodes)) this.markSummaryUpdated();
        this.loadedOnce = true;
      }catch(e: any){
        this.error = String(e?.message || e);
        if (!background) this.nodes = [];
      }finally{
        if (!background) this.loading = false;
      }
    }
  }
});
