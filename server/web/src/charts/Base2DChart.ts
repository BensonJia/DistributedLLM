import type { ChartHoverPayload, ChartPadding, PlotArea } from "@/charts/types";

type ThemePalette = {
  surface: string;
  onSurface: string;
  outline: string;
  primary: string;
};

type Base2DChartOptions = {
  padding?: Partial<ChartPadding>;
  animationMs?: number;
  minZoomSpan?: number;
  onHover?: (payload: ChartHoverPayload | null) => void;
};

const DEFAULT_PADDING: ChartPadding = {
  top: 50,
  right: 16,
  bottom: 44,
  left: 56
};

function clamp(v: number, lo: number, hi: number): number{
  return Math.min(hi, Math.max(lo, v));
}

export abstract class Base2DChart<TData> {
  protected readonly canvas: HTMLCanvasElement;
  protected readonly ctx: CanvasRenderingContext2D;
  protected readonly padding: ChartPadding;
  protected readonly animationMs: number;
  protected readonly minZoomSpan: number;

  protected data: TData | null = null;
  protected prevData: TData | null = null;
  protected plot: PlotArea = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  protected viewXMin = 0;
  protected viewXMax = 1;
  protected dataXMin = 0;
  protected dataXMax = 1;

  private dpr = 1;
  private width = 1;
  private height = 1;
  private raf = 0;
  private animationStartAt = 0;
  private isPanning = false;
  private panLastX = 0;

  private readonly onHover?: (payload: ChartHoverPayload | null) => void;
  private readonly pointerDownHandler: (e: PointerEvent) => void;
  private readonly pointerMoveHandler: (e: PointerEvent) => void;
  private readonly pointerUpHandler: (e: PointerEvent) => void;
  private readonly wheelHandler: (e: WheelEvent) => void;
  private readonly leaveHandler: () => void;

  constructor(canvas: HTMLCanvasElement, options?: Base2DChartOptions){
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D context unavailable.");

    this.canvas = canvas;
    this.ctx = ctx;
    this.padding = { ...DEFAULT_PADDING, ...(options?.padding || {}) };
    this.animationMs = options?.animationMs ?? 320;
    this.minZoomSpan = options?.minZoomSpan ?? 4;
    this.onHover = options?.onHover;

    this.pointerDownHandler = (e) => this.onPointerDown(e);
    this.pointerMoveHandler = (e) => this.onPointerMove(e);
    this.pointerUpHandler = () => this.onPointerUp();
    this.wheelHandler = (e) => this.onWheel(e);
    this.leaveHandler = () => this.onPointerLeave();

    this.canvas.addEventListener("pointerdown", this.pointerDownHandler);
    this.canvas.addEventListener("pointermove", this.pointerMoveHandler);
    this.canvas.addEventListener("pointerup", this.pointerUpHandler);
    this.canvas.addEventListener("pointercancel", this.pointerUpHandler);
    this.canvas.addEventListener("wheel", this.wheelHandler, { passive: false });
    this.canvas.addEventListener("mouseleave", this.leaveHandler);

    this.resize();
  }

  public destroy(): void{
    this.canvas.removeEventListener("pointerdown", this.pointerDownHandler);
    this.canvas.removeEventListener("pointermove", this.pointerMoveHandler);
    this.canvas.removeEventListener("pointerup", this.pointerUpHandler);
    this.canvas.removeEventListener("pointercancel", this.pointerUpHandler);
    this.canvas.removeEventListener("wheel", this.wheelHandler);
    this.canvas.removeEventListener("mouseleave", this.leaveHandler);
    if (this.raf) window.cancelAnimationFrame(this.raf);
  }

  public resize(): void{
    const rect = this.canvas.getBoundingClientRect();
    this.width = Math.max(1, rect.width || this.canvas.clientWidth || 1);
    this.height = Math.max(1, rect.height || this.canvas.clientHeight || 1);
    this.dpr = Math.max(1, window.devicePixelRatio || 1);

    this.canvas.width = Math.round(this.width * this.dpr);
    this.canvas.height = Math.round(this.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

    this.computePlotRect();
    this.scheduleRender();
  }

  public setData(data: TData): void{
    this.prevData = this.data;
    this.data = data;
    const domain = this.getXDomain(data);
    this.dataXMin = domain.min;
    this.dataXMax = domain.max;

    if (!Number.isFinite(this.viewXMin) || !Number.isFinite(this.viewXMax) || this.viewXMax <= this.viewXMin){
      this.viewXMin = domain.min;
      this.viewXMax = domain.max;
    }
    this.clampView();

    this.animationStartAt = this.prevData ? performance.now() : 0;
    this.scheduleRender();
  }

  protected abstract getXDomain(data: TData): { min: number; max: number };
  protected abstract draw(progress: number): void;
  protected abstract updateHover(pointerX: number, pointerY: number): void;
  protected abstract clearHover(): void;

  protected theme(): ThemePalette{
    const styles = getComputedStyle(this.canvas);
    return {
      surface: styles.getPropertyValue("--md-sys-color-surface").trim() || "#ffffff",
      onSurface: styles.getPropertyValue("--md-sys-color-on-surface").trim() || "#1d1b20",
      outline: styles.getPropertyValue("--md-sys-color-outline").trim() || "#c9c5d0",
      primary: styles.getPropertyValue("--md-sys-color-primary").trim() || "#6750a4"
    };
  }

  protected getProgress(now: number): number{
    if (!this.animationStartAt || !this.prevData) return 1;
    return clamp((now - this.animationStartAt) / this.animationMs, 0, 1);
  }

  protected getFont(size = 12, weight = 500): string{
    return `${weight} ${size}px var(--md-sys-font)`;
  }

  protected xToPixel(x: number): number{
    const span = Math.max(0.0001, this.viewXMax - this.viewXMin);
    return this.plot.left + ((x - this.viewXMin) / span) * this.plot.width;
  }

  protected pixelToX(pixelX: number): number{
    const span = Math.max(0.0001, this.viewXMax - this.viewXMin);
    return this.viewXMin + ((pixelX - this.plot.left) / Math.max(1, this.plot.width)) * span;
  }

  protected emitHover(payload: ChartHoverPayload | null): void{
    this.onHover?.(payload);
  }

  protected animateValue(prev: number | undefined, next: number, progress: number): number{
    if (prev == null || !Number.isFinite(prev)) return next;
    return prev + (next - prev) * progress;
  }

  private computePlotRect(): void{
    const left = this.padding.left;
    const top = this.padding.top;
    const right = Math.max(left + 1, this.width - this.padding.right);
    const bottom = Math.max(top + 1, this.height - this.padding.bottom);
    this.plot = {
      left,
      top,
      right,
      bottom,
      width: Math.max(1, right - left),
      height: Math.max(1, bottom - top)
    };
  }

  private scheduleRender(): void{
    if (this.raf) return;
    this.raf = window.requestAnimationFrame((ts) => {
      this.raf = 0;
      this.render(ts);
    });
  }

  private render(timestamp: number): void{
    const progress = this.getProgress(timestamp);
    this.ctx.clearRect(0, 0, this.width, this.height);
    this.draw(progress);
    if (progress < 1){
      this.scheduleRender();
    }else{
      this.prevData = null;
      this.animationStartAt = 0;
    }
  }

  private onPointerDown(e: PointerEvent): void{
    this.isPanning = true;
    this.panLastX = e.clientX;
    this.canvas.setPointerCapture(e.pointerId);
  }

  private onPointerMove(e: PointerEvent): void{
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (this.isPanning){
      const dx = e.clientX - this.panLastX;
      this.panLastX = e.clientX;
      const span = Math.max(0.0001, this.viewXMax - this.viewXMin);
      const deltaX = (dx / Math.max(1, this.plot.width)) * span;
      this.viewXMin -= deltaX;
      this.viewXMax -= deltaX;
      this.clampView();
      this.scheduleRender();
      return;
    }

    this.updateHover(x, y);
    this.scheduleRender();
  }

  private onPointerUp(): void{
    this.isPanning = false;
  }

  private onPointerLeave(): void{
    if (this.isPanning) return;
    this.clearHover();
    this.emitHover(null);
    this.scheduleRender();
  }

  private onWheel(e: WheelEvent): void{
    e.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const focusX = this.pixelToX(mouseX);

    const factor = Math.exp(e.deltaY * 0.0015);
    const span = Math.max(0.0001, this.viewXMax - this.viewXMin);
    const dataSpan = Math.max(0.0001, this.dataXMax - this.dataXMin);
    const minSpan = Math.min(this.minZoomSpan, dataSpan);
    const maxSpan = dataSpan;
    const nextSpan = clamp(span * factor, minSpan, maxSpan);
    const ratio = (focusX - this.viewXMin) / span;

    this.viewXMin = focusX - ratio * nextSpan;
    this.viewXMax = this.viewXMin + nextSpan;
    this.clampView();
    this.scheduleRender();
  }

  private clampView(): void{
    const domainSpan = Math.max(0.0001, this.dataXMax - this.dataXMin);
    const minSpan = Math.min(this.minZoomSpan, domainSpan);
    let span = clamp(this.viewXMax - this.viewXMin, minSpan, domainSpan);
    if (!Number.isFinite(span) || span <= 0) span = domainSpan;

    const minX = this.dataXMin;
    const maxX = this.dataXMax;

    if (this.viewXMin < minX){
      this.viewXMin = minX;
      this.viewXMax = this.viewXMin + span;
    }
    if (this.viewXMax > maxX){
      this.viewXMax = maxX;
      this.viewXMin = this.viewXMax - span;
    }
  }
}
