import { Base2DChart } from "@/charts/Base2DChart";
import type { ChartHoverPayload, LineChartData, LineSeries } from "@/charts/types";

type YRange = { min: number; max: number; ticks: number[] };

function clamp(v: number, lo: number, hi: number): number{
  return Math.min(hi, Math.max(lo, v));
}

function formatNumber(value: number): string{
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1000) return value.toFixed(0);
  if (Math.abs(value) >= 100) return value.toFixed(1);
  return value.toFixed(2).replace(/\.?0+$/, "");
}

export class LineChart2D extends Base2DChart<LineChartData> {
  private hoverIndex: number | null = null;

  protected getXDomain(data: LineChartData): { min: number; max: number }{
    const n = Math.max(1, data.labels.length);
    return { min: 0, max: Math.max(1, n - 1) };
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

    const x = Math.round(this.pixelToX(pointerX));
    const idx = clamp(x, 0, Math.max(0, this.data.labels.length - 1));
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

    const theme = this.theme();
    const yRange = this.computeYRange(progress);
    const yToPixel = (v: number) => {
      const span = Math.max(0.0001, yRange.max - yRange.min);
      const r = (v - yRange.min) / span;
      return this.plot.bottom - r * this.plot.height;
    };

    const ctx = this.ctx;
    ctx.fillStyle = theme.surface;
    ctx.fillRect(this.plot.left, this.plot.top, this.plot.width, this.plot.height);

    this.drawGrid(yRange);
    this.drawLegend();
    this.drawXAxis();
    this.drawYAxis(yRange);

    const hoverIdx = this.hoverIndex;
    for (const series of this.data.series){
      this.drawSeries(series, yToPixel, progress);
      if (hoverIdx != null){
        const x = this.xToPixel(hoverIdx);
        const value = this.valueFor(series, hoverIdx, progress);
        const y = yToPixel(value);
        if (x < this.plot.left || x > this.plot.right) continue;

        ctx.beginPath();
        ctx.fillStyle = series.color;
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = "#ffffff";
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    if (hoverIdx != null){
      const x = this.xToPixel(hoverIdx);
      if (x >= this.plot.left && x <= this.plot.right){
        ctx.save();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = `${theme.primary}88`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, this.plot.top);
        ctx.lineTo(x, this.plot.bottom);
        ctx.stroke();
        ctx.restore();
      }
    }
  }

  private drawSeries(series: LineSeries, yToPixel: (v: number) => number, progress: number): void{
    const ctx = this.ctx;
    const n = this.data?.labels.length || 0;
    if (n === 0) return;

    ctx.beginPath();
    ctx.lineWidth = series.width ?? 2;
    ctx.strokeStyle = series.color;
    let started = false;

    for (let i = 0; i < n; i++){
      const x = this.xToPixel(i);
      if (x < this.plot.left - 24 || x > this.plot.right + 24) continue;
      const v = this.valueFor(series, i, progress);
      const y = yToPixel(v);
      if (!started){
        ctx.moveTo(x, y);
        started = true;
      }else{
        ctx.lineTo(x, y);
      }
    }

    ctx.stroke();
  }

  private valueFor(series: LineSeries, idx: number, progress: number): number{
    const next = series.values[idx] ?? 0;
    if (!this.prevData || progress >= 1) return next;
    const prevSeries = this.prevData.series.find((s) => s.id === series.id);
    const prev = prevSeries?.values[idx];
    return this.animateValue(prev, next, progress);
  }

  private computeYRange(progress: number): YRange{
    const data = this.data!;
    const start = Math.floor(this.pixelToX(this.plot.left));
    const end = Math.ceil(this.pixelToX(this.plot.right));
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (const series of data.series){
      for (let i = start; i <= end; i++){
        const v = this.valueFor(series, i, progress);
        if (!Number.isFinite(v)) continue;
        min = Math.min(min, v);
        max = Math.max(max, v);
      }
    }

    if (!Number.isFinite(min) || !Number.isFinite(max)){
      min = 0;
      max = 1;
    }
    if (Math.abs(max - min) < 1e-6){
      max += 1;
      min -= 1;
    }
    const pad = (max - min) * 0.12;
    min -= pad;
    max += pad;
    return { min, max, ticks: this.makeTicks(min, max, 5) };
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

    const visibleCount = Math.max(1, Math.floor(this.pixelToX(this.plot.right) - this.pixelToX(this.plot.left)));
    const step = Math.max(1, Math.ceil(visibleCount / 8));
    const start = Math.max(0, Math.floor(this.pixelToX(this.plot.left)));
    const end = Math.min((this.data?.labels.length || 1) - 1, Math.ceil(this.pixelToX(this.plot.right)));

    for (let i = start; i <= end; i += step){
      const x = this.xToPixel(i);
      ctx.beginPath();
      ctx.moveTo(x, this.plot.top);
      ctx.lineTo(x, this.plot.bottom);
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

    const visibleCount = Math.max(1, Math.floor(this.pixelToX(this.plot.right) - this.pixelToX(this.plot.left)));
    const step = Math.max(1, Math.ceil(visibleCount / 8));
    const start = Math.max(0, Math.floor(this.pixelToX(this.plot.left)));
    const end = Math.min(this.data.labels.length - 1, Math.ceil(this.pixelToX(this.plot.right)));

    for (let i = start; i <= end; i += step){
      const x = this.xToPixel(i);
      const text = this.data.labels[i] ?? "";
      ctx.fillText(text, x, this.plot.bottom + 8);
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

