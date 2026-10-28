'use client';

import { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';

interface Props {
  sources: Record<string, number>;
  width?: number;
  height?: number;
}

const SOURCE_LABELS: Record<string, string> = {
  organic: 'Orgánico',
  whatsapp: 'WhatsApp',
  referral: 'Referido',
  instagram: 'Instagram',
  facebook: 'Facebook',
  email: 'Email',
  google: 'Google',
  website: 'Website',
  cold_call: 'Llamada fría',
};

const PALETTE = [
  '#8b5cf6', '#6366f1', '#3b82f6', '#22c55e',
  '#f59e0b', '#ef4444', '#ec4899', '#14b8a6',
  '#f97316', '#a855f7',
];

export function RadialAcquisitionWheel({ sources, width = 480, height = 480 }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  const draw = useCallback(() => {
    if (!svgRef.current) return;

    const entries = Object.entries(sources).filter(([, v]) => v > 0);
    if (entries.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const cx = width / 2;
    const cy = height / 2;
    const outerR = Math.min(cx, cy) - 40;
    const innerR = outerR * 0.55;

    const total = entries.reduce((s, [, v]) => s + v, 0);

    svg.attr('width', width).attr('height', height);

    const defs = svg.append('defs');

    // Glow filter
    const glowFilter = defs.append('filter').attr('id', 'glow');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Gradients for each slice
    entries.forEach(([key], i) => {
      const grad = defs
        .append('radialGradient')
        .attr('id', `sliceGrad-${i}`)
        .attr('cx', '50%')
        .attr('cy', '50%')
        .attr('r', '50%');
      grad
        .append('stop')
        .attr('offset', '0%')
        .attr('stop-color', PALETTE[i % PALETTE.length])
        .attr('stop-opacity', 0.9);
      grad
        .append('stop')
        .attr('offset', '100%')
        .attr('stop-color', PALETTE[i % PALETTE.length])
        .attr('stop-opacity', 0.5);
    });

    const g = svg.append('g').attr('transform', `translate(${cx},${cy})`);

    // Pie layout
    const pie = d3
      .pie<[string, number]>()
      .sort(null)
      .value(([, v]) => v)
      .padAngle(0.025);

    const arc = d3.arc<d3.PieArcDatum<[string, number]>>().innerRadius(innerR).outerRadius(outerR);
    const arcHover = d3
      .arc<d3.PieArcDatum<[string, number]>>()
      .innerRadius(innerR)
      .outerRadius(outerR + 12);
    const labelArc = d3
      .arc<d3.PieArcDatum<[string, number]>>()
      .innerRadius(outerR + 20)
      .outerRadius(outerR + 20);

    const arcs = pie(entries as [string, number][]);

    // Tooltip
    const tooltip = d3
      .select('body')
      .selectAll('.radial-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'radial-tooltip')
      .style('position', 'fixed')
      .style('background', 'rgba(15,23,42,0.95)')
      .style('color', '#f8fafc')
      .style('padding', '8px 12px')
      .style('border-radius', '8px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 9999)
      .style('box-shadow', '0 4px 24px rgba(0,0,0,0.3)');

    // Draw slices
    g.selectAll('.slice')
      .data(arcs)
      .join('path')
      .attr('class', 'slice')
      .attr('d', arc as any)
      .attr('fill', (_, i) => `url(#sliceGrad-${i})`)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('mouseover', function (event: MouseEvent, d: any) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('d', arcHover(d) as string)
          .attr('filter', 'url(#glow)');
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${SOURCE_LABELS[d.data[0]] || d.data[0]}</strong><br/>` +
            `${d.data[1]} contactos<br/>` +
            `${((d.data[1] / total) * 100).toFixed(1)}% del total`
          );
      })
      .on('mousemove', (event: MouseEvent) => {
        tooltip
          .style('left', event.clientX + 14 + 'px')
          .style('top', event.clientY - 10 + 'px');
      })
      .on('mouseout', function (event: MouseEvent, d: any) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('d', arc(d) as string)
          .attr('filter', null);
        tooltip.style('opacity', 0);
      })
      .transition()
      .duration(600)
      .attrTween('d', function (d: any) {
        const i = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
        return (t: number) => arc(i(t)) as string;
      });

    // Center label
    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '-0.2em')
      .attr('font-size', 26)
      .attr('font-weight', '700')
      .attr('fill', '#1e293b')
      .text(total);
    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '1.4em')
      .attr('font-size', 11)
      .attr('fill', '#94a3b8')
      .text('contactos');

    // Slice labels (outside)
    g.selectAll('.slice-label')
      .data(arcs.filter((d: any) => (d.data[1] / total) > 0.05))
      .join('text')
      .attr('class', 'slice-label')
      .attr('transform', (d: any) => `translate(${labelArc.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .attr('font-size', 10)
      .attr('font-weight', '600')
      .attr('fill', (_, i) => PALETTE[i % PALETTE.length])
      .text((d: any) => SOURCE_LABELS[d.data[0]] || d.data[0]);

    return () => {
      d3.select('body').selectAll('.radial-tooltip').remove();
    };
  }, [sources, width, height]);

  useEffect(() => {
    const cleanup = draw();
    return cleanup;
  }, [draw]);

  return (
    <div className="flex justify-center">
      <svg ref={svgRef} />
    </div>
  );
}
