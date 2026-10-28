/**
 * useLivingBrain - React hook for real-time AI synaptic brain events
 * Connects to Socket.IO backend and manages Living Brain Canvas state.
 * Events light up the neural mesh visualization in real-time.
 * Dynamically queries account/tenant topology (Channels, LEM Guardrail, Agents, Tools, RAG Docs).
 */
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import apiClient from '@/lib/api-client';

export type BrainNodeType = 'conductor' | 'rag_chunk' | 'tool' | 'agent' | 'query' | 'pulse' | 'lem' | 'channel';

export interface BrainNode {
  id: string;
  type: BrainNodeType;
  label: string;
  description?: string;
  metadata?: Record<string, unknown>;
  glowIntensity: number; // 0-1
  isActive: boolean;
  x: number;
  y: number;
  vx: number;
  vy: number;
  pulsePhase: number;
}

export interface SynapticEdge {
  source: string;
  target: string;
  isActive: boolean;
  particleProgress: number; // 0-1 for photon travel
  color: string;
}

export interface BrainEvent {
  id: string;
  event: string;
  label: string;
  detail: string;
  ts: string;
  nodeType: BrainNodeType;
  icon: string;
}

interface UseLivingBrainReturn {
  nodes: BrainNode[];
  edges: SynapticEdge[];
  recentEvents: BrainEvent[];
  isConnected: boolean;
  totalProcessed: number;
  simulateBrainActivity: (query: string) => Promise<void>;
  refetchTopology: () => Promise<void>;
  companyName: string;
}

const EVENT_ICONS: Record<string, string> = {
  AGENT_THOUGHT_START: '🧠',
  RAG_QUERY_START: '🔍',
  RAG_HIT: '📄',
  TOOL_DISPATCH: '⚡',
  TOOL_RESULT: '✅',
  AGENT_RESPONSE_COMPLETE: '🌐',
  SYNAPSE_PULSE: '💓',
  LEM_GUARD_EVALUATE: '⚖️',
};

const CANVAS_W = 900;
const CANVAS_H = 580;

function createFallbackNodes(): BrainNode[] {
  const cx = CANVAS_W / 2;
  const cy = CANVAS_H / 2;

  return [
    {
      id: 'channel_webchat_default',
      type: 'channel',
      label: 'Webchat / Copilot',
      description: 'Canal de mensajería web y copiloto administrativo.',
      glowIntensity: 0.6,
      isActive: false,
      x: cx - 280,
      y: cy + 150,
      vx: 0,
      vy: 0,
      pulsePhase: 0.5,
    },
    {
      id: 'lem_guardian',
      type: 'lem',
      label: 'Guardián LEM (E < 0.20)',
      description: 'Guardián determinista neurosimbólico (Latent Equilibrium Models).',
      glowIntensity: 0.8,
      isActive: false,
      x: cx - 140,
      y: cy + 80,
      vx: 0,
      vy: 0,
      pulsePhase: 1.0,
      metadata: { threshold: 0.20, engine: 'LEM-Ops' }
    },
    {
      id: 'conductor_core',
      type: 'conductor',
      label: 'Krof (Conductor IA)',
      description: 'Orquestador cognitivo central del sistema.',
      glowIntensity: 0.9,
      isActive: false,
      x: cx,
      y: cy - 20,
      vx: 0,
      vy: 0,
      pulsePhase: 0,
    },
    {
      id: 'rag_memory_core',
      type: 'rag_chunk',
      label: 'Memoria RAG',
      description: 'Base vectorial semántica de la organización.',
      glowIntensity: 0.5,
      isActive: false,
      x: cx - 240,
      y: cy - 130,
      vx: 0,
      vy: 0,
      pulsePhase: 1.2,
    },
    {
      id: 'tool_crm_pipeline',
      type: 'tool',
      label: 'CRM & Pipeline',
      description: 'Embudos de venta, contactos y scoring.',
      glowIntensity: 0.3,
      isActive: false,
      x: cx + 250,
      y: cy - 60,
      vx: 0,
      vy: 0,
      pulsePhase: 0.8,
    },
    {
      id: 'tool_payments',
      type: 'tool',
      label: 'Pasarela Pagos',
      description: 'Procesamiento de pagos y transacciones seguras.',
      glowIntensity: 0.3,
      isActive: false,
      x: cx + 270,
      y: cy + 40,
      vx: 0,
      vy: 0,
      pulsePhase: 1.8,
    },
    {
      id: 'tool_voice_livekit',
      type: 'tool',
      label: 'Voz WebRTC',
      description: 'Motor conversacional de baja latencia.',
      glowIntensity: 0.3,
      isActive: false,
      x: cx + 220,
      y: cy + 140,
      vx: 0,
      vy: 0,
      pulsePhase: 2.5,
    },
  ];
}

function createFallbackEdges(): SynapticEdge[] {
  return [
    { source: 'channel_webchat_default', target: 'lem_guardian', isActive: false, particleProgress: 0, color: '#10b981' },
    { source: 'lem_guardian', target: 'conductor_core', isActive: false, particleProgress: 0, color: '#f59e0b' },
    { source: 'conductor_core', target: 'rag_memory_core', isActive: false, particleProgress: 0, color: '#38bdf8' },
    { source: 'conductor_core', target: 'tool_crm_pipeline', isActive: false, particleProgress: 0, color: '#06b6d4' },
    { source: 'conductor_core', target: 'tool_payments', isActive: false, particleProgress: 0, color: '#06b6d4' },
    { source: 'conductor_core', target: 'tool_voice_livekit', isActive: false, particleProgress: 0, color: '#06b6d4' },
  ];
}

export function useLivingBrain(companyIdProp?: number | null): UseLivingBrainReturn {
  const socketRef = useRef<Socket | null>(null);
  const [nodes, setNodes] = useState<BrainNode[]>(createFallbackNodes);
  const [edges, setEdges] = useState<SynapticEdge[]>(createFallbackEdges);
  const [recentEvents, setRecentEvents] = useState<BrainEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [totalProcessed, setTotalProcessed] = useState(0);
  const [companyName, setCompanyName] = useState<string>('Mi Empresa');
  const [activeCompanyId, setActiveCompanyId] = useState<number | null>(companyIdProp || null);

  // Activate a node temporarily (glow + pulse)
  const activateNode = useCallback((nodeId: string, intensity: number = 1.0) => {
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId
          ? { ...n, isActive: true, glowIntensity: intensity }
          : n
      )
    );
    setTimeout(() => {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? { ...n, isActive: false, glowIntensity: Math.max(0.2, n.glowIntensity * 0.4) }
            : n
        )
      );
    }, 2800);
  }, []);

  // Send a photon particle along an edge
  const activateEdge = useCallback((sourceId: string, targetId: string) => {
    setEdges((prev) =>
      prev.map((e) =>
        (e.source === sourceId && e.target === targetId) || (e.source === targetId && e.target === sourceId)
          ? { ...e, isActive: true, particleProgress: 0 }
          : e
      )
    );
    setTimeout(() => {
      setEdges((prev) =>
        prev.map((e) =>
          (e.source === sourceId && e.target === targetId) || (e.source === targetId && e.target === sourceId)
            ? { ...e, isActive: false, particleProgress: 0 }
            : e
        )
      );
    }, 1200);
  }, []);

  // Add event to the event log
  const addEvent = useCallback((eventType: string, detail: string, nodeType: BrainNodeType) => {
    const newEvent: BrainEvent = {
      id: `${Date.now()}_${Math.random()}`,
      event: eventType,
      label: eventType.replace(/_/g, ' '),
      detail,
      ts: new Date().toLocaleTimeString(),
      nodeType,
      icon: EVENT_ICONS[eventType] || '●',
    };
    setRecentEvents((prev) => [newEvent, ...prev].slice(0, 50));
    setTotalProcessed((prev) => prev + 1);
  }, []);

  // Fetch real company dynamic topology
  const refetchTopology = useCallback(async () => {
    try {
      const res = await apiClient.get('/rag/brain-events/topology');
      const data = res.data;
      if (!data || !data.nodes) return;

      if (data.company_id) {
        setActiveCompanyId(data.company_id);
      }
      if (data.company_name) {
        setCompanyName(data.company_name);
      }

      // Position nodes dynamically across the canvas space (900 x 580)
      const rawNodes = data.nodes as Array<any>;
      const rawEdges = (data.edges || []) as Array<any>;

      const channelsList = rawNodes.filter(n => n.type === 'channel');
      const lemList = rawNodes.filter(n => n.type === 'lem');
      const conductorList = rawNodes.filter(n => n.type === 'conductor');
      const agentsList = rawNodes.filter(n => n.type === 'agent');
      const toolsList = rawNodes.filter(n => n.type === 'tool');
      const ragCoreList = rawNodes.filter(n => n.id === 'rag_memory_core');
      const docsList = rawNodes.filter(n => n.type === 'rag_chunk' && n.id !== 'rag_memory_core');

      const mappedNodes: BrainNode[] = [];

      // 1. Channels (Bottom-Left)
      channelsList.forEach((ch, idx) => {
        mappedNodes.push({
          id: ch.id,
          type: 'channel',
          label: ch.label,
          description: ch.description,
          metadata: ch.metadata,
          glowIntensity: ch.glowIntensity ?? 0.6,
          isActive: false,
          x: 120 + (idx % 2) * 80,
          y: 430 + Math.floor(idx / 2) * 60,
          vx: 0,
          vy: 0,
          pulsePhase: idx * 0.7,
        });
      });

      // 2. LEM Guardian (Positioned as arbiter between channels and conductor)
      lemList.forEach((lem) => {
        mappedNodes.push({
          id: lem.id,
          type: 'lem',
          label: lem.label,
          description: lem.description,
          metadata: lem.metadata,
          glowIntensity: lem.glowIntensity ?? 0.8,
          isActive: false,
          x: 310,
          y: 360,
          vx: 0,
          vy: 0,
          pulsePhase: 1.0,
        });
      });

      // 3. Conductor Core (Central Hub)
      conductorList.forEach((cond) => {
        mappedNodes.push({
          id: cond.id,
          type: 'conductor',
          label: cond.label,
          description: cond.description,
          metadata: cond.metadata,
          glowIntensity: cond.glowIntensity ?? 0.9,
          isActive: false,
          x: 470,
          y: 260,
          vx: 0,
          vy: 0,
          pulsePhase: 0,
        });
      });

      // 4. Specialized Agents (Orbit / Crown across top-center)
      const agentCount = agentsList.length || 1;
      agentsList.forEach((ag, idx) => {
        const step = Math.PI / (agentCount + 1);
        const angle = Math.PI - (idx + 1) * step; // Curve across upper dome
        const radius = 175;
        mappedNodes.push({
          id: ag.id,
          type: 'agent',
          label: ag.label,
          description: ag.description,
          metadata: ag.metadata,
          glowIntensity: ag.glowIntensity ?? 0.5,
          isActive: false,
          x: 470 + Math.cos(angle) * (radius + 20),
          y: 260 - Math.sin(angle) * (radius * 0.85),
          vx: 0,
          vy: 0,
          pulsePhase: idx * 0.4,
        });
      });

      // 5. Tools & Integrations (Right flank)
      toolsList.forEach((tool, idx) => {
        mappedNodes.push({
          id: tool.id,
          type: 'tool',
          label: tool.label,
          description: tool.description,
          metadata: tool.metadata,
          glowIntensity: tool.glowIntensity ?? 0.4,
          isActive: false,
          x: 740 + (idx % 2) * 45,
          y: 190 + idx * 80,
          vx: 0,
          vy: 0,
          pulsePhase: idx * 0.9,
        });
      });

      // 6. RAG Memory Core (Top-Left quadrant)
      ragCoreList.forEach((rc) => {
        mappedNodes.push({
          id: rc.id,
          type: 'rag_chunk',
          label: rc.label,
          description: rc.description,
          metadata: rc.metadata,
          glowIntensity: rc.glowIntensity ?? 0.6,
          isActive: false,
          x: 210,
          y: 140,
          vx: 0,
          vy: 0,
          pulsePhase: 1.5,
        });
      });

      // 7. Real Documents (Satellite nodes orbiting RAG Memory Core)
      docsList.forEach((doc, idx) => {
        mappedNodes.push({
          id: doc.id,
          type: 'rag_chunk',
          label: doc.label,
          description: doc.description,
          metadata: doc.metadata,
          glowIntensity: doc.glowIntensity ?? 0.3,
          isActive: false,
          x: 90 + (idx % 2) * 80,
          y: 80 + Math.floor(idx / 2) * 55,
          vx: 0,
          vy: 0,
          pulsePhase: idx * 0.6,
        });
      });

      setNodes(mappedNodes.length > 0 ? mappedNodes : createFallbackNodes());

      const mappedEdges: SynapticEdge[] = rawEdges.map((e: any) => ({
        source: e.source,
        target: e.target,
        isActive: false,
        particleProgress: 0,
        color: e.color || '#6366f1',
      }));

      setEdges(mappedEdges.length > 0 ? mappedEdges : createFallbackEdges());
    } catch (err) {
      console.warn('[useLivingBrain] Failed to load dynamic topology, using default mesh:', err);
    }
  }, []);

  // Handle incoming socket events
  const handleBrainEvent = useCallback(
    (eventType: string, data: Record<string, unknown>) => {
      switch (eventType) {
        case 'AGENT_THOUGHT_START': {
          activateNode('conductor_core', 1.0);
          activateNode('lem_guardian', 0.9);
          activateEdge('lem_guardian', 'conductor_core');
          const agentName = String(data.agent_name || 'Conductor IA');
          addEvent(eventType, `${agentName}: "${String(data.query_preview || '').slice(0, 60)}"`, 'conductor');
          break;
        }

        case 'RAG_QUERY_START':
          activateNode('conductor_core', 0.8);
          activateEdge('conductor_core', 'rag_memory_core');
          activateNode('rag_memory_core', 1.0);
          addEvent(eventType, `Búsqueda Vectorial: "${String(data.query || '').slice(0, 60)}"`, 'rag_chunk');
          break;

        case 'RAG_HIT': {
          const filename = String(data.filename || 'Documento');
          const score = Number(data.relevance_score || 0);
          activateNode('rag_memory_core', 0.8);
          activateNode('conductor_core', 0.7);
          activateEdge('rag_memory_core', 'conductor_core');
          addEvent(eventType, `${filename} (relevancia: ${(score * 100).toFixed(0)}%)`, 'rag_chunk');
          break;
        }

        case 'TOOL_DISPATCH': {
          const toolName = String(data.tool_name || 'tool');
          const matchingTool = nodes.find(n => n.type === 'tool' && n.label.toLowerCase().includes(toolName.toLowerCase().slice(0, 4))) || nodes.find(n => n.type === 'tool');
          if (matchingTool) {
            activateNode('conductor_core', 0.7);
            activateEdge('conductor_core', matchingTool.id);
            activateNode(matchingTool.id, 1.0);
          }
          addEvent(eventType, `Ejecución Tool: ${toolName}`, 'tool');
          break;
        }

        case 'TOOL_RESULT':
          addEvent(
            eventType,
            `${data.tool_name}: ${data.status === 'success' ? '✅ OK' : '❌ Error'}`,
            'tool'
          );
          break;

        case 'AGENT_RESPONSE_COMPLETE':
          activateNode('conductor_core', 1.0);
          activateNode('lem_guardian', 0.6);
          addEvent(
            eventType,
            `${data.agent_name || 'Agente'} → ${data.tokens_used || 0} tokens · canal: ${data.channel || 'webchat'}`,
            'conductor'
          );
          break;

        case 'SYNAPSE_PULSE':
          activateNode('conductor_core', 0.4);
          addEvent(eventType, `Pulso activo: ${data.active_agents || 1} agentes`, 'pulse');
          break;

        default:
          break;
      }
    },
    [activateNode, activateEdge, addEvent, nodes]
  );

  // Initial topology fetch
  useEffect(() => {
    refetchTopology();
  }, [refetchTopology]);

  // Socket.IO connection & auto-join room
  useEffect(() => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api';
    const socketUrl = API_URL.replace('/api', '');

    const socket = io(socketUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 2000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      if (activeCompanyId) {
        socket.emit('join_company', { company_id: activeCompanyId });
      }
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    const brainEvents = [
      'AGENT_THOUGHT_START',
      'RAG_QUERY_START',
      'RAG_HIT',
      'TOOL_DISPATCH',
      'TOOL_RESULT',
      'AGENT_RESPONSE_COMPLETE',
      'SYNAPSE_PULSE',
      'LEM_GUARD_EVALUATE'
    ];

    brainEvents.forEach((evt) => {
      socket.on(evt, (data: Record<string, unknown>) => {
        handleBrainEvent(evt, data);
      });
    });

    return () => {
      brainEvents.forEach((evt) => socket.off(evt));
      socket.disconnect();
    };
  }, [activeCompanyId, handleBrainEvent]);

  // If activeCompanyId changes after topology load, join the room immediately
  useEffect(() => {
    if (socketRef.current?.connected && activeCompanyId) {
      socketRef.current.emit('join_company', { company_id: activeCompanyId });
    }
  }, [activeCompanyId]);

  const simulateBrainActivity = useCallback(async (query: string) => {
    try {
      await apiClient.post('/rag/brain-events/simulate', { query });
    } catch (err) {
      console.error('[useLivingBrain] Simulate error:', err);
    }
  }, []);

  return {
    nodes,
    edges,
    recentEvents,
    isConnected,
    totalProcessed,
    simulateBrainActivity,
    refetchTopology,
    companyName,
  };
}
