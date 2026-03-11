<script setup lang="ts">
import { BarChart2D } from "@/charts/BarChart2D";
import type { BarChartData, ChartHoverPayload } from "@/charts/types";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  data: BarChartData;
  height?: number;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const hover = ref<ChartHoverPayload | null>(null);

let chart: BarChart2D | null = null;
let ro: ResizeObserver | null = null;

onMounted(() => {
  if (!canvasRef.value) return;
  chart = new BarChart2D(canvasRef.value, {
    minZoomSpan: 4,
    onHover: (payload) => {
      hover.value = payload;
    }
  });
  chart.setData(props.data);

  ro = new ResizeObserver(() => {
    chart?.resize();
  });
  ro.observe(canvasRef.value);
});

watch(() => props.data, (next) => {
  chart?.setData(next);
}, { deep: true });

onBeforeUnmount(() => {
  ro?.disconnect();
  ro = null;
  chart?.destroy();
  chart = null;
});
</script>

<template>
  <div class="chart-root">
    <canvas ref="canvasRef" class="chart-canvas" :style="{ height: `${height ?? 320}px` }" />
    <div v-if="hover" class="tooltip" :style="{ left: `${hover.x}px`, top: `${hover.y}px` }">
      <div class="tt-title">{{ hover.title }}</div>
      <div v-for="item in hover.items" :key="item.label" class="tt-row">
        <span class="dot" :style="{ background: item.color }"></span>
        <span class="name">{{ item.label }}</span>
        <span class="value mono">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-root{
  position: relative;
}
.chart-canvas{
  width: 100%;
  display: block;
  border-radius: 12px;
  touch-action: none;
  cursor: crosshair;
  background:
    radial-gradient(circle at 15% 15%, rgba(103,80,164,.07), transparent 44%),
    linear-gradient(180deg, #fdfbff, #ffffff);
}
.tooltip{
  position: absolute;
  pointer-events: none;
  min-width: 170px;
  max-width: 240px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,.10);
  box-shadow: var(--md-sys-elev-2);
  background: rgba(255,255,255,.95);
  backdrop-filter: blur(6px);
}
.tt-title{
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}
.tt-row{
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.dot{
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.name{
  flex: 1;
  color: rgba(0,0,0,.72);
}
.value{
  font-weight: 700;
}
</style>
