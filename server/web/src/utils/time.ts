export function formatRelTime(iso?: string): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  const now = Date.now();
  const s = Math.floor((now - t) / 1000);
  if (s < 5) return "刚刚";
  if (s < 60) return `${s}s 前`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m 前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h 前`;
  const d = Math.floor(h / 24);
  return `${d}d 前`;
}

export function formatIso(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}
