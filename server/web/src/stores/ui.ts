import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    drawerOpen: true,
    isMobile: false,
    autoRefresh: true,
    snackbar: {
      visible: false,
      message: ""
    }
  }),
  actions: {
    setMobile(v: boolean){
      this.isMobile = v;
      this.drawerOpen = !v;
    },
    toggleDrawer(){
      this.drawerOpen = !this.drawerOpen;
    },
    setDrawer(v: boolean){
      this.drawerOpen = v;
    },
    setAutoRefresh(v: boolean){
      this.autoRefresh = v;
    },
    toast(message: string, ms = 2500){
      this.snackbar.message = message;
      this.snackbar.visible = true;
      window.setTimeout(() => {
        this.snackbar.visible = false;
      }, ms);
    }
  }
});
