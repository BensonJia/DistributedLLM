const STORAGE_KEY = "dllm.admin.internal_key";

function readStorage(): string{
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(STORAGE_KEY) || "";
}

let internalKey = readStorage();

export function getInternalKey(): string{
  if (typeof window !== "undefined" && internalKey !== window.localStorage.getItem(STORAGE_KEY)){
    internalKey = window.localStorage.getItem(STORAGE_KEY) || "";
  }
  return internalKey;
}

export function hasInternalKey(): boolean{
  return !!getInternalKey();
}

export function setInternalKey(value: string){
  internalKey = value.trim();
  if (typeof window !== "undefined"){
    if (internalKey){
      window.localStorage.setItem(STORAGE_KEY, internalKey);
    }else{
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }
}

export function clearInternalKey(){
  internalKey = "";
  if (typeof window !== "undefined"){
    window.localStorage.removeItem(STORAGE_KEY);
  }
}
