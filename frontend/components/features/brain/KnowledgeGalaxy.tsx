'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import { Search, Compass, Network, X, ExternalLink, FileText, Bot, Building2, Sparkles, Image as ImageIcon } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface KGNode {
  id: string;
  type: 'document' | 'skill' | 'media' | 'agent' | 'department';
  label: string;
  description: string;
  metadata?: Record<string, any>;
}

interface KGEdge {
  source: string;
  target: string;
  relation: string;
}

interface Props {
  nodes: KGNode[];
  edges: KGEdge[];
  width?: number;
  height?: number;
}

const NODE_COLORS: Record<string, string> = {
  document: '#6366f1',
  skill: '#22c55e',
  media: '#f59e0b',
  agent: '#8b5cf6',
  department: '#3b82f6',
};

const NODE_RADII: Record<string, number> = {
  department: 16,
  agent: 13,
  skill: 10,
  document: 9,
  media: 8,
};

const NODE_ICONS: Record<string, string> = {
  document: '📄',
  skill: '⚡',
  media: '🎬',
  agent: '🤖',
  department: '🏢',
};

export function KnowledgeGalaxy({ nodes, edges, width: propWidth = 900, height: propHeight = 580 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<any, any> | null>(null);

  const [search, setSearch] = useState('');
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [projectionMode, setProjectionMode] = useState<'radial' | 'neural'>('radial');
  const [containerWidth, setContainerWidth] = useState(propWidth);

  // ResizeObserver for responsive width
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setContainerWidth(Math.round(entry.contentRect.width));
        }
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const draw = useCallback(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = Math.max(320, containerWidth);
    const height = propHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    svg.attr('width', width).attr('height', height);

    const defs = svg.append('defs');

    // Glow filter
    const glow = defs.append('filter').attr('id', 'kg-glow').attr('x', '-40%').attr('y', '-40%').attr('width', '180%').attr('height', '180%');
    glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
    const feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Background gradient
    const bgGrad = defs.append('radialGradient').attr('id', 'bg-grad').attr('cx', '50%').attr('cy', '50%').attr('r', '70%');
    bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#0f172a').attr('stop-opacity', 0.04);
    bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0f172a').attr('stop-opacity', 0);

    svg.append('rect').attr('width', width).attr('height', height).attr('fill', 'url(#bg-grad)').attr('rx', 16);

    const cx = width / 2;
    const cy = height / 2;

    // Zoom container
    const container = svg.append('g');
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.3, 3])
        .on('zoom', (event) => {
          container.attr('transform', event.transform.toString());
        })
    );

    // If in Radial Mode, draw concentric orbital rings
    if (projectionMode === 'radial') {
      const ringsG = container.append('g').attr('class', 'radial-rings');
      const maxR = Math.min(cx, cy) - 30;
      const ringRadii = [maxR * 0.28, maxR * 0.55, maxR * 0.85];

      ringRadii.forEach((r, idx) => {
        ringsG
          .append('circle')
          .attr('cx', cx)
          .attr('cy', cy)
          .attr('r', r)
          .attr('fill', 'none')
          .attr('stroke', '#94a3b8')
          .attr('stroke-opacity', 0.12)
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '4 3');

        ringsG
          .append('text')
          .attr('x', cx + r - 8)
          .attr('y', cy - 4)
          .attr('font-size', 8)
          .attr('font-mono', 'true')
          .attr('fill', '#94a3b8')
          .attr('opacity', 0.4)
          .text(idx === 0 ? 'NÚCLEO' : idx === 1 ? 'PILAR' : 'EXTERIOR');
      });
    }

    // Build node/edge simulation
    const simNodes: (KGNode & { x?: number; y?: number; targetX?: number; targetY?: number })[] = nodes.map((n) => ({ ...n }));
    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks = edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        relation: e.relation,
      }));

    // Layer assignments for neural or radial
    simNodes.forEach((n) => {
      if (projectionMode === 'neural') {
        // Horizontal layer projection: depts/memory (left) -> agents (mid-left) -> skills (mid-right) -> docs/media (right)
        const layerXMap = {
          department: width * 0.18,
          agent: width * 0.40,
          skill: width * 0.65,
          document: width * 0.85,
          media: width * 0.88,
        };
        n.targetX = layerXMap[n.type] || width / 2;
        n.targetY = cy + (Math.random() - 0.5) * (height * 0.7);
      }
    });

    const sim = d3.forceSimulation(simNodes as any);

    if (projectionMode === 'radial') {
      sim
        .force('link', d3.forceLink(simLinks as any).id((d: any) => d.id).distance(75).strength(0.35))
        .force('charge', d3.forceManyBody().strength(-160))
        .force('center', d3.forceCenter(cx, cy))
        .force('collision', d3.forceCollide((d: any) => (NODE_RADII[d.type] || 8) + 6));
    } else {
      // Neural Layered Mode
      sim
        .force('link', d3.forceLink(simLinks as any).id((d: any) => d.id).distance(80).strength(0.3))
        .force('x', d3.forceX((d: any) => d.targetX).strength(0.7))
        .force('y', d3.forceY(cy).strength(0.1))
        .force('collision', d3.forceCollide((d: any) => (NODE_RADII[d.type] || 8) + 8));
    }

    simRef.current = sim;

    // Links
    const link = container
      .append('g')
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-opacity', 0.25)
      .attr('stroke-width', 1);

    // Nodes
    const nodeG = container
      .append('g')
      .selectAll('.kg-node')
      .data(simNodes)
      .join('g')
      .attr('class', 'kg-node')
      .style('cursor', 'pointer')
      .call(
        (d3
          .drag<any, any>()
          .on('start', (event, d: any) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d: any) => {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as any)
      );

    // Glow Ring
    nodeG
      .append('circle')
      .attr('r', (d) => (NODE_RADII[d.type] || 8) + 4)
      .attr('fill', (d) => NODE_COLORS[d.type] || '#94a3b8')
      .attr('fill-opacity', 0.15)
      .attr('filter', 'url(#kg-glow)');

    // Core Circle
    nodeG
      .append('circle')
      .attr('r', (d) => NODE_RADII[d.type] || 8)
      .attr('fill', (d) => NODE_COLORS[d.type] || '#94a3b8')
      .attr('fill-opacity', 0.85)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    // Icon Emoji
    nodeG
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', (d) => (NODE_RADII[d.type] || 8) * 0.9)
      .text((d) => NODE_ICONS[d.type] || '●');

    // Label below
    nodeG
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => (NODE_RADII[d.type] || 8) + 12)
      .attr('font-size', 9)
      .attr('font-weight', '600')
      .attr('fill', '#475569')
      .attr('pointer-events', 'none')
      .text((d) => (d.label.length > 16 ? d.label.slice(0, 15) + '…' : d.label));

    // Selection & Drawer click
    nodeG.on('click', (_, d: any) => {
      setSelectedNode(d);
    });

    // Tooltip
    const tooltip = d3
      .select('body')
      .selectAll('.kg-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'kg-tooltip')
      .style('position', 'fixed')
      .style('background', 'rgba(15,23,42,0.97)')
      .style('color', '#f8fafc')
      .style('padding', '10px 14px')
      .style('border-radius', '10px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 9999)
      .style('max-width', '240px')
      .style('box-shadow', '0 4px 24px rgba(0,0,0,0.4)');

    nodeG
      .on('mouseover', (event: MouseEvent, d: any) => {
        tooltip
          .style('opacity', 1)
          .html(
            `${NODE_ICONS[d.type]} <strong>${d.label}</strong><br/>` +
            `<span style="opacity:0.6;font-size:10px;text-transform:uppercase;">${d.type}</span>` +
            (d.description ? `<br/><span style="opacity:0.8;font-size:11px;">${d.description.slice(0, 90)}</span>` : '') +
            `<br/><span style="color:#a78bfa;font-size:10px;">Clic para inspeccionar detalle →</span>`
          );
        d3.select(event.currentTarget as SVGGElement)
          .select('circle:last-of-type')
          .transition()
          .duration(150)
          .attr('fill-opacity', 1)
          .attr('r', (d: any) => (NODE_RADII[d.type] || 8) + 3);
      })
      .on('mousemove', (event: MouseEvent) => {
        tooltip
          .style('left', event.clientX + 14 + 'px')
          .style('top', event.clientY - 10 + 'px');
      })
      .on('mouseout', (event: MouseEvent, d: any) => {
        tooltip.style('opacity', 0);
        d3.select(event.currentTarget as SVGGElement)
          .select('circle:last-of-type')
          .transition()
          .duration(150)
          .attr('fill-opacity', 0.85)
          .attr('r', (d: any) => NODE_RADII[d.type] || 8);
      });

    sim.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodeG.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      sim.stop();
      d3.select('body').selectAll('.kg-tooltip').remove();
    };
  }, [nodes, edges, containerWidth, propHeight, projectionMode]);

  // Search filtering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const lc = search.toLowerCase();

    svg.selectAll('.kg-node').each(function (d: any) {
      const matches = lc && (d.label.toLowerCase().includes(lc) || d.description.toLowerCase().includes(lc));
      d3.select(this)
        .select('circle:last-of-type')
        .transition()
        .duration(200)
        .attr('fill-opacity', !lc || matches ? 0.85 : 0.15)
        .attr('r', !lc || matches ? (NODE_RADII[d.type] || 8) : (NODE_RADII[d.type] || 8) * 0.6);
    });
  }, [search, nodes]);

  useEffect(() => {
    const cleanup = draw();
    return cleanup;
  }, [draw]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
        Sin datos en el grafo de conocimiento
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex flex-col gap-3 relative">
      {/* Top Controls: Search + Radial/Neural Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative max-w-xs w-full">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8 h-8 text-xs"
            placeholder="Buscar en la memoria o RAG..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Projection Switcher */}
        <div className="flex items-center gap-1 p-0.5 rounded-lg border bg-muted/50 text-xs">
          <button
            onClick={() => setProjectionMode('radial')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-colors ${
              projectionMode === 'radial' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground'
            }`}
          >
            <Compass className="h-3.5 w-3.5" />
            Constelación Radial
          </button>
          <button
            onClick={() => setProjectionMode('neural')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-colors ${
              projectionMode === 'neural' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground'
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            Flujo Neural
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 text-xs">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted/60 text-muted-foreground">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
            {NODE_ICONS[type]} {type}
          </span>
        ))}
      </div>

      {/* Canvas */}
      <div className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
        <svg ref={svgRef} className="w-full" />

        {/* Knowledge Detail Side Drawer */}
        {selectedNode && (
          <div className="absolute top-0 right-0 h-full w-80 max-w-full bg-background/95 backdrop-blur-md border-l p-4 flex flex-col justify-between shadow-xl z-10 animate-in slide-in-from-right duration-200">
            <div>
              <div className="flex items-center justify-between pb-3 border-b">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{NODE_ICONS[selectedNode.type]}</span>
                  <div>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono">
                      {selectedNode.type}
                    </Badge>
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSelectedNode(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="mt-4 space-y-3">
                <div>
                  <h4 className="text-sm font-bold tracking-tight">{selectedNode.label}</h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    {selectedNode.description || 'Sin descripción adicional para este nodo de memoria.'}
                  </p>
                </div>

                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div className="p-2.5 rounded-xl border bg-muted/40 space-y-1">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground">Metadatos RAG</span>
                    {Object.entries(selectedNode.metadata).map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground capitalize">{k}:</span>
                        <span className="font-mono text-[11px] truncate max-w-[120px]">{String(v || '-')}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs gap-1.5"
                onClick={() => setSelectedNode(null)}
              >
                Cerrar Inspector
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
