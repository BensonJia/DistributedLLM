<script setup lang="ts">
import { onMounted, onBeforeUnmount } from "vue";
import { useJobsStore } from "@/stores/jobs";
import { useUiStore } from "@/stores/ui";
import JobList from "./components/JobList.vue";
import JobDetail from "./components/JobDetail.vue";

const store = useJobsStore();
const ui = useUiStore();

let timer: number | undefined;

async function tick(){
  await store.refreshList();
  if (store.selectedId) await store.select(store.selectedId);
}

onMounted(async () => {
  await tick();
  timer = window.setInterval(() => {
    if (ui.autoRefresh) tick();
  }, 2000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <div class="grid">
    <JobList />
    <transition name="slide" mode="out-in">
      <JobDetail v-if="store.selectedId" :key="store.selectedId" />
      <div v-else class="card pad empty">
        <div class="h">任务管理</div>
        <div class="p">从左侧选择一个任务查看模型、分配 worker、执行状态与结果。</div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.grid{
  display:grid;
  grid-template-columns: 420px 1fr;
  gap: 14px;
}
.empty .h{ font-weight: 800; font-size: 18px; margin-bottom: 6px; }
.empty .p{ color: rgba(0,0,0,.62); line-height: 1.5; }

@media (max-width: 980px){
  .grid{ grid-template-columns: 1fr; }
}
</style>
