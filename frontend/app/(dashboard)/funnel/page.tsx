'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslation } from 'react-i18next';
import apiClient from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  RefreshCw,
  TrendingUp,
  Users,
  Flame,
  DollarSign,
  Star,
  GitBranch,
  PieChart,
} from 'lucide-react';
import { toast } from 'sonner';
import ContactDetailsDrawer from '../contacts/contact-details-drawer';
import { useQueryClient } from '@tanstack/react-query';

// Lazy-load D3 components (no SSR)
const NeuralFunnelFlow = dynamic(
  () =>
    import('@/components/features/funnel/NeuralFunnelFlow').then((m) => ({
      default: m.NeuralFunnelFlow,
    })),
  { ssr: false, loading: () => <Skeleton className="h-96 w-full rounded-2xl" /> }
);

const RadialAcquisitionWheel = dynamic(
  () =>
    import('@/components/features/funnel/RadialAcquisitionWheel').then((m) => ({
      default: m.RadialAcquisitionWheel,
    })),
  { ssr: false, loading: () => <Skeleton className="h-96 w-full rounded-2xl" /> }
);

interface KPI {
  total_contacts: number;
  hot_leads: number;
  avg_score: number;
  total_value_usd: number;
}

interface FunnelData {
  stages: any[];
  contacts: any[];
  sources: Record<string, number>;
  kpis: KPI;
}

function KpiCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <Card className="rounded-xl border shadow-sm">
      <CardContent className="flex items-center gap-3 p-4">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-lg font-bold leading-none">{value}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function FunnelPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [data, setData] = useState<FunnelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null);

  const fetchFunnel = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await apiClient.get<FunnelData>('/funnel/live-flow');
      setData(res.data);
    } catch (err: any) {
      toast.error('Error al cargar el funnel: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchFunnel();
  }, []);

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 lg:p-8 min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 shadow-lg shadow-blue-500/20">
              <TrendingUp className="h-4.5 w-4.5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">Funnel Neural</h1>
            <Badge variant="outline" className="hidden sm:flex">Pipeline IA</Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-lg">
            Visualización interactiva del pipeline de ventas: flujo neuronal de contactos por etapa y rueda radial de adquisición.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchFunnel(true)}
          disabled={refreshing}
          className="self-start sm:self-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* KPI Row */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : data ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiCard
            icon={Users}
            label="Total contactos"
            value={data.kpis.total_contacts}
            color="bg-blue-500"
          />
          <KpiCard
            icon={Flame}
            label="Leads calientes"
            value={data.kpis.hot_leads}
            color="bg-red-500"
          />
          <KpiCard
            icon={Star}
            label="Score promedio"
            value={data.kpis.avg_score}
            color="bg-amber-500"
          />
          <KpiCard
            icon={DollarSign}
            label="Valor del pipeline"
            value={`$${data.kpis.total_value_usd.toLocaleString()}`}
            color="bg-emerald-500"
          />
        </div>
      ) : null}

      {/* Visualization Tabs */}
      <Tabs defaultValue="neural" className="flex-1">
        <TabsList className="mb-4 w-full sm:w-auto">
          <TabsTrigger value="neural" className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            Flujo Neural
          </TabsTrigger>
          <TabsTrigger value="radial" className="flex items-center gap-1.5">
            <PieChart className="h-3.5 w-3.5" />
            Rueda de Adquisición
          </TabsTrigger>
        </TabsList>

        <TabsContent value="neural">
          <Card className="rounded-2xl shadow-sm overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Flujo de contactos por etapa</CardTitle>
              <p className="text-xs text-muted-foreground">
                Cada burbuja es un contacto. Tamaño = lead score. Color = temperatura (🔴 caliente · 🟠 tibio · 🔵 frío).
                Pasa el cursor para ver detalles.
              </p>
            </CardHeader>
            <CardContent className="p-2">
              {loading ? (
                <Skeleton className="h-[500px] w-full rounded-xl" />
              ) : data ? (
                <NeuralFunnelFlow
                  stages={data.stages}
                  contacts={data.contacts}
                  width={880}
                  height={500}
                  onContactClick={(contactId) => setSelectedContactId(contactId)}
                />
              ) : (
                <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
                  Sin datos disponibles
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="radial">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="rounded-2xl shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Rueda de Adquisición</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Distribución de contactos por canal de origen. Pasa el cursor para ver el porcentaje.
                </p>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-80 w-80 mx-auto rounded-full" />
                ) : data ? (
                  <RadialAcquisitionWheel sources={data.sources} width={440} height={440} />
                ) : null}
              </CardContent>
            </Card>

            {/* Source breakdown table */}
            {data && (
              <Card className="rounded-2xl shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">Desglose por canal</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col gap-2">
                    {Object.entries(data.sources)
                      .sort(([, a], [, b]) => b - a)
                      .map(([channel, count]) => {
                        const total = Object.values(data.sources).reduce((a, b) => a + b, 0);
                        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0';
                        return (
                          <div key={channel} className="flex items-center gap-3">
                            <span className="min-w-[90px] text-sm font-medium capitalize">
                              {channel}
                            </span>
                            <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                              <div
                                className="h-2 rounded-full bg-primary"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground w-12 text-right">
                              {count} ({pct}%)
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Contact Details Drawer */}
      <ContactDetailsDrawer
        contactId={selectedContactId}
        onClose={() => setSelectedContactId(null)}
        onUpdated={() => {
          fetchFunnel(true);
          queryClient.invalidateQueries({ queryKey: ['contacts'] });
        }}
      />
    </div>
  );
}
