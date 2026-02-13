<script setup lang="ts">
import { computed } from "vue";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const visible = computed(() => ui.snackbar.visible);
const message = computed(() => ui.snackbar.message);
</script>

<template>
  <transition name="fade">
    <div v-if="visible" class="snackbar" role="status" aria-live="polite">
      <div class="card pad">{{ message }}</div>
    </div>
  </transition>
</template>

<style scoped>
.snackbar{
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 50;
  max-width: min(560px, calc(100vw - 32px));
}
.snackbar .card{
  background: rgba(29,27,32,.92);
  color: #fff;
  border: 1px solid rgba(255,255,255,.12);
  box-shadow: var(--md-sys-elev-2);
}
</style>
