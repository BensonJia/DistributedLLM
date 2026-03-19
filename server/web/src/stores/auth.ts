import { defineStore } from "pinia";
import { api } from "@/services/api";
import { HttpError } from "@/services/http";
import { clearInternalKey, getInternalKey, setInternalKey } from "@/services/adminSession";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    authenticated: false,
    checking: false,
    error: "" as string
  }),
  actions: {
    async restore(){
      if (this.checking) return;
      const existingKey = getInternalKey().trim();
      if (!existingKey){
        this.authenticated = false;
        this.error = "";
        return;
      }
      this.checking = true;
      try{
        setInternalKey(existingKey);
        await api.adminAuthCheck();
        this.authenticated = true;
        this.error = "";
      }catch(e: any){
        clearInternalKey();
        this.authenticated = false;
        this.error = e instanceof HttpError && e.status === 401 ? "Invalid internal key" : String(e?.message || e);
      }finally{
        this.checking = false;
      }
    },
    async login(internalKey: string){
      const key = internalKey.trim();
      if (!key) throw new Error("Please enter the internal key");
      this.checking = true;
      this.error = "";
      setInternalKey(key);
      try{
        await api.adminAuthCheck();
        this.authenticated = true;
      }catch(e: any){
        clearInternalKey();
        this.authenticated = false;
        this.error = e instanceof HttpError && e.status === 401 ? "Invalid internal key" : String(e?.message || e);
        throw e;
      }finally{
        this.checking = false;
      }
    },
    logout(){
      clearInternalKey();
      this.authenticated = false;
      this.error = "";
    }
  }
});
