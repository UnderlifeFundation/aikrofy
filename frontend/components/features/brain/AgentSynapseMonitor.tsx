'use client';

import { useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useLivingBrain, type BrainEvent, type BrainNodeType } from '@/lib/use-living-brain';
import {
  Brain,
  Zap,
  FileSearch,
  Wrench,
  CheckCircle,
  Radio,
  ActivitySquare,
  X,
  Send,
  Circle,
} from 'lucide-react';

// Dynamic import — no SSR (Canvas API unavailable on server)
const LivingBrainCanvas = dynamic(
  () => import('./LivingBrainCanvas').then((m) => m.LivingBrainCanvas),
  { ssr: false, loading: () => <CanvasPlaceholder /> }
);

function CanvasPlaceholder() {
  return (
    <div className="w-full h-[440px] rounded-xl bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-slate-600">
        <Brain className="w-12 h-12 animate-pulse" />
        <p className="text-sm">Inicializando neuronas...</p>
      </div>
    </div>
  );
}

interface AgentSynapseMonitorProps {
  isOpen: boolean;
  onClose: () => void;
  companyId?: number | null;
}

const EVENT_ICON_MAP: Record<BrainNodeType | string, typeof Brain> = {
  conductor: Brain,
  agent: Radio,
  rag_chunk: FileSearch,
  rag_query: FileSearch,
  tool: Wrench,
  query: Zap,
  pulse: ActivitySquare,
};

const EVENT_COLOR_MAP: Record<string, string> = {
  AGENT_THOUGHT_START: 'text-violet-400',
  RAG_QUERY_START: 'text-cyan-400',
  RAG_HIT: 'text-cyan-300',
  TOOL_DISPATCH: 'text-emerald-400',
  TOOL_RESULT: 'text-emerald-300',
  AGENT_RESPONSE_COMPLETE: 'text-violet-300',
  SYNAPSE_PULSE: 'text-slate-400',
};

const DOT_COLOR_MAP: Record<string, string> = {
  AGENT_THOUGHT_START: 'bg-violet-500',
  RAG_QUERY_START: 'bg-cyan-500',
  RAG_HIT: 'bg-cyan-400',
  TOOL_DISPATCH: 'bg-emerald-500',
  TOOL_RESULT: 'bg-emerald-400',
  AGENT_RESPONSE_COMPLETE: 'bg-violet-400',
  SYNAPSE_PULSE: 'bg-slate-500',
};

function EventRow({ event }: { event: BrainEvent }) {
  const Icon = EVENT_ICON_MAP[event.nodeType] || Circle;
  const textColor = EVENT_COLOR_MAP[event.event] || 'text-slate-400';
  const dotColor = DOT_COLOR_MAP[event.event] || 'bg-slate-500';

  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-slate-800/50 last:border-0">
      <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-medium ${textColor} flex items-center gap-1`}>
          <Icon className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">{event.icon} {event.detail}</span>
        </div>
        <p className="text-[10px] text-slate-600 mt-0.5">{event.ts}</p>
      </div>
    </div>
  );
}

export function AgentSynapseMonitor({ isOpen, onClose, companyId }: AgentSynapseMonitorProps) {
  const { nodes, edges, recentEvents, isConnected, totalProcessed, simulateBrainActivity } =
    useLivingBrain(companyId);
  const [query, setQuery] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const queryRef = useRef<HTMLTextAreaElement>(null);

  if (!isOpen) return null;

  const handleSimulate = async () => {
    if (!query.trim() || isSimulating) return;
    setIsSimulating(true);
    try {
      await simulateBrainActivity(query.trim());
      setQuery('');
    } finally {
      setTimeout(() => setIsSimulating(false), 3000);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSimulate();
    }
  };

  const activeNodeCount = nodes.filter((n) => n.isActive).length;

  return (
    // Full-screen overlay
    <div className="fixed inset-0 z-[999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-7xl h-[90vh] flex flex-col rounded-2xl overflow-hidden border border-slate-800/80 bg-slate-950/95 shadow-2xl shadow-violet-950/30 animate-in fade-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/70 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Brain className="w-6 h-6 text-violet-400" />
              {isConnected && (
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Monitor Sináptico de IA</h2>
              <p className="text-xs text-slate-500">
                Red neuronal activa · Cerebro vivo del agente
              </p>
            </div>
          </div>

          {/* Connection status */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-slate-500" />
                Procesados:{' '}
                <span className="text-slate-300 font-mono">{totalProcessed}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Nodos activos:{' '}
                <span className="text-amber-300 font-mono">{activeNodeCount}</span>
              </span>
              <span
                className={`flex items-center gap-1.5 ${
                  isConnected ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                <Radio className="w-3.5 h-3.5" />
                {isConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Main content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left — Brain Canvas */}
          <div className="flex-1 p-4 overflow-hidden flex flex-col">
            <LivingBrainCanvas nodes={nodes} edges={edges} className="flex-1" />

            {/* Legend */}
            <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-slate-500">
              {[
                { color: 'bg-violet-500', label: 'Conductor IA' },
                { color: 'bg-cyan-500', label: 'Memoria RAG' },
                { color: 'bg-emerald-500', label: 'Herramientas' },
                { color: 'bg-amber-500', label: 'Query Inbound' },
                { color: 'bg-blue-500', label: 'Agentes' },
              ].map((item) => (
                <span key={item.label} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${item.color}`} />
                  {item.label}
                </span>
              ))}
            </div>
          </div>

          {/* Right — Controls + Event Log */}
          <div className="w-[340px] flex flex-col border-l border-slate-800/70 flex-shrink-0">
            {/* Query Simulator */}
            <div className="p-4 border-b border-slate-800/70">
              <h3 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                <ActivitySquare className="w-3.5 h-3.5 text-violet-400" />
                Simulador de Razonamiento IA
              </h3>
              <p className="text-[10px] text-slate-600 mb-3">
                Escribe una consulta para observar el proceso sináptico en tiempo real
              </p>
              <textarea
                ref={queryRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="¿Cuánto cuesta el plan Pro? ¿Cuándo es la próxima cita?"
                rows={3}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <button
                onClick={handleSimulate}
                disabled={!query.trim() || isSimulating}
                className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-slate-800 disabled:text-slate-600 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                {isSimulating ? (
                  <>
                    <Brain className="w-3.5 h-3.5 animate-pulse" />
                    Procesando sinapsis...
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    Simular Consulta IA
                  </>
                )}
              </button>
            </div>

            {/* Event Log */}
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="px-4 py-3 flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 text-cyan-400" />
                  Eventos Sinápticos
                </h3>
                <span className="text-[10px] text-slate-600 font-mono bg-slate-900 px-1.5 py-0.5 rounded">
                  {recentEvents.length}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-0">
                {recentEvents.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-32 text-slate-700 text-xs text-center">
                    <Brain className="w-8 h-8 mb-2 opacity-30 animate-pulse" />
                    <p>Esperando actividad neuronal...</p>
                    <p className="text-[10px] mt-1 text-slate-800">
                      Los eventos aparecerán cuando el agente procese mensajes
                    </p>
                  </div>
                ) : (
                  recentEvents.slice(0, 30).map((evt) => (
                    <EventRow key={evt.id} event={evt} />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
