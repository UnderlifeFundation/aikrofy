'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Bot,
  Building2,
  Users,
  Zap,
  Activity,
  Cpu,
  Sparkles,
  MessageSquare,
  ShieldCheck,
  Server,
  Layers,
  ExternalLink,
  ChevronRight,
  Sliders,
} from 'lucide-react';

interface AgentLive {
  active_conversations: number;
  is_online: boolean;
  last_seen: string | null;
}

interface AgentNode {
  id: number | string;
  name: string;
  description?: string;
  role?: string;
  tone?: string;
  objective?: string;
  priority?: number;
  is_active: boolean;
  is_core?: boolean;
  category?: string;
  tier?: 'lead' | 'worker';
  tools?: string[];
  live: AgentLive;
}

interface Pillar {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  employee_count: number;
  tools?: string[];
  agents: AgentNode[];
}

interface HierarchyData {
  operator?: {
    name: string;
    role: string;
    email: string;
  };
  triad?: {
    brain: { title: string; caption: string; href: string; status: string };
    conductor: AgentNode | null;
    comms: { title: string; caption: string; href: string; status: string; channels?: any[] };
  };
  conductor: AgentNode | null;
  core_agents?: AgentNode[];
  pillars: Pillar[];
  stats: {
    total_agents: number;
    custom_agents?: number;
    core_agents?: number;
    total_departments: number;
  };
}

interface Props {
  data: HierarchyData;
}

function StatusDot({ online }: { online: boolean }) {
  return (
    <span className="relative flex h-2 w-2 shrink-0">
      {online && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
      )}
      <span
        className={`relative inline-flex h-2 w-2 rounded-full ${
          online ? 'bg-emerald-500' : 'bg-slate-400'
        }`}
      />
    </span>
  );
}

export function OrgConductorTree({ data }: Props) {
  const { operator, triad, conductor, core_agents = [], pillars = [], stats } = data;
  const [activeTab, setActiveTab] = useState<'all' | 'custom' | 'core'>('all');

  const activeConductor = triad?.conductor || conductor;

  return (
    <div className="flex flex-col items-center gap-10 py-6 px-2 min-w-full">
      {/* ── Filter / View Switcher (All / Custom / Core) ────────────────── */}
      <div className="flex flex-wrap items-center justify-between w-full max-w-5xl gap-4 pb-2 border-b">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-6 gap-1 px-2 text-xs font-mono">
            <Layers className="h-3 w-3 text-primary" />
            {stats.total_agents} AGENTES
          </Badge>
          <Badge variant="secondary" className="h-6 gap-1 px-2 text-xs">
            {stats.total_departments} DEPARTAMENTOS
          </Badge>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-xl bg-muted/60 border text-xs">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeTab === 'all' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Vista Completa
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeTab === 'custom' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Agentes Empresa ({stats.custom_agents ?? pillars.flatMap(p => p.agents).length})
          </button>
          <button
            onClick={() => setActiveTab('core')}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeTab === 'core' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Núcleo Autónomo ({core_agents.length})
          </button>
        </div>
      </div>

      {/* ── CEO / Operator Header ───────────────────────────────────────── */}
      <div className="flex flex-col items-center text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-slate-900 to-slate-700 text-white shadow-md">
          <Users className="h-6 w-6" />
        </div>
        <h2 className="mt-2 text-base font-bold tracking-tight">{operator?.name || 'Director Ejecutivo'}</h2>
        <span className="text-[10px] uppercase font-mono tracking-widest text-muted-foreground">
          {operator?.role || 'Operator / Super Admin'}
        </span>
        <div className="mt-2 h-6 w-px bg-border" />
        <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          Conductor (Super Agent Orchestrator)
        </div>
        <div className="h-4 w-px bg-border" />
      </div>

      {/* ── Triad: G-Brain Knowledge ── Conductor IA ── Comms Feed ─────── */}
      <div className="flex flex-col md:flex-row items-center justify-center gap-3 w-full max-w-4xl">
        {/* Left: G-Brain Memory Card */}
        <Link
          href={triad?.brain.href || '/documents'}
          className="w-full md:w-56 p-3.5 rounded-2xl border bg-card/70 hover:bg-card hover:border-violet-400 hover:shadow-md transition-all group text-center"
        >
          <div className="flex justify-center mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-600 group-hover:scale-105 transition-transform">
              <Sparkles className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs font-bold">{triad?.brain.title || 'G-Brain RAG'}</div>
          <div className="text-[10px] text-muted-foreground mt-0.5">{triad?.brain.caption || 'Memoria vectorial Pinecone'}</div>
          <div className="mt-2 flex items-center justify-center gap-1 text-[10px] font-medium text-violet-600">
            Explorar Memoria <ChevronRight className="h-3 w-3" />
          </div>
        </Link>

        {/* Horizontal Connector (Desktop) */}
        <div className="hidden md:block h-px w-10 bg-border" />

        {/* Center: Conductor Super Agent Card */}
        <div className="relative w-full md:w-72 p-4 rounded-2xl border-2 border-violet-500/40 bg-gradient-to-b from-card to-violet-500/5 shadow-lg shadow-violet-500/10 text-center">
          <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-widest bg-violet-600 text-white font-semibold">
            SUPER AGENT HOST
          </span>
          <div className="flex justify-center my-1">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 text-white shadow-md">
              <Zap className="h-7 w-7" />
            </div>
          </div>
          <h3 className="text-sm font-bold mt-1">{activeConductor?.name || 'Conductor IA'}</h3>
          <p className="text-[11px] text-muted-foreground line-clamp-1">{activeConductor?.description || 'Orquestador autónomo del sistema'}</p>
          <div className="mt-2.5 flex items-center justify-center gap-1.5 text-xs text-emerald-600 bg-emerald-500/10 py-1 px-2.5 rounded-lg">
            <Activity className="h-3.5 w-3.5" />
            <span className="font-semibold">{activeConductor?.live?.active_conversations ?? 0} conversaciones activas</span>
          </div>
        </div>

        {/* Horizontal Connector (Desktop) */}
        <div className="hidden md:block h-px w-10 bg-border" />

        {/* Right: Comms Feed Card */}
        <Link
          href={triad?.comms.href || '/channels'}
          className="w-full md:w-56 p-3.5 rounded-2xl border bg-card/70 hover:bg-card hover:border-emerald-400 hover:shadow-md transition-all group text-center"
        >
          <div className="flex justify-center mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 group-hover:scale-105 transition-transform">
              <MessageSquare className="h-5 w-5" />
            </div>
          </div>
          <div className="text-xs font-bold">{triad?.comms.title || 'Comms Feed'}</div>
          <div className="text-[10px] text-muted-foreground mt-0.5">{triad?.comms.caption || 'WhatsApp · Webchat · Omnicanal'}</div>
          <div className="mt-2 flex items-center justify-center gap-1 text-[10px] font-medium text-emerald-600">
            Gestionar Canales <ChevronRight className="h-3 w-3" />
          </div>
        </Link>
      </div>

      {/* Trunk Line down to Departments Rail */}
      <div className="h-8 w-px bg-border" />

      {/* ── Core Autonomous Machine Workers (Under-the-hood System Agents) ── */}
      {(activeTab === 'all' || activeTab === 'core') && core_agents.length > 0 && (
        <div className="w-full max-w-5xl rounded-2xl border border-dashed p-4 bg-muted/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-violet-500" />
              <span className="text-xs font-bold tracking-tight">Núcleo Autónomo del Sistema (System Core Agents)</span>
              <Badge variant="outline" className="text-[10px] font-mono">INMUTABLE</Badge>
            </div>
            <span className="text-[11px] text-muted-foreground">Ejecución en background vía Celery / FastAPI</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {core_agents.map((agent) => (
              <div key={agent.id} className="flex flex-col p-3 rounded-xl border bg-card shadow-xs">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <StatusDot online={true} />
                    <span className="text-xs font-bold truncate">{agent.name}</span>
                  </div>
                  <Badge variant="secondary" className="text-[9px] px-1 font-mono">
                    {agent.category || 'CORE'}
                  </Badge>
                </div>
                <p className="text-[10px] text-muted-foreground line-clamp-2 mt-0.5">{agent.role}</p>
                {agent.tools && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {agent.tools.map((tool) => (
                      <span key={tool} className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm bg-muted text-muted-foreground">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Department Crews Rail (Expandable & Ultra-wide Panoramic) ─────── */}
      {(activeTab === 'all' || activeTab === 'custom') && (
        <div className="w-full overflow-x-auto pb-6">
          <div className="flex justify-center min-w-max gap-5 px-4 mx-auto">
            {pillars.map((pillar, index) => {
              const borderColors = [
                'border-violet-500/30 hover:border-violet-500/60',
                'border-blue-500/30 hover:border-blue-500/60',
                'border-emerald-500/30 hover:border-emerald-500/60',
                'border-amber-500/30 hover:border-amber-500/60',
              ];
              const borderColor = borderColors[index % borderColors.length];

              return (
                <div
                  key={pillar.id}
                  className={`flex flex-col w-72 shrink-0 rounded-2xl border bg-card p-4 gap-3 shadow-xs transition-all ${borderColor}`}
                >
                  {/* Department Header */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold leading-tight">{pillar.name}</h4>
                      <p className="text-[10px] text-muted-foreground">{pillar.employee_count} colaboradores</p>
                    </div>
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-muted">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="h-px bg-border" />

                  {/* Agents Assigned */}
                  <div className="flex flex-col gap-1.5 min-h-[90px]">
                    <div className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground mb-0.5">
                      Agentes asignados ({pillar.agents.length})
                    </div>
                    {pillar.agents.length === 0 ? (
                      <div className="flex h-20 items-center justify-center text-center text-[11px] text-muted-foreground border border-dashed rounded-xl p-2">
                        Sin agentes asignados a este departamento
                      </div>
                    ) : (
                      pillar.agents.map((agent) => (
                        <div
                          key={agent.id}
                          className="flex items-center justify-between p-2 rounded-xl border bg-muted/40 hover:bg-muted/80 transition-colors"
                        >
                          <div className="min-w-0 flex-1 pr-2">
                            <div className="flex items-center gap-1.5">
                              <StatusDot online={agent.live?.is_online ?? true} />
                              <span className="text-xs font-semibold truncate">{agent.name}</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground capitalize">
                              {agent.objective || 'Worker'}
                            </span>
                          </div>
                          {agent.live?.active_conversations > 0 ? (
                            <Badge className="text-[9px] bg-emerald-500/10 text-emerald-600 border-0">
                              {agent.live.active_conversations} conv
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[9px]">
                              Listo
                            </Badge>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  {/* Department Tools */}
                  {pillar.tools && pillar.tools.length > 0 && (
                    <div className="mt-auto pt-2 border-t">
                      <div className="text-[8px] font-mono uppercase tracking-widest text-muted-foreground mb-1 text-center">
                        Herramientas del Pilar
                      </div>
                      <div className="flex flex-wrap justify-center gap-1">
                        {pillar.tools.map((t) => (
                          <span
                            key={t}
                            className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm bg-muted text-muted-foreground"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
