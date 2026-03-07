<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useClustersStore } from "@/stores/clusters";
import { useUiStore } from "@/stores/ui";
import { formatIso, formatRelTime } from "@/utils/time";
import type { ClusterNode } from "@/types";

const store = useClustersStore();
const ui = useUiStore();

let timer: number | undefined;
let ticking = false;

async function tick(){
  if (ticking) return;
  ticking = true;
  try{
    await store.refreshList(store.loadedOnce);
  }finally{
    ticking = false;
  }
}

onMounted(async () => {
  await tick();
  timer = window.setInterval(() => {
    if (ui.autoRefresh) tick();
  }, 3000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});

const sortedNodes = computed(() => {
  return [...store.nodes].sort((a, b) => a.node_id.localeCompare(b.node_id));
});

const selfNode = computed(() => sortedNodes.value.find(n => n.is_self) || null);
const remoteNodes = computed(() => sortedNodes.value.filter(n => !n.is_self));
const aliveCount = computed(() => remoteNodes.value.filter(n => n.is_alive).length);

const graph = computed(() => {
  const width = 980;
  const height = 460;
  const cx = width / 2;
  const cy = height / 2;
  const ring = Math.min(width, height) * 0.36;
  const nodes = [...remoteNodes.value];
  const n = nodes.length;

  const points = nodes.map((node, i) => {
    const angle = (Math.PI * 2 * i) / Math.max(1, n) - Math.PI / 2;
    return {
      node,
      x: cx + ring * Math.cos(angle),
      y: cy + ring * Math.sin(angle),
      shortId: shortNode(node.node_id)
    };
  });

  return { width, height, cx, cy, points };
});

function shortNode(id: string): string{
  if (!id) return "";
  if (id.length <= 16) return id;
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
}

function statusText(node: ClusterNode): string{
  return node.is_alive ? "alive" : "offline";
}

function latencyText(node: ClusterNode): string{
  if (!node.is_alive) return "—";
  if (node.latency_ms == null) return "unknown";
  return `${node.latency_ms} ms`;
}
</script>

<template>
  <div class="col">
    <section class="card pad">
      <div class="head">
        <div>
          <div class="title">Cluster Topology</div>
          <div class="sub">当前节点与所有已发现服务器节点连接关系</div>
        </div>
        <div class="stats">
          <span class="chip dot" :class="{ 'updated-flash': store.summaryUpdated }">total {{ remoteNodes.length }}</span>
          <span class="chip dot ok" :class="{ 'updated-flash': store.summaryUpdated }">alive {{ aliveCount }}</span>
          <span class="chip dot err" :class="{ 'updated-flash': store.summaryUpdated }">offline {{ remoteNodes.length - aliveCount }}</span>
        </div>
      </div>

      <div v-if="store.loading" class="skeleton" style="height: 360px;"></div>

      <div v-else-if="!selfNode" class="empty">
        当前节点尚未出现在 `/admin/cluster/nodes` 列表，请确认 `cluster_enabled=true` 且完成一次同步。
      </div>

      <div v-else-if="remoteNodes.length === 0" class="empty">
        暂无可展示的远端节点。
      </div>

      <div v-else class="graph-wrap">
        <svg :viewBox="`0 0 ${graph.width} ${graph.height}`" class="graph" role="img" aria-label="cluster topology graph">
          <line
            v-for="p in graph.points"
            :key="`line-${p.node.node_id}`"
            :x1="graph.cx"
            :y1="graph.cy"
            :x2="p.x"
            :y2="p.y"
            :class="['edge', p.node.is_alive ? 'alive' : 'offline']"
          />

          <circle class="node self" :cx="graph.cx" :cy="graph.cy" r="36" />
          <text class="label self" :x="graph.cx" :y="graph.cy - 2" text-anchor="middle">SELF</text>
          <text class="label sub" :x="graph.cx" :y="graph.cy + 16" text-anchor="middle">{{ shortNode(selfNode.node_id) }}</text>

          <g v-for="p in graph.points" :key="p.node.node_id">
            <circle :class="['node', p.node.is_alive ? 'alive' : 'offline', store.updatedNodeIds[p.node.node_id] ? 'updated-flash' : '']" :cx="p.x" :cy="p.y" r="24" />
            <text class="label" :x="p.x" :y="p.y - 34" text-anchor="middle">{{ p.shortId }}</text>
            <text class="label sub" :x="p.x" :y="p.y + 5" text-anchor="middle">{{ p.node.is_alive ? "UP" : "DOWN" }}</text>
          </g>
        </svg>
      </div>

      <div v-if="store.error" class="foot">
        <span class="chip dot err">Error</span>
        <span class="muted">{{ store.error }}</span>
      </div>
    </section>

    <section class="card pad">
      <div class="title">Nodes</div>
      <div class="sub">节点详情</div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>node_id</th>
              <th>status</th>
              <th>base_url</th>
              <th>latency</th>
              <th>workers</th>
              <th>models</th>
              <th>last_seen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in sortedNodes" :key="n.node_id" :class="{ 'updated-flash': store.updatedNodeIds[n.node_id] }">
              <td class="mono">{{ n.node_id }}</td>
              <td>
                <span :class="['chip dot', n.is_alive ? 'ok' : 'err']">
                  {{ n.is_self ? "self" : statusText(n) }}
                </span>
              </td>
              <td class="mono">{{ n.base_url }}</td>
              <td class="mono">{{ latencyText(n) }}</td>
              <td class="mono">{{ n.idle_workers }} / {{ n.busy_workers }}</td>
              <td>{{ (n.models || []).join(", ") || "—" }}</td>
              <td :title="formatIso(n.last_seen_at || undefined)">{{ formatRelTime(n.last_seen_at || undefined) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.col{
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.head{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.title{ font-weight: 800; }
.sub{ font-size: 12px; color: rgba(0,0,0,.62); margin-top: 3px; }
.stats{ display: flex; flex-wrap: wrap; gap: 8px; }
.foot{
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.muted{ color: rgba(0,0,0,.62); font-size: 12px; }
.empty{
  border: 1px dashed rgba(0,0,0,.16);
  border-radius: 12px;
  padding: 18px;
  color: rgba(0,0,0,.72);
  background: rgba(0,0,0,.02);
}
.graph-wrap{
  border: 1px solid rgba(0,0,0,.06);
  border-radius: 14px;
  overflow: hidden;
  background:
    radial-gradient(circle at center, rgba(103,80,164,.08), transparent 55%),
    linear-gradient(180deg, #fcfbff, #ffffff);
}
.graph{
  width: 100%;
  height: 460px;
  display: block;
}
.edge{
  stroke-width: 2;
}
.edge.alive{
  stroke: rgba(26,127,55,.6);
}
.edge.offline{
  stroke: rgba(179,38,30,.45);
  stroke-dasharray: 6 6;
}
.node{
  stroke-width: 2;
}
.node.self{
  fill: rgba(103,80,164,.18);
  stroke: rgba(103,80,164,.65);
}
.node.alive{
  fill: rgba(26,127,55,.16);
  stroke: rgba(26,127,55,.7);
}
.node.offline{
  fill: rgba(179,38,30,.12);
  stroke: rgba(179,38,30,.7);
}
.label{
  font-size: 12px;
  fill: rgba(0,0,0,.78);
  font-weight: 700;
}
.label.self{
  font-size: 13px;
  fill: rgba(0,0,0,.86);
}
.label.sub{
  font-size: 11px;
  fill: rgba(0,0,0,.6);
  font-weight: 600;
}
.table-wrap{
  margin-top: 10px;
  overflow-x: auto;
}
</style>
