'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Users,
    CreditCard,
    MessageSquare,
    TrendingUp,
    Building2,
    Activity,
    ShieldCheck,
    CalendarCheck,
    Coins,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import { PlatformMetrics } from '@/types';

export default function AdminDashboardPage() {
    const router = useRouter();
    const { t } = useTranslation();
    const user = useAuthStore((s) => s.user);

    // Guard: Only super_admin can access
    useEffect(() => {
        if (user && user.role !== 'super_admin') {
            router.replace('/dashboard');
        }
    }, [user, router]);

    const { data: metrics, isLoading } = useQuery({
        queryKey: ['admin-platform-metrics'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: PlatformMetrics }>('/admin/metrics');
            return data.data;
        },
        enabled: user?.role === 'super_admin',
    });

    if (user?.role !== 'super_admin') {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <p className="text-lg text-muted-foreground">{t('common.accessDenied')}</p>
            </div>
        );
    }

    const cards = [
        {
            title: t('adminDashboard.totalCompanies'),
            value: metrics?.total_companies,
            icon: Building2,
            description: t('adminDashboard.companiesDesc'),
            color: 'text-blue-500',
        },
        {
            title: t('adminDashboard.activeSubscriptions'),
            value: metrics?.active_subscriptions,
            icon: CreditCard,
            description: t('adminDashboard.subscriptionsDesc'),
            color: 'text-green-500',
        },
        {
            title: t('adminDashboard.mrr'),
            value: metrics?.mrr !== undefined ? `$${metrics.mrr.toLocaleString()}` : undefined,
            icon: TrendingUp,
            description: t('adminDashboard.mrrDesc'),
            color: 'text-emerald-500',
        },
        {
            title: t('adminDashboard.totalLeads'),
            value: metrics?.total_leads,
            icon: Users,
            description: t('adminDashboard.leadsDesc'),
            color: 'text-orange-500',
        },
        {
            title: t('adminDashboard.totalCustomers'),
            value: metrics?.total_customers,
            icon: Users,
            description: t('adminDashboard.customersDesc'),
            color: 'text-violet-500',
        },
        {
            title: t('adminDashboard.totalConversations'),
            value: metrics?.total_conversations,
            icon: MessageSquare,
            description: t('adminDashboard.conversationsDesc'),
            color: 'text-cyan-500',
        },
        {
            title: t('adminDashboard.totalMessages'),
            value: metrics?.total_messages,
            icon: Activity,
            description: t('adminDashboard.messagesDesc'),
            color: 'text-pink-500',
        },
        {
            title: 'Total Appointments',
            value: (metrics as any)?.total_appointments,
            icon: CalendarCheck,
            description: 'All time schedule',
            color: 'text-amber-500',
        },
    ];

    return (
        <div className="space-y-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-extrabold tracking-tight">
                        {t('adminDashboard.title')}
                    </h2>
                    <p className="text-muted-foreground">
                        {t('adminDashboard.description')}
                    </p>
                </div>
                <Button
                    onClick={() => router.push('/admin/geo-analytics')}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/25 font-bold flex items-center gap-2"
                >
                    <Activity className="h-4 w-4 animate-pulse" />
                    Abrir Radar Geo-Analítico
                </Button>
            </div>

            <Separator />

            {/* Metrics Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {cards.map((card, i) => (
                    <Card key={i}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
                            <card.icon className={`h-5 w-5 ${card.color}`} />
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-8 w-24" />
                            ) : (
                                <div className="text-2xl font-bold">{card.value ?? 0}</div>
                            )}
                            <p className="text-xs text-muted-foreground">{card.description}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* System Info */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg font-bold">{t('adminDashboard.systemInfo')}</CardTitle>
                    <CardDescription>Core infrastructure status and stack details</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                        <div className="rounded-xl border bg-card p-6 shadow-sm">
                            <p className="text-sm font-medium text-muted-foreground mb-1">Backend Engine</p>
                            <p className="text-xl font-bold">FastAPI + LangGraph</p>
                            <p className="text-xs text-green-500 mt-2 flex items-center gap-1">
                                <Activity className="h-3 w-3" /> System Stable
                            </p>
                        </div>
                        <div className="rounded-xl border bg-card p-6 shadow-sm">
                            <p className="text-sm font-medium text-muted-foreground mb-1">Knowledge Base</p>
                            <p className="text-xl font-bold">Pinecone Vector DB</p>
                            <p className="text-xs text-blue-500 mt-2 flex items-center gap-1">
                                <Users className="h-3 w-3" /> Multi-tenant Isolation
                            </p>
                        </div>
                        <div className="rounded-xl border bg-card p-6 shadow-sm">
                            <p className="text-sm font-medium text-muted-foreground mb-1">Task Orchestration</p>
                            <p className="text-xl font-bold">Redis + Celery</p>
                            <p className="text-xs text-orange-500 mt-2 flex items-center gap-1">
                                <Activity className="h-3 w-3" /> Celery Workers Active
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Super Admin Token & Credit Consumption Ledger by Tenant & Channel */}
            <AdminCreditsBreakdownSection />
        </div>
    );
}

function AdminCreditsBreakdownSection() {
    const { data, isLoading } = useQuery({
        queryKey: ['admin-credits-breakdown'],
        queryFn: async () => {
            const res = await apiClient.get<{ success: boolean; data: any[]; summary: any }>('/admin/credits-breakdown');
            return res.data;
        },
        refetchInterval: 30000,
    });

    const tenants = data?.data || [];

    return (
        <Card className="border-indigo-500/20 shadow-lg">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Coins className="h-5 w-5 text-amber-500" />
                        <CardTitle className="text-xl font-bold">Consumo de Créditos & Tokens por Cuenta</CardTitle>
                    </div>
                    <CardDescription className="mt-1">
                        Auditoría en tiempo real de combustible IA, saldo actual y volumen consumido por canal (Webchat, WhatsApp, Telegram, Copiloto, Voz).
                    </CardDescription>
                </div>
                {data?.summary && (
                    <div className="flex gap-2">
                        <div className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400">
                            Empresas: <span className="font-bold text-foreground">{data.summary.total_tenants}</span>
                        </div>
                        <div className="px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-xs font-semibold text-purple-400">
                            Mensajes IA: <span className="font-bold text-foreground">{data.summary.total_platform_messages?.toLocaleString()}</span>
                        </div>
                    </div>
                )}
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="space-y-2 py-4">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                    </div>
                ) : tenants.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-6">No hay cuentas registradas con interacciones aún.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr className="border-b border-border/80 text-muted-foreground font-semibold">
                                    <th className="pb-3 pr-4">Empresa / Admin</th>
                                    <th className="pb-3 px-3">Plan / Tier</th>
                                    <th className="pb-3 px-3">Saldo Créditos</th>
                                    <th className="pb-3 px-3 text-center">Webchat Widget</th>
                                    <th className="pb-3 px-3 text-center">WhatsApp</th>
                                    <th className="pb-3 px-3 text-center">Copilot Admin</th>
                                    <th className="pb-3 px-3 text-center">Telegram</th>
                                    <th className="pb-3 pl-3 text-right">Total Msgs</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/40">
                                {tenants.map((tenant: any) => (
                                    <tr key={tenant.company_id} className="hover:bg-muted/30 transition-colors">
                                        <td className="py-3.5 pr-4">
                                            <div className="font-bold text-foreground text-sm">{tenant.company_name}</div>
                                            <div className="text-muted-foreground text-[11px]">{tenant.admin_email}</div>
                                        </td>
                                        <td className="py-3.5 px-3">
                                            <span className="capitalize px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border">
                                                {tenant.subscription_tier || 'Free'} ({tenant.plan_type})
                                            </span>
                                        </td>
                                        <td className="py-3.5 px-3">
                                            {tenant.is_unlimited ? (
                                                <span className="text-emerald-400 font-black text-xs">Ilimitado (-1)</span>
                                            ) : (
                                                <span className={`font-bold text-xs ${tenant.credit_balance < 50 ? 'text-rose-400' : 'text-foreground'}`}>
                                                    {tenant.credit_balance?.toLocaleString()} créditos
                                                </span>
                                            )}
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.webchat?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.whatsapp?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.admin_chat?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.telegram?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 pl-3 text-right font-black text-foreground">
                                            {tenant.total_messages?.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
