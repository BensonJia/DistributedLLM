<script setup lang="ts">
import { onMounted, onBeforeUnmount } from "vue";
import { useWorkersStore } from "@/stores/workers";
import { useUiStore } from "@/stores/ui";
import WorkerList from "./components/WorkerList.vue";
import WorkerDetail from "./components/WorkerDetail.vue";

const store = useWorkersStore();
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
    <WorkerList />
    <transition name="slide" mode="out-in">
      <WorkerDetail v-if="store.selectedId" :key="store.selectedId" />
      <div v-else class="card pad empty">
        <div class="h">Worker 管理</div>
        <div class="p">从左侧列表选择一个 Worker 查看详细信息（模型/价格/任务）。</div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.grid{
  display:grid;
  grid-template-columns: 380px 1fr;
  gap: 14px;
}
.empty .h{ font-weight: 800; font-size: 18px; margin-bottom: 6px; }
.empty .p{ color: rgba(0,0,0,.62); line-height: 1.5; }

@media (max-width: 980px){
  .grid{ grid-template-columns: 1fr; }
}
</style>
