<script setup lang="ts">
import BarChartCanvas from "@/components/charts/BarChartCanvas.vue";
import LineChartCanvas from "@/components/charts/LineChartCanvas.vue";
import type { BarChartData, LineChartData } from "@/charts/types";
import { api } from "@/services/api";
import { useJobsStore } from "@/stores/jobs";
import { useUiStore } from "@/stores/ui";
import { useWorkersStore } from "@/stores/workers";
import type { JobDetail, JobSummary, WorkerDetail } from "@/types";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const workersStore = useWorkersStore();
const jobsStore = useJobsStore();
const ui = useUiStore();

const loading = ref(false);
const error = ref("");
const selectedWorkerId = ref("");
const selectedModel = ref("");
const workerDetails = ref<Record<string, WorkerDetail>>({});
const jobDetails = ref<Record<string, JobDetail>>({});

let timer: number | undefined;
let ticking = false;

function shortId(id: string): string{
  if (!id) return "";
  if (id.length <= 14) return id;
  return `${id.slice(0, 6)}...${id.slice(-4)}`;
}

function ts(job: JobSummary): number{
  const raw = job.updated_at || job.created_at || "";
  const parsed = Date.parse(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function ensureDefaultSelections(): void{
  if (!selectedWorkerId.value || !workersStore.workers.some(w => w.worker_id === selectedWorkerId.value)){
    selectedWorkerId.value = workersStore.workers[0]?.worker_id || "";
  }
  if (!selectedModel.value || !modelOptions.value.includes(selectedModel.value)){
    selectedModel.value = modelOptions.value[0] || "";
  }
}

function powerPer100Token(detail?: JobDetail): number{
  const power = detail?.result?.avg_power_watts;
  const tokens = detail?.result?.total_tokens ?? 0;
  if (power == null || !Number.isFinite(power) || tokens <= 0) return 0;
  return (power * 100) / tokens;
}

async function hydrateWorkerDetails(): Promise<void>{
  const ids = workersStore.workers.map(w => w.worker_id);
  const pairs = await Promise.all(ids.map(async (id) => {
    try{
      const detail = await api.getWorker(id);
      return [id, detail] as const;
    }catch{
      return null;
    }
  }));
  const next: Record<string, WorkerDetail> = {};
  for (const pair of pairs){
    if (!pair) continue;
    next[pair[0]] = pair[1];
  }
  workerDetails.value = next;
}

async function hydrateJobDetails(jobIds: string[]): Promise<void>{
  const missing = jobIds.filter(id => !jobDetails.value[id]);
  if (missing.length === 0) return;
  const pairs = await Promise.all(missing.map(async (id) => {
    try{
      const detail = await api.getJob(id);
      return [id, detail] as const;
    }catch{
      return null;
    }
  }));
  if (pairs.every(p => !p)) return;
  const next = { ...jobDetails.value };
  for (const pair of pairs){
    if (!pair) continue;
    next[pair[0]] = pair[1];
  }
  jobDetails.value = next;
}

async function tick(): Promise<void>{
  if (ticking) return;
  ticking = true;
  loading.value = !workersStore.loadedOnce || !jobsStore.loadedOnce;
  error.value = "";
  try{
    await Promise.all([
      workersStore.refreshList(workersStore.loadedOnce),
      jobsStore.refreshList(jobsStore.loadedOnce)
    ]);
    await hydrateWorkerDetails();
    ensureDefaultSelections();

    if (selectedModel.value){
      const targetJobIds = jobsStore.jobs
        .filter(j => j.status === "done" && j.model === selectedModel.value)
        .sort((a, b) => ts(b) - ts(a))
        .slice(0, 150)
        .map(j => j.job_id);
      await hydrateJobDetails(targetJobIds);
    }
  }catch(e: any){
    error.value = String(e?.message || e);
  }finally{
    loading.value = false;
    ticking = false;
  }
}

onMounted(async () => {
  await tick();
  timer = window.setInterval(() => {
    if (ui.autoRefresh) void tick();
  }, 3000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});

watch(() => selectedModel.value, async (model) => {
  if (!model) return;
  const targetJobIds = jobsStore.jobs
    .filter(j => j.status === "done" && j.model === model)
    .sort((a, b) => ts(b) - ts(a))
    .slice(0, 150)
    .map(j => j.job_id);
  await hydrateJobDetails(targetJobIds);
});

const jobsCountByWorker = computed(() => {
  const map = new Map<string, number>();
  for (const worker of workersStore.workers){
    map.set(worker.worker_id, 0);
  }
  for (const job of jobsStore.jobs){
    map.set(job.assigned_worker_id, (map.get(job.assigned_worker_id) || 0) + 1);
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1]);
});

const taskCountBarData = computed<BarChartData>(() => ({
  labels: jobsCountByWorker.value.map(([id]) => shortId(id)),
  yLabel: "Tasks",
  series: [
    {
      id: "count",
      label: "任务数",
      color: "rgba(103,80,164,.75)",
      values: jobsCountByWorker.value.map(([, count]) => count)
    }
  ]
}));

const modelOptions = computed(() => {
  const set = new Set<string>();
  for (const detail of Object.values(workerDetails.value)){
    for (const model of detail.models || []){
      if (model?.name) set.add(model.name);
    }
  }
  return [...set].sort();
});

const selectedWorkerDetail = computed(() => workerDetails.value[selectedWorkerId.value] || null);

const workerSpeedBarData = computed<BarChartData>(() => {
  const detail = selectedWorkerDetail.value;
  const models = [...(detail?.models || [])].sort((a, b) => (b.speed_tps || 0) - (a.speed_tps || 0));
  return {
    labels: models.map(m => m.name),
    yLabel: "Token/s",
    series: [
      {
        id: "speed",
        label: "速度 (tps)",
        color: "rgba(26,127,55,.75)",
        values: models.map(m => m.speed_tps || 0)
      }
    ]
  };
});

const powerLineData = computed<LineChartData>(() => {
  const labels = Array.from({ length: 10 }, (_, i) => `任务${i + 1}`);
  const eligible = Object.values(workerDetails.value).filter(d => (d.models || []).some(m => m.name === selectedModel.value));
  const series = eligible
    .map((detail) => {
      const jobs = jobsStore.jobs
        .filter(j => j.status === "done" && j.model === selectedModel.value && j.assigned_worker_id === detail.worker_id)
        .sort((a, b) => ts(b) - ts(a))
        .slice(0, 10)
        .reverse();
      if (jobs.length === 0) return null;

      const values = jobs.map(j => powerPer100Token(jobDetails.value[j.job_id]));
      while (values.length < 10) values.unshift(0);
      const color = detail.worker_id === selectedWorkerId.value ? "#6750a4" : "#1a7f37";
      return {
        id: detail.worker_id,
        label: shortId(detail.worker_id),
        color,
        values
      };
    })
    .filter((v): v is NonNullable<typeof v> => !!v);

  return {
    labels,
    yLabel: "W / 100 tok",
    series
  };
});
</script>

<template>
  <div class="col">
    <section class="card pad">
      <div class="head">
        <div>
          <div class="title">Worker 任务数统计</div>
          <div class="sub">各个 worker 已处理任务总量</div>
        </div>
      </div>
      <div v-if="loading" class="skeleton" style="height: 320px;"></div>
      <div v-else-if="taskCountBarData.labels.length === 0" class="empty">暂无任务数据</div>
      <BarChartCanvas v-else :data="taskCountBarData" :height="320" />
    </section>

    <section class="card pad">
      <div class="head">
        <div>
          <div class="title">Worker 监视栏</div>
          <div class="sub">选定 worker 后，展示其各模型推理速度</div>
        </div>
        <select v-model="selectedWorkerId" class="select">
          <option v-for="w in workersStore.workers" :key="w.worker_id" :value="w.worker_id">
            {{ shortId(w.worker_id) }}
          </option>
        </select>
      </div>
      <div v-if="loading" class="skeleton" style="height: 300px;"></div>
      <div v-else-if="!selectedWorkerDetail" class="empty">未选择 worker 或 worker 不可用</div>
      <div v-else-if="workerSpeedBarData.labels.length === 0" class="empty">该 worker 暂无模型速度数据</div>
      <BarChartCanvas v-else :data="workerSpeedBarData" :height="300" />
    </section>

    <section class="card pad">
      <div class="head">
        <div>
          <div class="title">功耗对比栏</div>
          <div class="sub">选择模型后，展示具备该模型 workers 最近 10 任务的每100token功耗曲线</div>
        </div>
        <select v-model="selectedModel" class="select">
          <option v-for="m in modelOptions" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <div v-if="loading" class="skeleton" style="height: 320px;"></div>
      <div v-else-if="!selectedModel" class="empty">暂无可选择模型</div>
      <div v-else-if="powerLineData.series.length === 0" class="empty">该模型暂无任务功耗数据</div>
      <LineChartCanvas v-else :data="powerLineData" :height="320" />
    </section>

    <div v-if="error" class="card pad errbox">
      <div class="k">Error</div>
      <div class="p mono">{{ error }}</div>
    </div>
  </div>
</template>

<style scoped>
.col{
  display:flex;
  flex-direction:column;
  gap:14px;
}
.head{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:10px;
  margin-bottom:12px;
}
.title{ font-weight:800; }
.sub{ font-size:12px; color: rgba(0,0,0,.62); margin-top:3px; }
.select{
  min-width: 220px;
  border: 1px solid rgba(0,0,0,.12);
  border-radius: 12px;
  padding: 8px 10px;
  background: #fff;
  font: inherit;
}
.empty{
  border: 1px dashed rgba(0,0,0,.16);
  border-radius: 12px;
  padding: 18px;
  color: rgba(0,0,0,.72);
  background: rgba(0,0,0,.02);
}
.errbox{
  border-color: rgba(179,38,30,.25);
  background: rgba(179,38,30,.06);
}
.k{
  font-size: 12px;
  color: rgba(0,0,0,.62);
  font-weight: 700;
}
.p{
  margin-top: 6px;
  color: rgba(0,0,0,.84);
}
@media (max-width: 980px){
  .head{
    flex-direction: column;
    align-items: stretch;
  }
  .select{ min-width: 0; width: 100%; }
}
</style>
