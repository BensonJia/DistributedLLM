<script setup lang="ts">
import { computed } from "vue";
import { useWorkersStore } from "@/stores/workers";
import { fmtCost } from "@/utils/format";
import { formatIso, formatRelTime } from "@/utils/time";
import { useUiStore } from "@/stores/ui";

const store = useWorkersStore();
const ui = useUiStore();
const w = computed(() => store.selected);

function chipClass(){
  if (!w.value) return "chip dot";
  if (w.value.status === "offline") return "chip dot err";
  if (w.value.work_state === "busy") return "chip dot warn";
  return "chip dot ok";
}
function chipText(){
  if (!w.value) return "—";
  if (w.value.status === "offline") return "Offline";
  if (w.value.work_state === "busy") return "Online · Busy";
  return "Online · Idle";
}
function copy(text: string){
  navigator.clipboard?.writeText(text);
  ui.toast("已复制");
}
</script>

<template>
  <section class="card pad">
    <div v-if="!w" class="skeleton" style="height: 220px;"></div>

    <template v-else>
      <div class="head">
        <div class="h">
          <div class="mono">{{ w.worker_id }}</div>
          <button class="mini" @click="copy(w.worker_id)">复制</button>
        </div>
        <div class="sub">
          <span :class="chipClass()">{{ chipText() }}</span>
          <span class="muted" :title="formatIso(w.last_heartbeat)">
            last hb: {{ formatRelTime(w.last_heartbeat) }}
          </span>
        </div>
      </div>

      <div class="grid">
        <div class="card pad soft">
          <div class="k">工作状态</div>
          <div class="v">{{ w.work_state }}</div>
          <div class="k">在线状态</div>
          <div class="v">{{ w.status }}</div>
          <div class="k">当前任务</div>
          <div class="v mono">{{ w.work_state==='busy' ? (w.current_job_id || '—') : '—' }}</div>
        </div>

        <div class="card pad soft">
          <div class="k">模型与价格</div>
          <table class="table" v-if="w.models?.length">
            <thead>
              <tr><th>模型</th><th>cost_per_token</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in [...w.models].sort((a,b)=>a.cost_per_token-b.cost_per_token)" :key="m.name">
                <td class="mono">{{ m.name }}</td>
                <td class="mono">{{ fmtCost(m.cost_per_token) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted">暂无模型信息</div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.head{ display:flex; flex-direction:column; gap: 8px; margin-bottom: 12px; }
.h{ display:flex; align-items:center; justify-content:space-between; gap: 10px; }
.sub{ display:flex; align-items:center; gap: 10px; flex-wrap: wrap; }
.muted{ color: rgba(0,0,0,.62); font-size: 12px; }
.grid{ display:grid; grid-template-columns: 320px 1fr; gap: 12px; }
.soft{ background: var(--md-sys-color-surface-variant); border: 1px solid rgba(0,0,0,.06); box-shadow: none; }
.k{ font-size: 12px; color: rgba(0,0,0,.62); margin-top: 8px; font-weight: 700; }
.v{ font-weight: 700; margin-top: 2px; }
.mini{
  border: 1px solid rgba(0,0,0,.10);
  background: #fff;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
}
@media (max-width: 980px){
  .grid{ grid-template-columns: 1fr; }
}
</style>
