'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import { Smartphone, Monitor } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface Stage {
  id: number | null;
  name: string;
  sort_order: number;
  count: number;
  value_usd: number;
}

interface Contact {
  id: number;
  name: string;
  stage_id: number | null;
  stage_name: string;
  relationship: 'hot' | 'warm' | 'cold';
  touches: number;
  source_channel: string;
  amount_usd: number;
  lead_score: number;
  phone?: string;
  email?: string;
}

interface Props {
  stages: Stage[];
  contacts: Contact[];
  width?: number;
  height?: number;
  onContactClick?: (contactId: number) => void;
}

const HEAT_COLORS: Record<string, string> = {
  hot: '#ef4444',
  warm: '#f97316',
  cold: '#60a5fa',
};

const STAGE_COLORS = [
  '#8b5cf6',
  '#6366f1',
  '#3b82f6',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
];

export function NeuralFunnelFlow({
  stages,
  contacts,
  width: propWidth = 900,
  height: propHeight = 480,
  onContactClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [containerWidth, setContainerWidth] = useState(propWidth);
  const [isMobileMode, setIsMobileMode] = useState(false);

  // ResizeObserver for responsive canvas
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.round(entry.contentRect.width);
        if (w > 0) {
          setContainerWidth(w);
          setIsMobileMode(w < 640);
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const draw = useCallback(() => {
    if (!svgRef.current || stages.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const currentW = Math.max(320, containerWidth);
    const isSmall = currentW < 640;

    // Tooltip instance
    const tooltip = d3
      .select('body')
      .selectAll('.funnel-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'funnel-tooltip')
      .style('position', 'fixed')
      .style('background', 'rgba(15,23,42,0.95)')
      .style('color', '#f8fafc')
      .style('padding', '8px 12px')
      .style('border-radius', '10px')
      .style('border', '1px solid rgba(255,255,255,0.15)')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 9999)
      .style('max-width', '240px')
      .style('box-shadow', '0 8px 32px rgba(0,0,0,0.4)');

    // In mobile mode, we draw vertical layers with biological neural connection filaments
    if (isSmall) {
      const margin = { top: 24, right: 16, bottom: 44, left: 16 };
      const w = currentW - margin.left - margin.right;
      const stageH = Math.max(72, Math.floor(460 / stages.length));
      const totalH = stageH * stages.length + margin.top + margin.bottom;

      svg.attr('width', currentW).attr('height', totalH);

      const defs = svg.append('defs');
      stages.forEach((_, i) => {
        const grad = defs
          .append('linearGradient')
          .attr('id', `stageGradMob-${i}`)
          .attr('x1', '0%')
          .attr('y1', '0%')
          .attr('x2', '100%')
          .attr('y2', '0%');
        grad.append('stop').attr('offset', '0%').attr('stop-color', STAGE_COLORS[i % STAGE_COLORS.length]).attr('stop-opacity', 0.22);
        grad.append('stop').attr('offset', '100%').attr('stop-color', STAGE_COLORS[i % STAGE_COLORS.length]).attr('stop-opacity', 0.04);
      });

      // Bio neural pulse filter
      const filter = defs.append('filter').attr('id', 'mob-glow').attr('x', '-30%').attr('y', '-30%').attr('width', '160%').attr('height', '160%');
      filter.append('feGaussianBlur').attr('stdDeviation', 2.5).attr('result', 'coloredBlur');
      const feMerge = filter.append('feMerge');
      feMerge.append('feMergeNode').attr('in', 'coloredBlur');
      feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      // Inter-stage neural synapse lines in mobile
      for (let i = 0; i < stages.length - 1; i++) {
        const y1 = i * stageH + stageH - 8;
        const y2 = (i + 1) * stageH + 8;
        const xMid = w - 100;
        
        g.append('line')
          .attr('x1', xMid - 25)
          .attr('y1', y1)
          .attr('x2', xMid - 10)
          .attr('y2', y2)
          .attr('stroke', STAGE_COLORS[i % STAGE_COLORS.length])
          .attr('stroke-width', 1.5)
          .attr('stroke-dasharray', '3,3')
          .attr('stroke-opacity', 0.45);

        g.append('line')
          .attr('x1', xMid + 20)
          .attr('y1', y1)
          .attr('x2', xMid + 10)
          .attr('y2', y2)
          .attr('stroke', STAGE_COLORS[(i + 1) % STAGE_COLORS.length])
          .attr('stroke-width', 1.5)
          .attr('stroke-dasharray', '4,3')
          .attr('stroke-opacity', 0.45);
      }

      // Stages as stacked horizontal funnel bars
      stages.forEach((stage, i) => {
        const stageG = g.append('g').attr('transform', `translate(0, ${i * stageH})`);

        // Layer background
        stageG
          .append('rect')
          .attr('width', w)
          .attr('height', stageH - 8)
          .attr('rx', 12)
          .attr('fill', `url(#stageGradMob-${i})`)
          .attr('stroke', STAGE_COLORS[i % STAGE_COLORS.length])
          .attr('stroke-opacity', 0.35)
          .attr('stroke-width', 1.2);

        // Stage Title & Count
        stageG
          .append('text')
          .attr('x', 14)
          .attr('y', 24)
          .attr('font-size', 13)
          .attr('font-weight', '700')
          .attr('fill', STAGE_COLORS[i % STAGE_COLORS.length])
          .text(stage.name);

        stageG
          .append('text')
          .attr('x', 14)
          .attr('y', 42)
          .attr('font-size', 11)
          .attr('fill', '#94a3b8')
          .text(`${stage.count} leads · $${stage.value_usd.toLocaleString()}`);

        // Contact dots within this stage layer
        const stageContacts = contacts.filter((c) => c.stage_id === stage.id).slice(0, 16);
        const dotsContainerW = Math.min(180, w * 0.48);
        const dotG = stageG.append('g').attr('transform', `translate(${w - dotsContainerW - 10}, 0)`);

        stageContacts.forEach((contact, ci) => {
          // Wrap into 2 micro-rows if there are many contacts
          const inRow2 = ci >= 8;
          const colIndex = inRow2 ? ci - 8 : ci;
          const cx = Math.min(dotsContainerW, colIndex * 18 + 12);
          const cy = inRow2 ? (stageH - 8) * 0.68 : (stageH - 8) * 0.36;
          const r = Math.max(5.5, Math.min(8.5, 5 + (contact.lead_score / 100) * 3.5));

          const circle = dotG
            .append('circle')
            .attr('cx', cx)
            .attr('cy', cy)
            .attr('r', r)
            .attr('fill', HEAT_COLORS[contact.relationship] || '#60a5fa')
            .attr('fill-opacity', 0.9)
            .attr('stroke', '#ffffff')
            .attr('stroke-width', 1.5)
            .style('cursor', 'pointer')
            .attr('filter', 'url(#mob-glow)');

          // Pulse animation on hot/high score dots
          if (contact.relationship === 'hot' || contact.lead_score >= 70) {
            circle
              .append('animate')
              .attr('attributeName', 'r')
              .attr('values', `${r};${r + 2};${r}`)
              .attr('dur', '2s')
              .attr('repeatCount', 'indefinite');
          }

          // Tooltip on hover/touch
          circle
            .on('mouseenter touchstart', (event: any) => {
              const clientX = event.touches ? event.touches[0].clientX : event.clientX;
              const clientY = event.touches ? event.touches[0].clientY : event.clientY;
              tooltip
                .style('opacity', 1)
                .html(
                  `<strong>${contact.name}</strong><br/>` +
                  `Etapa: <strong>${contact.stage_name}</strong><br/>` +
                  `Score: <strong>${contact.lead_score}</strong> (${contact.relationship.toUpperCase()})<br/>` +
                  `Canal: ${contact.source_channel}<br/>` +
                  `<span style="color:#a78bfa;font-size:11px;">Toca para abrir perfil →</span>`
                )
                .style('left', Math.min(window.innerWidth - 250, Math.max(10, clientX - 100)) + 'px')
                .style('top', Math.max(10, clientY - 80) + 'px');
            })
            .on('mouseleave touchend', () => {
              tooltip.style('opacity', 0);
            })
            .on('click', (event: MouseEvent) => {
              event.stopPropagation();
              tooltip.style('opacity', 0);
              onContactClick?.(contact.id);
            });
        });
      });

      return () => {
        d3.select('body').selectAll('.funnel-tooltip').remove();
      };
    }

    // ── Desktop / Tablet Mode: Horizontal Force Columns ────────────────
    const margin = { top: 40, right: 30, bottom: 60, left: 30 };
    const w = currentW - margin.left - margin.right;
    const h = propHeight - margin.top - margin.bottom;

    const g = svg
      .attr('width', currentW)
      .attr('height', propHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const defs = svg.append('defs');
    stages.forEach((stage, i) => {
      const grad = defs
        .append('linearGradient')
        .attr('id', `stageGrad-${i}`)
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '0%')
        .attr('y2', '100%');
      grad
        .append('stop')
        .attr('offset', '0%')
        .attr('stop-color', STAGE_COLORS[i % STAGE_COLORS.length])
        .attr('stop-opacity', 0.18);
      grad
        .append('stop')
        .attr('offset', '100%')
        .attr('stop-color', STAGE_COLORS[i % STAGE_COLORS.length])
        .attr('stop-opacity', 0.03);
    });

    // Drop shadow
    const filter = defs.append('filter').attr('id', 'shadow').attr('x', '-30%').attr('y', '-30%').attr('width', '160%').attr('height', '160%');
    filter.append('feDropShadow').attr('dx', 0).attr('dy', 3).attr('stdDeviation', 4).attr('flood-opacity', 0.35);

    // Glow filter for neural biological pulses
    const bioGlow = defs.append('filter').attr('id', 'bio-glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    bioGlow.append('feGaussianBlur').attr('stdDeviation', 3.5).attr('result', 'coloredBlur');
    const bgMerge = bioGlow.append('feMerge');
    bgMerge.append('feMergeNode').attr('in', 'coloredBlur');
    bgMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    const stageWidth = w / stages.length;

    // Background columns
    const stageGs = g
      .selectAll('.stage')
      .data(stages)
      .join('g')
      .attr('class', 'stage')
      .attr('transform', (_, i) => `translate(${i * stageWidth}, 0)`);

    stageGs
      .append('rect')
      .attr('width', stageWidth - 10)
      .attr('height', h)
      .attr('rx', 14)
      .attr('fill', (_, i) => `url(#stageGrad-${i})`)
      .attr('stroke', (_, i) => STAGE_COLORS[i % STAGE_COLORS.length])
      .attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1.2);

    stageGs
      .append('text')
      .attr('x', stageWidth / 2 - 5)
      .attr('y', -14)
      .attr('text-anchor', 'middle')
      .attr('font-size', Math.min(13, Math.max(10, Math.floor(stageWidth / 10))))
      .attr('font-weight', '700')
      .attr('fill', (_, i) => STAGE_COLORS[i % STAGE_COLORS.length])
      .text((d) => d.name);

    stageGs
      .append('text')
      .attr('x', stageWidth / 2 - 5)
      .attr('y', -2)
      .attr('text-anchor', 'middle')
      .attr('font-size', 11)
      .attr('fill', '#94a3b8')
      .text((d) => `${d.count} · $${d.value_usd.toLocaleString()}`);

    const stageIndexMap = new Map(stages.map((s, i) => [s.id, i]));

    const nodes = contacts.slice(0, 140).map((c) => {
      const si = stageIndexMap.has(c.stage_id) ? stageIndexMap.get(c.stage_id)! : 0;
      return {
        ...c,
        stageIndex: si,
        targetX: si * stageWidth + stageWidth / 2 - 5,
        targetY: h / 2,
        x: si * stageWidth + stageWidth / 2 - 5 + (Math.random() - 0.5) * 40,
        y: Math.random() * h,
        r: Math.max(5.5, Math.min(14, 5 + (c.lead_score / 100) * 8)),
      };
    });

    // Biological Neural Synaptic Connections between adjacent stages
    const synapseG = g.append('g').attr('class', 'synaptic-connections');
    for (let i = 0; i < stages.length - 1; i++) {
      const xStart = i * stageWidth + stageWidth - 10;
      const xEnd = (i + 1) * stageWidth;
      const midY1 = h * 0.35;
      const midY2 = h * 0.65;

      // Top synaptic wave
      const path1 = d3.path();
      path1.moveTo(xStart, midY1);
      path1.bezierCurveTo(xStart + (xEnd - xStart) / 2, midY1 - 20, xStart + (xEnd - xStart) / 2, midY2, xEnd, midY2);
      synapseG
        .append('path')
        .attr('d', path1.toString())
        .attr('fill', 'none')
        .attr('stroke', STAGE_COLORS[i % STAGE_COLORS.length])
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.4)
        .attr('stroke-dasharray', '4,4');

      // Bottom synaptic wave
      const path2 = d3.path();
      path2.moveTo(xStart, midY2);
      path2.bezierCurveTo(xStart + (xEnd - xStart) / 2, midY2 + 20, xStart + (xEnd - xStart) / 2, midY1, xEnd, midY1);
      synapseG
        .append('path')
        .attr('d', path2.toString())
        .attr('fill', 'none')
        .attr('stroke', STAGE_COLORS[(i + 1) % STAGE_COLORS.length])
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.4)
        .attr('stroke-dasharray', '5,5');
    }

    const sim = d3
      .forceSimulation(nodes as any)
      .force('x', d3.forceX((d: any) => d.targetX).strength(0.68))
      .force('y', d3.forceY(h / 2).strength(0.07))
      .force('collision', d3.forceCollide((d: any) => d.r + 3.5))
      .stop();

    for (let i = 0; i < 140; i++) sim.tick();

    // Contact bubbles (Neural cells)
    const nodeSelection = g
      .selectAll('.contact-node')
      .data(nodes)
      .join('circle')
      .attr('class', 'contact-node')
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y)
      .attr('r', (d: any) => d.r)
      .attr('fill', (d: any) => HEAT_COLORS[d.relationship] || '#60a5fa')
      .attr('fill-opacity', 0.85)
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 1.6)
      .attr('stroke-opacity', 0.9)
      .attr('filter', 'url(#shadow)')
      .style('cursor', 'pointer')
      .on('mouseover', (event: MouseEvent, d: any) => {
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${d.name}</strong><br/>` +
            `Etapa: <strong>${d.stage_name}</strong><br/>` +
            `Score: <strong>${d.lead_score}</strong> (${d.relationship.toUpperCase()})<br/>` +
            `Canal: ${d.source_channel}<br/>` +
            `Toques: ${d.touches}` +
            (d.amount_usd > 0 ? `<br/>Valor Pipeline: <strong>$${d.amount_usd.toFixed(0)}</strong>` : '') +
            `<br/><span style="color:#a78bfa;font-size:11px;">Haz clic para ver detalles →</span>`
          );
        d3.select(event.target as SVGCircleElement)
          .transition()
          .duration(150)
          .attr('r', (d: any) => d.r * 1.4)
          .attr('fill-opacity', 1)
          .attr('filter', 'url(#bio-glow)');
      })
      .on('mousemove', (event: MouseEvent) => {
        tooltip
          .style('left', event.clientX + 16 + 'px')
          .style('top', event.clientY - 12 + 'px');
      })
      .on('mouseout', (event: MouseEvent, d: any) => {
        tooltip.style('opacity', 0);
        d3.select(event.target as SVGCircleElement)
          .transition()
          .duration(150)
          .attr('r', (d: any) => d.r)
          .attr('fill-opacity', 0.85)
          .attr('filter', 'url(#shadow)');
      })
      .on('click', (event: MouseEvent, d: any) => {
        event.stopPropagation();
        tooltip.style('opacity', 0);
        onContactClick?.(d.id);
      });

    // Legend
    const legend = g.append('g').attr('transform', `translate(0, ${h + 20})`);
    const heatLegend = [
      { key: 'hot', label: 'Caliente ≥70', color: '#ef4444' },
      { key: 'warm', label: 'Tibio 30-69', color: '#f97316' },
      { key: 'cold', label: 'Frío <30', color: '#60a5fa' },
    ];

    heatLegend.forEach((item, i) => {
      const lg = legend.append('g').attr('transform', `translate(${i * 140}, 0)`);
      lg.append('circle').attr('r', 5).attr('fill', item.color).attr('fill-opacity', 0.85);
      lg.append('text')
        .attr('x', 12)
        .attr('y', 4)
        .attr('font-size', 11)
        .attr('fill', '#64748b')
        .text(item.label);
    });

    return () => {
      d3.select('body').selectAll('.funnel-tooltip').remove();
    };
  }, [stages, contacts, containerWidth, propHeight, onContactClick]);

  useEffect(() => {
    const cleanup = draw();
    return cleanup;
  }, [draw]);

  if (stages.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
        Sin etapas de funnel configuradas
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground px-2">
        <span className="flex items-center gap-1.5">
          {isMobileMode ? <Smartphone className="h-3.5 w-3.5 text-primary" /> : <Monitor className="h-3.5 w-3.5 text-primary" />}
          {isMobileMode ? 'Modo móvil optimizado (Capas neuronales táctiles)' : 'Modo panorámico (Flujo neuronal interactivo)'}
        </span>
        <Badge variant="outline" className="text-[10px]">
          {contacts.length} contactos
        </Badge>
      </div>
      <div className="w-full overflow-x-auto overflow-y-hidden">
        <svg ref={svgRef} className="w-full" />
      </div>
    </div>
  );
}
