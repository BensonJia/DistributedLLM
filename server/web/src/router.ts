import { createRouter, createWebHistory } from "vue-router";
import WorkersPage from "@/pages/workers/WorkersPage.vue";
import JobsPage from "@/pages/jobs/JobsPage.vue";
import ClusterPage from "@/pages/cluster/ClusterPage.vue";
import StatsPage from "@/pages/stats/StatsPage.vue";
import LoginPage from "@/pages/auth/LoginPage.vue";
import { pinia } from "@/pinia";
import { useAuthStore } from "@/stores/auth";
import { hasInternalKey } from "@/services/adminSession";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage, meta: { requiresAuth: false } },
    { path: "/", redirect: "/workers" },
    { path: "/workers", component: WorkersPage, meta: { requiresAuth: true } },
    { path: "/jobs", component: JobsPage, meta: { requiresAuth: true } },
    { path: "/cluster", component: ClusterPage, meta: { requiresAuth: true } },
    { path: "/stats", component: StatsPage, meta: { requiresAuth: true } }
  ]
});

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia);
  if (!auth.authenticated && auth.error === "" && !auth.checking && hasInternalKey()){
    await auth.restore();
  }
  if (to.path === "/login" && auth.authenticated){
    return { path: "/workers" };
  }
  if (to.meta.requiresAuth !== false && !auth.authenticated){
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
