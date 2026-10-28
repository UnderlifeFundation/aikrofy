'use client';

import { useEffect, useRef } from 'react';
import type { BrainNode, SynapticEdge } from '@/lib/use-living-brain';

interface Props {
  nodes: BrainNode[];
  edges: SynapticEdge[];
  /** Optional fixed height in px. By default the canvas fills its container. */
  height?: number;
  className?: string;
  onNodeClick?: (node: BrainNode) => void;
  onNodeDoubleClick?: (node: BrainNode) => void;
}

/* ──────────────────────────────────────────────────────────────────────────
 * Visual config for the "hub" nodes that come from the telemetry hook.
 * Everything else (the dense mesh of small neurons) is generated locally.
 * ────────────────────────────────────────────────────────────────────────── */
const NODE_CONFIG: Record<
  string,
  { radius: number; color: string; shape: 'circle' | 'hexagon' | 'diamond'; kind: string }
> = {
  conductor: { radius: 24, color: '#a78bfa', shape: 'circle', kind: 'Conductor IA' },
  agent: { radius: 18, color: '#60a5fa', shape: 'circle', kind: 'Agente' },
  rag_chunk: { radius: 14, color: '#22d3ee', shape: 'hexagon', kind: 'Memoria / RAG' },
  tool: { radius: 15, color: '#34d399', shape: 'diamond', kind: 'Herramienta' },
  query: { radius: 17, color: '#fbbf24', shape: 'circle', kind: 'Consulta entrante' },
  pulse: { radius: 11, color: '#94a3b8', shape: 'circle', kind: 'Pulso' },
  lem: { radius: 22, color: '#f59e0b', shape: 'diamond', kind: 'Guardián LEM (E < 0.20)' },
  channel: { radius: 18, color: '#10b981', shape: 'circle', kind: 'Canal Habilitado' },
};

// Coordinate space the hook uses for its default node layout.
const HOOK_W = 900;
const HOOK_H = 580;
const MAX_PHOTONS = 320;
// Probability that a photon arriving at a neuron re-emits, indexed by generation.
const CHAIN_PROB = [0.95, 0.72, 0.5, 0.3, 0];

/* ───────────────────────────── helpers ───────────────────────────── */
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const spriteCache = new Map<string, HTMLCanvasElement>();
/** Pre-rendered soft radial glow — far cheaper than ctx.shadowBlur per frame. */
function glowSprite(color: string): HTMLCanvasElement {
  const cached = spriteCache.get(color);
  if (cached) return cached;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, color);
  grad.addColorStop(0.25, color + '99');
  grad.addColorStop(0.6, color + '22');
  grad.addColorStop(1, color + '00');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  spriteCache.set(color, c);
  return c;
}

function tracePath(
  ctx: CanvasRenderingContext2D,
  shape: 'circle' | 'hexagon' | 'diamond',
  x: number,
  y: number,
  r: number,
) {
  ctx.beginPath();
  if (shape === 'hexagon') {
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 6;
      const px = x + r * Math.cos(a);
      const py = y + r * Math.sin(a);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
  } else if (shape === 'diamond') {
    ctx.moveTo(x, y - r);
    ctx.lineTo(x + r, y);
    ctx.lineTo(x, y + r);
    ctx.lineTo(x - r, y);
    ctx.closePath();
  } else {
    ctx.arc(x, y, r, 0, Math.PI * 2);
  }
}

/* ───────────────────────────── simulation types ───────────────────────────── */
interface Sim {
  id: string;
  hub: boolean;
  type: string;
  label: string;
  color: string;
  shape: 'circle' | 'hexagon' | 'diamond';
  r: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  hfx: number; // home position (fraction of canvas) — hubs only
  hfy: number;
  act: number; // current activation 0..1
  glow: number; // resting glow from telemetry (hubs)
  phase: number;
}
interface Link {
  a: number;
  b: number;
  rest: number;
  curv: number;
  color: string;
  hubEdge: boolean;
  hot: number;
}
interface Photon {
  l: number;
  t: number;
  dir: 1 | -1;
  speed: number;
  color: string;
  size: number;
  delay: number;
  gen: number;
}
interface Star {
  x: number;
  y: number;
  s: number;
  p: number;
}
interface World {
  w: number;
  h: number;
  sims: Sim[];
  links: Link[];
  adj: number[][]; // sim index -> link indices
  photons: Photon[];
  stars: Star[];
  hubIndex: Map<string, number>;
  hubLink: Map<string, number>;
  prevNodeActive: Map<string, boolean>;
  prevEdgeActive: Map<string, boolean>;
  hover: number;
  drag: number;
  mx: number;
  my: number;
  mouseIn: boolean;
  lastT: number;
  nextFire: number;
  rnd: () => number;
  ambientCount: number;
}

export function LivingBrainCanvas({ nodes, edges, height, className = '', onNodeClick, onNodeDoubleClick }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const worldRef = useRef<World | null>(null);
  const sizeRef = useRef({ w: 0, h: 0, dpr: 1 });
  const latest = useRef({ nodes, edges });
  const syncRef = useRef<() => void>(() => {});
  const pulseRef = useRef<(idx: number) => void>(() => {});

  /* Keep latest props reachable from the animation loop, then diff them in. */
  useEffect(() => {
    latest.current = { nodes, edges };
    syncRef.current();
  }, [nodes, edges]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    /* ── world construction ───────────────────────────────────────── */
    const build = (w: number, h: number): World | null => {
      const { nodes: hubNodes, edges: hubEdges } = latest.current;
      if (!hubNodes.length) return null;
      const rnd = mulberry32(20261014);
      const sc = Math.max(0.7, Math.min(1.15, Math.min(w, h) / 520));

      const sims: Sim[] = [];
      const hubIndex = new Map<string, number>();

      hubNodes.forEach((n) => {
        const cfg = NODE_CONFIG[n.type] || NODE_CONFIG.agent;
        hubIndex.set(n.id, sims.length);
        sims.push({
          id: n.id,
          hub: true,
          type: n.type,
          label: n.label,
          color: cfg.color,
          shape: cfg.shape,
          r: cfg.radius * sc,
          x: (n.x / HOOK_W) * w,
          y: (n.y / HOOK_H) * h,
          vx: 0,
          vy: 0,
          hfx: n.x / HOOK_W,
          hfy: n.y / HOOK_H,
          act: 0,
          glow: n.glowIntensity,
          phase: n.pulsePhase,
        });
      });

      // Dense mesh of small "neurons" clustered around the hubs.
      const hubCount = sims.length;
      const weights = sims.map((s) => (s.type === 'conductor' ? 3.2 : 1));
      const totalW = weights.reduce((a, b) => a + b, 0);
      const ambientTarget = Math.max(44, Math.min(110, Math.round((w * h) / 5200)));
      const parentOf: number[] = [];
      for (let i = 0; i < ambientTarget; i++) {
        let pick = rnd() * totalW;
        let p = 0;
        for (; p < hubCount - 1; p++) {
          pick -= weights[p];
          if (pick <= 0) break;
        }
        const parent = sims[p];
        const ang = rnd() * Math.PI * 2;
        const dist = (36 + rnd() * rnd() * 190) * sc;
        sims.push({
          id: `n${i}`,
          hub: false,
          type: 'neuron',
          label: '',
          color: parent.color,
          shape: 'circle',
          r: 1.5 + rnd() * 2.1,
          x: Math.max(24, Math.min(w - 24, parent.x + Math.cos(ang) * dist)),
          y: Math.max(24, Math.min(h - 24, parent.y + Math.sin(ang) * dist)),
          vx: 0,
          vy: 0,
          hfx: 0,
          hfy: 0,
          act: 0,
          glow: 0.1,
          phase: rnd() * 10,
        });
        parentOf.push(p);
      }

      const links: Link[] = [];
      const seen = new Map<string, number>();
      const pairKey = (a: number, b: number) => (a < b ? `${a}-${b}` : `${b}-${a}`);
      const addLink = (
        a: number,
        b: number,
        color: string,
        hubEdge: boolean,
        rest?: number,
      ): number => {
        if (a === b) return -1;
        const key = pairKey(a, b);
        const existing = seen.get(key);
        if (existing !== undefined) return existing;
        const d = Math.hypot(sims[a].x - sims[b].x, sims[a].y - sims[b].y);
        links.push({
          a,
          b,
          rest: rest ?? Math.max(18, d * 0.85),
          curv: (rnd() - 0.5) * 0.42,
          color,
          hubEdge,
          hot: 0,
        });
        seen.set(key, links.length - 1);
        return links.length - 1;
      };

      // Hub ↔ hub edges from the telemetry graph (reverse pairs share one link).
      const hubLink = new Map<string, number>();
      hubEdges.forEach((e) => {
        const a = hubIndex.get(e.source);
        const b = hubIndex.get(e.target);
        if (a === undefined || b === undefined) return;
        const li = addLink(a, b, e.color, true);
        if (li >= 0) hubLink.set(`${e.source}->${e.target}`, li);
      });

      // Each neuron → its hub, and → its 2 nearest neurons.
      for (let i = 0; i < ambientTarget; i++) {
        const idx = hubCount + i;
        addLink(idx, parentOf[i], sims[parentOf[i]].color, false, 40 * sc + rnd() * 50);
        const dists: Array<[number, number]> = [];
        for (let j = 0; j < ambientTarget; j++) {
          if (j === i) continue;
          const o = hubCount + j;
          dists.push([Math.hypot(sims[idx].x - sims[o].x, sims[idx].y - sims[o].y), o]);
        }
        dists.sort((x, y) => x[0] - y[0]);
        for (let k = 0; k < 2; k++) addLink(idx, dists[k][1], sims[idx].color, false);
      }

      const adj: number[][] = sims.map(() => []);
      links.forEach((l, li) => {
        adj[l.a].push(li);
        adj[l.b].push(li);
      });

      const stars: Star[] = Array.from({ length: 90 }, () => ({
        x: rnd(),
        y: rnd(),
        s: 0.3 + rnd() * 1.1,
        p: rnd() * 10,
      }));

      return {
        w,
        h,
        sims,
        links,
        adj,
        photons: [],
        stars,
        hubIndex,
        hubLink,
        prevNodeActive: new Map(),
        prevEdgeActive: new Map(),
        hover: -1,
        drag: -1,
        mx: 0,
        my: 0,
        mouseIn: false,
        lastT: 0,
        nextFire: 600,
        rnd,
        ambientCount: ambientTarget,
      };
    };

    /* ── photons & activation ─────────────────────────────────────── */
    const spawnPhoton = (
      wd: World,
      l: number,
      dir: 1 | -1,
      color: string,
      size: number,
      gen: number,
      delay = 0,
    ) => {
      if (wd.photons.length >= MAX_PHOTONS) return;
      wd.photons.push({
        l,
        t: 0,
        dir,
        speed: 0.5 + wd.rnd() * 0.55,
        color,
        size,
        delay,
        gen,
      });
    };

    /** Emit photons outward from a node along (some of) its synapses. */
    const emit = (wd: World, idx: number, gen: number, max: number, skipLink = -1) => {
      const sim = wd.sims[idx];
      const options = wd.adj[idx].filter((li) => li !== skipLink);
      for (let n = 0; n < max && options.length; n++) {
        const pick = Math.floor(wd.rnd() * options.length);
        const li = options.splice(pick, 1)[0];
        const dir: 1 | -1 = wd.links[li].a === idx ? 1 : -1;
        spawnPhoton(wd, li, dir, sim.color, sim.hub ? 3.2 : 2.2, gen);
      }
    };

    const pulse = (idx: number) => {
      const wd = worldRef.current;
      if (!wd) return;
      wd.sims[idx].act = 1;
      emit(wd, idx, 0, 99);
    };
    pulseRef.current = pulse;

    /** Diff incoming telemetry props against the sim and trigger visuals. */
    syncRef.current = () => {
      const wd = worldRef.current;
      if (!wd) return;
      const { nodes: ns, edges: es } = latest.current;
      ns.forEach((n) => {
        const idx = wd.hubIndex.get(n.id);
        if (idx === undefined) return;
        const sim = wd.sims[idx];
        sim.label = n.label;
        sim.glow = n.glowIntensity;
        const was = wd.prevNodeActive.get(n.id) || false;
        if (n.isActive && !was) pulse(idx);
        wd.prevNodeActive.set(n.id, n.isActive);
      });
      es.forEach((e) => {
        const key = `${e.source}->${e.target}`;
        const was = wd.prevEdgeActive.get(key) || false;
        if (e.isActive && !was) {
          const li = wd.hubLink.get(key);
          const from = wd.hubIndex.get(e.source);
          if (li !== undefined && from !== undefined) {
            wd.links[li].hot = 1;
            const dir: 1 | -1 = wd.links[li].a === from ? 1 : -1;
            for (let i = 0; i < 6; i++) spawnPhoton(wd, li, dir, e.color, 3.8, 3, i * 0.1);
          }
        }
        wd.prevEdgeActive.set(key, e.isActive);
      });
    };

    /* ── sizing ───────────────────────────────────────────────────── */
    const resize = () => {
      const rect = container.getBoundingClientRect();
      const w = Math.max(1, Math.round(rect.width));
      const h = Math.max(1, Math.round(height ?? rect.height));
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      sizeRef.current = { w, h, dpr };
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;

      const wd = worldRef.current;
      if (wd) {
        const sx = w / wd.w;
        const sy = h / wd.h;
        wd.sims.forEach((s) => {
          s.x *= sx;
          s.y *= sy;
        });
        wd.w = w;
        wd.h = h;
      }
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);

    /* ── frame loop ───────────────────────────────────────────────── */
    let raf = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const { w, h, dpr } = sizeRef.current;
      if (w < 2 || h < 2) return;

      if (!worldRef.current) {
        const built = build(w, h);
        if (!built) return;
        worldRef.current = built;
        syncRef.current();
      }
      const wd = worldRef.current;
      const dt = Math.min(0.033, wd.lastT ? (now - wd.lastT) / 1000 : 0.016);
      wd.lastT = now;
      const t = now * 0.001;
      const k60 = dt * 60;
      const { sims, links, adj } = wd;

      /* physics ---------------------------------------------------- */
      const sc = Math.max(0.7, Math.min(1.15, Math.min(w, h) / 520));
      const R = 118 * sc;
      for (let i = 0; i < sims.length; i++) {
        const A = sims[i];
        for (let j = i + 1; j < sims.length; j++) {
          const B = sims[j];
          const dx = B.x - A.x;
          const dy = B.y - A.y;
          const reach = A.hub || B.hub ? R * 1.5 : R;
          if (dx > reach || dx < -reach || dy > reach || dy < -reach) continue;
          const d = Math.hypot(dx, dy) || 0.01;
          if (d >= reach) continue;
          const f = (1 - d / reach) * (A.hub || B.hub ? 0.9 : 0.5) * k60;
          const fx = (dx / d) * f;
          const fy = (dy / d) * f;
          A.vx -= fx;
          A.vy -= fy;
          B.vx += fx;
          B.vy += fy;
        }
      }
      for (const l of links) {
        const A = sims[l.a];
        const B = sims[l.b];
        const dx = B.x - A.x;
        const dy = B.y - A.y;
        const d = Math.hypot(dx, dy) || 0.01;
        const f = (d - l.rest) * (l.hubEdge ? 0.0035 : 0.009) * k60;
        const fx = (dx / d) * f;
        const fy = (dy / d) * f;
        A.vx += fx;
        A.vy += fy;
        B.vx -= fx;
        B.vy -= fy;
      }
      const damp = Math.pow(0.9, k60);
      for (let i = 0; i < sims.length; i++) {
        const s = sims[i];
        if (s.hub) {
          s.vx += (s.hfx * w - s.x) * 0.012 * k60;
          s.vy += (s.hfy * h - s.y) * 0.012 * k60;
        } else {
          s.vx += (w / 2 - s.x) * 0.0006 * k60;
          s.vy += (h / 2 - s.y) * 0.0006 * k60;
        }
        if (!reduceMotion) {
          s.vx += Math.sin(t * 0.8 + s.phase * 3) * 0.02 * k60;
          s.vy += Math.cos(t * 0.7 + s.phase * 2) * 0.02 * k60;
        }
        if (wd.mouseIn && wd.drag < 0) {
          const mdx = s.x - wd.mx;
          const mdy = s.y - wd.my;
          const md = Math.hypot(mdx, mdy);
          if (md < 90 && md > 0.01) {
            const f = (1 - md / 90) * 0.7 * k60;
            s.vx += (mdx / md) * f;
            s.vy += (mdy / md) * f;
          }
        }
        if (wd.drag === i) {
          s.x = wd.mx;
          s.y = wd.my;
          s.vx = s.vy = 0;
        } else {
          s.vx *= damp;
          s.vy *= damp;
          s.x += s.vx * k60;
          s.y += s.vy * k60;
        }
        const pad = 22;
        if (s.x < pad) {
          s.x = pad;
          s.vx *= -0.3;
        } else if (s.x > w - pad) {
          s.x = w - pad;
          s.vx *= -0.3;
        }
        if (s.y < pad) {
          s.y = pad;
          s.vy *= -0.3;
        } else if (s.y > h - pad) {
          s.y = h - pad;
          s.vy *= -0.3;
        }
        s.act *= Math.exp(-dt * 1.7);
      }
      for (const l of links) l.hot *= Math.exp(-dt * 1.1);

      /* autonomous background firing ---------------------------- */
      if (now > wd.nextFire) {
        const idx = wd.sims.length - 1 - Math.floor(wd.rnd() * wd.ambientCount);
        sims[idx].act = Math.max(sims[idx].act, 0.9);
        emit(wd, idx, 1, 3);
        wd.nextFire = now + (reduceMotion ? 2200 : 450 + wd.rnd() * 900);
      }

      /* photons --------------------------------------------------- */
      for (let i = wd.photons.length - 1; i >= 0; i--) {
        const p = wd.photons[i];
        if (p.delay > 0) {
          p.delay -= dt;
          continue;
        }
        p.t += p.speed * dt;
        if (p.t >= 1) {
          const l = links[p.l];
          const target = p.dir === 1 ? l.b : l.a;
          const tgt = sims[target];
          tgt.act = Math.max(tgt.act, tgt.hub ? 1 : 0.85);
          if (wd.rnd() < (CHAIN_PROB[p.gen] ?? 0)) emit(wd, target, p.gen + 1, 2, p.l);
          wd.photons.splice(i, 1);
        }
      }

      /* ───────────────────────── render ───────────────────────── */
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;

      const bg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.75);
      bg.addColorStop(0, '#0e0a26');
      bg.addColorStop(0.55, '#06061a');
      bg.addColorStop(1, '#02040c');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // Slow drifting nebula
      const nebula: Array<[number, number, string]> = [
        [0.3 + Math.sin(t * 0.07) * 0.1, 0.35 + Math.cos(t * 0.05) * 0.1, '#7c3aed'],
        [0.72 + Math.cos(t * 0.06) * 0.1, 0.6 + Math.sin(t * 0.08) * 0.1, '#0891b2'],
        [0.5 + Math.sin(t * 0.04) * 0.15, 0.85, '#4f46e5'],
      ];
      ctx.globalAlpha = 0.16;
      for (const [fx, fy, col] of nebula) {
        const r = Math.max(w, h) * 0.5;
        ctx.drawImage(glowSprite(col), fx * w - r, fy * h - r, r * 2, r * 2);
      }

      // Stars
      ctx.fillStyle = '#cbd5e1';
      for (const s of wd.stars) {
        ctx.globalAlpha = 0.12 + 0.25 * (0.5 + 0.5 * Math.sin(t * 0.9 + s.p));
        const sx = (s.x * w + Math.sin(t * 0.05 + s.p) * 6 + w) % w;
        ctx.fillRect(sx, s.y * h, s.s, s.s);
      }

      // Everything luminous is additive.
      ctx.globalCompositeOperation = 'lighter';

      // Synapses
      for (const l of links) {
        const A = sims[l.a];
        const B = sims[l.b];
        const mx = (A.x + B.x) / 2;
        const my = (A.y + B.y) / 2;
        const len = Math.hypot(B.x - A.x, B.y - A.y) || 1;
        const cx = mx + (-(B.y - A.y) / len) * len * l.curv;
        const cy = my + ((B.x - A.x) / len) * len * l.curv;
        const energy = Math.max(A.act, B.act);
        ctx.globalAlpha = Math.min(
          0.95,
          (l.hubEdge ? 0.16 : 0.07) + energy * 0.28 + l.hot * 0.65,
        );
        ctx.strokeStyle = l.color;
        ctx.lineWidth = l.hubEdge ? 1.2 + l.hot * 2 : 0.7 + energy * 0.8;
        ctx.beginPath();
        ctx.moveTo(A.x, A.y);
        ctx.quadraticCurveTo(cx, cy, B.x, B.y);
        ctx.stroke();
      }

      // Photons (comet tails)
      for (const p of wd.photons) {
        if (p.delay > 0) continue;
        const l = links[p.l];
        const A = sims[l.a];
        const B = sims[l.b];
        const mx = (A.x + B.x) / 2;
        const my = (A.y + B.y) / 2;
        const len = Math.hypot(B.x - A.x, B.y - A.y) || 1;
        const cx = mx + (-(B.y - A.y) / len) * len * l.curv;
        const cy = my + ((B.x - A.x) / len) * len * l.curv;
        const sprite = glowSprite(p.color);
        for (let tail = 0; tail < 3; tail++) {
          const tt = Math.max(0, p.t - tail * 0.035);
          const u = p.dir === 1 ? tt : 1 - tt;
          const iu = 1 - u;
          const px = iu * iu * A.x + 2 * iu * u * cx + u * u * B.x;
          const py = iu * iu * A.y + 2 * iu * u * cy + u * u * B.y;
          const s = p.size * (tail === 0 ? 7 : 5 - tail * 1.3);
          ctx.globalAlpha = tail === 0 ? 0.95 : 0.4 / tail;
          ctx.drawImage(sprite, px - s / 2, py - s / 2, s, s);
          if (tail === 0) {
            ctx.globalAlpha = 1;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(px, py, p.size * 0.38, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // Neurons & hubs
      for (let i = 0; i < sims.length; i++) {
        const s = sims[i];
        const sprite = glowSprite(s.color);
        if (!s.hub) {
          const a = Math.min(1, 0.35 + s.act * 0.65);
          const tw = 0.85 + 0.15 * Math.sin(t * 2 + s.phase);
          const gs = s.r * (6 + s.act * 9) * tw;
          ctx.globalAlpha = Math.min(1, 0.3 + s.act * 0.7);
          ctx.drawImage(sprite, s.x - gs / 2, s.y - gs / 2, gs, gs);
          ctx.globalAlpha = a;
          ctx.fillStyle = s.act > 0.5 ? '#ffffff' : s.color;
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.r * (1 + s.act * 0.6), 0, Math.PI * 2);
          ctx.fill();
          continue;
        }

        const breathe = 1 + Math.sin(t * 1.4 + s.phase) * 0.05;
        const rr = s.r * breathe * (1 + s.act * 0.18);
        const energy = Math.min(1, 0.25 + s.glow * 0.5 + s.act);
        const gs = rr * (4.2 + s.act * 4);
        ctx.globalAlpha = Math.min(1, 0.45 + energy * 0.5);
        ctx.drawImage(sprite, s.x - gs / 2, s.y - gs / 2, gs, gs);

        tracePath(ctx, s.shape, s.x, s.y, rr);
        const fill = ctx.createRadialGradient(s.x - rr * 0.3, s.y - rr * 0.3, 0, s.x, s.y, rr);
        fill.addColorStop(0, s.act > 0.3 ? '#ffffff' : s.color);
        fill.addColorStop(0.55, s.color);
        fill.addColorStop(1, s.color + '55');
        ctx.globalAlpha = 0.95;
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.globalAlpha = 0.7;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        if (s.type === 'conductor') {
          ctx.globalAlpha = 0.5 + s.act * 0.4;
          ctx.strokeStyle = s.color;
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 7]);
          ctx.lineDashOffset = -t * 14;
          ctx.beginPath();
          ctx.arc(s.x, s.y, rr + 8, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }

      // Labels, tooltip, HUD — normal blending
      ctx.globalCompositeOperation = 'source-over';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.font = '600 11px Inter, system-ui, sans-serif';
      for (const s of sims) {
        if (!s.hub) continue;
        ctx.globalAlpha = 0.55 + Math.min(1, s.act + s.glow) * 0.45;
        ctx.fillStyle = '#e2e8f0';
        ctx.fillText(s.label.slice(0, 20), s.x, s.y + s.r + 9);
      }

      if (wd.hover >= 0) {
        const s = sims[wd.hover];
        const title = s.hub ? s.label : 'Neurona de la malla';
        const sub = s.hub
          ? `${NODE_CONFIG[s.type]?.kind ?? s.type} · activación ${Math.round(Math.min(1, s.act + s.glow * 0.5) * 100)}%`
          : `${adj[wd.hover].length} sinapsis · activación ${Math.round(s.act * 100)}%`;
        ctx.font = '600 11px Inter, system-ui, sans-serif';
        const tw = Math.max(ctx.measureText(title).width, ctx.measureText(sub).width) + 20;
        const tx = Math.min(w - tw - 6, Math.max(6, s.x + 14));
        const ty = Math.max(6, Math.min(h - 46, s.y - 44));
        ctx.globalAlpha = 0.92;
        ctx.fillStyle = '#0b1020';
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(tx, ty, tw, 38, 8);
        ctx.fill();
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.textAlign = 'left';
        ctx.fillStyle = '#f1f5f9';
        ctx.fillText(title, tx + 10, ty + 7);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.fillText(sub, tx + 10, ty + 22);
      }

      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.font = '10px ui-monospace, SFMono-Regular, monospace';
      ctx.globalAlpha = 0.55;
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(
        `${wd.ambientCount} neuronas · ${links.length} sinapsis · ${wd.photons.length} fotones en vuelo`,
        14,
        h - 12,
      );
      ctx.globalAlpha = 1;
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      syncRef.current = () => {};
      pulseRef.current = () => {};
      worldRef.current = null;
    };
    // Canvas lifecycle is independent of props; props flow in through `latest`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);

  /* ── pointer interaction ──────────────────────────────────────── */
  const localPoint = (e: React.PointerEvent | React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };
  const hit = (x: number, y: number) => {
    const wd = worldRef.current;
    if (!wd) return -1;
    let best = -1;
    let bestD = Infinity;
    wd.sims.forEach((s, i) => {
      const d = Math.hypot(s.x - x, s.y - y);
      const reach = (s.hub ? s.r : s.r + 3) + 8;
      if (d < reach && d < bestD) {
        best = i;
        bestD = d;
      }
    });
    return best;
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full ${height ? '' : 'h-full min-h-[320px]'} ${className}`}
      style={height ? { height } : undefined}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 touch-none rounded-xl"
        style={{ cursor: 'grab' }}
        onPointerMove={(e) => {
          const wd = worldRef.current;
          if (!wd) return;
          const p = localPoint(e);
          wd.mx = p.x;
          wd.my = p.y;
          wd.mouseIn = true;
          if (wd.drag < 0) wd.hover = hit(p.x, p.y);
        }}
        onPointerDown={(e) => {
          const wd = worldRef.current;
          if (!wd) return;
          const p = localPoint(e);
          const idx = hit(p.x, p.y);
          if (idx >= 0) {
            wd.drag = idx;
            wd.hover = idx;
            (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
            (e.target as HTMLCanvasElement).style.cursor = 'grabbing';
          }
        }}
        onPointerUp={(e) => {
          const wd = worldRef.current;
          if (!wd) return;
          wd.drag = -1;
          (e.target as HTMLCanvasElement).style.cursor = 'grab';
        }}
        onPointerLeave={() => {
          const wd = worldRef.current;
          if (!wd) return;
          wd.mouseIn = false;
          if (wd.drag < 0) wd.hover = -1;
        }}
        onDoubleClick={(e) => {
          const p = localPoint(e);
          const idx = hit(p.x, p.y);
          if (idx >= 0) {
            pulseRef.current(idx);
            const wd = worldRef.current;
            if (wd && wd.sims[idx]) {
              const sim = wd.sims[idx];
              const matchedNode = latest.current.nodes.find((n) => n.id === sim.id);
              if (matchedNode && onNodeDoubleClick) {
                onNodeDoubleClick(matchedNode);
              }
            }
          }
        }}
      />
    </div>
  );
}
