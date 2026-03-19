<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const internalKey = ref("");
const submitting = ref(false);

function safeRedirect(value: unknown): string{
  return typeof value === "string" && value.startsWith("/") ? value : "/workers";
}

onMounted(() => {
  if (auth.authenticated){
    router.replace(safeRedirect(route.query.redirect));
  }
});

async function submit(){
  if (submitting.value) return;
  submitting.value = true;
  try{
    await auth.login(internalKey.value);
    await router.replace(safeRedirect(route.query.redirect));
  }catch{
    // error is exposed by the store
  }finally{
    submitting.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <div class="login-card">
      <div class="eyebrow">Distributed LLM Admin</div>
      <h1>Internal Key Required</h1>
      <p class="lead">输入 internal key 后才能访问 Worker、Job 和 Cluster 管理界面。</p>

      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span>Internal key</span>
          <input
            v-model="internalKey"
            type="password"
            autocomplete="current-password"
            placeholder="Paste internal key here"
            autofocus
          />
        </label>

        <button class="submit" type="submit" :disabled="submitting || auth.checking">
          {{ auth.checking ? "Verifying..." : "Enter dashboard" }}
        </button>

        <p v-if="auth.error" class="error">{{ auth.error }}</p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-shell{
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(41, 120, 255, .18), transparent 36%),
    radial-gradient(circle at bottom right, rgba(0, 180, 140, .16), transparent 34%),
    linear-gradient(180deg, #f4f7fb 0%, #eef3f8 100%);
}
.login-card{
  width: min(560px, 100%);
  border-radius: 24px;
  padding: 28px;
  background: rgba(255,255,255,.88);
  border: 1px solid rgba(30, 41, 59, .08);
  box-shadow: 0 18px 60px rgba(15, 23, 42, .12);
  backdrop-filter: blur(10px);
}
.eyebrow{
  display: inline-flex;
  font-size: 12px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: rgba(15,23,42,.6);
  margin-bottom: 16px;
}
h1{
  margin: 0;
  font-size: 34px;
  line-height: 1.05;
  letter-spacing: -.03em;
}
.lead{
  margin: 12px 0 0;
  color: rgba(15,23,42,.7);
  line-height: 1.6;
}
.form{
  margin-top: 24px;
  display: grid;
  gap: 14px;
}
.field{
  display: grid;
  gap: 8px;
  font-size: 14px;
  color: rgba(15,23,42,.75);
}
input{
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(30,41,59,.16);
  border-radius: 14px;
  padding: 14px 16px;
  font-size: 15px;
  background: rgba(255,255,255,.95);
  color: #0f172a;
  outline: none;
}
input:focus{
  border-color: rgba(41, 120, 255, .8);
  box-shadow: 0 0 0 4px rgba(41, 120, 255, .12);
}
.submit{
  border: 0;
  border-radius: 14px;
  padding: 14px 16px;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #0f172a, #2344ff);
  cursor: pointer;
}
.submit:disabled{
  opacity: .72;
  cursor: progress;
}
.error{
  margin: 0;
  color: #b42318;
  font-size: 14px;
  line-height: 1.5;
}
</style>
