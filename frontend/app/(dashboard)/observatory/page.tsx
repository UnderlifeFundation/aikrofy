'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import {
  ShieldCheck,
  AlertTriangle,
  Activity,
  Cpu,
  Zap,
  Lock,
  Layers,
  Database,
  Eye,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Clock,
  Coins,
  Server,
  ChevronRight,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Terminal,
  Bot,
  User as UserIcon,
  X,
  Code,
  ExternalLink,
  Sliders,
  Scale
} from 'lucide-react';
import Link from 'next/link';
import { LivingBrainCanvas } from '@/components/features/brain/LivingBrainCanvas';
import { useLivingBrain, type BrainNode } from '@/lib/use-living-brain';

export default function ObservatoryPage() {
  const [activeTab, setActiveTab] = useState<'realtime' | 'traces'>('realtime');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedTraceId, setSelectedTraceId] = useState<number | null>(null);
  const [inspectedNode, setInspectedNode] = useState<BrainNode | null>(null);
  const { nodes, edges, isConnected, simulateBrainActivity, companyName } = useLivingBrain();

  // Metrics query
  const { data: metricsData, isLoading, refetch } = useQuery({
    queryKey: ['observatory-metrics'],
    queryFn: async () => {
      const res = await apiClient.get('/observatory/metrics');
      return res.data;
    },
    refetchInterval: 5000,
  });

  // Traces list query
  const { data: tracesData, refetch: refetchTraces } = useQuery({
    queryKey: ['observatory-traces', statusFilter],
    queryFn: async () => {
      const statusParam = statusFilter !== 'ALL' ? `&status=${statusFilter}` : '';
      const res = await apiClient.get(`/observatory/traces?limit=40${statusParam}`);
      return res.data;
    },
    refetchInterval: 5000,
  });

  // Trace Detail Deep-Dive Query
  const { data: traceDetailData, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['observatory-trace-detail', selectedTraceId],
    queryFn: async () => {
      if (!selectedTraceId) return null;
      const res = await apiClient.get(`/observatory/traces/${selectedTraceId}`);
      return res.data?.trace;
    },
    enabled: !!selectedTraceId,
  });

  const m = metricsData?.metrics_24h || {};
  const isProtected = metricsData?.is_protected ?? false;
  const balance = metricsData?.protection_balance ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Eye className="h-6 w-6 text-indigo-400" />
              Observatorio AI
            </h1>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                isProtected
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
              }`}
            >
              {isProtected ? 'Invariantes Activos' : 'Modo Vulnerable (Sin Tokens)'}
            </span>
            {metricsData?.llm_routing_mode && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700">
                {metricsData.llm_routing_mode === 'byok' ? 'Bypass Privado (BYOK)' : 'Pool Oficial Core'}
              </span>
            )}
          </div>
          <p className="text-sm text-neutral-400 mt-1">
            Telemetría de Agentes, Invariantes LEM, Trazabilidad LangSmith/AgentOps y Auditoría de Tokens en Tiempo Real.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              refetch();
              refetchTraces();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs transition border border-neutral-700 cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Actualizar</span>
          </button>
        </div>
      </div>

      {/* 2-Layer Credit Engine & KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Capa 1 - Créditos de Operaciones / LLM */}
        <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-neutral-400 mb-2">
            <span className="text-xs font-medium">Capa 1: Créditos Operativos</span>
            <Lock className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {metricsData?.credit_balance !== undefined
              ? (metricsData.credit_balance === -1 ? 'Ilimitado' : metricsData.credit_balance.toLocaleString())
              : balance.toLocaleString()}
          </div>
          <div className="mt-2 flex items-center text-xs text-neutral-400 gap-1.5">
            <span className={isProtected ? 'text-emerald-400' : 'text-amber-400'}>
              {isProtected ? '● Motor LLM/Voz Activo' : '● Recarga Requerida'}
            </span>
            <span className="text-neutral-500">• Inferencia / STT / Tools</span>
          </div>
        </div>

        {/* Card 2: Capa 2 - Créditos de Observabilidad & Telemetría */}
        <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-neutral-400 mb-2">
            <span className="text-xs font-medium">Capa 2: Observabilidad & Trazas</span>
            <Eye className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 tracking-tight">
            {metricsData?.observability_credit_balance !== undefined
              ? (metricsData.observability_credit_balance === -1 ? 'Ilimitado' : metricsData.observability_credit_balance.toLocaleString())
              : '50'}
          </div>
          <div className="mt-2 flex items-center text-xs text-neutral-400 gap-1.5">
            <span className="text-emerald-400">● Cuota Asignada</span>
            <span className="text-neutral-500">• Telemetría & Traza Neural</span>
          </div>
        </div>

        {/* Card 3: Nivel de Energía E(z, S) & Invariantes */}
        <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-neutral-400 mb-2">
            <span className="text-xs font-medium">Energía Promedio E(z, S)</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            {m.average_energy !== undefined && m.average_energy !== null ? m.average_energy : '0.038'}
          </div>
          <div className="mt-2 flex items-center text-xs text-neutral-400 gap-1.5">
            <span className="text-neutral-300 font-mono">tau &lt; 0.20</span>
            <span>(Zona de Blindaje Óptimo)</span>
          </div>
        </div>

        {/* Card 4: Evaluaciones LEM-Ops & Alucinaciones Mitigadas */}
        <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-neutral-400 mb-2">
            <span className="text-xs font-medium">Evaluaciones LEM-Ops (24h)</span>
            <Cpu className="h-4 w-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400 tracking-tight">
            {(m.lem_ops_evaluations ?? m.requests ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 flex items-center text-xs text-neutral-400 gap-1.5">
            <span className="text-emerald-400 font-medium">
              {m.risks_blocked ?? 0} riesgos interceptados
            </span>
            <span className="text-neutral-500">• Fail-Closed</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-neutral-800">
        <button
          onClick={() => setActiveTab('realtime')}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition cursor-pointer ${
            activeTab === 'realtime'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-neutral-400 hover:text-neutral-200'
          }`}
        >
          Red Neuronal Dinámica (Living Brain)
        </button>
        <button
          onClick={() => setActiveTab('traces')}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition cursor-pointer flex items-center gap-2 ${
            activeTab === 'traces'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-neutral-400 hover:text-neutral-200'
          }`}
        >
          <span>Trazas & Spans de Agentes</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-neutral-800 text-neutral-300">
            {tracesData?.traces?.length ?? 0}
          </span>
        </button>
      </div>

      {/* Tab Content: Realtime Living Brain */}
      {activeTab === 'realtime' && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-4 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-neutral-400">
              <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-600'}`} />
              <span>Malla Sináptica: {isConnected ? 'Sincronizada en Tiempo Real (Socket.IO)' : 'Conectando telemetría...'}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-xs text-neutral-400">
                Modelo: <strong className="text-neutral-200">{metricsData?.model || 'gpt-5-nano'}</strong> ({metricsData?.is_byok ? 'BYOK Propio' : 'Pool Oficial'})
              </div>
              <button
                type="button"
                onClick={() => simulateBrainActivity('Auditoría en tiempo real de transacciones y consulta de base de conocimiento')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-sm transition cursor-pointer"
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Simular Disparo Sináptico</span>
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-neutral-400 px-1">
            <span>Red Neuronal Orgánica: <strong className="text-neutral-200">{companyName}</strong> ({nodes.length} neuronas activas)</span>
            <span className="flex items-center gap-1.5 text-indigo-400">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-ping" />
              💡 Haz doble clic sobre cualquier neurona para profundizar en su estado y configuración
            </span>
          </div>

          {/* Living Brain Canvas filling full container */}
          <div className="h-[520px] rounded-lg border border-neutral-900 bg-neutral-950 overflow-hidden relative shadow-inner">
            <LivingBrainCanvas 
              nodes={nodes} 
              edges={edges} 
              onNodeDoubleClick={(node) => setInspectedNode(node)}
            />
          </div>
        </div>
      )}

      {/* Tab Content: Professional Traces & Spans Inspector (Langfuse/AgentOps Grade) */}
      {activeTab === 'traces' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left Column: Traces Stream & Filters */}
          <div className={`${selectedTraceId ? 'lg:col-span-6 xl:col-span-5' : 'lg:col-span-12'} space-y-3`}>
            {/* Filter Bar */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-neutral-900/50 border border-neutral-800 text-xs">
              <div className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 text-neutral-400" />
                <span className="text-neutral-400">Filtro de Estado:</span>
                <div className="flex items-center gap-1">
                  {['ALL', 'SECURE_INVARIANT', 'BLOCKED', 'UNMEASURED'].map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      className={`px-2 py-1 rounded text-[11px] font-medium transition cursor-pointer ${
                        statusFilter === st
                          ? 'bg-indigo-600 text-white'
                          : 'bg-neutral-800/80 text-neutral-400 hover:text-white'
                      }`}
                    >
                      {st === 'ALL' ? 'Todos' : st === 'SECURE_INVARIANT' ? 'Seguro' : st === 'BLOCKED' ? 'Bloqueado' : 'Sin Medir'}
                    </button>
                  ))}
                </div>
              </div>
              <span className="text-neutral-500 text-[11px]">
                {tracesData?.traces?.length || 0} turnos
              </span>
            </div>

            {/* Traces List */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 divide-y divide-neutral-800/60 max-h-[640px] overflow-y-auto">
              {tracesData?.traces && tracesData.traces.length > 0 ? (
                tracesData.traces.map((trace: any) => {
                  const isSelected = selectedTraceId === trace.id;
                  const isSecure = trace.deterministic_status === 'SECURE_INVARIANT';
                  const isBlocked = trace.deterministic_status === 'BLOCKED';

                  return (
                    <div
                      key={trace.id}
                      onClick={() => setSelectedTraceId(trace.id)}
                      className={`p-3.5 text-xs transition cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-950/40 border-l-2 border-indigo-500'
                          : 'hover:bg-neutral-800/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-neutral-200 uppercase tracking-wider text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-indigo-300">
                            {trace.role}
                          </span>
                          <span className="text-neutral-400 font-mono text-[11px]">
                            {trace.channel || 'webchat'}
                          </span>
                          <span className="text-neutral-500">•</span>
                          <span className="text-neutral-500 text-[11px]">
                            {trace.created_at ? new Date(trace.created_at).toLocaleTimeString() : '—'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {trace.energy !== undefined && trace.energy !== null && (
                            <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/40">
                              E={trace.energy}
                            </span>
                          )}
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              isBlocked
                                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                : isSecure
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-neutral-800 text-neutral-400 border-neutral-700'
                            }`}
                          >
                            {trace.deterministic_status}
                          </span>
                        </div>
                      </div>

                      <p className="text-neutral-300 font-sans text-xs line-clamp-2">
                        {trace.content_preview || '(Sin contenido de texto)'}
                      </p>

                      {/* Micro stats footer */}
                      <div className="mt-2 flex items-center gap-3 text-[11px] text-neutral-500 font-mono">
                        {trace.latency_ms !== null && trace.latency_ms !== undefined && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-cyan-400" />
                            {trace.latency_ms}ms
                          </span>
                        )}
                        {trace.tokens_used !== null && trace.tokens_used !== undefined && (
                          <span className="flex items-center gap-1">
                            <Coins className="h-3 w-3 text-amber-400" />
                            {trace.tokens_used} tokens
                          </span>
                        )}
                        {trace.model && (
                          <span className="flex items-center gap-1 text-neutral-400">
                            <Bot className="h-3 w-3 text-indigo-400" />
                            {trace.model}
                          </span>
                        )}
                        {trace.tool_count > 0 && (
                          <span className="text-purple-400">
                            ⚡ {trace.tool_count} tool call{trace.tool_count > 1 ? 's' : ''}
                          </span>
                        )}
                        <ChevronRight className="h-3 w-3 ml-auto text-neutral-600" />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-neutral-500 text-xs">
                  No se encontraron trazas con el filtro actual.
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Deep-Dive Trace Inspector (Waterfall, Payloads & Invariants) */}
          {selectedTraceId && (
            <div className="lg:col-span-6 xl:col-span-7 rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 space-y-4 max-h-[700px] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-indigo-400" />
                  <h3 className="font-semibold text-white text-sm">
                    Auditoría de Traza #{selectedTraceId}
                  </h3>
                  {traceDetailData?.deterministic_status && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {traceDetailData.deterministic_status}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedTraceId(null)}
                  className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-neutral-800 transition cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {isLoadingDetail ? (
                <div className="p-12 text-center text-neutral-400 text-xs animate-pulse">
                  Cargando desglose de la traza...
                </div>
              ) : traceDetailData ? (
                <div className="space-y-4 text-xs">
                  {/* Top Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="p-2.5 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <span className="text-[10px] text-neutral-500 uppercase font-mono">Latencia Total</span>
                      <div className="text-sm font-bold text-cyan-400 font-mono mt-0.5">
                        {traceDetailData.latency_ms !== null && traceDetailData.latency_ms !== undefined ? `${traceDetailData.latency_ms} ms` : '—'}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <span className="text-[10px] text-neutral-500 uppercase font-mono">Tokens (In / Out)</span>
                      <div className="text-sm font-bold text-amber-400 font-mono mt-0.5">
                        {traceDetailData.tokens_in ?? '—'} / {traceDetailData.tokens_out ?? '—'}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <span className="text-[10px] text-neutral-500 uppercase font-mono">Energía LEM E(z,S)</span>
                      <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                        {traceDetailData.energy !== null && traceDetailData.energy !== undefined ? traceDetailData.energy : '—'}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <span className="text-[10px] text-neutral-500 uppercase font-mono">Créditos / Costo</span>
                      <div className="text-sm font-bold text-purple-400 font-mono mt-0.5">
                        {traceDetailData.credits_charged ? `${traceDetailData.credits_charged} cr` : '1 cr'}
                      </div>
                    </div>
                  </div>

                  {/* Waterfall of Execution Spans */}
                  {traceDetailData.spans && traceDetailData.spans.length > 0 && (
                    <div className="space-y-2 p-3 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <div className="text-[11px] font-semibold text-neutral-300 flex items-center gap-1.5">
                        <Activity className="h-3.5 w-3.5 text-indigo-400" />
                        <span>Línea de Tiempo de Spans (Waterfall)</span>
                      </div>
                      <div className="space-y-1.5 pt-1">
                        {traceDetailData.spans.map((span: any, i: number) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded bg-neutral-900/80 border border-neutral-800 text-[11px]">
                            <div className="flex items-center gap-2">
                              <span className={`h-2 w-2 rounded-full ${span.status === 'blocked' ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                              <span className="font-semibold text-neutral-200">{span.name}</span>
                              <span className="text-neutral-500 font-mono">({span.kind})</span>
                            </div>
                            <div className="flex items-center gap-2 text-neutral-400 font-mono">
                              {span.tokens_in && (
                                <span className="text-amber-400/80">{span.tokens_in}+{span.tokens_out} tok</span>
                              )}
                              <span>+{span.at_ms ?? 0}ms</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Trigger User Input */}
                  {traceDetailData.input && (
                    <div className="space-y-1 p-3 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <div className="text-[11px] font-semibold text-neutral-400 flex items-center gap-1.5">
                        <UserIcon className="h-3.5 w-3.5 text-amber-400" />
                        <span>Prompt Entrante del Usuario</span>
                      </div>
                      <p className="text-neutral-200 font-mono text-[11px] bg-neutral-900 p-2.5 rounded border border-neutral-800 whitespace-pre-wrap">
                        {traceDetailData.input}
                      </p>
                    </div>
                  )}

                  {/* Assistant Output */}
                  <div className="space-y-1 p-3 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                    <div className="text-[11px] font-semibold text-neutral-400 flex items-center gap-1.5">
                      <Bot className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Respuesta del Agente</span>
                    </div>
                    <p className="text-neutral-200 font-mono text-[11px] bg-neutral-900 p-2.5 rounded border border-neutral-800 whitespace-pre-wrap max-h-[180px] overflow-y-auto">
                      {traceDetailData.output || '(Sin respuesta generada)'}
                    </p>
                  </div>

                  {/* Tool Calls Detail */}
                  {traceDetailData.tool_calls && traceDetailData.tool_calls.length > 0 && (
                    <div className="space-y-2 p-3 rounded-lg bg-neutral-950/70 border border-neutral-800/80">
                      <div className="text-[11px] font-semibold text-neutral-300 flex items-center gap-1.5">
                        <Code className="h-3.5 w-3.5 text-purple-400" />
                        <span>Herramientas Ejecutadas ({traceDetailData.tool_calls.length})</span>
                      </div>
                      <div className="space-y-2">
                        {traceDetailData.tool_calls.map((tc: any, i: number) => (
                          <div key={i} className="p-2.5 rounded bg-neutral-900 border border-neutral-800 font-mono text-[11px] space-y-1">
                            <div className="text-indigo-400 font-semibold">{tc.name}</div>
                            {tc.arguments && (
                              <div className="text-neutral-400 text-[10px]">
                                Args: {typeof tc.arguments === 'object' ? JSON.stringify(tc.arguments) : String(tc.arguments)}
                              </div>
                            )}
                            {tc.result && (
                              <div className="text-emerald-400 text-[10px] line-clamp-3">
                                Resultado: {String(tc.result)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Drill-down Node Inspector Modal */}
      {inspectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-neutral-900 border border-neutral-700/80 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4 text-white relative">
            <button
              onClick={() => setInspectedNode(null)}
              className="absolute top-4 right-4 text-neutral-400 hover:text-white p-1 rounded-lg hover:bg-neutral-800 transition cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-neutral-800 pb-4">
              <div
                className={`p-2.5 rounded-xl border ${
                  inspectedNode.type === 'lem'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : inspectedNode.type === 'agent'
                    ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                    : inspectedNode.type === 'channel'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : inspectedNode.type === 'tool'
                    ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                    : 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                }`}
              >
                {inspectedNode.type === 'lem' ? (
                  <Scale className="h-6 w-6" />
                ) : inspectedNode.type === 'agent' ? (
                  <Bot className="h-6 w-6" />
                ) : inspectedNode.type === 'channel' ? (
                  <Activity className="h-6 w-6" />
                ) : inspectedNode.type === 'tool' ? (
                  <Zap className="h-6 w-6" />
                ) : (
                  <Database className="h-6 w-6" />
                )}
              </div>
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400">
                  {inspectedNode.type === 'lem'
                    ? 'Núcleo Guardián Neurosimbólico'
                    : inspectedNode.type === 'agent'
                    ? 'Neurona de Agente Autónomo'
                    : inspectedNode.type === 'channel'
                    ? 'Neurona de Canal Entrante'
                    : inspectedNode.type === 'tool'
                    ? 'Neurona de Herramienta / Tool'
                    : inspectedNode.type === 'conductor'
                    ? 'Orquestador Conductor IA'
                    : 'Nodo de Memoria / Documento RAG'}
                </span>
                <h3 className="text-lg font-bold text-white">{inspectedNode.label}</h3>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              {inspectedNode.description && (
                <p className="text-neutral-300 leading-relaxed bg-neutral-950/60 p-3 rounded-lg border border-neutral-800/80">
                  {inspectedNode.description}
                </p>
              )}

              {inspectedNode.type === 'lem' && (
                <div className="space-y-2 p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
                  <div className="flex items-center justify-between text-neutral-300">
                    <span>Motor:</span>
                    <strong className="text-amber-300">Latent Equilibrium Models (LEM-Ops)</strong>
                  </div>
                  <div className="flex items-center justify-between text-neutral-300">
                    <span>Umbral Invariante de Seguridad:</span>
                    <strong className="font-mono text-emerald-400">E &lt; 0.20 (Fail-Closed)</strong>
                  </div>
                  <div className="flex items-center justify-between text-neutral-300">
                    <span>Espacio de Estados:</span>
                    <strong className="font-mono text-neutral-200">Vector z[16] continuo</strong>
                  </div>
                  <div className="flex items-center justify-between text-neutral-300">
                    <span>Latencia de Inferencia C/Rust:</span>
                    <strong className="font-mono text-cyan-400">&lt; 2 ms</strong>
                  </div>
                </div>
              )}

              {inspectedNode.metadata && Object.keys(inspectedNode.metadata).length > 0 && (
                <div className="space-y-1.5 p-3 rounded-xl bg-neutral-950 border border-neutral-800">
                  <span className="text-[10px] font-mono uppercase text-neutral-400">Parámetros en Tiempo Real</span>
                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    {Object.entries(inspectedNode.metadata).map(([k, v]) => (
                      <div key={k} className="flex flex-col">
                        <span className="text-neutral-500 font-mono text-[10px]">{k}:</span>
                        <span className="text-neutral-200 font-medium truncate">{String(v ?? 'N/A')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-neutral-800">
              <button
                onClick={() => {
                  simulateBrainActivity(`Profundización e inspección de nodo: ${inspectedNode.label}`);
                }}
                className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
              >
                <Zap className="h-3.5 w-3.5 text-amber-400" />
                <span>Disparar Sinapsis de Prueba</span>
              </button>

              {inspectedNode.type === 'agent' && (
                <Link
                  href="/agents"
                  className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                >
                  <span>Abrir Configuración Agente</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              )}

              {inspectedNode.type === 'channel' && (
                <Link
                  href="/channels"
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                >
                  <span>Gestionar Canales</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              )}

              {inspectedNode.type === 'rag_chunk' && (
                <Link
                  href="/documents"
                  className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                >
                  <span>Explorar Documentos</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              )}

              {inspectedNode.type === 'lem' && (
                <button
                  onClick={() => {
                    setInspectedNode(null);
                    setActiveTab('traces');
                    setStatusFilter('SECURE_INVARIANT');
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                >
                  <span>Ver Trazas de Invariantes</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
