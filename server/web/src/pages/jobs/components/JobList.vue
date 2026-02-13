<script setup lang="ts">
import { computed, ref } from "vue";
import { useJobsStore } from "@/stores/jobs";
import { useUiStore } from "@/stores/ui";
import { shortId } from "@/utils/format";
import { formatRelTime, formatIso } from "@/utils/time";
import type { JobSummary } from "@/types";

const store = useJobsStore();
const ui = useUiStore();

const q = ref("");
const filter = ref<"all"|"pending"|"running"|"done"|"failed">("all");

const sortedFiltered = computed(() => {
  const arr = [...store.jobs];
  arr.sort((a,b) => {
    const ta = a.created_at ? Date.parse(a.created_at) : 0;
    const tb = b.created_at ? Date.parse(b.created_at) : 0;
    return tb - ta;
  });
  const qq = q.value.trim().toLowerCase();
  return arr.filter((j) => {
    if (filter.value !== "all" && j.status !== filter.value) return false;
    if (qq && !j.job_id.toLowerCase().includes(qq)) return false;
    return true;
  });
});

function chipClass(j: JobSummary){
  if (j.status === "failed") return "chip dot err";
  if (j.status === "running") return "chip dot warn";
  if (j.status === "pending") return "chip dot";
  return "chip dot ok";
}

function select(j: JobSummary){
  store.select(j.job_id);
  ui.toast(`已选择任务 ${shortId(j.job_id)}`);
}

function copy(text: string){
  navigator.clipboard?.writeText(text);
  ui.toast("已复制");
}
</script>

<template>
  <section class="card">
    <div class="head">
      <div class="title">Jobs</div>
      <div class="sub">按创建时间倒序</div>
    </div>

    <div class="filters">
      <input class="input" v-model="q" placeholder="搜索 job_id…" />
      <div class="seg">
        <button class="seg-btn" :class="{active: filter==='all'}" @click="filter='all'">All</button>
        <button class="seg-btn" :class="{active: filter==='pending'}" @click="filter='pending'">Pending</button>
        <button class="seg-btn" :class="{active: filter==='running'}" @click="filter='running'">Running</button>
        <button class="seg-btn" :class="{active: filter==='done'}" @click="filter='done'">Done</button>
        <button class="seg-btn" :class="{active: filter==='failed'}" @click="filter='failed'">Failed</button>
      </div>
    </div>

    <div v-if="store.loading" class="list pad">
      <div class="row skeleton" style="height:66px;"></div>
      <div class="row skeleton" style="height:66px;"></div>
      <div class="row skeleton" style="height:66px;"></div>
    </div>

    <div v-else class="list">
      <button v-for="j in sortedFiltered" :key="j.job_id" class="row" :class="{active: j.job_id===store.selectedId}" @click="select(j)">
        <div class="top">
          <div class="mono id" :title="j.job_id">{{ shortId(j.job_id) }}</div>
          <span :class="chipClass(j)">{{ j.status }}</span>
        </div>
        <div class="mid">
          <div class="mono">{{ j.model }}</div>
          <div class="muted">worker: <span class="mono">{{ shortId(j.assigned_worker_id) }}</span></div>
        </div>
        <div class="bottom">
          <div class="muted" :title="formatIso(j.created_at)">
            created: {{ formatRelTime(j.created_at) }}
          </div>
          <button class="mini" @click.stop="copy(j.job_id)">复制</button>
        </div>
      </button>

      <div v-if="sortedFiltered.length===0" class="pad muted">无匹配任务</div>
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
.mid{ display:flex; align-items:center; justify-content:space-between; gap: 10px; margin-top: 8px; }
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
