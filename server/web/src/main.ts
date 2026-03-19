import { createApp } from "vue";
import router from "./router";
import { pinia } from "./pinia";
import App from "./App.vue";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/transitions.css";

createApp(App).use(pinia).use(router).mount("#app");
