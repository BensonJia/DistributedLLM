export type ChartPadding = {
  top: number;
  right: number;
  bottom: number;
  left: number;
};

export type PlotArea = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

export type ChartLegendItem = {
  label: string;
  color: string;
  value: string;
};

export type ChartHoverPayload = {
  x: number;
  y: number;
  title: string;
  items: ChartLegendItem[];
};

export type LineSeries = {
  id: string;
  label: string;
  color: string;
  values: number[];
  width?: number;
};

export type LineChartData = {
  labels: string[];
  series: LineSeries[];
  yLabel?: string;
};

export type BarSeries = {
  id: string;
  label: string;
  color: string;
  values: number[];
};

export type BarChartData = {
  labels: string[];
  series: BarSeries[];
  yLabel?: string;
};

