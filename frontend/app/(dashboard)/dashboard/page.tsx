'use client';

import { useQuery } from '@tanstack/react-query';
import { OnboardingDashboardBanner } from '@/components/shared/onboarding-dashboard-banner';
import {
    MessageCircle,
    Plug,
    FileText,
    CalendarCheck,
    DollarSign,
    Users,
    Activity,
    CreditCard,
    Bot,
    Phone,
    Calendar,
    Database,
    Send,
    ShoppingCart,
    Server,
    Sparkles,
    Shield,
    Cpu,
} from 'lucide-react';
import { useState } from 'react';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';

import { useTranslation } from 'react-i18next';

// --- Types mapping to Python backend ---
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
        list: any[];
    };
    documents: {
        total: number;
        indexed: number;
    };
    team: {
        employees: number;
    };
    agents: {
        total: number;
        list: Array<{ id: number; name: string; status: string }>;
    };
    integrations: {
        google_calendar?: { connected: boolean; calendar_id: string | null };
        google_sheets?: { connected: boolean; sheet_id: string | null };
        crm?: { connected: boolean; platform: string | null };
        ecommerce?: { connected: boolean; platform: string | null };
        erp?: { connected: boolean; platform: string | null };
        payments?: { connected: boolean; platform: string | null };
    };
}

interface SummaryStats {
    appointments: number;
    total_revenue: number;
    period_days: number;
}

interface FunnelData {
    funnel: Array<{ stage: string; count: number }>;
}

export default function DashboardPage() {
    const { t } = useTranslation();
    const [period, setPeriod] = useState(90); // Default to 90 days to show existing January data

    // 1. Fetch main dashboard data
    const { data: dashboard, isLoading: loadingDash } = useQuery({
        queryKey: ['analytics-dashboard'],
        queryFn: async () => {
            const { data } = await apiClient.get<DashboardOverview>('/analytics/dashboard');
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    // 2. Fetch summary stats (appointments, revenue)
    const { data: summary, isLoading: loadingSummary } = useQuery({
        queryKey: ['analytics-summary', period],
        queryFn: async () => {
            const { data } = await apiClient.get<SummaryStats>(`/analytics/summary?days=${period}`);
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    // 3. Fetch funnel
    const { data: funnelData, isLoading: loadingFunnel } = useQuery({
        queryKey: ['analytics-funnel', period],
        queryFn: async () => {
            const { data } = await apiClient.get<FunnelData>(`/analytics/funnel?days=${period}`);
            return data;
        },
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    const { data: observatoryData } = useQuery({
        queryKey: ['dashboard-observatory-summary'],
        queryFn: async () => {
            try {
                const { data } = await apiClient.get('/observatory/metrics');
                return data;
            } catch {
                return null;
            }
        },
        staleTime: 30 * 1000,
        refetchInterval: 10000,
    });

    const periodLabel = period === 7 ? t('analytics.last7Days') : period === 30 ? t('analytics.last30Days') : period === 90 ? t('analytics.last90Days') : t('analytics.last12Months');


    return (
        <div className="space-y-8">
            <OnboardingDashboardBanner />
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">{t('dashboard.title')}</h2>
                <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
                    <Tabs value={period.toString()} onValueChange={(v) => setPeriod(parseInt(v))}>
                        <TabsList className="bg-muted/50">
                            <TabsTrigger value="7">7D</TabsTrigger>
                            <TabsTrigger value="30">30D</TabsTrigger>
                            <TabsTrigger value="90">90D</TabsTrigger>
                            <TabsTrigger value="365">1Y</TabsTrigger>
                        </TabsList>
                    </Tabs>
                    <Link href="/analytics" className="hidden sm:inline-flex">
                        <Button variant="outline">{t('analytics.title')}</Button>
                    </Link>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.totalConversations')}</CardTitle>
                        <MessageCircle className="h-4 w-4 text-purple-600" />
                    </CardHeader>
                    <CardContent>
                        {loadingDash ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{dashboard?.overview?.total_conversations || 0}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">{t('dashboard.allTimeInteractions')}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.connectedChannels')}</CardTitle>
                        <Plug className="h-4 w-4 text-orange-600" />
                    </CardHeader>
                    <CardContent>
                        {loadingDash ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{dashboard?.channels?.connected || 0}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">{t('dashboard.activeCommunicationLayers')}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.indexedDocuments')}</CardTitle>
                        <FileText className="h-4 w-4 text-blue-600" />
                    </CardHeader>
                    <CardContent>
                        {loadingDash ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{dashboard?.documents?.indexed || 0}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">{t('dashboard.vectorsInPinecone')}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.appointments')}</CardTitle>
                        <CalendarCheck className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        {loadingSummary ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{summary?.appointments || 0}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">{t('dashboard.lastPeriod', { period: periodLabel })}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('dashboard.revenue')}</CardTitle>
                        <DollarSign className="h-4 w-4 text-teal-600" />
                    </CardHeader>
                    <CardContent>
                        {loadingSummary ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">${summary?.total_revenue?.toLocaleString('en-US') || 0}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">{t('dashboard.lastPeriod', { period: periodLabel })}</p>
                    </CardContent>
                </Card>

                {/* 🛡️ Card 6: Sentinel LEM-Ops Invariant State */}
                <Card className="border-indigo-500/30 bg-gradient-to-br from-card via-indigo-950/10 to-card">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-indigo-400">Blindaje LEM-Ops</CardTitle>
                        <Shield className="h-4 w-4 text-emerald-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-2">
                            <span className="text-2xl font-bold text-white tracking-tight">
                                {observatoryData?.is_protected ? 'Activo' : 'Vulnerable'}
                            </span>
                            <span className={`h-2 w-2 rounded-full ${observatoryData?.is_protected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                        </div>
                        <div className="flex items-center justify-between mt-1 text-xs">
                            <span className="text-neutral-400 font-mono">E={observatoryData?.metrics_24h?.average_energy ?? '0.042'}</span>
                            <Link href="/observatory" className="text-indigo-400 hover:underline font-semibold">
                                Ver &rarr;
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Sales Funnel - Large (Spans 2 columns) */}
                <Card className="col-span-2 min-h-[400px]">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>{t('dashboard.salesFunnel')} ({periodLabel})</CardTitle>
                                <CardDescription>{t('dashboard.salesFunnelDesc')}</CardDescription>
                            </div>
                            <Link href="/analytics">
                                <Button variant="ghost" size="sm">{t('dashboard.seeDetails')}</Button>
                            </Link>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {loadingFunnel ? (
                            <div className="space-y-4">
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-5/6" />
                                <Skeleton className="h-10 w-4/6" />
                                <Skeleton className="h-10 w-3/6" />
                            </div>
                        ) : !funnelData?.funnel || funnelData.funnel.length === 0 ? (
                            <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                                {t('dashboard.noFunnelData')}
                            </div>
                        ) : (
                            <div className="flex flex-col gap-3 py-4">
                                {funnelData.funnel.map((item, index) => {
                                    const maxCount = Math.max(...funnelData.funnel.map(f => f.count), 1);
                                    const percentage = (item.count / maxCount) * 100;
                                    // Funnel colors mimicking ChartJS colors from jinja
                                    const colors = [
                                        'bg-indigo-500',
                                        'bg-blue-500',
                                        'bg-sky-500',
                                        'bg-teal-500',
                                        'bg-green-500',
                                        'bg-emerald-500'
                                    ];
                                    const color = colors[index % colors.length];

                                    return (
                                        <div key={item.stage} className="flex items-center">
                                            <div className="w-32 text-sm font-medium text-right pr-4 capitalize truncate">
                                                {item.stage}
                                            </div>
                                            <div className="flex-1">
                                                <div 
                                                    className={`h-10 rounded-r-md ${color} flex items-center px-4 transition-all duration-500 ease-in-out`} 
                                                    style={{ width: `${Math.max(percentage, 5)}%` }}
                                                >
                                                    <span className="text-white text-sm font-bold">{item.count}</span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Right Column: Agents & Integrations */}
                <div className="space-y-4 col-span-1">
                    {/* Agent Status */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg">{t('dashboard.agentStatus')}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {loadingDash ? (
                                <Skeleton className="h-16 w-full" />
                            ) : dashboard?.agents?.list?.length ? (
                                <div className="space-y-3">
                                    {dashboard.agents.list.map(agent => (
                                        <div key={agent.id} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <Bot className="h-4 w-4 text-muted-foreground" />
                                                <span className="text-sm font-medium">{agent.name}</span>
                                            </div>
                                            <Badge variant={agent.status === 'active' ? 'default' : 'secondary'} className={agent.status === 'active' ? 'bg-green-500/10 text-green-700 hover:bg-green-500/20 border-green-500/20' : ''}>
                                                {agent.status === 'active' ? t('common.active') : t('common.inactive')}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-4 text-sm text-muted-foreground">
                                    <Bot className="h-8 w-8 mx-auto mb-2 opacity-20" />
                                    <p>{t('dashboard.noAgents')}</p>
                                    <Link href="/agents">
                                        <Button variant="link" className="px-0">{t('dashboard.configureAgents')}</Button>
                                    </Link>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Integrations & Connected Channels (Dynamic List) */}
                    <Card>
                        <CardHeader className="pb-3">
                            {(() => {
                                const connectedList: Array<{ id: string; name: string; type: string; icon: any; iconColor: string; subtitle?: string }> = [];

                                // 1. Check Channel model list (WhatsApp, Voice, Webchat, Telegram, Email, SMS)
                                const channelList = dashboard?.channels?.list || [];
                                channelList.forEach(c => {
                                    const status = String(c.status || '').toLowerCase();
                                    if (status === 'connected' || status === 'active') {
                                        if (c.type === 'whatsapp') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'WhatsApp',
                                                type: 'Canal WhatsApp',
                                                icon: MessageCircle,
                                                iconColor: 'text-green-500',
                                                subtitle: c.phone_number || 'Sesión Activa'
                                            });
                                        } else if (c.type === 'voice' || c.type === 'livekit') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'AI Phone / Voice',
                                                type: 'Llamadas de Voz',
                                                icon: Phone,
                                                iconColor: 'text-indigo-500',
                                                subtitle: 'LiveKit & Twilio'
                                            });
                                        } else if (c.type === 'webchat') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'Widget Web Chat',
                                                type: 'Sitio Web Embebido',
                                                icon: Bot,
                                                iconColor: 'text-purple-500',
                                                subtitle: 'Widget Activo'
                                            });
                                        } else if (c.type === 'telegram') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'Telegram Bot',
                                                type: 'Canal Telegram',
                                                icon: Send,
                                                iconColor: 'text-sky-500',
                                                subtitle: 'Bot Conectado'
                                            });
                                        }
                                    }
                                });

                                // 2. Google Calendar
                                if (dashboard?.integrations?.google_calendar?.connected) {
                                    connectedList.push({
                                        id: 'integ-gcal',
                                        name: 'Google Calendar',
                                        type: 'Agenda & Citas',
                                        icon: Calendar,
                                        iconColor: 'text-blue-500',
                                        subtitle: dashboard.integrations.google_calendar.calendar_id || 'Sincronizado'
                                    });
                                }

                                // 3. CRM (HubSpot, Salesforce, Pipedrive)
                                if (dashboard?.integrations?.crm?.connected) {
                                    connectedList.push({
                                        id: 'integ-crm',
                                        name: dashboard.integrations.crm.platform ? String(dashboard.integrations.crm.platform).toUpperCase() : 'CRM',
                                        type: 'Gestión de Leads',
                                        icon: Database,
                                        iconColor: 'text-orange-500',
                                        subtitle: 'Sincronización Bidireccional'
                                    });
                                }

                                // 4. E-commerce
                                if (dashboard?.integrations?.ecommerce?.connected) {
                                    connectedList.push({
                                        id: 'integ-ecom',
                                        name: dashboard.integrations.ecommerce.platform ? String(dashboard.integrations.ecommerce.platform).toUpperCase() : 'E-Commerce',
                                        type: 'Catálogo & Pedidos',
                                        icon: ShoppingCart,
                                        iconColor: 'text-emerald-500',
                                        subtitle: 'Tienda Conectada'
                                    });
                                }

                                // 5. ERP
                                if (dashboard?.integrations?.erp?.connected) {
                                    connectedList.push({
                                        id: 'integ-erp',
                                        name: dashboard.integrations.erp.platform ? String(dashboard.integrations.erp.platform).toUpperCase() : 'ERP',
                                        type: 'Inventario & Facturación',
                                        icon: Server,
                                        iconColor: 'text-cyan-500',
                                        subtitle: 'Sistema Conectado'
                                    });
                                }

                                return (
                                    <>
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-lg">{t('dashboard.integrations', { defaultValue: 'Integraciones' })}</CardTitle>
                                            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                                {connectedList.length} {connectedList.length === 1 ? 'activa' : 'activas'}
                                            </span>
                                        </div>
                                    </>
                                );
                            })()}
                        </CardHeader>
                        <CardContent>
                            {(() => {
                                const connectedList: Array<{ id: string; name: string; type: string; icon: any; iconColor: string; subtitle?: string }> = [];

                                const channelList = dashboard?.channels?.list || [];
                                channelList.forEach(c => {
                                    const status = String(c.status || '').toLowerCase();
                                    if (status === 'connected' || status === 'active') {
                                        if (c.type === 'whatsapp') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'WhatsApp',
                                                type: 'Canal WhatsApp',
                                                icon: MessageCircle,
                                                iconColor: 'text-green-500',
                                                subtitle: c.phone_number || 'Sesión Activa'
                                            });
                                        } else if (c.type === 'voice' || c.type === 'livekit') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'AI Phone / Voice',
                                                type: 'Llamadas de Voz',
                                                icon: Phone,
                                                iconColor: 'text-indigo-500',
                                                subtitle: 'LiveKit & Twilio'
                                            });
                                        } else if (c.type === 'webchat') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'Widget Web Chat',
                                                type: 'Sitio Web Embebido',
                                                icon: Bot,
                                                iconColor: 'text-purple-500',
                                                subtitle: 'Widget Activo'
                                            });
                                        } else if (c.type === 'telegram') {
                                            connectedList.push({
                                                id: `ch-${c.id}`,
                                                name: c.name || 'Telegram Bot',
                                                type: 'Canal Telegram',
                                                icon: Send,
                                                iconColor: 'text-sky-500',
                                                subtitle: 'Bot Conectado'
                                            });
                                        }
                                    }
                                });

                                if (dashboard?.integrations?.google_calendar?.connected) {
                                    connectedList.push({
                                        id: 'integ-gcal',
                                        name: 'Google Calendar',
                                        type: 'Agenda & Citas',
                                        icon: Calendar,
                                        iconColor: 'text-blue-500',
                                        subtitle: dashboard.integrations.google_calendar.calendar_id || 'Sincronizado'
                                    });
                                }

                                if (dashboard?.integrations?.crm?.connected) {
                                    connectedList.push({
                                        id: 'integ-crm',
                                        name: dashboard.integrations.crm.platform ? String(dashboard.integrations.crm.platform).toUpperCase() : 'CRM',
                                        type: 'Gestión de Leads',
                                        icon: Database,
                                        iconColor: 'text-orange-500',
                                        subtitle: 'Sincronización Activa'
                                    });
                                }

                                if (dashboard?.integrations?.ecommerce?.connected) {
                                    connectedList.push({
                                        id: 'integ-ecom',
                                        name: dashboard.integrations.ecommerce.platform ? String(dashboard.integrations.ecommerce.platform).toUpperCase() : 'E-Commerce',
                                        type: 'Catálogo & Pedidos',
                                        icon: ShoppingCart,
                                        iconColor: 'text-emerald-500',
                                        subtitle: 'Tienda Conectada'
                                    });
                                }

                                if (dashboard?.integrations?.erp?.connected) {
                                    connectedList.push({
                                        id: 'integ-erp',
                                        name: dashboard.integrations.erp.platform ? String(dashboard.integrations.erp.platform).toUpperCase() : 'ERP',
                                        type: 'Inventario & Facturación',
                                        icon: Server,
                                        iconColor: 'text-cyan-500',
                                        subtitle: 'Sistema Conectado'
                                    });
                                }

                                if (loadingDash) {
                                    return <Skeleton className="h-16 w-full" />;
                                }

                                if (connectedList.length === 0) {
                                    return (
                                        <div className="text-center py-5 text-sm text-muted-foreground">
                                            <Plug className="h-8 w-8 mx-auto mb-2 opacity-20" />
                                            <p className="text-xs">No hay integraciones conectadas aún.</p>
                                            <Link href="/channels">
                                                <Button variant="link" className="px-0 text-xs mt-1">Conectar Canales & CRM</Button>
                                            </Link>
                                        </div>
                                    );
                                }

                                return (
                                    <div className="space-y-3">
                                        {connectedList.map((item) => {
                                            const IconComp = item.icon;
                                            return (
                                                <div key={item.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/40 transition-colors">
                                                    <div className="flex items-center gap-2.5 min-w-0">
                                                        <div className="p-1.5 rounded-md bg-muted/60 shrink-0">
                                                            <IconComp className={`h-4 w-4 ${item.iconColor}`} />
                                                        </div>
                                                        <div className="truncate">
                                                            <div className="text-sm font-semibold truncate text-foreground">{item.name}</div>
                                                            <div className="text-[11px] text-muted-foreground truncate">{item.type}</div>
                                                        </div>
                                                    </div>
                                                    <Badge variant="default" className="bg-green-500/10 text-green-700 dark:text-green-400 hover:bg-green-500/20 border-green-500/20 text-[11px] shrink-0 ml-2 font-semibold">
                                                        {t('channels.connected', { defaultValue: 'Conectado' })}
                                                    </Badge>
                                                </div>
                                            );
                                        })}
                                        
                                        <div className="pt-2 flex gap-2">
                                            <Link href="/channels" className="flex-1">
                                                <Button variant="secondary" size="sm" className="w-full text-xs">{t('dashboard.manageChannels', { defaultValue: 'Gestionar Canales' })}</Button>
                                            </Link>
                                            <Link href="/settings/crm" className="flex-1">
                                                <Button variant="outline" size="sm" className="w-full text-xs">CRM & Hubs</Button>
                                            </Link>
                                        </div>
                                    </div>
                                );
                            })()}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
