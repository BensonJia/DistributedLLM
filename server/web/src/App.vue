<script setup lang="ts">
import AppShell from "@/layouts/AppShell.vue";
</script>

<template>
  <AppShell>
    <transition name="route" mode="out-in">
      <router-view />
    </transition>
  </AppShell>
</template>
