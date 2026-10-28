'use client';

import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// Dynamically import AdminGeoMap with SSR disabled for Leaflet client-only DOM binding
const AdminGeoMap = dynamic(() => import('@/components/admin/AdminGeoMap'), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] w-full rounded-2xl border border-border/60 bg-muted/20 flex flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      <div className="text-sm font-medium text-muted-foreground">
        Cargando Mapa de Telemetría OpenStreetMap...
      </div>
    </div>
  )
});

export default function SuperAdminGeoAnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['super-admin-geo-analytics'],
    queryFn: async () => {
      const response = await apiClient.get('/admin/geo-analytics');
      return response.data;
    },
    refetchInterval: 20000, // Refresh every 20s for live telemetry
    staleTime: 10000
  });

  if (error) {
    return (
      <div className="p-6">
        <Card className="border-red-500/30 bg-red-500/5">
          <CardContent className="p-6 flex flex-col items-center justify-center text-center gap-3">
            <AlertCircle className="h-10 w-10 text-red-500" />
            <div className="text-base font-bold text-red-600 dark:text-red-400">
              Error al cargar la telemetría geoespacial
            </div>
            <div className="text-xs text-muted-foreground max-w-md">
              No se pudo conectar con el endpoint de super admin o no posees los permisos necesarios.
            </div>
            <Button size="sm" onClick={() => refetch()} variant="outline" className="mt-2">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <AdminGeoMap
        data={data || null}
        isLoading={isLoading}
        onRefresh={() => refetch()}
      />
    </div>
  );
}
