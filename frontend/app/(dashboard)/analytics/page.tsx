'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    BarChart3,
    MessageCircle,
    CalendarCheck,
    DollarSign,
    Activity,
    TrendingUp,
    Smile,
    Radio,
    SlidersHorizontal,
    X,
    RefreshCw,
    LayoutGrid,
    EyeOff,
    Database,
    Check,
    Undo,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api-client';
import {
    ConversationTimeline,
    SentimentPieChart,
    ChannelDistributionChart,
} from '@/components/analytics/analytics-charts';

import {
    ResponsiveContainer,
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
} from 'recharts';

// ── Types ──────────────────────────────────

interface SummaryStats {
    total_messages: number;
    total_conversations: number;
    total_customers: number;
    appointments: number;
    total_revenue: number;
    inbound_messages: number;
    outbound_messages: number;
    period_days: number;
    emails_sent?: number;
}

interface ConversationStats {
    daily: Array<{ date: string; count: number }>;
    by_channel: Array<{ channel: string; count: number }>;
    by_type: Array<{ type: string; count: number }>;
    resolution_rate: number;
    period_days: number;
}

interface SentimentStats {
    average_sentiment: number;
    distribution: {
        positive: number;
        neutral: number;
        negative: number;
    };
    period_days: number;
}

interface DashboardOverview {
    overview: {
        total_conversations: number;
        active_conversations: number;
        today_conversations: number;
        total_messages: number;
        today_messages: number;
    };
    channels: {
        total: number;
        connected: number;
        list: Array<{ type: string; status: string }>;
    };
    documents: { total: number; indexed: number };
    team: { employees: number };
    agents: {
        total: number;
        list: Array<{ id: number; name: string; status: string }>;
    };
}

interface WidgetLayout {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
}

interface WidgetConfig {
    id: number;
    title: string;
    chartType: 'card' | 'bar' | 'line' | 'pie' | 'funnel';
    layout: WidgetLayout;
    metric_key: string;
}

interface DashboardResponse {
    dashboard_id: number;
    name: string;
    widgets: WidgetConfig[];
}

interface WidgetDataItem {
    label: string;
    value: number;
}

interface WidgetDataResponse {
    widget_id: number;
    title: string;
    chart_type: string;
    metric_key: string;
    data: WidgetDataItem[];
}

// ── Main Page ──────────────────────────────

export default function AnalyticsPage() {
    const { t } = useTranslation();
    const [days, setDays] = useState('90');
    const [isCustomizing, setIsCustomizing] = useState(false);

    // ── Visibility State & Local Storage ──
    const [visibility, setVisibility] = useState<Record<string, boolean>>(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('aikrofy_analytics_visibility');
            if (saved) {
                try {
                    return JSON.parse(saved);
                } catch (e) {
                    console.error('Error loading visibility settings:', e);
                }
            }
        }
        return {};
    });

    const isVisible = (key: string) => {
        return visibility[key] !== false; // visible by default
    };

    const toggleVisibility = (key: string) => {
        const nextState = !isVisible(key);
        setVisibility((prev) => {
            const next = { ...prev, [key]: nextState };
            if (typeof window !== 'undefined') {
                localStorage.setItem('aikrofy_analytics_visibility', JSON.stringify(next));
            }
            return next;
        });
        toast.info(
            nextState 
                ? t('analytics.elementShown', 'Gráfico reactivado') 
                : t('analytics.elementHidden', 'Gráfico ocultado')
        );
    };

    const hideComponent = (key: string) => {
        setVisibility((prev) => {
            const next = { ...prev, [key]: false };
            if (typeof window !== 'undefined') {
                localStorage.setItem('aikrofy_analytics_visibility', JSON.stringify(next));
            }
            return next;
        });
        toast.success(t('analytics.dismissedAlert', 'Métrica ocultada. Puedes reactivarla en "Personalizar Informe".'));
    };

    const restoreAll = () => {
        setVisibility({});
        if (typeof window !== 'undefined') {
            localStorage.removeItem('aikrofy_analytics_visibility');
        }
        toast.success(t('analytics.allRestored', 'Se han reactivado todos los gráficos del informe.'));
    };

    // ── Queries for Standard Metrics ──
    const { data: summary, isLoading: loadingSummary, refetch: refetchSummary } = useQuery({
        queryKey: ['analytics-summary', days],
        queryFn: async () => {
            const { data } = await apiClient.get<SummaryStats>(`/analytics/summary?days=${days}`);
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    const { data: convStats, isLoading: loadingConv, refetch: refetchConv } = useQuery({
        queryKey: ['analytics-conversations', days],
        queryFn: async () => {
            const { data } = await apiClient.get<ConversationStats>(`/analytics/conversations?days=${days}`);
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    const { data: sentiment, isLoading: loadingSentiment, refetch: refetchSentiment } = useQuery({
        queryKey: ['analytics-sentiment', days],
        queryFn: async () => {
            const { data } = await apiClient.get<SentimentStats>(`/analytics/sentiment?days=${days}`);
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    const { data: dashboard, isLoading: loadingDash, refetch: refetchDash } = useQuery({
        queryKey: ['analytics-dashboard'],
        queryFn: async () => {
            const { data } = await apiClient.get<DashboardOverview>('/analytics/dashboard');
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    // ── Queries & State for Custom CRM Metrics ──
    const { data: customConfig, isLoading: loadingCustomConfig } = useQuery<DashboardResponse>({
        queryKey: ['custom-dashboard-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<DashboardResponse>('/analytics/custom-config');
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    const [customWidgetData, setCustomWidgetData] = useState<Record<string, WidgetDataItem[]>>({});
    const [loadingCustomWidgets, setLoadingCustomWidgets] = useState<Record<string, boolean>>({});

    const loadCustomWidgetData = async (widgetId: number, metricKey: string) => {
        setLoadingCustomWidgets((prev) => ({ ...prev, [metricKey]: true }));
        try {
            const { data } = await apiClient.post<WidgetDataResponse>('/analytics/widget-data', {
                widget_id: widgetId,
                days_back: parseInt(days, 10),
            });
            setCustomWidgetData((prev) => ({ ...prev, [metricKey]: data.data }));
        } catch (error) {
            console.error(`Error loading data for custom widget ${metricKey}:`, error);
        } finally {
            setLoadingCustomWidgets((prev) => ({ ...prev, [metricKey]: false }));
        }
    };

    useEffect(() => {
        if (customConfig?.widgets) {
            customConfig.widgets.forEach((widget) => {
                loadCustomWidgetData(widget.id, widget.metric_key);
            });
        }
    }, [customConfig, days]);

    const handleRefreshAll = () => {
        refetchSummary();
        refetchConv();
        refetchSentiment();
        refetchDash();
        if (customConfig?.widgets) {
            customConfig.widgets.forEach((widget) => {
                loadCustomWidgetData(widget.id, widget.metric_key);
            });
        }
        toast.success(t('analytics.refreshed', 'Datos actualizados correctamente.'));
    };

    // Calculate count of hidden items
    const allKeys = [
        'kpi-messages', 'kpi-conversations', 'kpi-appointments', 'kpi-revenue',
        'chart-timeline', 'chart-sentiment', 'chart-channels',
        'panel-channel_status', 'panel-period_summary', 'panel-conv_types'
    ];
    if (customConfig?.widgets) {
        customConfig.widgets.forEach(w => {
            allKeys.push(`widget-${w.metric_key}`);
        });
    }
    const hiddenCount = allKeys.filter(key => !isVisible(key)).length;

    // Helper to render customization toggle items
    const renderToggleItem = (key: string, label: string) => {
        const checked = isVisible(key);
        return (
            <label
                className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border cursor-pointer select-none transition-all duration-200 ${
                    checked
                        ? 'border-primary/30 bg-primary/5 text-foreground font-medium shadow-[0_2px_8px_rgba(var(--primary),0.02)]'
                        : 'border-border bg-transparent text-muted-foreground hover:bg-muted/40 hover:text-foreground'
                }`}
            >
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleVisibility(key)}
                    className="sr-only"
                />
                <div className={`h-4.5 w-4.5 rounded-lg border flex items-center justify-center transition-all ${
                    checked ? 'bg-primary border-primary text-primary-foreground' : 'border-input bg-background'
                }`}>
                    {checked && <Check className="h-3 w-3 stroke-[3.5]" />}
                </div>
                <span className="text-xs truncate">{label}</span>
            </label>
        );
    };

    const hasVisibleWidgets = customConfig?.widgets?.some(w => isVisible(`widget-${w.metric_key}`));

    return (
        <div className="space-y-8 pb-12">
            {/* ───── Header ───── */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h2 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight">
                        <BarChart3 className="h-7 w-7 text-primary animate-pulse" />
                        {t('analytics.title')}
                    </h2>
                    <p className="text-muted-foreground">
                        {t('analytics.description')}
                    </p>
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                        variant="outline"
                        size="icon"
                        onClick={handleRefreshAll}
                        title="Actualizar datos"
                        className="h-10 w-10 border-input shrink-0"
                    >
                        <RefreshCw className="h-4.5 w-4.5 text-muted-foreground hover:text-foreground transition-transform duration-500 active:rotate-180" />
                    </Button>

                    <Button
                        variant={isCustomizing ? "secondary" : "outline"}
                        onClick={() => setIsCustomizing(!isCustomizing)}
                        className={`gap-2 h-10 px-4 text-sm font-medium transition-all shrink-0 ${
                            isCustomizing ? 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/15' : ''
                        }`}
                    >
                        <SlidersHorizontal className="h-4 w-4" />
                        {t('analytics.personalize', 'Personalizar Informe')}
                    </Button>

                    <Select value={days} onValueChange={setDays}>
                        <SelectTrigger className="w-[180px] h-10">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7">{t('analytics.last7Days')}</SelectItem>
                            <SelectItem value="30">{t('analytics.last30Days')}</SelectItem>
                            <SelectItem value="90">{t('analytics.last90Days')}</SelectItem>
                            <SelectItem value="365">{t('analytics.last12Months')}</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* ───── Hidden Elements Notification Banner ───── */}
            {hiddenCount > 0 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-2xl border bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/20 gap-3 shadow-[0_2px_12px_rgba(245,158,11,0.05)] animate-fade-in">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-amber-500/20">
                            <EyeOff className="h-4.5 w-4.5 text-amber-600 dark:text-amber-400" />
                        </div>
                        <span className="text-sm font-medium">
                            {t('analytics.hiddenNotice', 'Tienes {{count}} elementos de análisis ocultos temporalmente.', { count: hiddenCount })}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 w-full sm:w-auto shrink-0 justify-end">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setIsCustomizing(true)}
                            className="h-8 text-xs font-semibold hover:bg-amber-500/20 text-amber-700 dark:text-amber-400"
                        >
                            {t('analytics.reactivate', 'Reactivar')}
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={restoreAll}
                            className="h-8 text-xs font-semibold border-amber-500/30 hover:bg-amber-500/25 bg-background/50 text-amber-700 dark:text-amber-300"
                        >
                            {t('analytics.showAll', 'Mostrar todo')}
                        </Button>
                    </div>
                </div>
            )}

            {/* ───── HubSpot-style Customization Panel ───── */}
            {isCustomizing && (
                <Card className="border border-primary/20 bg-card/65 backdrop-blur-md shadow-xl transition-all duration-300 overflow-hidden animate-slide-down">
                    <CardHeader className="bg-muted/30 p-5 border-b flex flex-row items-center justify-between space-y-0">
                        <div>
                            <CardTitle className="text-lg font-bold flex items-center gap-2">
                                <SlidersHorizontal className="h-5 w-5 text-primary" />
                                {t('analytics.personalizeTitle', 'Personalizar Informe de Analíticas')}
                            </CardTitle>
                            <CardDescription>
                                {t('analytics.personalizeDesc', 'Muestra u oculta elementos del informe para crear una vista a tu medida.')}
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={restoreAll} className="h-8 text-xs gap-1 border-muted-foreground/20">
                                <Undo className="h-3.5 w-3.5" />
                                {t('analytics.reset', 'Reestablecer')}
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => setIsCustomizing(false)} className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg">
                                <X className="h-4.5 w-4.5" />
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6 space-y-6">
                        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                            {/* Category 1: KPIs */}
                            <div className="space-y-3.5">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                                    <LayoutGrid className="h-3.5 w-3.5" />
                                    {t('analytics.catKpis', 'Resúmenes (KPIs)')}
                                </h4>
                                <div className="space-y-2">
                                    {renderToggleItem('kpi-messages', t('analytics.totalMessages', 'Total Mensajes'))}
                                    {renderToggleItem('kpi-conversations', t('analytics.conversations', 'Conversaciones'))}
                                    {renderToggleItem('kpi-appointments', t('analytics.appointments', 'Citas Agendadas'))}
                                    {renderToggleItem('kpi-revenue', t('analytics.revenue', 'Ingresos Totales'))}
                                </div>
                            </div>

                            {/* Category 2: Core Charts */}
                            <div className="space-y-3.5">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                                    <TrendingUp className="h-3.5 w-3.5" />
                                    {t('analytics.catCoreCharts', 'Gráficos Conversación')}
                                </h4>
                                <div className="space-y-2">
                                    {renderToggleItem('chart-timeline', t('analytics.convVolume', 'Volumen de Conversación'))}
                                    {renderToggleItem('chart-sentiment', t('analytics.sentimentAnalysis', 'Análisis de Sentimiento'))}
                                    {renderToggleItem('chart-channels', t('analytics.channelDistribution', 'Distribución de Canales'))}
                                </div>
                            </div>

                            {/* Category 3: CRM / DB */}
                            <div className="space-y-3.5">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                                    <Database className="h-3.5 w-3.5" />
                                    {t('analytics.catCrm', 'Métricas del CRM (Base de datos)')}
                                </h4>
                                <div className="space-y-2">
                                    {loadingCustomConfig ? (
                                        <div className="space-y-2">
                                            <Skeleton className="h-8.5 w-full rounded-xl" />
                                            <Skeleton className="h-8.5 w-full rounded-xl" />
                                        </div>
                                    ) : customConfig?.widgets?.length ? (
                                        customConfig.widgets.map((widget) => (
                                            <div key={widget.id}>
                                                {renderToggleItem(`widget-${widget.metric_key}`, widget.title)}
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-xs text-muted-foreground italic">{t('analytics.noCustomWidgets', 'Sin métricas personalizadas')}</p>
                                    )}
                                </div>
                            </div>

                            {/* Category 4: Bottom Rows */}
                            <div className="space-y-3.5">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                                    <Activity className="h-3.5 w-3.5" />
                                    {t('analytics.catPanels', 'Paneles de Detalle')}
                                </h4>
                                <div className="space-y-2">
                                    {renderToggleItem('panel-channel_status', t('analytics.channelStatus', 'Estado de Canales'))}
                                    {renderToggleItem('panel-period_summary', t('analytics.periodSummary', 'Resumen del Período'))}
                                    {renderToggleItem('panel-conv_types', t('analytics.convTypes', 'Tipos de Conversación'))}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* ───── KPI Cards Row ───── */}
            {(isVisible('kpi-messages') || isVisible('kpi-conversations') || isVisible('kpi-appointments') || isVisible('kpi-revenue')) && (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {isVisible('kpi-messages') && (
                        <MetricCard
                            title={t('analytics.totalMessages')}
                            value={summary?.total_messages}
                            subtitle={t('analytics.inboundOutbound', { inbound: summary?.inbound_messages || 0, outbound: summary?.outbound_messages || 0 })}
                            icon={<MessageCircle className="h-5 w-5" />}
                            loading={loadingSummary}
                            color="text-purple-600"
                            bgColor="bg-purple-100 dark:bg-purple-900/30"
                            onHide={() => hideComponent('kpi-messages')}
                        />
                    )}
                    {isVisible('kpi-conversations') && (
                        <MetricCard
                            title={t('analytics.conversations')}
                            value={summary?.total_conversations}
                            subtitle={t('analytics.activeNow', { count: dashboard?.overview?.active_conversations || 0 })}
                            icon={<Activity className="h-5 w-5" />}
                            loading={loadingSummary}
                            color="text-blue-600"
                            bgColor="bg-blue-100 dark:bg-blue-900/30"
                            onHide={() => hideComponent('kpi-conversations')}
                        />
                    )}
                    {isVisible('kpi-appointments') && (
                        <MetricCard
                            title={t('analytics.appointments')}
                            value={summary?.appointments}
                            subtitle={t('analytics.inLastDays', { days })}
                            icon={<CalendarCheck className="h-5 w-5" />}
                            loading={loadingSummary}
                            color="text-green-600"
                            bgColor="bg-green-100 dark:bg-green-900/30"
                            onHide={() => hideComponent('kpi-appointments')}
                        />
                    )}
                    {isVisible('kpi-revenue') && (
                        <MetricCard
                            title={t('analytics.revenue')}
                            value={summary?.total_revenue}
                            isCurrency
                            subtitle={t('analytics.inLastDays', { days })}
                            icon={<DollarSign className="h-5 w-5" />}
                            loading={loadingSummary}
                            color="text-teal-600"
                            bgColor="bg-teal-100 dark:bg-teal-900/30"
                            onHide={() => hideComponent('kpi-revenue')}
                        />
                    )}
                </div>
            )}

            {/* ───── Chart Row 1: Timeline (full width) ───── */}
            {isVisible('chart-timeline') && (
                <Card className="relative group overflow-hidden">
                    <button
                        onClick={() => hideComponent('chart-timeline')}
                        className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                        title="Ocultar gráfico"
                    >
                        <X className="h-4 w-4" />
                    </button>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-primary" />
                            {t('analytics.convVolume')}
                        </CardTitle>
                        <CardDescription>
                            {t('analytics.convVolumeDesc', { days })}
                            {convStats?.resolution_rate !== undefined && (
                                <span className="ml-3">
                                    · {t('analytics.resolutionRate')}:{' '}
                                    <span className="font-semibold text-foreground">
                                        {convStats.resolution_rate}%
                                    </span>
                                </span>
                            )}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ConversationTimeline data={convStats?.daily || []} loading={loadingConv} />
                    </CardContent>
                </Card>
            )}

            {/* ───── Chart Row 2: Sentiment + Channel Distribution ───── */}
            {(isVisible('chart-sentiment') || isVisible('chart-channels')) && (
                <div className="grid gap-6 lg:grid-cols-2">
                    {/* Sentiment Pie */}
                    {isVisible('chart-sentiment') && (
                        <Card className="relative group overflow-hidden">
                            <button
                                onClick={() => hideComponent('chart-sentiment')}
                                className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                title="Ocultar gráfico"
                            >
                                <X className="h-4 w-4" />
                            </button>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Smile className="h-5 w-5 text-primary" />
                                    {t('analytics.sentimentAnalysis')}
                                </CardTitle>
                                <CardDescription>
                                    {t('analytics.sentimentDesc')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <SentimentPieChart
                                    data={sentiment?.distribution || { positive: 0, neutral: 0, negative: 0 }}
                                    avgScore={sentiment?.average_sentiment || 0}
                                    loading={loadingSentiment}
                                />
                            </CardContent>
                        </Card>
                    )}

                    {/* Channel Distribution */}
                    {isVisible('chart-channels') && (
                        <Card className="relative group overflow-hidden">
                            <button
                                onClick={() => hideComponent('chart-channels')}
                                className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                title="Ocultar gráfico"
                            >
                                <X className="h-4 w-4" />
                            </button>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Radio className="h-5 w-5 text-primary" />
                                    {t('analytics.channelDistribution')}
                                </CardTitle>
                                <CardDescription>
                                    {t('analytics.channelDistributionDesc')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ChannelDistributionChart
                                    data={convStats?.by_channel || []}
                                    loading={loadingConv}
                                />
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}

            {/* ───── Chart Row 3: Custom CRM Metrics ───── */}
            {hasVisibleWidgets && (
                <div className="space-y-4 pt-4 border-t border-muted/50">
                    <div className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        <h3 className="text-xl font-bold tracking-tight">
                            {t('analytics.crmSectionTitle', 'Métricas de Negocio y Conversión CRM')}
                        </h3>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {customConfig?.widgets?.map((widget) => {
                            const key = `widget-${widget.metric_key}`;
                            if (!isVisible(key)) return null;

                            const data = customWidgetData[widget.metric_key] || [];
                            const isLoading = loadingCustomWidgets[widget.metric_key];

                            return (
                                <Card key={widget.id} className="relative group overflow-hidden flex flex-col justify-between">
                                    <button
                                        onClick={() => hideComponent(key)}
                                        className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                        title="Ocultar gráfico"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-sm font-semibold tracking-tight text-foreground pr-6 truncate">
                                            {widget.title === 'Calificación de Prospectos (Leads por Nivel de Score)'
                                                ? t('analytics.leadsByScoreTitle', 'Calificación de Prospectos (Leads por Nivel de Score)')
                                                : widget.title === 'Distribución de Contactos por Canal de Origen Conversacional'
                                                ? t('analytics.contactsByChannelTitle', 'Distribución de Contactos por Canal de Origen Conversacional')
                                                : widget.title === 'Conversiones del Embudo (Proporción de Leads por Etapa de Kanban)'
                                                ? t('analytics.funnelConversionsTitle', 'Conversiones del Embudo (Proporción de Leads por Etapa de Kanban)')
                                                : t(widget.title, widget.title)}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="h-[260px] flex flex-col justify-end pt-2">
                                        {widget.metric_key === 'leads_by_score_range' && (
                                            <LeadsByScoreChart data={data} loading={isLoading} />
                                        )}
                                        {widget.metric_key === 'contacts_by_channel' && (
                                            <ContactsByChannelChart data={data} loading={isLoading} />
                                        )}
                                        {widget.metric_key === 'funnel_conversions' && (
                                            <FunnelConversionsChart data={data} loading={isLoading} />
                                        )}
                                        {widget.metric_key !== 'leads_by_score_range' &&
                                            widget.metric_key !== 'contacts_by_channel' &&
                                            widget.metric_key !== 'funnel_conversions' && (
                                                <GenericChart chartType={widget.chartType} data={data} loading={isLoading} />
                                            )}
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* ───── Bottom Row: Quick Stats ───── */}
            {(isVisible('panel-channel_status') || isVisible('panel-period_summary') || isVisible('panel-conv_types')) && (
                <div className="grid gap-6 lg:grid-cols-3 border-t border-muted/50 pt-6">
                    {/* Channel Activity */}
                    {isVisible('panel-channel_status') && (
                        <Card className="relative group overflow-hidden">
                            <button
                                onClick={() => hideComponent('panel-channel_status')}
                                className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                title="Ocultar panel"
                            >
                                <X className="h-4 w-4" />
                            </button>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg">{t('analytics.channelStatus')}</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {loadingDash ? (
                                    <Skeleton className="h-24 w-full rounded-xl" />
                                ) : (
                                    <div className="space-y-4">
                                        {dashboard?.channels?.list?.length ? (
                                            dashboard.channels.list.map((ch) => (
                                                <div key={ch.type || Math.random()} className="flex items-center justify-between">
                                                    <span className="text-sm capitalize">{(ch.type || 'unknown').replace('_', ' ')}</span>
                                                    <Badge
                                                        variant={ch.status === 'connected' ? 'default' : 'secondary'}
                                                        className={
                                                            ch.status === 'connected'
                                                                ? 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20'
                                                                : ''
                                                        }
                                                    >
                                                        {ch.status === 'connected' ? t('channels.connected') : t('channels.disconnected')}
                                                    </Badge>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="text-sm text-muted-foreground text-center py-4">
                                                {t('analytics.noChannels')}
                                            </p>
                                        )}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* Period Summary */}
                    {isVisible('panel-period_summary') && (
                        <Card className="relative group overflow-hidden">
                            <button
                                onClick={() => hideComponent('panel-period_summary')}
                                className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                title="Ocultar panel"
                            >
                                <X className="h-4 w-4" />
                            </button>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg">{t('analytics.periodSummary')}</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">{t('analytics.emailsSent')}</span>
                                    <span className="font-medium">{summary?.emails_sent || 0}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">{t('analytics.customers')}</span>
                                    <span className="font-medium">{summary?.total_customers || 0}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">{t('analytics.teamMembers')}</span>
                                    <span className="font-medium">{dashboard?.team?.employees || 0}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">{t('analytics.activeAgents')}</span>
                                    <span className="font-medium">{dashboard?.agents?.total || 0}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">{t('analytics.ragDocuments')}</span>
                                    <span className="font-medium">{dashboard?.documents?.indexed || 0}</span>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Conversation Breakdown */}
                    {isVisible('panel-conv_types') && (
                        <Card className="relative group overflow-hidden">
                            <button
                                onClick={() => hideComponent('panel-conv_types')}
                                className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                title="Ocultar panel"
                            >
                                <X className="h-4 w-4" />
                            </button>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-lg">{t('analytics.convTypes')}</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {loadingConv ? (
                                    <Skeleton className="h-24 w-full rounded-xl" />
                                ) : convStats?.by_type?.length ? (
                                    <div className="space-y-3">
                                        {convStats.by_type.map((t_item) => {
                                            const total = convStats.by_type.reduce((a, b) => a + b.count, 0);
                                            const pct = total > 0 ? ((t_item.count / total) * 100).toFixed(0) : '0';
                                            return (
                                                <div key={t_item.type} className="space-y-1">
                                                    <div className="flex justify-between text-sm">
                                                        <span className="capitalize text-muted-foreground">
                                                            {t_item.type.replace('_', ' ')}
                                                        </span>
                                                        <span className="font-medium">{t_item.count} ({pct}%)</span>
                                                    </div>
                                                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                                                        <div
                                                            className="h-full rounded-full bg-primary/70 transition-all duration-700"
                                                            style={{ width: `${pct}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted-foreground text-center py-4">
                                        {t('analytics.noData')}
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Metric Card Component ──────────────────

function MetricCard({
    title,
    value,
    subtitle,
    icon,
    loading,
    color,
    bgColor,
    isCurrency = false,
    onHide,
}: {
    title: string;
    value?: number;
    subtitle: string;
    icon: React.ReactNode;
    loading: boolean;
    color: string;
    bgColor: string;
    isCurrency?: boolean;
    onHide?: () => void;
}) {
    return (
        <Card className="overflow-hidden relative group">
            {onHide && (
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onHide();
                    }}
                    className="absolute top-2.5 right-2.5 p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                    title="Ocultar métrica"
                >
                    <X className="h-3.5 w-3.5" />
                </button>
            )}
            <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-muted-foreground pr-4 truncate">{title}</span>
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${bgColor} ${color}`}>
                        {icon}
                    </div>
                </div>
                {loading ? (
                    <Skeleton className="h-9 w-24 rounded-lg" />
                ) : (
                    <div className="text-3xl font-bold tracking-tight">
                        {isCurrency ? `$${(value || 0).toLocaleString('en-US')}` : (value || 0).toLocaleString()}
                    </div>
                )}
                <p className="text-xs text-muted-foreground mt-1 truncate">{subtitle}</p>
            </CardContent>
        </Card>
    );
}

// ── CRM Metric Helper Chart Components ──────────────────

function LeadsByScoreChart({ data, loading }: { data: WidgetDataItem[]; loading: boolean }) {
    if (loading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Skeleton className="h-[200px] w-full rounded-xl" />
            </div>
        );
    }
    if (!data || data.length === 0) {
        return (
            <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                Sin datos en este período.
            </div>
        );
    }

    // Order data for clean display: Caliente, Templado, Frío
    const orderedData = [...data].sort((a, b) => {
        const getPriority = (label: string) => {
            if (label.includes('Caliente')) return 1;
            if (label.includes('Templado')) return 2;
            if (label.includes('Frío')) return 3;
            return 4;
        };
        return getPriority(a.label) - getPriority(b.label);
    });

    const colors: Record<string, string> = {
        'Caliente': '#ef4444', // red
        'Templado': '#f59e0b', // amber
        'Frío': '#3b82f6', // blue
    };

    const { t } = useTranslation();

    const formattedData = orderedData.map((item) => {
        let fill = '#6366f1';
        for (const [key, color] of Object.entries(colors)) {
            if (item.label.includes(key)) {
                fill = color;
                break;
            }
        }
        let translatedLabel = item.label;
        if (item.label.includes('Caliente')) {
            translatedLabel = t('analytics.leadScoreHot', 'Caliente (80-100)');
        } else if (item.label.includes('Templado')) {
            translatedLabel = t('analytics.leadScoreWarm', 'Templado (50-79)');
        } else if (item.label.includes('Frío')) {
            translatedLabel = t('analytics.leadScoreCold', 'Frío (0-49)');
        }
        return { ...item, label: translatedLabel, fill };
    });

    return (
        <ResponsiveContainer width="100%" height={220}>
            <BarChart data={formattedData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                    contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 600 }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {formattedData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}

function ContactsByChannelChart({ data, loading }: { data: WidgetDataItem[]; loading: boolean }) {
    const { t } = useTranslation();
    if (loading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Skeleton className="h-[200px] w-full rounded-xl" />
            </div>
        );
    }
    if (!data || data.length === 0) {
        return (
            <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                {t('analytics.noData', 'Sin datos en este período.')}
            </div>
        );
    }

    const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#3b82f6'];
    const total = data.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="relative w-full h-full flex flex-col justify-between">
            <div className="relative h-[160px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={45}
                            outerRadius={65}
                            paddingAngle={3}
                            dataKey="value"
                            nameKey="label"
                        >
                            {data.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                fontSize: '11px',
                            }}
                            formatter={(val: any) => [`${val} contactos (${total > 0 ? ((Number(val) / total) * 100).toFixed(0) : 0}%)`]}
                        />
                    </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-xl font-bold text-foreground">{total}</span>
                    <span className="text-[9px] text-muted-foreground uppercase tracking-wider">Total</span>
                </div>
            </div>
            {/* Scrollable Flowing Legend */}
            <div className="flex flex-wrap gap-2 justify-center max-h-[50px] overflow-y-auto px-1 pt-1 pb-2">
                {data.map((item, idx) => (
                    <div key={item.label} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                        <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                        <span className="truncate max-w-[80px]">{item.label}</span>
                        <span className="font-semibold text-foreground">{item.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function FunnelConversionsChart({ data, loading }: { data: WidgetDataItem[]; loading: boolean }) {
    const { t } = useTranslation();
    if (loading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Skeleton className="h-[200px] w-full rounded-xl" />
            </div>
        );
    }
    if (!data || data.length === 0) {
        return (
            <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                {t('analytics.noData', 'Sin datos en este período.')}
            </div>
        );
    }

    const getStageTranslation = (label: string) => {
        switch (label.toLowerCase()) {
            case 'lead': return t('kanban.stage.lead', 'Lead');
            case 'contactado': return t('kanban.stage.contacted', 'Contactado');
            case 'calificado': return t('kanban.stage.qualified', 'Calificado');
            case 'propuesta': return t('kanban.stage.proposal', 'Propuesta');
            case 'negociación':
            case 'negociacion': return t('kanban.stage.negotiation', 'Negociación');
            case 'ganado': return t('kanban.stage.won', 'Ganado');
            case 'perdido': return t('kanban.stage.lost', 'Perdido');
            default: return t(`kanban.stage.${label.toLowerCase()}`, label);
        }
    };

    const translatedData = data.map(item => ({
        ...item,
        label: getStageTranslation(item.label)
    }));

    return (
        <ResponsiveContainer width="100%" height={220}>
            <BarChart data={translatedData} layout="vertical" margin={{ top: 10, right: 15, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 9 }} className="fill-muted-foreground" tickLine={false} axisLine={false} allowDecimals={false} />
                <YAxis type="category" dataKey="label" tick={{ fontSize: 9 }} width={70} className="fill-muted-foreground" tickLine={false} axisLine={false} />
                <Tooltip
                    contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 600 }}
                />
                <Bar dataKey="value" fill="hsl(250, 90%, 65%)" radius={[0, 6, 6, 0]} />
            </BarChart>
        </ResponsiveContainer>
    );
}

function GenericChart({ chartType, data, loading }: { chartType: string; data: WidgetDataItem[]; loading: boolean }) {
    if (loading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Skeleton className="h-[200px] w-full rounded-xl" />
            </div>
        );
    }
    if (!data || data.length === 0) {
        return (
            <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                Sin datos en este período.
            </div>
        );
    }
    const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

    if (chartType === 'card') {
        return (
            <div className="flex flex-col justify-center h-full text-center">
                <span className="text-4xl font-extrabold text-primary tracking-tight">
                    {data[0]?.value || 0}
                </span>
                <span className="text-xs text-muted-foreground mt-1">
                    {data[0]?.label || 'Total'}
                </span>
            </div>
        );
    }

    if (chartType === 'pie') {
        return (
            <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                    <Pie data={data} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={65}>
                        {data.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }} />
                </PieChart>
            </ResponsiveContainer>
        );
    }

    if (chartType === 'line') {
        return (
            <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" vertical={false} />
                    <XAxis dataKey="label" fontSize={9} stroke="#888888" tickLine={false} axisLine={false} />
                    <YAxis fontSize={9} stroke="#888888" tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }} />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
            </ResponsiveContainer>
        );
    }

    // Default: bar
    return (
        <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" vertical={false} />
                <XAxis dataKey="label" fontSize={9} stroke="#888888" tickLine={false} axisLine={false} />
                <YAxis fontSize={9} stroke="#888888" tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }} />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
        </ResponsiveContainer>
    );
}
