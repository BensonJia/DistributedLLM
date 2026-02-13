export function shortId(id: string, left = 8, right = 6): string{
  if (!id) return "";
  if (id.length <= left + right + 3) return id;
  return `${id.slice(0,left)}...${id.slice(-right)}`;
}

export function fmtCost(v: number): string{
  if (!Number.isFinite(v)) return "—";
  if (v !== 0 && Math.abs(v) < 0.0001) return v.toExponential(2);
  return String(v.toFixed(6));
}
