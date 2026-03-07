<script setup lang="ts">
import { computed, ref } from "vue";
import { useWorkersStore } from "@/stores/workers";
import { useUiStore } from "@/stores/ui";
import { shortId } from "@/utils/format";
import { formatRelTime, formatIso } from "@/utils/time";
import type { WorkerSummary } from "@/types";

const store = useWorkersStore();
const ui = useUiStore();

const q = ref("");
const filter = ref<"all"|"online"|"busy"|"offline">("all");

const sortedFiltered = computed(() => {
  const arr = [...store.workers];
  // 按 worker_id 排序（用户要求）
  arr.sort((a,b) => a.worker_id.localeCompare(b.worker_id));

  const qq = q.value.trim().toLowerCase();
  return arr.filter((w) => {
    if (filter.value === "online" && w.status !== "online") return false;
    if (filter.value === "offline" && w.status !== "offline") return false;
    if (filter.value === "busy" && w.work_state !== "busy") return false;
    if (qq && !w.worker_id.toLowerCase().includes(qq)) return false;
    return true;
  });
});

function chipClass(w: WorkerSummary){
  if (w.status === "offline") return "chip dot err";
  if (w.work_state === "busy") return "chip dot warn";
  return "chip dot ok";
}
function chipText(w: WorkerSummary){
  if (w.status === "offline") return "Offline";
  if (w.work_state === "busy") return "Online · Busy";
  return "Online · Idle";
}

async function select(w: WorkerSummary){
  await store.select(w.worker_id);
  ui.toast(`已选择 Worker ${shortId(w.worker_id)}`);
}

function copy(text: string){
  navigator.clipboard?.writeText(text);
  ui.toast("已复制");
}
</script>

<template>
  <section class="card">
    <div class="head">
      <div class="title">Workers</div>
      <div class="sub">按 worker_id 排序</div>
    </div>

    <div class="filters">
      <input class="input" v-model="q" placeholder="搜索 worker_id…" />
      <div class="seg">
        <button class="seg-btn" :class="{active: filter==='all'}" @click="filter='all'">All</button>
        <button class="seg-btn" :class="{active: filter==='online'}" @click="filter='online'">Online</button>
        <button class="seg-btn" :class="{active: filter==='busy'}" @click="filter='busy'">Busy</button>
        <button class="seg-btn" :class="{active: filter==='offline'}" @click="filter='offline'">Offline</button>
      </div>
    </div>

    <div v-if="store.loading" class="list pad">
      <div class="row skeleton" style="height:58px;"></div>
      <div class="row skeleton" style="height:58px;"></div>
      <div class="row skeleton" style="height:58px;"></div>
    </div>

    <div v-else class="list">
      <button
        v-for="w in sortedFiltered"
        :key="w.worker_id"
        class="row"
        :class="{active: w.worker_id===store.selectedId, 'updated-flash': !!store.updatedWorkerIds[w.worker_id]}"
        @click="select(w)"
      >
        <div class="top">
          <div class="mono id" :title="w.worker_id">{{ shortId(w.worker_id) }}</div>
          <span :class="chipClass(w)">{{ chipText(w) }}</span>
        </div>
        <div class="bottom">
          <div class="muted" :title="formatIso(w.last_heartbeat)">
            last hb: {{ formatRelTime(w.last_heartbeat) }}
          </div>
          <button class="mini" @click.stop="copy(w.worker_id)">复制</button>
        </div>
      </button>

      <div v-if="sortedFiltered.length===0" class="pad muted">无匹配 Worker</div>
    </div>

    <div v-if="store.error" class="foot">
      <span class="chip dot err">Error</span>
      <span class="muted">{{ store.error }}</span>
    </div>
  </section>
</template>

<style scoped>
.head{ padding: 14px 14px 8px; }
.title{ font-weight: 800; }
.sub{ font-size: 12px; color: rgba(0,0,0,.62); margin-top: 3px; }

.filters{ padding: 0 14px 12px; display:flex; flex-direction:column; gap: 10px; }
.seg{ display:flex; gap: 6px; flex-wrap: wrap; }
.seg-btn{
  border: 1px solid rgba(0,0,0,.12);
  background: #fff;
  padding: 8px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color .18s ease, border-color .18s ease;
}
.seg-btn.active{
  background: rgba(103,80,164,.12);
  border-color: rgba(103,80,164,.22);
}

.list{ padding: 6px; display:flex; flex-direction:column; gap: 8px; }
.pad{ padding: 14px; }

.row{
  text-align:left;
  width: 100%;
  border: 1px solid rgba(0,0,0,.08);
  background: #fff;
  border-radius: 14px;
  padding: 10px 10px;
  cursor: pointer;
  transition: transform .08s ease, box-shadow .18s ease, border-color .18s ease;
}
.row:hover{ box-shadow: var(--md-sys-elev-1); }
.row:active{ transform: translateY(1px); }
.row.active{ border-color: rgba(103,80,164,.35); background: rgba(103,80,164,.06); }

.top{ display:flex; align-items:center; justify-content:space-between; gap: 10px; }
.bottom{ display:flex; align-items:center; justify-content:space-between; margin-top: 8px; }
.id{ font-weight: 700; }
.muted{ color: rgba(0,0,0,.62); font-size: 12px; }

.mini{
  border: 1px solid rgba(0,0,0,.10);
  background: #fff;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.foot{ padding: 10px 14px 14px; display:flex; gap: 10px; align-items:center; }
</style>
