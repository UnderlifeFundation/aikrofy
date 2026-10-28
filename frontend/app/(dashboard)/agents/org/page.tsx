'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslation } from 'react-i18next';
import apiClient from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, Zap, Bot, Building2, Activity } from 'lucide-react';
import { toast } from 'sonner';

// Lazy-load the D3 tree (SSR: false) to avoid hydration issues
const OrgConductorTree = dynamic(
  () =>
    import('@/components/features/org/OrgConductorTree').then((m) => ({
      default: m.OrgConductorTree,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-col gap-4 items-center py-10">
        <Skeleton className="h-16 w-16 rounded-2xl" />
        <div className="flex gap-4 mt-8">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64 w-48 rounded-2xl" />
          ))}
        </div>
      </div>
    ),
  }
);

interface HierarchyData {
  conductor: any;
  pillars: any[];
  stats: { total_agents: number; total_departments: number };
}

export default function AgentOrgPage() {
  const { t } = useTranslation();

  const [data, setData] = useState<HierarchyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHierarchy = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await apiClient.get<HierarchyData>('/agents/hierarchy');
      setData(res.data);
    } catch (err: any) {
      toast.error('Error al cargar el organigrama: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHierarchy();
  }, []);

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 lg:p-8 min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/20">
              <Zap className="h-4.5 w-4.5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Conductor IA</h1>
            <Badge variant="outline" className="hidden sm:flex">Organigrama</Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-lg">
            Vista jerárquica del ecosistema de agentes: conductor orquestador, pilares departamentales y workers activos.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchHierarchy(true)}
          disabled={refreshing}
          className="self-start sm:self-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Stats pills */}
      {data && (
        <div className="flex flex-wrap gap-3">
          <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-sm">
            <Bot className="h-4 w-4 text-violet-500" />
            <div>
              <p className="text-lg font-bold leading-none">{data.stats.total_agents}</p>
              <p className="text-[11px] text-muted-foreground">Agentes</p>
            </div>
          </Card>
          <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-sm">
            <Building2 className="h-4 w-4 text-blue-500" />
            <div>
              <p className="text-lg font-bold leading-none">{data.stats.total_departments}</p>
              <p className="text-[11px] text-muted-foreground">Departamentos</p>
            </div>
          </Card>
          <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-sm">
            <Activity className="h-4 w-4 text-emerald-500" />
            <div>
              <p className="text-lg font-bold leading-none text-emerald-600">
                {data.conductor?.live?.active_conversations ?? 0}
              </p>
              <p className="text-[11px] text-muted-foreground">Conversaciones activas</p>
            </div>
          </Card>
        </div>
      )}

      {/* Main Tree */}
      <Card className="overflow-auto rounded-2xl shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex flex-col gap-4 items-center py-12 px-6">
              <Skeleton className="h-16 w-16 rounded-2xl" />
              <Skeleton className="h-4 w-32" />
              <div className="flex gap-4 mt-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-56 w-48 rounded-2xl" />
                ))}
              </div>
            </div>
          ) : data ? (
            <div className="overflow-x-auto">
              <OrgConductorTree data={data} />
            </div>
          ) : (
            <div className="flex h-48 flex-col items-center justify-center gap-3 text-muted-foreground">
              <Bot className="h-10 w-10 opacity-30" />
              <p className="text-sm">No se pudo cargar el organigrama</p>
              <Button variant="outline" size="sm" onClick={() => fetchHierarchy()}>
                Reintentar
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info footer */}
      <p className="text-xs text-muted-foreground text-center">
        Los datos se actualizan en tiempo real. Haz clic en &quot;Actualizar&quot; para ver el estado más reciente.
      </p>
    </div>
  );
}
