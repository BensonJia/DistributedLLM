import { createApp } from "vue";
import { createPinia } from "pinia";
import router from "./router";
import App from "./App.vue";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/transitions.css";

createApp(App).use(createPinia()).use(router).mount("#app");
