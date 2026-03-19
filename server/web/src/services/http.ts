import { API_BASE, API_KEY } from "./env";
import { getInternalKey } from "./adminSession";

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string){
    super(message);
    this.status = status;
  }
}

export async function httpJson<T>(path: string, init: RequestInit = {}): Promise<T>{
  const url = API_BASE ? (API_BASE.replace(/\/$/, "") + path) : path;
  const headers: Record<string,string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string,string> || {})
  };
  if (API_KEY) headers["Authorization"] = `Bearer ${API_KEY}`;
  const internalKey = getInternalKey();
  if (internalKey) headers["X-Worker-Token"] = internalKey;

  const res = await fetch(url, { ...init, headers });
  if (!res.ok){
    const text = await res.text().catch(() => "");
    throw new HttpError(res.status, text || res.statusText);
  }
  return (await res.json()) as T;
}
