<script setup lang="ts">
import { onMounted, onBeforeUnmount } from "vue";
import SideNav from "@/components/navigation/SideNav.vue";
import TopAppBar from "@/components/layout/TopAppBar.vue";
import SnackbarHost from "@/components/ui/SnackbarHost.vue";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();

function handleResize(){
  ui.setMobile(window.innerWidth < 980);
}
onMounted(() => {
  handleResize();
  window.addEventListener("resize", handleResize);
});
onBeforeUnmount(() => window.removeEventListener("resize", handleResize));
</script>

<template>
  <div class="root">
    <SideNav />
    <div class="main">
      <TopAppBar />
      <main class="content">
        <slot />
      </main>
    </div>
    <SnackbarHost />
    <div v-if="ui.drawerOpen && ui.isMobile" class="backdrop" @click="ui.setDrawer(false)"></div>
  </div>
</template>

<style scoped>
.root{
  display:flex;
  min-height: 100vh;
}
.main{
  flex: 1;
  min-width: 0;
}
.content{
  padding: 16px;
}
.backdrop{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.28);
  z-index: 15;
}
</style>
