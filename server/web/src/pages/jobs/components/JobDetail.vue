<script setup lang="ts">
import { computed, ref } from "vue";
import { useJobsStore } from "@/stores/jobs";
import { formatIso } from "@/utils/time";
import { fmtWatts } from "@/utils/format";
import { useUiStore } from "@/stores/ui";

const store = useJobsStore();
const ui = useUiStore();
const j = computed(() => store.selected);
const expanded = ref(true);

function chipClass(){
  if (!j.value) return "chip dot";
  if (j.value.status === "failed") return "chip dot err";
  if (j.value.status === "running") return "chip dot warn";
  if (j.value.status === "pending") return "chip dot";
  return "chip dot ok";
}

function copy(text: string){
  navigator.clipboard?.writeText(text);
  ui.toast("已复制");
}
</script>

<template>
  <section class="card pad">
    <div v-if="!j" class="skeleton" style="height: 240px;"></div>

    <template v-else>
      <div class="head" :class="{ 'updated-flash': store.selectedMetaUpdated }">
        <div class="h">
          <div class="mono">{{ j.job_id }}</div>
          <button class="mini" @click="copy(j.job_id)">复制</button>
        </div>
        <div class="sub">
          <span :class="chipClass()">{{ j.status }}</span>
          <span class="muted">model: <span class="mono">{{ j.model }}</span></span>
          <span class="muted">worker: <span class="mono">{{ j.assigned_worker_id }}</span></span>
        </div>
        <div class="sub muted">
          created: {{ formatIso(j.created_at) }} · updated: {{ formatIso(j.updated_at) }}
        </div>
      </div>

      <div v-if="j.status==='running'" class="card pad soft" :class="{ 'updated-flash': store.selectedMetaUpdated }">
        <div class="k">执行中</div>
        <div class="p">Worker 正在处理该任务。</div>
      </div>

      <div v-else-if="j.status==='pending'" class="card pad soft" :class="{ 'updated-flash': store.selectedMetaUpdated }">
        <div class="k">等待执行</div>
        <div class="p">任务已入队，等待 Worker 拉取。</div>
      </div>

      <div v-else-if="j.status==='failed'" class="card pad soft errbox" :class="{ 'updated-flash': store.selectedMetaUpdated }">
        <div class="k">失败</div>
        <div class="p mono">{{ j.error || 'unknown error' }}</div>
      </div>

      <div v-else class="card pad soft" :class="{ 'updated-flash': store.selectedResultUpdated }">
        <div class="row">
          <div class="k">结果</div>
          <button class="mini" @click="expanded=!expanded">{{ expanded ? "收起" : "展开" }}</button>
        </div>
        <transition name="fade">
          <div v-if="expanded" class="content">
            <div class="k">输出</div>
            <pre class="pre">{{ j.result?.output_text || "" }}</pre>
            <div class="k">Token Usage</div>
            <div class="usage mono">
              prompt={{ j.result?.prompt_tokens ?? 0 }} · completion={{ j.result?.completion_tokens ?? 0 }} · total={{ j.result?.total_tokens ?? 0 }}
            </div>
            <div class="k" style="margin-top: 10px;">推理平均功耗</div>
            <div class="usage mono">{{ fmtWatts(j.result?.avg_power_watts) }}</div>
          </div>
        </transition>
      </div>
    </template>
  </section>
</template>

<style scoped>
.head{ display:flex; flex-direction:column; gap: 8px; margin-bottom: 12px; }
.h{ display:flex; align-items:center; justify-content:space-between; gap: 10px; }
.sub{ display:flex; align-items:center; gap: 10px; flex-wrap: wrap; }
.muted{ color: rgba(0,0,0,.62); font-size: 12px; }
.soft{ background: var(--md-sys-color-surface-variant); border: 1px solid rgba(0,0,0,.06); box-shadow: none; }
.errbox{ border-color: rgba(179,38,30,.25); background: rgba(179,38,30,.06); }
.k{ font-size: 12px; color: rgba(0,0,0,.62); font-weight: 700; }
.p{ margin-top: 6px; color: rgba(0,0,0,.72); }
.row{ display:flex; justify-content:space-between; align-items:center; gap: 10px; }
.pre{
  margin: 8px 0 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,.08);
  background: #fff;
  white-space: pre-wrap;
  word-break: break-word;
}
.usage{ font-size: 13px; }

.mini{
  border: 1px solid rgba(0,0,0,.10);
  background: #fff;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
}
</style>
