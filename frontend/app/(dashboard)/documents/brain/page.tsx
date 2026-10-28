'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import apiClient from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, Sparkles, FileText, Zap, Bot, Building2, Image as ImageIcon } from 'lucide-react';
import { toast } from 'sonner';

// Lazy-load the D3 galaxy (SSR: false)
const KnowledgeGalaxy = dynamic(
  () =>
    import('@/components/features/brain/KnowledgeGalaxy').then((m) => ({
      default: m.KnowledgeGalaxy,
    })),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[580px] w-full rounded-2xl" />,
  }
);

interface GraphStats {
  documents: number;
  skills: number;
  media: number;
  agents: number;
  departments: number;
  total_nodes: number;
  total_edges: number;
}

interface GraphData {
  nodes: any[];
  edges: any[];
  stats: GraphStats;
}

function StatPill({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${color} bg-card shadow-sm`}>
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <strong>{value}</strong>
      <span className="text-muted-foreground text-xs">{label}</span>
    </div>
  );
}

export default function BrainGalaxyPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchGraph = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await apiClient.get<GraphData>('/rag/knowledge-graph');
      setData(res.data);
    } catch (err: any) {
      toast.error('Error al cargar la galaxia: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 lg:p-8 min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
              <Sparkles className="h-4.5 w-4.5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Galaxia del Conocimiento</h1>
            <Badge variant="outline" className="hidden sm:flex">Brain RAG</Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-lg">
            Grafo interactivo de todos los activos de conocimiento de tu empresa: documentos, skills, media, agentes y departamentos, interconectados semánticamente.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchGraph(true)}
          disabled={refreshing}
          className="self-start sm:self-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Stats row */}
      {data && (
        <div className="flex flex-wrap gap-2">
          <StatPill icon={FileText} label="Documentos" value={data.stats.documents} color="text-indigo-600" />
          <StatPill icon={Zap} label="Skills" value={data.stats.skills} color="text-emerald-600" />
          <StatPill icon={ImageIcon} label="Media" value={data.stats.media} color="text-amber-600" />
          <StatPill icon={Bot} label="Agentes" value={data.stats.agents} color="text-violet-600" />
          <StatPill icon={Building2} label="Departamentos" value={data.stats.departments} color="text-blue-600" />
          <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-muted-foreground bg-muted/40 shadow-sm">
            <span className="font-medium text-foreground">{data.stats.total_nodes}</span> nodos ·
            <span className="font-medium text-foreground">{data.stats.total_edges}</span> conexiones
          </div>
        </div>
      )}

      {/* Graph */}
      <Card className="rounded-2xl shadow-sm overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Grafo de conocimiento interactivo</CardTitle>
          <p className="text-xs text-muted-foreground">
            Arrastra los nodos para reorganizar. Usa el scroll para zoom. Pasa el cursor para ver detalles. Busca nodos con la barra de búsqueda.
          </p>
        </CardHeader>
        <CardContent className="p-3">
          {loading ? (
            <Skeleton className="h-[580px] w-full rounded-xl" />
          ) : data ? (
            <KnowledgeGalaxy
              nodes={data.nodes}
              edges={data.edges}
              width={860}
              height={580}
            />
          ) : (
            <div className="flex h-48 flex-col items-center justify-center gap-3 text-muted-foreground">
              <Sparkles className="h-10 w-10 opacity-30" />
              <p className="text-sm">No se pudo cargar el grafo de conocimiento</p>
              <Button variant="outline" size="sm" onClick={() => fetchGraph()}>
                Reintentar
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tip */}
      <div className="flex items-start gap-2 rounded-xl border border-violet-200 bg-violet-50 dark:bg-violet-950/20 dark:border-violet-800 p-3 text-xs text-violet-700 dark:text-violet-300">
        <Sparkles className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        <span>
          <strong>Tip:</strong> Las conexiones entre nodos representan relaciones semánticas. Los agentes se conectan con skills que usan y documentos que consultan via RAG. Los departamentos se conectan con sus agentes y documentos asociados.
        </span>
      </div>
    </div>
  );
}
