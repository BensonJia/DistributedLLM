import { createRouter, createWebHistory } from "vue-router";
import WorkersPage from "@/pages/workers/WorkersPage.vue";
import JobsPage from "@/pages/jobs/JobsPage.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/workers" },
    { path: "/workers", component: WorkersPage },
    { path: "/jobs", component: JobsPage }
  ]
});
