export const API_BASE = (import.meta.env.VITE_API_BASE as string) || "";
export const API_KEY = (import.meta.env.VITE_API_KEY as string) || "";
export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK || "false").toLowerCase() === "true";
