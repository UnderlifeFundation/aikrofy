'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { BarChart3, TrendingUp, PieChart as PieIcon, LineChart as LineIcon, Download } from 'lucide-react';

export interface ChartDataPoint {
  label: string;
  value: number;
  [key: string]: any;
}

export interface ChartConfig {
  title?: string;
  type: 'bar' | 'line' | 'pie' | 'area';
  data: ChartDataPoint[];
  color?: string;
  colors?: string[];
  /** Map of label → color for precise per-item color assignment.
   *  e.g. {"Caliente (80-100)": "rojo", "Templado (50-79)": "amarillo", "Frío (0-49)": "azul"}
   *  itemColors takes priority over colors[] and DEFAULT_COLORS. */
  itemColors?: Record<string, string>;
  xKey?: string;
  yKey?: string;
}

const DEFAULT_COLORS = [
  '#8b5cf6', // Violet
  '#3b82f6', // Blue
  '#10b981', // Emerald
  '#f59e0b', // Amber
  '#ec4899', // Pink
  '#06b6d4', // Cyan
  '#6366f1', // Indigo
  '#f97316', // Orange
  '#14b8a6', // Teal
  '#a855f7', // Purple
];

const COLOR_MAP: Record<string, string> = {
  // Spanish
  'rojo': '#ef4444',
  'roja': '#ef4444',
  'rojo oscuro': '#b91c1c',
  'verde': '#22c55e',
  'verde oscuro': '#15803d',
  'verde claro': '#86efac',
  'azul': '#3b82f6',
  'azul oscuro': '#1d4ed8',
  'azul claro': '#93c5fd',
  'amarillo': '#eab308',
  'amarilla': '#eab308',
  'amarillo claro': '#fef08a',
  'naranja': '#f97316',
  'naranja oscuro': '#c2410c',
  'morado': '#a855f7',
  'morada': '#a855f7',
  'purpura': '#a855f7',
  'violeta': '#8b5cf6',
  'lila': '#c084fc',
  'rosa': '#ec4899',
  'rosado': '#ec4899',
  'fucsia': '#d946ef',
  'celeste': '#06b6d4',
  'turquesa': '#14b8a6',
  'cian': '#06b6d4',
  'esmeralda': '#10b981',
  'ambar': '#f59e0b',
  'lima': '#84cc16',
  'dorado': '#eab308',
  'plateado': '#94a3b8',
  'marron': '#78350f',
  'cafe': '#78350f',
  'gris': '#64748b',
  'gris oscuro': '#334155',
  'gris claro': '#94a3b8',
  'negro': '#0f172a',
  'blanco': '#f8fafc',
  // English
  'red': '#ef4444',
  'green': '#22c55e',
  'blue': '#3b82f6',
  'yellow': '#eab308',
  'orange': '#f97316',
  'purple': '#a855f7',
  'pink': '#ec4899',
  'cyan': '#06b6d4',
  'teal': '#14b8a6',
  'gray': '#64748b',
  'grey': '#64748b',
  'black': '#0f172a',
  'white': '#f8fafc',
  'emerald': '#10b981',
  'amber': '#f59e0b',
  'indigo': '#6366f1',
  'violet': '#8b5cf6',
  'lime': '#84cc16',
  'sky': '#0ea5e9',
  'fuchsia': '#d946ef',
  'rose': '#f43f5e',
  'gold': '#eab308',
  'silver': '#94a3b8',
  'brown': '#78350f',
};

/**
 * Resolves a color name / hex string to a valid CSS hex color.
 * Supports Spanish/English names, direct hex (#RRGGBB / #RGB), and bare hex strings.
 */
export function normalizeColor(c?: string, fallback = '#8b5cf6'): string {
  if (!c || typeof c !== 'string') return fallback;
  const trimmed = c.trim().toLowerCase();
  const cleaned = trimmed.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (COLOR_MAP[cleaned]) return COLOR_MAP[cleaned];
  if (COLOR_MAP[trimmed]) return COLOR_MAP[trimmed];
  if (trimmed.startsWith('#')) return trimmed;
  // bare hex without # (e.g. "ef4444")
  if (/^[0-9a-f]{3,8}$/i.test(trimmed)) return `#${trimmed}`;
  return fallback;
}

function adjustLightness(hex: string, percent: number): string {
  let clean = hex.replace('#', '');
  if (clean.length === 3) clean = clean.split('').map(x => x + x).join('');
  let num = parseInt(clean, 16);
  if (isNaN(num)) return hex;
  let r = (num >> 16) + Math.round(255 * (percent / 100));
  let g = ((num >> 8) & 0x00FF) + Math.round(255 * (percent / 100));
  let b = (num & 0x0000FF) + Math.round(255 * (percent / 100));
  r = Math.min(255, Math.max(0, r));
  g = Math.min(255, Math.max(0, g));
  b = Math.min(255, Math.max(0, b));
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

function generateShades(baseHex: string, count: number): string[] {
  const hex = normalizeColor(baseHex, '#3b82f6');
  const shades: string[] = [];
  const step = 40 / Math.max(1, count - 1);
  for (let i = 0; i < count; i++) {
    const offset = -20 + (i * step);
    shades.push(adjustLightness(hex, offset));
  }
  return shades;
}

export function ChatChartWidget({ config }: { config: ChartConfig }) {
  if (!config || !config.data || !Array.isArray(config.data) || config.data.length === 0) {
    return null;
  }

  const { title, type = 'bar', data, color, colors, itemColors, xKey = 'label', yKey = 'value' } = config;

  const reactId = React.useId();
  // Stable gradient ID derived purely from useId() — no Math.random() to avoid SSR hydration mismatch
  const cleanId = reactId.replace(/[^a-zA-Z0-9]/g, '');
  const areaGradientId = `chartAreaGrad_${cleanId}`;

  /**
   * Color resolution priority (highest → lowest):
   *  0. point.color / point.fill — direct color property on data item (e.g. {"label": "Caliente", "color": "#ff0000"})
   *  1. itemColors[label]        — precise per-item color map specified by user
   *  2. colors[]                 — ordered array of colors for each bar/slice in sequence
   *  3. color                    — single base color → generates shades across items
   *  4. DEFAULT_COLORS           — vibrant default palette (each item gets a distinct color)
   */
  const resolvedColors: string[] = React.useMemo(() => {
    const cleanStr = (s: string) =>
      s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

    // 0. Check if individual objects inside data[] have explicit color properties (e.g. {"label": "Caliente", "value": 21, "color": "#ff0000"})
    const hasItemLevelColors = data.some(p => p.color || p.itemColor || p.fill || p.hex);
    if (hasItemLevelColors) {
      return data.map((point, i) => {
        const itemCol = point.color || point.itemColor || point.fill || point.hex;
        if (itemCol && typeof itemCol === 'string') {
          return normalizeColor(itemCol, DEFAULT_COLORS[i % DEFAULT_COLORS.length]);
        }
        return DEFAULT_COLORS[i % DEFAULT_COLORS.length];
      });
    }

    // 1. If itemColors provided (e.g. {"Caliente": "verde", "Templado": "azul", "Frío": "verde"})
    if (itemColors && typeof itemColors === 'object' && Object.keys(itemColors).length > 0) {
      const normalizedMap: Record<string, string> = {};
      for (const [k, v] of Object.entries(itemColors)) {
        normalizedMap[cleanStr(k)] = String(v);
      }

      return data.map((point, i) => {
        const rawLabel = String(point[xKey] || point.label || '');
        const cleanedLabel = cleanStr(rawLabel);

        // Exact match on cleaned string
        if (normalizedMap[cleanedLabel]) {
          return normalizeColor(normalizedMap[cleanedLabel], DEFAULT_COLORS[i % DEFAULT_COLORS.length]);
        }

        // Substring match (e.g. "caliente" matching "caliente (80-100)")
        for (const [mapKey, colVal] of Object.entries(normalizedMap)) {
          if (cleanedLabel.includes(mapKey) || mapKey.includes(cleanedLabel)) {
            return normalizeColor(colVal, DEFAULT_COLORS[i % DEFAULT_COLORS.length]);
          }
        }

        // Positional fallback if array colors available
        if (Array.isArray(colors) && colors[i]) {
          return normalizeColor(colors[i], DEFAULT_COLORS[i % DEFAULT_COLORS.length]);
        }
        return DEFAULT_COLORS[i % DEFAULT_COLORS.length];
      });
    }

    // 2. colors[] array provided (e.g. ["verde", "azul", "verde"] or ["#22c55e", "#3b82f6", "#22c55e"])
    if (Array.isArray(colors) && colors.length > 1) {
      return colors.map((c, i) => normalizeColor(c, DEFAULT_COLORS[i % DEFAULT_COLORS.length]));
    }
    if (Array.isArray(colors) && colors.length === 1) {
      const single = normalizeColor(colors[0], DEFAULT_COLORS[0]);
      return generateShades(single, data.length);
    }

    // 3. Single color provided -> generate shades
    if (color) {
      const single = normalizeColor(color, DEFAULT_COLORS[0]);
      return generateShades(single, data.length);
    }

    // 4. Default vibrant palette (each bar gets a distinct color)
    return DEFAULT_COLORS;
  }, [data, colors, color, itemColors, xKey]);

  const primaryColor = resolvedColors[0] || DEFAULT_COLORS[0];
  const totalVal = React.useMemo(() => data.reduce((acc, curr) => acc + (Number(curr[yKey]) || 0), 0), [data, yKey]);

  const containerRef = React.useRef<HTMLDivElement>(null);

  const exportAsCSV = () => {
    const headers = [xKey, yKey];
    const rows = data.map(d => [d[xKey], d[yKey]]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${title || 'chart'}_data.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportAsPNG = () => {
    if (!containerRef.current) return;
    const svgElement = containerRef.current.querySelector('svg');
    if (!svgElement) return;

    try {
      const xml = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' });
      const UrlObj = window.URL || (window as any).webkitURL;
      const blobURL = UrlObj.createObjectURL(svgBlob);

      const image = new Image();
      image.onload = () => {
        const canvas = document.createElement('canvas');
        const bbox = svgElement.getBoundingClientRect();
        canvas.width = (bbox.width || 400) * 2;
        canvas.height = (bbox.height || 220) * 2;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.scale(2, 2);
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(image, 0, 0);
          const png = canvas.toDataURL('image/png');
          const link = document.createElement('a');
          link.download = `${title || 'grafico'}_aikrofy.png`;
          link.href = png;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      };
      image.src = blobURL;
    } catch (e) {
      console.error("Failed to export chart as PNG:", e);
    }
  };

  const renderIcon = () => {
    switch (type) {
      case 'line': return <LineIcon className="h-4 w-4 text-blue-500" />;
      case 'pie': return <PieIcon className="h-4 w-4 text-emerald-500" />;
      case 'area': return <TrendingUp className="h-4 w-4 text-purple-500" />;
      default: return <BarChart3 className="h-4 w-4 text-violet-500" />;
    }
  };

  const renderCustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0];
      const itemVal = Number(item.value) || 0;
      const percentage = totalVal > 0 ? ((itemVal / totalVal) * 100).toFixed(1) : null;
      const fillColor = item.color || item.fill || item.payload?.fill || primaryColor;

      return (
        <div className="rounded-xl border border-border bg-slate-900/95 p-3 shadow-xl backdrop-blur-md text-white text-xs z-50">
          <div className="font-semibold border-b border-white/10 pb-1 mb-1.5 text-slate-200">{label}</div>
          <div className="flex items-center justify-between gap-4 font-medium">
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="h-2.5 w-2.5 rounded-full inline-block shadow-sm" style={{ backgroundColor: fillColor }} />
              {item.name || yKey}:
            </span>
            <span className="font-bold text-emerald-400">{typeof item.value === 'number' ? item.value.toLocaleString() : item.value}</span>
          </div>
          {percentage && (
            <div className="mt-1 text-[10px] text-slate-400 font-mono flex items-center justify-between gap-2">
              <span>Cuota / Proporción:</span>
              <span className="font-bold text-violet-300">{percentage}%</span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="mt-3 my-2 w-full rounded-2xl border border-border bg-card p-4 shadow-sm dark:border-white/10 dark:bg-slate-900/80 animate-fade-in">
      <div className="flex items-center justify-between border-b border-border/50 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          {renderIcon()}
          <span className="text-xs font-bold tracking-tight text-foreground">{title || 'Gráfico de Análisis'}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={exportAsPNG}
            className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted px-2.5 py-1 rounded-md border border-border/40 transition-all"
            title="Descargar imagen PNG del gráfico"
          >
            <Download className="h-3 w-3 text-violet-400" />
            <span>PNG</span>
          </button>
          <button
            onClick={exportAsCSV}
            className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted px-2.5 py-1 rounded-md border border-border/40 transition-all"
            title="Descargar datos CSV"
          >
            <Download className="h-3 w-3 text-blue-400" />
            <span>CSV</span>
          </button>
        </div>
      </div>

      <div ref={containerRef} className="w-full h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          {type === 'line' ? (
            <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
              <XAxis dataKey={xKey} tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <Tooltip content={renderCustomTooltip} />
              <Line type="monotone" dataKey={yKey} stroke={primaryColor} strokeWidth={2.5} dot={{ r: 5, fill: primaryColor }} activeDot={{ r: 7 }} />
            </LineChart>
          ) : type === 'area' ? (
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={areaGradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={primaryColor} stopOpacity={0.55} />
                  <stop offset="95%" stopColor={primaryColor} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
              <XAxis dataKey={xKey} tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <Tooltip content={renderCustomTooltip} />
              <Area type="monotone" dataKey={yKey} stroke={primaryColor} strokeWidth={2} fillOpacity={1} fill={`url(#${areaGradientId})`} dot={{ r: 4, fill: primaryColor }} />
            </AreaChart>
          ) : type === 'pie' ? (
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={75}
                paddingAngle={4}
                dataKey={yKey}
                nameKey={xKey}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={resolvedColors[index % resolvedColors.length]} />
                ))}
              </Pie>
              <Tooltip content={renderCustomTooltip} />
              <Legend wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          ) : (
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
              <XAxis dataKey={xKey} tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} />
              <Tooltip content={renderCustomTooltip} />
              <Bar dataKey={yKey} fill={primaryColor} radius={[6, 6, 0, 0]}>
                {data.map((_, index) => (
                  <Cell
                    key={`cell-bar-${index}`}
                    fill={resolvedColors[index % resolvedColors.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function parseChartJSON(text: string): { cleanText: string; chartConfig: ChartConfig | null; chartConfigs: ChartConfig[] } {
  if (!text) return { cleanText: '', chartConfig: null, chartConfigs: [] };

  const chartConfigs: ChartConfig[] = [];

  const sanitizeJsonStr = (rawStr: string) => {
    return rawStr
      .replace(/\/\/.*/g, '') // Remove // JS single-line comments
      .replace(/\/\*[\s\S]*?\*\//g, '') // Remove /* */ multi-line comments
      .replace(/,\s*([}\]])/g, '$1') // Remove trailing commas before } or ]
      .trim();
  };

  // Match both ```json:chart ... ``` and standard ```json ... ``` blocks
  const allChartRegex = /```(?:json:chart|json)\s*([\s\S]*?)\s*```/gi;
  let match;

  while ((match = allChartRegex.exec(text)) !== null) {
    const rawInner = match[1];
    const sanitized = sanitizeJsonStr(rawInner);
    try {
      const parsed = JSON.parse(sanitized);
      if (parsed) {
        // Normalize Chart.js format { labels: [...], datasets: [{ data: [...], label: ... }] } to Recharts format { data: [{ label, value }] }
        if (parsed.data && typeof parsed.data === 'object' && !Array.isArray(parsed.data)) {
          const rawDataObj = parsed.data;
          const labels: string[] = Array.isArray(rawDataObj.labels) ? rawDataObj.labels : [];
          const datasets: any[] = Array.isArray(rawDataObj.datasets) ? rawDataObj.datasets : [];
          const dataset = datasets[0] || {};
          const values: number[] = Array.isArray(dataset.data) ? dataset.data : [];

          const normalizedData = labels.map((lbl, idx) => ({
            label: String(lbl),
            value: Number(values[idx]) || 0
          }));

          parsed.data = normalizedData;
          if (!parsed.title && dataset.label) {
            parsed.title = dataset.label;
          }
          if (!parsed.color && (dataset.borderColor || dataset.backgroundColor)) {
            parsed.color = dataset.borderColor || dataset.backgroundColor;
          }
        }

        // Ensure parsed.data is an array and each item has label and value
        if (Array.isArray(parsed.data) && parsed.data.length > 0) {
          // Normalize individual items if needed
          parsed.data = parsed.data.map((item: any, idx: number) => {
            if (typeof item === 'object' && item !== null) {
              return {
                ...item,
                label: String(item.label ?? item.name ?? item.x ?? `Punto ${idx + 1}`),
                value: Number(item.value ?? item.y ?? item.count ?? 0)
              };
            }
            return { label: `Item ${idx + 1}`, value: Number(item) || 0 };
          });
          chartConfigs.push(parsed);
        } else if (parsed.type && !parsed.data) {
          // Empty or invalid data array, ignore to prevent client crash
          console.warn("[ChatChartWidget] Chart config has no valid data array:", parsed);
        }
      }
    } catch (e) {
      console.error("[ChatChartWidget] Failed to parse chart JSON block:", e, rawInner);
    }
  }

  // Strip chart code blocks from cleanText (ALWAYS strip json:chart blocks to avoid raw code leaking to UI)
  const replaceRegex = /```(?:json:chart|json)\s*([\s\S]*?)\s*```/gi;
  let cleanText = text.replace(replaceRegex, (fullMatch, group1) => {
    const isExplicitChart = fullMatch.toLowerCase().startsWith('```json:chart');
    if (isExplicitChart) return '';
    const sanitized = sanitizeJsonStr(group1);
    try {
      const parsed = JSON.parse(sanitized);
      if (parsed && (parsed.data || parsed.type)) {
        return '';
      }
    } catch (e) {}
    return fullMatch;
  });

  // Remove leftover empty headings (e.g. ### 1. Total de Conversaciones...) orphaned by chart removal
  cleanText = cleanText
    .replace(/^(?:###?\s*\d+\.\s*.*|^\d+\.\s*\*\*.*\*\*)\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return {
    cleanText,
    chartConfig: chartConfigs[0] || null,
    chartConfigs
  };
}
