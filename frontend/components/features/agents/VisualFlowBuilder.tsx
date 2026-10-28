'use client';

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  MiniMap, 
  applyNodeChanges, 
  applyEdgeChanges, 
  addEdge,
  Connection, 
  Edge, 
  Node, 
  NodeChange, 
  EdgeChange,
  MarkerType,
  BackgroundVariant,
  Panel,
  useReactFlow,
  ReactFlowProvider,
  type NodeTypes
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { 
  GitFork, 
  Play, 
  Save, 
  Plus, 
  Trash2, 
  Workflow, 
  HelpCircle, 
  UserCheck, 
  MessageSquare, 
  Wrench,
  Layers,
  Sparkles,
  RefreshCw,
  Eye,
  Maximize2,
  MousePointer,
  RotateCcw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { WorkflowNode, WorkflowNodeData } from './WorkflowNode';
import { DeletableEdge } from './DeletableEdge';

export type FlowNodeType = 'message' | 'question' | 'decision' | 'action' | 'handover';

const INITIAL_NODES: Node<WorkflowNodeData>[] = [
  {
    id: 'node-welcome',
    type: 'workflowNode',
    position: { x: 250, y: 50 },
    data: {
      label: 'Bienvenida Inicial',
      type: 'message',
      text: '¡Hola! Bienvenido a Aikrofy. ¿En qué podemos asesorarte hoy?',
      isStart: true,
    }
  },
  {
    id: 'node-ask-topic',
    type: 'workflowNode',
    position: { x: 250, y: 220 },
    data: {
      label: 'Calificar Interés',
      type: 'question',
      field: 'tipo_servicio',
      text: '¿Buscas automatizar canales de WhatsApp o integrar tus sistemas ERP/CRM?',
      isStart: false,
    }
  },
  {
    id: 'node-decision',
    type: 'workflowNode',
    position: { x: 100, y: 400 },
    data: {
      label: 'Interés Enterprise',
      type: 'decision',
      condition: 'tipo_servicio == "enterprise"',
      isStart: false,
    }
  },
  {
    id: 'node-handover',
    type: 'workflowNode',
    position: { x: 100, y: 560 },
    data: {
      label: 'Escalar a Director Comercial',
      type: 'handover',
      reason: 'Lead Enterprise de alto volumen',
      target_role: 'sales_executive',
      isStart: false,
    }
  },
  {
    id: 'node-action-catalog',
    type: 'workflowNode',
    position: { x: 420, y: 400 },
    data: {
      label: 'Enviar Catálogo REST',
      type: 'action',
      action_name: 'consultar_catalogo_servicios',
      isStart: false,
    }
  }
];

const INITIAL_EDGES: Edge[] = [
  {
    id: 'e-welcome-ask',
    source: 'node-welcome',
    target: 'node-ask-topic',
    animated: true,
    style: { stroke: '#8b5cf6', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' }
  },
  {
    id: 'e-ask-decision',
    source: 'node-ask-topic',
    target: 'node-decision',
    animated: true,
    style: { stroke: '#f59e0b', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' }
  },
  {
    id: 'e-decision-handover',
    source: 'node-decision',
    target: 'node-handover',
    animated: true,
    style: { stroke: '#f43f5e', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f43f5e' }
  },
  {
    id: 'e-ask-action',
    source: 'node-ask-topic',
    target: 'node-action-catalog',
    animated: true,
    style: { stroke: '#10b981', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' }
  }
];

function FlowCanvasInner() {
  const queryClient = useQueryClient();
  const reactFlowInstance = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  const [nodes, setNodes] = useState<Node<WorkflowNodeData>[]>(INITIAL_NODES);
  const [edges, setEdges] = useState<Edge[]>(INITIAL_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('node-welcome');
  const [selectedGraphId, setSelectedGraphId] = useState<number | null>(null);
  const [graphName, setGraphName] = useState('Flujo Inteligente Multicanal');
  const [graphDescription, setGraphDescription] = useState('Orquestación visual de LangGraph StateGraph');
  const [isLivePreview, setIsLivePreview] = useState(false);

  // Fetch graphs from backend
  const { data: graphsData } = useQuery({
    queryKey: ['company-graphs'],
    queryFn: async () => {
      const res = await apiClient.get('/enterprise/graphs');
      return res.data?.graphs || [];
    }
  });

  // Sync existing graph if found
  useEffect(() => {
    if (graphsData && graphsData.length > 0 && !selectedGraphId) {
      const activeGraph = graphsData.find((g: any) => g.is_published) || graphsData[0];
      setSelectedGraphId(activeGraph.id);
      setGraphName(activeGraph.name);
      setGraphDescription(activeGraph.description || '');

      const canvas = activeGraph.canvas_data;
      if (canvas?.nodes && Array.isArray(canvas.nodes) && canvas.nodes.length > 0) {
        // Map raw canvas nodes to xyflow nodes
        const mappedNodes: Node<WorkflowNodeData>[] = canvas.nodes.map((n: any, idx: number) => ({
          id: n.id,
          type: 'workflowNode',
          position: n.position || { x: 250, y: 60 + idx * 160 },
          data: {
            ...n.data,
            isStart: idx === 0 || n.data?.isStart
          }
        }));
        const mappedEdges: Edge[] = (canvas.edges || []).map((e: any) => ({
          id: e.id || `e-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          animated: true,
          style: { stroke: '#8b5cf6', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' }
        }));

        setNodes(mappedNodes);
        setEdges(mappedEdges);
        setSelectedNodeId(mappedNodes[0].id);
      }
    }
  }, [graphsData, selectedGraphId]);

  // Handle deletion inside node callback
  const handleDeleteNode = useCallback((id: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelectedNodeId((prev) => (prev === id ? null : prev));
    toast.success('Paso eliminado del flujo');
  }, []);

  // Handle direct edge deletion / disconnection
  const handleDeleteEdge = useCallback((edgeId: string) => {
    setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    toast.success('Enlace desconectado');
  }, []);

  // Pass onDelete handler into node data
  const nodesWithHandlers = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        onDelete: handleDeleteNode
      }
    }));
  }, [nodes, handleDeleteNode]);

  // Pass onDelete handler and custom type into edges
  const edgesWithHandlers = useMemo(() => {
    return edges.map((edge) => ({
      ...edge,
      type: 'deletableEdge',
      data: {
        ...edge.data,
        onDelete: handleDeleteEdge
      }
    }));
  }, [edges, handleDeleteEdge]);

  // React Flow changes
  const onNodesChange = useCallback(
    (changes: NodeChange<Node<WorkflowNodeData>>[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'deletableEdge',
            animated: true,
            style: { stroke: '#8b5cf6', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' }
          },
          eds
        )
      );
      toast.success('Cables conectados');
    },
    []
  );

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      setEdges((els) => els.filter((e) => e.id !== oldEdge.id).concat({
        ...oldEdge,
        ...newConnection,
        type: 'deletableEdge',
        animated: true,
        style: { stroke: '#8b5cf6', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' }
      }));
      toast.success('Conexión reorientada');
    },
    []
  );

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  // Add node dynamically at good viewport offset
  const handleAddNode = (type: FlowNodeType) => {
    const id = `node-${Date.now()}`;
    const defaultLabels: Record<FlowNodeType, string> = {
      message: 'Mensaje IA',
      question: 'Pregunta / Calificación',
      decision: 'Bifurcación Condicional',
      action: 'Acción Conector REST',
      handover: 'Traspaso Asesor Humano'
    };

    // Calculate position offset based on current nodes count
    const lastNode = nodes[nodes.length - 1];
    const newX = lastNode ? lastNode.position.x + 30 : 250;
    const newY = lastNode ? lastNode.position.y + 140 : 100;

    const newNode: Node<WorkflowNodeData> = {
      id,
      type: 'workflowNode',
      position: { x: newX, y: newY },
      data: {
        label: defaultLabels[type],
        type,
        text: type === 'message' ? 'Mensaje para el cliente...' : type === 'question' ? '¿En qué te ayudamos?' : undefined,
        field: type === 'question' ? 'categoria_cliente' : undefined,
        condition: type === 'decision' ? 'valor > 500' : undefined,
        action_name: type === 'action' ? 'consultar_stock' : undefined,
        reason: type === 'handover' ? 'Atención especializada' : undefined,
        target_role: type === 'handover' ? 'sales_executive' : undefined,
        isStart: false
      }
    };

    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeId(id);

    // Auto connect from last node
    if (lastNode) {
      setEdges((eds) => [
        ...eds,
        {
          id: `e-${lastNode.id}-${id}`,
          source: lastNode.id,
          target: id,
          animated: true,
          style: { stroke: '#8b5cf6', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' }
        }
      ]);
    }

    toast.success(`Nodo ${defaultLabels[type]} añadido al canvas`);
  };

  // Drag and Drop from sidebar panel
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow') as FlowNodeType;
      if (!type) return;

      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!bounds) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const id = `node-${Date.now()}`;
      const defaultLabels: Record<FlowNodeType, string> = {
        message: 'Mensaje IA',
        question: 'Pregunta / Calificación',
        decision: 'Bifurcación Condicional',
        action: 'Acción Conector REST',
        handover: 'Traspaso Humano'
      };

      const newNode: Node<WorkflowNodeData> = {
        id,
        type: 'workflowNode',
        position,
        data: {
          label: defaultLabels[type] || 'Nuevo Paso',
          type,
          text: type === 'message' ? 'Mensaje para el cliente...' : type === 'question' ? '¿En qué te ayudamos?' : undefined,
          field: type === 'question' ? 'dato_cliente' : undefined,
          condition: type === 'decision' ? 'valor == 1' : undefined,
          action_name: type === 'action' ? 'ejecutar_api' : undefined,
          reason: type === 'handover' ? 'Traspaso automático' : undefined,
          target_role: type === 'handover' ? 'sales_executive' : undefined,
          isStart: false
        }
      };

      setNodes((nds) => [...nds, newNode]);
      setSelectedNodeId(id);
      toast.success(`Nodo soltado en el canvas`);
    },
    [reactFlowInstance]
  );

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        id: selectedGraphId,
        name: graphName,
        description: graphDescription,
        canvas_data: {
          nodes: nodes.map((n) => ({
            id: n.id,
            type: n.data.type,
            position: n.position,
            data: n.data
          })),
          edges: edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target
          }))
        }
      };
      const res = await apiClient.post('/enterprise/graphs', payload);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('Flujo visual guardado exitosamente');
      queryClient.invalidateQueries({ queryKey: ['company-graphs'] });
      if (data.graph?.id) setSelectedGraphId(data.graph.id);
    },
    onError: (err: any) => {
      toast.error('Error al guardar: ' + (err.response?.data?.error || err.message));
    }
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: async () => {
      const saveRes = await apiClient.post('/enterprise/graphs', {
        id: selectedGraphId,
        name: graphName,
        description: graphDescription,
        canvas_data: {
          nodes: nodes.map((n) => ({
            id: n.id,
            type: n.data.type,
            position: n.position,
            data: n.data
          })),
          edges: edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target
          }))
        }
      });
      const gId = saveRes.data.graph.id;
      setSelectedGraphId(gId);
      const res = await apiClient.post(`/enterprise/graphs/${gId}/publish`);
      return res.data;
    },
    onSuccess: () => {
      toast.success('¡Flujo publicado con éxito! Ahora gobierna el enrutamiento de agentes.');
      queryClient.invalidateQueries({ queryKey: ['company-graphs'] });
    },
    onError: (err: any) => {
      toast.error('Error al publicar: ' + (err.response?.data?.error || err.message));
    }
  });

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  const updateSelectedNodeData = (key: string, value: any) => {
    if (!selectedNodeId) return;
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === selectedNodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              [key]: value
            }
          };
        }
        return n;
      })
    );
  };

  // Cast necesario: @xyflow/react v12 tipa NodeTypes con props de nodo completas,
  // mientras WorkflowNode declara NodeProps<any>; render idéntico en runtime.
  const nodeTypes = useMemo<NodeTypes>(() => ({ workflowNode: WorkflowNode as unknown as NodeTypes[string] }), []);
  const edgeTypes = useMemo(() => ({ deletableEdge: DeletableEdge }), []);

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card border rounded-2xl p-5 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 shadow-md text-white">
              <Workflow className="h-4 w-4" />
            </div>
            <h3 className="text-lg font-bold">Flow Studio — Orquestador de Flujos No-Code</h3>
            <Badge variant="outline" className="text-xs bg-violet-500/10 text-violet-600 border-violet-200">
              Lienzo Interactivo en Tiempo Real
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Arrastra, conecta, reconecta y desconecta cajas con cables curvos interactivos. Diseña el razonamiento de tus agentes con zoom y paneo fluido.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsLivePreview(!isLivePreview)}
            className="text-xs gap-1.5"
          >
            <Eye className="w-3.5 h-3.5 text-indigo-500" />
            {isLivePreview ? 'Ocultar JSON' : 'Ver Spec JSON'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="text-xs gap-1.5"
          >
            {saveMutation.isPending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-blue-500" />}
            Guardar
          </Button>

          <Button
            size="sm"
            onClick={() => publishMutation.mutate()}
            disabled={publishMutation.isPending}
            className="text-xs gap-1.5 vivid-gradient-violet text-white shadow-md hover:opacity-95"
          >
            {publishMutation.isPending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            Publicar en Vivo
          </Button>
        </div>
      </div>

      {/* Main Builder Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full max-w-full overflow-hidden">
        {/* Left Drag & Drop Toolbar Palette */}
        <div className="lg:col-span-2 space-y-3">
          <Card className="border-border shadow-xs">
            <CardHeader className="p-3 pb-2 border-b">
              <CardTitle className="text-xs font-semibold flex items-center gap-1.5">
                <MousePointer className="w-3.5 h-3.5 text-violet-500" />
                Herramientas
              </CardTitle>
              <CardDescription className="text-[11px]">
                Arrastra al lienzo o pulsa para añadir
              </CardDescription>
            </CardHeader>
            <CardContent className="p-3 grid grid-cols-2 lg:grid-cols-1 gap-2">
              <div
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'message')}
                onClick={() => handleAddNode('message')}
                className="flex items-center gap-2 p-2 rounded-xl border border-sky-500/30 bg-sky-500/5 hover:bg-sky-500/10 cursor-grab active:cursor-grabbing transition-all text-xs font-medium text-sky-600 dark:text-sky-400 select-none"
              >
                <MessageSquare className="w-4 h-4 shrink-0" />
                <span className="truncate">Mensaje IA</span>
              </div>

              <div
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'question')}
                onClick={() => handleAddNode('question')}
                className="flex items-center gap-2 p-2 rounded-xl border border-indigo-500/30 bg-indigo-500/5 hover:bg-indigo-500/10 cursor-grab active:cursor-grabbing transition-all text-xs font-medium text-indigo-600 dark:text-indigo-400 select-none"
              >
                <HelpCircle className="w-4 h-4 shrink-0" />
                <span className="truncate">Pregunta</span>
              </div>

              <div
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'decision')}
                onClick={() => handleAddNode('decision')}
                className="flex items-center gap-2 p-2 rounded-xl border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 cursor-grab active:cursor-grabbing transition-all text-xs font-medium text-amber-600 dark:text-amber-400 select-none"
              >
                <GitFork className="w-4 h-4 shrink-0" />
                <span className="truncate">Bifurcación</span>
              </div>

              <div
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'action')}
                onClick={() => handleAddNode('action')}
                className="flex items-center gap-2 p-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10 cursor-grab active:cursor-grabbing transition-all text-xs font-medium text-emerald-600 dark:text-emerald-400 select-none"
              >
                <Wrench className="w-4 h-4 shrink-0" />
                <span className="truncate">Acción REST</span>
              </div>

              <div
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/reactflow', 'handover')}
                onClick={() => handleAddNode('handover')}
                className="col-span-2 lg:col-span-1 flex items-center gap-2 p-2 rounded-xl border border-rose-500/30 bg-rose-500/5 hover:bg-rose-500/10 cursor-grab active:cursor-grabbing transition-all text-xs font-medium text-rose-600 dark:text-rose-400 select-none"
              >
                <UserCheck className="w-4 h-4 shrink-0" />
                <span className="truncate">Handover Humano</span>
              </div>
            </CardContent>
          </Card>

          {/* Quick instructions */}
          <div className="p-3 rounded-xl bg-muted/40 border text-[11px] text-muted-foreground space-y-1.5 hidden sm:block">
            <p className="font-semibold text-foreground">Tips de Conexión y Desconexión:</p>
            <p>• <span className="text-foreground font-medium">Conectar:</span> Arrastra desde el conector inferior (morado) al superior de otro paso.</p>
            <p>• <span className="text-foreground font-medium">Desconectar:</span> Haz clic en el botón circular <span className="text-rose-500 font-bold">✕</span> situado en medio de cualquier cable, o selecciónalo y presiona <kbd className="px-1 py-0.5 bg-muted border rounded text-[10px]">Supr</kbd>.</p>
            <p>• <span className="text-foreground font-medium">Reconectar:</span> Arrastra el extremo del cable a otra caja para cambiar de destino.</p>
          </div>
        </div>

        {/* Center: React Flow Interactive Canvas */}
        <div className="lg:col-span-7 min-w-0" ref={reactFlowWrapper}>
          <div className="relative w-full h-[520px] sm:h-[620px] lg:h-[720px] rounded-2xl border bg-slate-950/5 dark:bg-slate-950/80 overflow-hidden shadow-inner">
            <ReactFlow
              nodes={nodesWithHandlers}
              edges={edgesWithHandlers}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onReconnect={onReconnect}
              onNodeClick={onNodeClick}
              onDrop={onDrop}
              onDragOver={onDragOver}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              fitView
              minZoom={0.2}
              maxZoom={1.8}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1.5} color="#8882" />
              <Controls position="bottom-left" className="!bg-card !border-border !shadow-md !rounded-xl overflow-hidden" />
              <MiniMap 
                position="bottom-right" 
                className="!bg-card !border !border-border !rounded-xl !shadow-md" 
                nodeColor="#8b5cf6" 
                maskColor="rgba(0,0,0,0.4)" 
              />
              
              <Panel position="top-right" className="bg-card/90 backdrop-blur-md px-3 py-1.5 rounded-xl border shadow-xs text-xs font-mono text-muted-foreground">
                {nodes.length} Nodos • {edges.length} Conexiones
              </Panel>
            </ReactFlow>
          </div>

          {/* JSON Spec Inspector */}
          {isLivePreview && (
            <Card className="mt-4 border-border bg-slate-900 text-slate-100 font-mono text-xs">
              <CardHeader className="py-2.5 px-4 border-b border-slate-800 flex flex-row items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">Spec Compilada de Nodos & Conexiones</span>
                <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30">
                  Ready
                </Badge>
              </CardHeader>
              <CardContent className="p-4 overflow-x-auto max-h-52">
                <pre>{JSON.stringify({ nodes, edges }, null, 2)}</pre>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Side: Selected Node Inspector */}
        <div className="lg:col-span-3 space-y-4">
          <Card className="border-border sticky top-4 shadow-sm">
            <CardHeader className="p-4 border-b">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-500" />
                Configurar Paso Activo
              </CardTitle>
              <CardDescription className="text-xs">
                Modifica el comportamiento del nodo en tiempo real
              </CardDescription>
            </CardHeader>

            <CardContent className="p-4 space-y-4">
              {selectedNode ? (
                <>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Nombre / Etiqueta</Label>
                    <Input
                      value={selectedNode.data.label || ''}
                      onChange={(e) => updateSelectedNodeData('label', e.target.value)}
                      className="text-xs"
                      placeholder="Nombre descriptivo"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Tipo de Nodo</Label>
                    <Select
                      value={selectedNode.data.type}
                      onValueChange={(val: FlowNodeType) => updateSelectedNodeData('type', val)}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="message">Mensaje IA</SelectItem>
                        <SelectItem value="question">Pregunta / Calificación</SelectItem>
                        <SelectItem value="decision">Bifurcación / Decisión</SelectItem>
                        <SelectItem value="action">Acción Conector REST</SelectItem>
                        <SelectItem value="handover">Traspaso Humano</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedNode.data.type === 'message' && (
                    <div className="space-y-1.5">
                      <Label className="text-xs">Contenido del Mensaje</Label>
                      <Textarea
                        rows={4}
                        value={selectedNode.data.text || ''}
                        onChange={(e) => updateSelectedNodeData('text', e.target.value)}
                        className="text-xs"
                        placeholder="Escribe lo que el agente comunicará al cliente..."
                      />
                    </div>
                  )}

                  {selectedNode.data.type === 'question' && (
                    <>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Pregunta</Label>
                        <Textarea
                          rows={3}
                          value={selectedNode.data.text || ''}
                          onChange={(e) => updateSelectedNodeData('text', e.target.value)}
                          className="text-xs"
                          placeholder="Pregunta de calificación..."
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Variable de Sesión</Label>
                        <Input
                          value={selectedNode.data.field || ''}
                          onChange={(e) => updateSelectedNodeData('field', e.target.value)}
                          className="text-xs font-mono"
                          placeholder="presupuesto, email, cargo..."
                        />
                      </div>
                    </>
                  )}

                  {selectedNode.data.type === 'decision' && (
                    <div className="space-y-1.5">
                      <Label className="text-xs">Condición de Evaluación</Label>
                      <Input
                        value={selectedNode.data.condition || ''}
                        onChange={(e) => updateSelectedNodeData('condition', e.target.value)}
                        className="text-xs font-mono text-amber-600 dark:text-amber-400"
                        placeholder="interes == 'ventas'"
                      />
                    </div>
                  )}

                  {selectedNode.data.type === 'action' && (
                    <div className="space-y-1.5">
                      <Label className="text-xs">Nombre del Tool REST</Label>
                      <Input
                        value={selectedNode.data.action_name || ''}
                        onChange={(e) => updateSelectedNodeData('action_name', e.target.value)}
                        className="text-xs font-mono"
                        placeholder="consultar_stock, facturar..."
                      />
                    </div>
                  )}

                  {selectedNode.data.type === 'handover' && (
                    <>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Motivo del Traspaso</Label>
                        <Input
                          value={selectedNode.data.reason || ''}
                          onChange={(e) => updateSelectedNodeData('reason', e.target.value)}
                          className="text-xs"
                          placeholder="Lead calificado de alta prioridad"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Rol Asignado</Label>
                        <Select
                          value={selectedNode.data.target_role || 'sales_executive'}
                          onValueChange={(val) => updateSelectedNodeData('target_role', val)}
                        >
                          <SelectTrigger className="text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="sales_executive">Ventas / Asesor Comercial</SelectItem>
                            <SelectItem value="support_tier2">Soporte Nivel 2</SelectItem>
                            <SelectItem value="supervisor">Supervisor</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  )}

                  {/* Active Connections List with Quick Disconnect */}
                  {(() => {
                    const connectedOut = edges.filter((e) => e.source === selectedNode.id);
                    const connectedIn = edges.filter((e) => e.target === selectedNode.id);

                    return (
                      <div className="pt-2 border-t space-y-2">
                        <Label className="text-xs font-semibold flex items-center justify-between">
                          <span>Conexiones Activas</span>
                          <span className="text-[10px] text-muted-foreground font-mono">
                            {connectedOut.length + connectedIn.length} enlaces
                          </span>
                        </Label>

                        {connectedOut.length === 0 && connectedIn.length === 0 ? (
                          <p className="text-[11px] text-muted-foreground italic">
                            Sin conexiones activas. Conecta este nodo arrastrando sus puntos morados.
                          </p>
                        ) : (
                          <div className="space-y-1.5 max-h-36 overflow-y-auto">
                            {connectedOut.map((e) => {
                              const targetNode = nodes.find((n) => n.id === e.target);
                              return (
                                <div
                                  key={e.id}
                                  className="flex items-center justify-between p-1.5 rounded-lg bg-muted/50 border text-[11px]"
                                >
                                  <span className="truncate max-w-[140px]">
                                    → Conecta con: <span className="font-medium text-foreground">{String(targetNode?.data?.label || e.target)}</span>
                                  </span>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteEdge(e.id)}
                                    className="h-6 px-1.5 text-[10px] text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                                    title="Desconectar este enlace"
                                  >
                                    Desconectar
                                  </Button>
                                </div>
                              );
                            })}

                            {connectedIn.map((e) => {
                              const sourceNode = nodes.find((n) => n.id === e.source);
                              return (
                                <div
                                  key={e.id}
                                  className="flex items-center justify-between p-1.5 rounded-lg bg-muted/50 border text-[11px]"
                                >
                                  <span className="truncate max-w-[140px]">
                                    ← Viene de: <span className="font-medium text-foreground">{String(sourceNode?.data?.label || e.source)}</span>
                                  </span>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteEdge(e.id)}
                                    className="h-6 px-1.5 text-[10px] text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                                    title="Desconectar este enlace"
                                  >
                                    Desconectar
                                  </Button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })()}

                  {!selectedNode.data.isStart && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteNode(selectedNode.id)}
                      className="w-full text-xs text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 border-rose-200 dark:border-rose-900 mt-2"
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                      Eliminar Paso
                    </Button>
                  )}
                </>
              ) : (
                <div className="text-center py-10 text-muted-foreground text-xs">
                  Haz clic en un nodo del canvas para editar sus propiedades.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function VisualFlowBuilder() {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner />
    </ReactFlowProvider>
  );
}
