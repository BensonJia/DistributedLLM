import { Base2DChart } from "@/charts/Base2DChart";
import type { BarChartData, BarSeries, ChartHoverPayload } from "@/charts/types";

function clamp(v: number, lo: number, hi: number): number{
  return Math.min(hi, Math.max(lo, v));
}

function formatNumber(value: number): string{
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1000) return value.toFixed(0);
  return value.toFixed(2).replace(/\.?0+$/, "");
}

type YRange = { min: number; max: number; ticks: number[] };

export class BarChart2D extends Base2DChart<BarChartData> {
  private hoverIndex: number | null = null;

  protected getXDomain(data: BarChartData): { min: number; max: number }{
    const n = Math.max(1, data.labels.length);
    return { min: -0.5, max: n - 0.5 };
  }

  protected clearHover(): void{
    this.hoverIndex = null;
  }

  protected updateHover(pointerX: number, pointerY: number): void{
    if (!this.data){
      this.hoverIndex = null;
      this.emitHover(null);
      return;
    }
    if (
      pointerX < this.plot.left ||
      pointerX > this.plot.right ||
      pointerY < this.plot.top ||
      pointerY > this.plot.bottom
    ){
      this.hoverIndex = null;
      this.emitHover(null);
      return;
    }

    const idx = clamp(Math.floor(this.pixelToX(pointerX) + 0.5), 0, Math.max(0, this.data.labels.length - 1));
    this.hoverIndex = idx;

    const items = this.data.series.map((series) => ({
      label: series.label,
      color: series.color,
      value: formatNumber(series.values[idx] ?? NaN)
    }));
    const payload: ChartHoverPayload = {
      x: pointerX + 12,
      y: pointerY + 12,
      title: this.data.labels[idx] ?? `#${idx}`,
      items
    };
    this.emitHover(payload);
  }

  protected draw(progress: number): void{
    if (!this.data) return;
    const ctx = this.ctx;
    const theme = this.theme();
    const yRange = this.computeYRange(progress);
    const yToPixel = (v: number) => {
      const span = Math.max(0.0001, yRange.max - yRange.min);
      const ratio = (v - yRange.min) / span;
      return this.plot.bottom - ratio * this.plot.height;
    };
    const yZero = yToPixel(0);

    ctx.fillStyle = theme.surface;
    ctx.fillRect(this.plot.left, this.plot.top, this.plot.width, this.plot.height);

    this.drawGrid(yRange);
    this.drawLegend();
    this.drawXAxis();
    this.drawYAxis(yRange);

    const seriesCount = Math.max(1, this.data.series.length);
    const groupWidth = 0.82;
    const barWidth = groupWidth / seriesCount;

    const start = Math.max(0, Math.floor(this.pixelToX(this.plot.left) - 0.5));
    const end = Math.min(this.data.labels.length - 1, Math.ceil(this.pixelToX(this.plot.right) + 0.5));

    for (let i = start; i <= end; i++){
      for (let s = 0; s < seriesCount; s++){
        const series = this.data.series[s];
        const value = this.valueFor(series, i, progress);
        const x0 = i - groupWidth / 2 + s * barWidth;
        const x1 = x0 + barWidth * 0.88;
        const px0 = this.xToPixel(x0);
        const px1 = this.xToPixel(x1);
        const top = yToPixel(Math.max(0, value));
        const bottom = yToPixel(Math.min(0, value));
        const w = Math.max(1, px1 - px0);
        const h = Math.max(1, bottom - top);

        ctx.fillStyle = series.color;
        ctx.fillRect(px0, top, w, h);

        if (this.hoverIndex === i){
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1;
          ctx.strokeRect(px0 + 0.5, top + 0.5, Math.max(0, w - 1), Math.max(0, h - 1));
        }
      }
    }

    ctx.strokeStyle = `${theme.onSurface}90`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(this.plot.left, yZero);
    ctx.lineTo(this.plot.right, yZero);
    ctx.stroke();
  }

  private valueFor(series: BarSeries, idx: number, progress: number): number{
    const next = series.values[idx] ?? 0;
    if (!this.prevData || progress >= 1) return next;
    const prevSeries = this.prevData.series.find((s) => s.id === series.id);
    const prev = prevSeries?.values[idx];
    return this.animateValue(prev, next, progress);
  }

  private computeYRange(progress: number): YRange{
    const data = this.data!;
    const start = Math.max(0, Math.floor(this.pixelToX(this.plot.left) - 0.5));
    const end = Math.min(data.labels.length - 1, Math.ceil(this.pixelToX(this.plot.right) + 0.5));

    let min = 0;
    let max = 0;
    for (const series of data.series){
      for (let i = start; i <= end; i++){
        const v = this.valueFor(series, i, progress);
        if (!Number.isFinite(v)) continue;
        min = Math.min(min, v);
        max = Math.max(max, v);
      }
    }

    if (Math.abs(max - min) < 1e-6){
      max += 1;
      min -= 1;
    }
    const pad = (max - min) * 0.14;
    return {
      min: min - pad,
      max: max + pad,
      ticks: this.makeTicks(min - pad, max + pad, 5)
    };
  }

  private makeTicks(min: number, max: number, count: number): number[]{
    const ticks: number[] = [];
    const span = Math.max(1e-6, max - min);
    const raw = span / Math.max(1, count - 1);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    let nice = 1;
    if (norm >= 5) nice = 5;
    else if (norm >= 2) nice = 2;
    const step = nice * mag;
    const start = Math.floor(min / step) * step;
    const end = Math.ceil(max / step) * step;
    for (let v = start; v <= end + step * 0.5; v += step){
      ticks.push(v);
    }
    return ticks;
  }

  private drawGrid(yRange: YRange): void{
    const ctx = this.ctx;
    const theme = this.theme();
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = `${theme.outline}88`;
    ctx.lineWidth = 1;

    for (const y of yRange.ticks){
      const py = this.plot.bottom - ((y - yRange.min) / (yRange.max - yRange.min)) * this.plot.height;
      if (py < this.plot.top || py > this.plot.bottom) continue;
      ctx.beginPath();
      ctx.moveTo(this.plot.left, py);
      ctx.lineTo(this.plot.right, py);
      ctx.stroke();
    }
    ctx.restore();
  }

  private drawXAxis(): void{
    if (!this.data) return;
    const ctx = this.ctx;
    const theme = this.theme();
    ctx.font = this.getFont(11, 500);
    ctx.fillStyle = `${theme.onSurface}B0`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    const visible = Math.max(1, Math.floor(this.pixelToX(this.plot.right) - this.pixelToX(this.plot.left)));
    const step = Math.max(1, Math.ceil(visible / 8));
    const start = Math.max(0, Math.floor(this.pixelToX(this.plot.left) + 0.5));
    const end = Math.min(this.data.labels.length - 1, Math.ceil(this.pixelToX(this.plot.right) - 0.5));

    for (let i = start; i <= end; i += step){
      const x = this.xToPixel(i);
      ctx.fillText(this.data.labels[i] ?? "", x, this.plot.bottom + 8);
    }
  }

  private drawYAxis(yRange: YRange): void{
    const ctx = this.ctx;
    const theme = this.theme();
    ctx.font = this.getFont(11, 500);
    ctx.fillStyle = `${theme.onSurface}A8`;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";

    for (const y of yRange.ticks){
      const py = this.plot.bottom - ((y - yRange.min) / (yRange.max - yRange.min)) * this.plot.height;
      if (py < this.plot.top || py > this.plot.bottom) continue;
      ctx.fillText(formatNumber(y), this.plot.left - 8, py);
    }

    if (this.data?.yLabel){
      ctx.save();
      ctx.translate(18, (this.plot.top + this.plot.bottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(this.data.yLabel, 0, 0);
      ctx.restore();
    }
  }

  private drawLegend(): void{
    if (!this.data) return;
    const ctx = this.ctx;
    const theme = this.theme();
    ctx.font = this.getFont(12, 600);
    ctx.textBaseline = "middle";

    let x = this.plot.left;
    const y = this.plot.top - 24;
    for (const series of this.data.series){
      ctx.fillStyle = series.color;
      ctx.fillRect(x, y - 4, 16, 8);
      x += 22;
      ctx.fillStyle = `${theme.onSurface}D0`;
      ctx.textAlign = "left";
      ctx.fillText(series.label, x, y);
      x += ctx.measureText(series.label).width + 16;
    }
  }
}

