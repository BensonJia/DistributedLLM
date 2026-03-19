<script setup lang="ts">
import AppShell from "@/layouts/AppShell.vue";
</script>

<template>
  <router-view v-slot="{ Component, route: currentRoute }">
    <AppShell v-if="currentRoute.meta.requiresAuth !== false">
      <transition name="route" mode="out-in">
        <component :is="Component" />
      </transition>
    </AppShell>
    <component v-else :is="Component" />
  </router-view>
</template>
