<script setup lang="ts">
import { computed } from "vue";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const auto = computed({
  get: () => ui.autoRefresh,
  set: (v: boolean) => ui.setAutoRefresh(v)
});

function toggleDrawer(){
  ui.toggleDrawer();
}
</script>

<template>
  <header class="bar">
    <button class="icon" @click="toggleDrawer" aria-label="Toggle navigation">
      <span class="material-icon">≡</span>
    </button>
    <div class="title">Distributed LLM Admin</div>
    <div class="spacer"></div>

    <label class="switch" title="Auto refresh">
      <input type="checkbox" v-model="auto" />
      <span class="track"></span>
      <span class="text">Auto</span>
    </label>
  </header>
</template>

<style scoped>
.bar{
  position: sticky;
  top: 0;
  z-index: 10;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: rgba(255,255,255,.86);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0,0,0,.06);
}
.title{ font-weight: 700; letter-spacing: .2px; }
.spacer{ flex: 1; }
.icon{
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,.08);
  background: #fff;
  cursor: pointer;
  transition: transform .08s ease, box-shadow .18s ease;
}
.icon:active{ transform: translateY(1px); }

.switch{
  display:flex;
  align-items:center;
  gap: 10px;
  user-select: none;
  font-size: 13px;
  color: rgba(0,0,0,.72);
}
.switch input{ display:none; }
.track{
  width: 44px; height: 24px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,.12);
  background: #fff;
  position: relative;
  transition: background-color .18s ease;
}
.track::after{
  content:"";
  position:absolute;
  top: 50%;
  left: 3px;
  transform: translateY(-50%);
  width: 18px; height: 18px;
  border-radius: 50%;
  background: var(--md-sys-color-primary);
  transition: left .18s ease, background-color .18s ease;
}
.switch input:checked + .track{
  background: rgba(103,80,164,.12);
}
.switch input:checked + .track::after{
  left: 23px;
}
</style>
