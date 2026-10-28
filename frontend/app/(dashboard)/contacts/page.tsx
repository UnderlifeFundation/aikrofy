'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import dynamic from 'next/dynamic';
import { List, LayoutGrid, Search, UserPlus, FileSpreadsheet, TrendingUp, GitBranch, PieChart, Users, Flame, Star, DollarSign, RefreshCw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import ContactsTable from './contacts-table';
import ContactsKanban from './contacts-kanban';
import ContactDetailsDrawer from './contact-details-drawer';
import CreateContactModal from './create-contact-modal';
import BulkUploadDialog from '@/components/shared/bulk-upload-dialog';
import { useQueryClient } from '@tanstack/react-query';

const NeuralFunnelFlow = dynamic(
    () => import('@/components/features/funnel/NeuralFunnelFlow').then((m) => ({ default: m.NeuralFunnelFlow })),
    { ssr: false, loading: () => <Skeleton className="h-96 w-full rounded-2xl" /> }
);

const RadialAcquisitionWheel = dynamic(
    () => import('@/components/features/funnel/RadialAcquisitionWheel').then((m) => ({ default: m.RadialAcquisitionWheel })),
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

export default function ContactsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [viewMode, setViewMode] = useState<'table' | 'kanban' | 'funnel'>('kanban');
    const [search, setSearch] = useState('');
    const [selectedContactId, setSelectedContactId] = useState<number | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isBulkUploadOpen, setIsBulkUploadOpen] = useState(false);
    // Funnel Neural data
    const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
    const [loadingFunnel, setLoadingFunnel] = useState(false);
    const [refreshingFunnel, setRefreshingFunnel] = useState(false);
    const [funnelTab, setFunnelTab] = useState<'neural' | 'radial'>('neural');

    const fetchFunnel = async (silent = false) => {
        if (!silent) setLoadingFunnel(true);
        else setRefreshingFunnel(true);
        try {
            const res = await apiClient.get<FunnelData>('/funnel/live-flow');
            setFunnelData(res.data);
        } catch (err: any) {
            toast.error('Error al cargar el funnel: ' + (err.response?.data?.error || err.message));
        } finally {
            setLoadingFunnel(false);
            setRefreshingFunnel(false);
        }
    };

    useEffect(() => {
        if (viewMode === 'funnel' && !funnelData) {
            fetchFunnel();
        }
    }, [viewMode]);

    const handleContactClick = (id: number) => {
        setSelectedContactId(id);
    };

    const handleUpdate = () => {
        queryClient.invalidateQueries({ queryKey: ['contacts'] });
        queryClient.invalidateQueries({ queryKey: ['contacts-kanban'] });
        if (viewMode === 'funnel') fetchFunnel(true);
    };

    return (
        <div className="space-y-6 w-full max-w-[1920px] mx-auto pb-12">
            {/* Header section with view toggle & Add button */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">{t('contacts.title')}</h2>
                    <p className="text-sm text-muted-foreground mt-0.5 sm:mt-1">
                        {t('contacts.subtitle', { defaultValue: 'Manage, organize, and prioritize your customer pipeline in real-time.' })}
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto justify-start sm:justify-end">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setIsBulkUploadOpen(true)}
                        className="gap-1.5 h-9"
                    >
                        <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                        Importar CSV / Excel
                    </Button>

                    <Button
                        size="sm"
                        onClick={() => setIsCreateModalOpen(true)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 h-9"
                    >
                        <UserPlus className="h-4 w-4" />
                        {t('contacts.newContactBtn', { defaultValue: 'Nuevo Contacto' })}
                    </Button>

                    <Tabs
                        value={viewMode}
                        onValueChange={(val) => setViewMode(val as 'table' | 'kanban' | 'funnel')}
                        className="w-auto"
                    >
                        <TabsList className="grid grid-cols-3 w-[330px]">
                            <TabsTrigger value="kanban" className="gap-1.5 text-xs">
                                <LayoutGrid className="h-3.5 w-3.5" />
                                {t('contacts.viewKanban', { defaultValue: 'Kanban' })}
                            </TabsTrigger>
                            <TabsTrigger value="table" className="gap-1.5 text-xs">
                                <List className="h-3.5 w-3.5" />
                                {t('contacts.viewTable', { defaultValue: 'Tabla' })}
                            </TabsTrigger>
                            <TabsTrigger value="funnel" className="gap-1.5 text-xs">
                                <TrendingUp className="h-3.5 w-3.5 text-blue-500" />
                                Funnel Neural
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>
                </div>
            </div>

            {/* Global search and filter block (only for table and kanban views) */}
            {viewMode !== 'funnel' && (
                <div className="flex items-center gap-2 p-3 bg-muted/20 rounded-xl border">
                    <div className="relative flex-1 max-w-sm">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder={t('contacts.filterPlaceholder')}
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9 bg-background"
                        />
                    </div>
                </div>
            )}

            {/* Dynamic Rendering */}
            <div className="mt-4">
                {viewMode === 'table' ? (
                    <ContactsTable search={search} onContactClick={handleContactClick} />
                ) : viewMode === 'kanban' ? (
                    <ContactsKanban search={search} onContactClick={handleContactClick} />
                ) : (
                    <div className="space-y-6">
                        {/* Funnel header toolbar */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border">
                            <div>
                                <h3 className="text-base font-semibold flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-blue-500" />
                                    Visualización Neural de Pipeline & Adquisición
                                </h3>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    Flujo de partículas por etapa según temperatura del lead y rueda radial de fuentes de adquisición.
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchFunnel(true)}
                                disabled={refreshingFunnel}
                                className="self-start sm:self-center"
                            >
                                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshingFunnel ? 'animate-spin' : ''}`} />
                                Actualizar Funnel
                            </Button>
                        </div>

                        {/* KPI Cards */}
                        {loadingFunnel ? (
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                                {[1, 2, 3, 4].map((i) => (
                                    <Skeleton key={i} className="h-20 rounded-xl" />
                                ))}
                            </div>
                        ) : funnelData ? (
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                                <Card className="rounded-xl border shadow-xs">
                                    <CardContent className="flex items-center gap-3 p-4">
                                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-500">
                                            <Users className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-bold leading-none">{funnelData.kpis.total_contacts}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">Total contactos</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-xl border shadow-xs">
                                    <CardContent className="flex items-center gap-3 p-4">
                                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-500">
                                            <Flame className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-bold leading-none">{funnelData.kpis.hot_leads}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">Leads calientes</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-xl border shadow-xs">
                                    <CardContent className="flex items-center gap-3 p-4">
                                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500">
                                            <Star className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-bold leading-none">{funnelData.kpis.avg_score}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">Score promedio</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-xl border shadow-xs">
                                    <CardContent className="flex items-center gap-3 p-4">
                                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500">
                                            <DollarSign className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-bold leading-none">${funnelData.kpis.total_value_usd.toLocaleString()}</p>
                                            <p className="text-xs text-muted-foreground mt-0.5">Valor del pipeline</p>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        ) : null}

                        {/* Visualization Tabs */}
                        <Tabs value={funnelTab} onValueChange={(val) => setFunnelTab(val as 'neural' | 'radial')} className="flex-1">
                            <TabsList className="mb-4">
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
                                <Card className="rounded-2xl shadow-xs overflow-hidden">
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-sm font-semibold">Flujo de contactos por etapa</CardTitle>
                                        <p className="text-xs text-muted-foreground">
                                            Cada burbuja representa un contacto. Tamaño = lead score. Color = temperatura (🔴 caliente · 🟠 tibio · 🔵 frío).
                                        </p>
                                    </CardHeader>
                                    <CardContent className="p-2">
                                        {loadingFunnel ? (
                                            <Skeleton className="h-[500px] w-full rounded-xl" />
                                        ) : funnelData ? (
                                            <NeuralFunnelFlow
                                                stages={funnelData.stages}
                                                contacts={funnelData.contacts}
                                                width={900}
                                                height={500}
                                                onContactClick={(contactId) => setSelectedContactId(contactId)}
                                            />
                                        ) : (
                                            <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
                                                Sin datos de funnel disponibles
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            <TabsContent value="radial">
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <Card className="rounded-2xl shadow-xs">
                                        <CardHeader className="pb-2">
                                            <CardTitle className="text-sm font-semibold">Rueda de Adquisición</CardTitle>
                                            <p className="text-xs text-muted-foreground">
                                                Distribución de contactos por canal de origen.
                                            </p>
                                        </CardHeader>
                                        <CardContent>
                                            {loadingFunnel ? (
                                                <Skeleton className="h-80 w-80 mx-auto rounded-full" />
                                            ) : funnelData ? (
                                                <RadialAcquisitionWheel sources={funnelData.sources} width={440} height={440} />
                                            ) : null}
                                        </CardContent>
                                    </Card>

                                    {funnelData && (
                                        <Card className="rounded-2xl shadow-xs">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-sm font-semibold">Desglose por canal</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="flex flex-col gap-2">
                                                    {Object.entries(funnelData.sources)
                                                        .sort(([, a], [, b]) => b - a)
                                                        .map(([channel, count]) => {
                                                            const total = Object.values(funnelData.sources).reduce((a, b) => a + b, 0);
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
                    </div>
                )}
            </div>

            {/* In-page Slide-out Details Drawer */}
            <ContactDetailsDrawer
                contactId={selectedContactId}
                isOpen={selectedContactId !== null}
                onClose={() => setSelectedContactId(null)}
                onUpdate={handleUpdate}
            />

            {/* Create Contact Modal */}
            <CreateContactModal
                isOpen={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                onSuccess={handleUpdate}
            />

            {/* Bulk Upload Modal */}
            <BulkUploadDialog
                open={isBulkUploadOpen}
                onOpenChange={setIsBulkUploadOpen}
                defaultEntity="leads"
                invalidateKeys={['contacts', 'contacts-kanban']}
            />
        </div>
    );
}

