<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const route = useRoute();
const router = useRouter();

const open = computed(() => ui.drawerOpen);
function go(path: string){
  router.push(path);
  if (ui.isMobile) ui.setDrawer(false);
}
</script>

<template>
  <aside class="drawer" :class="{ open }">
    <div class="brand">
      <div class="logo">◈</div>
      <div>
        <div class="name">Control Plane</div>
        <div class="sub">Workers · Jobs</div>
      </div>
    </div>

    <nav class="nav">
      <button class="item" :class="{ active: route.path.startsWith('/workers') }" @click="go('/workers')">
        <span class="ic">🧩</span>
        Worker 管理
      </button>
      <button class="item" :class="{ active: route.path.startsWith('/jobs') }" @click="go('/jobs')">
        <span class="ic">🧾</span>
        任务管理
      </button>
    </nav>

    <div class="hint">
      <div class="chip dot">Material-ish · CSS</div>
    </div>
  </aside>
</template>

<style scoped>
.drawer{
  width: 280px;
  min-width: 280px;
  height: 100vh;
  position: sticky;
  top: 0;
  padding: 14px 12px;
  background: rgba(255,255,255,.72);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0,0,0,.06);
}
.brand{
  display:flex;
  align-items:center;
  gap: 10px;
  padding: 10px 10px 14px;
}
.logo{
  width: 40px; height: 40px;
  border-radius: 14px;
  display:flex; align-items:center; justify-content:center;
  background: rgba(103,80,164,.12);
  border: 1px solid rgba(103,80,164,.18);
  font-weight: 800;
}
.name{ font-weight: 800; }
.sub{ font-size: 12px; color: rgba(0,0,0,.62); margin-top: 2px; }
.nav{ display:flex; flex-direction:column; gap: 8px; padding: 6px; }
.item{
  width: 100%;
  display:flex; align-items:center; gap: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: rgba(0,0,0,.78);
  transition: background-color .18s ease, transform .08s ease, border-color .18s ease;
}
.item:hover{
  background: rgba(0,0,0,.04);
}
.item.active{
  background: rgba(103,80,164,.12);
  border-color: rgba(103,80,164,.18);
  color: rgba(0,0,0,.88);
}
.item:active{ transform: translateY(1px); }
.ic{ width: 20px; text-align:center; }
.hint{ padding: 10px 12px; }
@media (max-width: 980px){
  .drawer{
    position: fixed;
    left: -300px;
    z-index: 20;
    box-shadow: var(--md-sys-elev-2);
    transition: left .18s ease;
  }
  .drawer.open{ left: 0; }
}
</style>
