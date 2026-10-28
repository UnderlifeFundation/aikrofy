'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { Bot, Save, Loader2, Plus, Trash2, Smile, Plug, Link, Wrench, Brain, Sparkles, Network, Zap, Building2, Activity, RefreshCw, GitFork, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const OrgConductorTree = dynamic(
    () => import('@/components/features/org/OrgConductorTree').then((m) => ({ default: m.OrgConductorTree })),
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

const AgentSynapseMonitor = dynamic(
    () => import('@/components/features/brain/AgentSynapseMonitor').then((m) => ({ default: m.AgentSynapseMonitor })),
    { ssr: false }
);

const VisualFlowBuilder = dynamic(
    () => import('@/components/features/agents/VisualFlowBuilder').then((m) => ({ default: m.VisualFlowBuilder })),
    { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">Cargando Krof Studio...</div> }
);

const ActionConnectorsManager = dynamic(
    () => import('@/components/features/agents/ActionConnectorsManager').then((m) => ({ default: m.ActionConnectorsManager })),
    { ssr: false }
);

const TrustGuardrailsManager = dynamic(
    () => import('@/components/features/agents/TrustGuardrailsManager').then((m) => ({ default: m.TrustGuardrailsManager })),
    { ssr: false }
);

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

import apiClient from '@/lib/api-client';
import { useTranslation } from 'react-i18next';
import { AgentConfig, AgentFeature } from '@/types';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useAuthStore } from '@/store/use-auth-store';

export default function AgentSetupPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const searchParams = useSearchParams();
    const selectParam = searchParams.get('selected');
    const { user } = useAuthStore();

    const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
    const [agentsMode, setAgentsMode] = useState<'config' | 'org' | 'studio' | 'actions' | 'guardrails'>('config');
    const [synapseMonitorOpen, setSynapseMonitorOpen] = useState(false);

    // Horizontal tabs navigation scroll management
    const tabsNavRef = useRef<HTMLDivElement>(null);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(false);

    const updateScrollIndicators = () => {
        const el = tabsNavRef.current;
        if (!el) return;
        // Check if there is genuine overflow beyond rounding margins
        const hasOverflow = el.scrollWidth > el.clientWidth + 16;
        if (!hasOverflow) {
            setCanScrollLeft(false);
            setCanScrollRight(false);
            return;
        }
        setCanScrollLeft(el.scrollLeft > 12);
        // Only show right indicator if more than 16px remains hidden
        setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 16);
    };

    useEffect(() => {
        const el = tabsNavRef.current;
        if (!el) return;
        updateScrollIndicators();
        el.addEventListener('scroll', updateScrollIndicators, { passive: true });
        window.addEventListener('resize', updateScrollIndicators);
        // Small delay check to account for font & layout shifts post-mount
        const timer = setTimeout(updateScrollIndicators, 150);
        return () => {
            clearTimeout(timer);
            el.removeEventListener('scroll', updateScrollIndicators);
            window.removeEventListener('resize', updateScrollIndicators);
        };
    }, []);

    const handleTabChange = (mode: 'config' | 'org' | 'studio' | 'actions' | 'guardrails') => {
        setAgentsMode(mode);
        // Safely scroll only the tabs container without moving the page or card
        setTimeout(() => {
            const container = tabsNavRef.current;
            if (!container) return;
            const activeBtn = container.querySelector(`[data-tab-key="${mode}"]`) as HTMLElement;
            if (activeBtn) {
                const targetScrollLeft = activeBtn.offsetLeft - (container.clientWidth / 2) + (activeBtn.clientWidth / 2);
                container.scrollTo({ left: Math.max(0, targetScrollLeft), behavior: 'smooth' });
            }
            updateScrollIndicators();
        }, 50);
    };

    const scrollTabs = (direction: 'left' | 'right') => {
        const el = tabsNavRef.current;
        if (!el) return;
        const amount = direction === 'left' ? -220 : 220;
        el.scrollBy({ left: amount, behavior: 'smooth' });
    };

    // Org Conductor hierarchy state
    const [hierarchyData, setHierarchyData] = useState<any | null>(null);
    const [loadingHierarchy, setLoadingHierarchy] = useState(false);
    const [refreshingHierarchy, setRefreshingHierarchy] = useState(false);

    const fetchHierarchy = async (silent = false) => {
        if (!silent) setLoadingHierarchy(true);
        else setRefreshingHierarchy(true);
        try {
            const res = await apiClient.get('/agents/hierarchy');
            setHierarchyData(res.data);
        } catch (err: any) {
            toast.error('Error al cargar el organigrama: ' + (err.response?.data?.error || err.message));
        } finally {
            setLoadingHierarchy(false);
            setRefreshingHierarchy(false);
        }
    };

    const tabParam = searchParams.get('tab');

    useEffect(() => {
        if (tabParam && ['config', 'org', 'studio', 'actions', 'guardrails'].includes(tabParam)) {
            setAgentsMode(tabParam as any);
        }
    }, [tabParam]);

    useEffect(() => {
        if (agentsMode === 'org' && !hierarchyData) {
            fetchHierarchy();
        }
    }, [agentsMode]);

    // Fetch Agents
    const { data: agentsData, isLoading: loadingAgents } = useQuery({
        queryKey: ['agents'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ agents: AgentConfig[] }>('/agents/');
            return data.agents;
        },
    });

    // Fetch Strategic Campaigns
    const { data: campaignsList = [] } = useQuery({
        queryKey: ['strategic-campaigns'],
        queryFn: async () => {
            const { data } = await apiClient.get('/campaigns');
            return data.campaigns || [];
        },
    });

    // Auto-select agent
    useEffect(() => {
        if (agentsData?.length) {
            if (selectParam) {
                const found = agentsData.find(a => {
                    const normParam = selectParam.toLowerCase().replace(/[^a-z0-9]/g, '');
                    const normName = a.name.toLowerCase().replace(/[^a-z0-9]/g, '');
                    return String(a.id) === selectParam || 
                           normName === normParam || 
                           normParam.includes(normName) || 
                           normName.includes(normParam);
                });
                if (found) {
                    setSelectedAgentId(found.id);
                    return;
                }
            }
            if (!selectedAgentId) {
                setSelectedAgentId(agentsData[0].id);
            }
        }
    }, [agentsData, selectedAgentId, selectParam]);

    const { startTour, hasCompletedTour } = useOnboardingStore();

    // Check if coming directly from voice onboarding to initiate the virtual tour
    useEffect(() => {
        if (typeof window !== 'undefined' && user?.is_company_owner) {
            const shouldStart = sessionStorage.getItem('aikrofy_start_agent_tour');
            if (shouldStart === 'true' && !hasCompletedTour) {
                sessionStorage.removeItem('aikrofy_start_agent_tour');
                const timer = setTimeout(() => {
                    startTour(1); // Step 1 is Agents, then continues to Channels, RAG Docs, CRM, Integrations
                }, 1200);
                return () => clearTimeout(timer);
            }
        }
    }, [startTour, hasCompletedTour, user?.is_company_owner]);

    // Handle real-time select events from Copiloto sidebar
    useEffect(() => {
        const handleSelectAgent = async (e: Event) => {
            const customEvent = e as CustomEvent;
            const targetAgentId = customEvent.detail?.agentId;
            if (targetAgentId) {
                // Invalidate query to fetch new agent instantly
                await queryClient.invalidateQueries({ queryKey: ['agents'] });
                setSelectedAgentId(Number(targetAgentId));
            }
        };

        window.addEventListener('aikrofy-select-agent', handleSelectAgent);
        return () => window.removeEventListener('aikrofy-select-agent', handleSelectAgent);
    }, [queryClient]);

    const selectedAgent = agentsData?.find(a => a.id === selectedAgentId);

    // Fetch detailed agent config (like features)
    const { data: featuresData, isLoading: loadingFeatures } = useQuery({
        queryKey: ['agent-features', selectedAgentId],
        queryFn: async () => {
            if (!selectedAgentId) return null;
            const { data } = await apiClient.get<{ features: Record<string, AgentFeature[]> }>(`/agents/${selectedAgentId}/features`);
            return data.features;
        },
        enabled: !!selectedAgentId,
    });

    const createAgentMutation = useMutation({
        mutationFn: async (name: string) => {
            const { data } = await apiClient.post('/agents/', { name });
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['agents'] });
            setSelectedAgentId(data.agent.id);
            toast.success(t('common.success'));
        },
        onError: () => toast.error(t('common.error'))
    });

    const updateAgentMutation = useMutation({
        mutationFn: async (agentUpdate: Partial<AgentConfig>) => {
            const { data } = await apiClient.put(`/agents/${selectedAgentId}`, agentUpdate);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['agents'] });
            toast.success(t('common.success'));
        },
        onError: () => toast.error(t('common.error'))
    });
    
    const deleteAgentMutation = useMutation({
        mutationFn: async () => {
            await apiClient.delete(`/agents/${selectedAgentId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['agents'] });
            setSelectedAgentId(null);
            toast.success(t('common.success'));
        },
        onError: () => toast.error(t('common.error'))
    });

    const toggleFeatureMutation = useMutation({
        mutationFn: async ({ featureId, isEnabled }: { featureId: number, isEnabled: boolean }) => {
            const { data } = await apiClient.put(`/agents/${selectedAgentId}/features/${featureId}`, { is_enabled: isEnabled });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['agent-features', selectedAgentId] });
        },
        onError: () => toast.error(t('common.error'))
    });

    const handleCreateAgent = () => {
        const name = prompt(t('common.name'));
        if (name) createAgentMutation.mutate(name);
    };

    if (loadingAgents) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-7xl 2xl:max-w-[1600px] w-full mx-auto px-2 sm:px-4 pb-12 animate-slow-fade overflow-hidden">
            <div className="relative overflow-hidden rounded-2xl vivid-gradient-violet p-6 sm:p-8 text-white shadow-lg">
                <div className="relative z-10 flex flex-col gap-5">
                    {/* Top Row: Title, Description & Action Buttons */}
                    <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                        <div>
                            <h2 className="flex items-center gap-3 text-2xl sm:text-3xl font-bold tracking-tight">
                                <Bot className="h-7 w-7 sm:h-8 sm:w-8 text-white/90 shrink-0" />
                                {t('agentSetup.multiAgentSystem')}
                            </h2>
                            <p className="mt-1.5 text-white/80 text-sm max-w-2xl leading-relaxed">
                                {t('agentSetup.configureDesc')}
                            </p>
                        </div>

                        {/* Quick Actions (Always neatly aligned and reachable) */}
                        <div className="flex items-center gap-2.5 self-start sm:self-center shrink-0">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSynapseMonitorOpen(true)}
                                className="bg-white/10 hover:bg-white/20 border-white/25 text-white text-xs font-semibold backdrop-blur-md gap-1.5 rounded-xl h-9 px-3.5 transition-all shadow-sm"
                            >
                                <Brain className="w-3.5 h-3.5 text-pink-300 animate-pulse" />
                                <span>{t('agentSetup.synapseMonitor', { defaultValue: 'Monitor Sináptico' })}</span>
                            </Button>

                            {agentsMode === 'config' && (
                                <Button 
                                    onClick={handleCreateAgent} 
                                    disabled={createAgentMutation.isPending}
                                    size="sm"
                                    className="bg-white text-violet-950 hover:bg-white/90 font-semibold shadow-md rounded-xl h-9 px-4 transition-all"
                                >
                                    {createAgentMutation.isPending ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <Plus className="w-4 h-4 mr-1.5" />}
                                    {t('agentSetup.createAgent')}
                                </Button>
                            )}
                        </div>
                    </div>

                    {/* Bottom Row: Silicon Valley Guided Interactive Navigation Bar */}
                    <div className="w-full pt-2 border-t border-white/15">
                        <div className="relative flex items-center w-full group/nav">
                            {/* Left Scroll Assist Arrow (Appears when scrolled right, Mobile/Tablet only) */}
                            {canScrollLeft && (
                                <button
                                    type="button"
                                    onClick={() => scrollTabs('left')}
                                    aria-label="Anterior pestaña"
                                    className="absolute left-1 z-20 hidden sm:flex lg:hidden items-center justify-center w-8 h-8 rounded-full bg-violet-950/90 text-white shadow-lg border border-white/20 hover:bg-violet-900 transition-all cursor-pointer backdrop-blur-md"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                            )}

                            {/* Left gradient hint */}
                            {canScrollLeft && (
                                <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-violet-950/80 to-transparent pointer-events-none z-10 rounded-l-xl lg:hidden" />
                            )}

                            {/* Scrollable Tabs Container */}
                            <div 
                                ref={tabsNavRef}
                                className="w-full overflow-x-auto py-1 px-1 scroll-smooth scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none]"
                            >
                                <div className="bg-black/25 backdrop-blur-xl border border-white/20 p-1.5 h-12 w-fit lg:w-full min-w-max lg:min-w-0 lg:grid lg:grid-cols-5 flex items-center gap-1.5 rounded-xl shadow-inner mx-auto">
                                    <button
                                        type="button"
                                        data-tab-key="config"
                                        onClick={() => handleTabChange('config')}
                                        className={cn(
                                            "h-9 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center justify-center gap-2 shrink-0 lg:flex-1 cursor-pointer",
                                            agentsMode === 'config'
                                                ? "bg-white text-violet-950 shadow-md font-bold scale-[1.02]"
                                                : "text-white/75 hover:text-white hover:bg-white/10"
                                        )}
                                    >
                                        <Bot className="w-3.5 h-3.5 shrink-0" />
                                        <span>{t('agentSetup.tabConfiguration', { defaultValue: 'Configuración' })}</span>
                                    </button>

                                    <button
                                        type="button"
                                        data-tab-key="studio"
                                        onClick={() => handleTabChange('studio')}
                                        className={cn(
                                            "h-9 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center justify-center gap-2 shrink-0 lg:flex-1 cursor-pointer",
                                            agentsMode === 'studio'
                                                ? "bg-white text-violet-950 shadow-md font-bold scale-[1.02]"
                                                : "text-white/75 hover:text-white hover:bg-white/10"
                                        )}
                                    >
                                        <GitFork className={cn("w-3.5 h-3.5 shrink-0", agentsMode === 'studio' ? "text-violet-700" : "text-violet-300")} />
                                        <span>{t('agentSetup.tabFlowStudio', { defaultValue: 'Flow Studio' })}</span>
                                    </button>

                                    <button
                                        type="button"
                                        data-tab-key="actions"
                                        onClick={() => handleTabChange('actions')}
                                        className={cn(
                                            "h-9 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center justify-center gap-2 shrink-0 lg:flex-1 cursor-pointer",
                                            agentsMode === 'actions'
                                                ? "bg-white text-violet-950 shadow-md font-bold scale-[1.02]"
                                                : "text-white/75 hover:text-white hover:bg-white/10"
                                        )}
                                    >
                                        <Wrench className={cn("w-3.5 h-3.5 shrink-0", agentsMode === 'actions' ? "text-emerald-600" : "text-emerald-300")} />
                                        <span>{t('agentSetup.tabApiConnectors', { defaultValue: 'Conectores API' })}</span>
                                    </button>

                                    <button
                                        type="button"
                                        data-tab-key="guardrails"
                                        onClick={() => handleTabChange('guardrails')}
                                        className={cn(
                                            "h-9 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center justify-center gap-2 shrink-0 lg:flex-1 cursor-pointer",
                                            agentsMode === 'guardrails'
                                                ? "bg-white text-violet-950 shadow-md font-bold scale-[1.02]"
                                                : "text-white/75 hover:text-white hover:bg-white/10"
                                        )}
                                    >
                                        <ShieldCheck className={cn("w-3.5 h-3.5 shrink-0", agentsMode === 'guardrails' ? "text-indigo-600" : "text-sky-300")} />
                                        <span>{t('agentSetup.tabGuardrails', { defaultValue: 'Guardrails' })}</span>
                                    </button>

                                    <button
                                        type="button"
                                        data-tab-key="org"
                                        onClick={() => handleTabChange('org')}
                                        className={cn(
                                            "h-9 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center justify-center gap-2 shrink-0 lg:flex-1 cursor-pointer",
                                            agentsMode === 'org'
                                                ? "bg-white text-violet-950 shadow-md font-bold scale-[1.02]"
                                                : "text-white/75 hover:text-white hover:bg-white/10"
                                        )}
                                    >
                                        <Network className={cn("w-3.5 h-3.5 shrink-0", agentsMode === 'org' ? "text-amber-600" : "text-amber-300")} />
                                        <span>{t('agentSetup.tabOrgConductor', { defaultValue: 'Conductor IA' })}</span>
                                    </button>
                                </div>
                            </div>

                            {/* Right gradient hint with cue */}
                            {canScrollRight && (
                                <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-violet-950/80 to-transparent pointer-events-none z-10 rounded-r-xl flex items-center justify-end pr-1 lg:hidden">
                                    <span className="text-[10px] text-white/50 animate-pulse font-bold sm:hidden">›</span>
                                </div>
                            )}

                            {/* Right Scroll Assist Arrow (Mobile/Tablet only when overflow exists) */}
                            {canScrollRight && (
                                <button
                                    type="button"
                                    onClick={() => scrollTabs('right')}
                                    aria-label="Siguiente pestaña"
                                    className="absolute right-1 z-20 hidden sm:flex lg:hidden items-center justify-center w-8 h-8 rounded-full bg-violet-950/90 text-white shadow-lg border border-white/20 hover:bg-violet-900 transition-all cursor-pointer backdrop-blur-md"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    </div>
                </div>
                {/* Decorative elements */}
                <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
                <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-primary/20 blur-3xl" />
            </div>

            {agentsMode === 'studio' ? (
                <VisualFlowBuilder />
            ) : agentsMode === 'actions' ? (
                <ActionConnectorsManager />
            ) : agentsMode === 'guardrails' ? (
                <TrustGuardrailsManager />
            ) : agentsMode === 'org' ? (
                <div className="space-y-6">
                    {/* Conductor Toolbar */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-md">
                                    <Zap className="h-4 w-4 text-white" />
                                </div>
                                <h3 className="text-base font-semibold">Organigrama Conductor IA</h3>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Árbol jerárquico que muestra al Conductor IA, pilares departamentales y agentes operativos en tiempo real.
                            </p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => fetchHierarchy(true)}
                            disabled={refreshingHierarchy}
                            className="self-start sm:self-center"
                        >
                            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshingHierarchy ? 'animate-spin' : ''}`} />
                            Actualizar Organigrama
                        </Button>
                    </div>

                    {/* Stats pills */}
                    {hierarchyData && (
                        <div className="flex flex-wrap gap-3">
                            <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-xs">
                                <Bot className="h-4 w-4 text-violet-500" />
                                <div>
                                    <p className="text-lg font-bold leading-none">{hierarchyData.stats.total_agents}</p>
                                    <p className="text-[11px] text-muted-foreground">Agentes</p>
                                </div>
                            </Card>
                            <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-xs">
                                <Building2 className="h-4 w-4 text-blue-500" />
                                <div>
                                    <p className="text-lg font-bold leading-none">{hierarchyData.stats.total_departments}</p>
                                    <p className="text-[11px] text-muted-foreground">Departamentos</p>
                                </div>
                            </Card>
                            <Card className="flex items-center gap-3 px-4 py-2.5 rounded-xl border bg-card shadow-xs">
                                <Activity className="h-4 w-4 text-emerald-500" />
                                <div>
                                    <p className="text-lg font-bold leading-none text-emerald-600">
                                        {hierarchyData.conductor?.live?.active_conversations ?? 0}
                                    </p>
                                    <p className="text-[11px] text-muted-foreground">Conversaciones activas</p>
                                </div>
                            </Card>
                        </div>
                    )}

                    {/* Main Tree Card */}
                    <Card className="overflow-auto rounded-2xl shadow-xs">
                        <CardContent className="p-0">
                            {loadingHierarchy ? (
                                <div className="flex flex-col gap-4 items-center py-12 px-6">
                                    <Skeleton className="h-16 w-16 rounded-2xl" />
                                    <Skeleton className="h-4 w-32" />
                                    <div className="flex gap-4 mt-4">
                                        {[1, 2, 3].map((i) => (
                                            <Skeleton key={i} className="h-56 w-48 rounded-2xl" />
                                        ))}
                                    </div>
                                </div>
                            ) : hierarchyData ? (
                                <div className="overflow-x-auto p-4">
                                    <OrgConductorTree data={hierarchyData} />
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
                </div>
            ) : (
                <>

            {/* Agent Selector */}
            <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
                <CardContent className="p-6 flex items-center justify-between gap-6">
                    <div className="flex-1 space-y-2">
                        <Label>{t('agentSetup.selectAgent')}</Label>
                        <Select 
                            value={selectedAgentId?.toString() || ''} 
                            onValueChange={(val) => setSelectedAgentId(Number(val))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder={`-- ${t('agentSetup.selectAgent')} --`} />
                            </SelectTrigger>
                            <SelectContent>
                                {agentsData?.map(agent => (
                                    <SelectItem key={agent.id} value={agent.id.toString()}>
                                        {agent.name} {agent.is_active ? '' : `(${t('common.inactive')})`}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    {selectedAgent && (
                        <>
                            <div className="space-y-2">
                                <Label>{t('agentSetup.status')}</Label>
                                <div className="flex items-center space-x-2 h-10">
                                    <Switch 
                                        checked={selectedAgent.is_active} 
                                        onCheckedChange={(checked) => updateAgentMutation.mutate({ is_active: checked })}
                                    />
                                    <span className="text-sm">{selectedAgent.is_active ? t('common.active') : t('common.inactive')}</span>
                                </div>
                            </div>
                            <div className="space-y-2 flex flex-col justify-end">
                                <Label className="opacity-0">Acciones</Label>
                                <Button 
                                    onClick={() => window.location.href = `/agents/playground?agentId=${selectedAgent.id}`}
                                    className="flex items-center gap-2 h-10 px-4 vivid-gradient-violet border-none hover:opacity-90 text-white"
                                >
                                    <Sparkles className="w-4 h-4" />
                                    <span>Probar Agente</span>
                                </Button>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>

            {selectedAgent && (
                <div className="grid gap-6" key={selectedAgent.id}>
                    {/* Personality & Tone Configuration */}
                    <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
                        <CardHeader>
                            <CardTitle className="flex items-center text-lg">
                                <Smile className="w-5 h-5 mr-2 text-primary" />
                                {t('agentSetup.personalityTone')}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label>{t('agentSetup.agentName')}</Label>
                                    <Input 
                                        defaultValue={selectedAgent.name} 
                                        onBlur={(e) => {
                                            if (e.target.value !== selectedAgent.name) {
                                                updateAgentMutation.mutate({ name: e.target.value });
                                            }
                                        }}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('agentSetup.agentGender')}</Label>
                                    <Select 
                                        value={selectedAgent.gender || 'neutral'} 
                                        onValueChange={(val) => updateAgentMutation.mutate({ gender: val })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="neutral">{t('common.neutral')}</SelectItem>
                                            <SelectItem value="female">{t('common.female')}</SelectItem>
                                            <SelectItem value="male">{t('common.male')}</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="space-y-2">
                                    <Label>{t('agentSetup.tone')}</Label>
                                    <Select 
                                        value={selectedAgent.tone || 'professional'} 
                                        onValueChange={(val) => updateAgentMutation.mutate({ tone: val })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="professional">{t('common.professional')}</SelectItem>
                                            <SelectItem value="friendly">{t('common.friendly')}</SelectItem>
                                            <SelectItem value="receptionist">{t('common.receptionist')}</SelectItem>
                                            <SelectItem value="sales">{t('common.sales')}</SelectItem>
                                            <SelectItem value="support">{t('common.support')}</SelectItem>
                                            <SelectItem value="concierge">{t('common.concierge')}</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('agentSetup.objective')}</Label>
                                    <Select 
                                        value={selectedAgent.objective || 'general'} 
                                        onValueChange={(val) => updateAgentMutation.mutate({ objective: val })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="general">{t('common.general')}</SelectItem>
                                            <SelectItem value="customer_service">{t('common.customer_service')}</SelectItem>
                                            <SelectItem value="sales">{t('common.sales')}</SelectItem>
                                            <SelectItem value="scheduling">{t('common.scheduling')}</SelectItem>
                                            <SelectItem value="lead_qualification">{t('common.lead_qualification')}</SelectItem>
                                            <SelectItem value="support">{t('common.support')}</SelectItem>
                                            <SelectItem value="payments">{t('common.payments')}</SelectItem>
                                            <SelectItem value="inventory">{t('common.inventory')}</SelectItem>
                                            <SelectItem value="internal">🏢 {t('common.internal') || 'Interno (Equipo)'}</SelectItem>
                                            <SelectItem value="analytics">📊 {t('common.analytics') || 'Análisis de Datos'}</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('agentSetup.priority')}</Label>
                                    <Select 
                                        value={selectedAgent.priority?.toString() || '1'} 
                                        onValueChange={(val) => updateAgentMutation.mutate({ priority: Number(val) })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="1">{t('agentSetup.priorityLevel', { level: 1 })} ({t('agentSetup.standard')})</SelectItem>
                                            <SelectItem value="2">{t('agentSetup.priorityLevel', { level: 2 })} ({t('agentSetup.advance')})</SelectItem>
                                            <SelectItem value="3">{t('agentSetup.priorityLevel', { level: 3 })} ({t('agentSetup.expert')})</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Strategic Campaign Association */}
                            <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <Label className="text-sm font-semibold flex items-center gap-2">
                                            <span>🎯 Vincular a Campaña Estratégica</span>
                                        </Label>
                                        <p className="text-xs text-muted-foreground">
                                            Asocia este agente a una campaña activa para que priorice sus directrices, promociones y contexto especial.
                                        </p>
                                    </div>
                                    <Switch
                                        checked={Boolean(selectedAgent.system_prompt && /\[CAMPAIGN_ID:\d+\]/.test(selectedAgent.system_prompt))}
                                        onCheckedChange={(checked) => {
                                            if (!checked) {
                                                updateAgentMutation.mutate({ campaign_id: null } as any);
                                            } else if (campaignsList.length > 0) {
                                                updateAgentMutation.mutate({ campaign_id: campaignsList[0].id } as any);
                                            } else {
                                                toast.info('No hay campañas creadas aún. Crea una en la sección de Campañas.');
                                            }
                                        }}
                                    />
                                </div>

                                {Boolean(selectedAgent.system_prompt && /\[CAMPAIGN_ID:\d+\]/.test(selectedAgent.system_prompt)) && (
                                    <div className="pt-2">
                                        <Label className="text-xs text-muted-foreground mb-1 block">Selecciona la Campaña:</Label>
                                        <Select
                                            value={(() => {
                                                const match = selectedAgent.system_prompt?.match(/\[CAMPAIGN_ID:(\d+)\]/);
                                                return match ? match[1] : '';
                                            })()}
                                            onValueChange={(val) => {
                                                updateAgentMutation.mutate({ campaign_id: Number(val) } as any);
                                            }}
                                        >
                                            <SelectTrigger className="w-full bg-background border-border">
                                                <SelectValue placeholder="Selecciona una campaña..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {campaignsList.map((c: any) => (
                                                    <SelectItem key={c.id} value={String(c.id)}>
                                                        {c.name} {c.is_active ? '(Activa)' : '(Pausada)'}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label>{t('agentSetup.customInstructions')}</Label>
                                <Textarea 
                                    placeholder={t('agentSetup.personalityInstructionsPlaceholder')}
                                    defaultValue={selectedAgent.system_prompt || ''}
                                    onBlur={(e) => {
                                        if (e.target.value !== selectedAgent.system_prompt) {
                                            updateAgentMutation.mutate({ system_prompt: e.target.value });
                                        }
                                    }}
                                    rows={4}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Features Panels */}
                    {loadingFeatures ? (
                        <div className="space-y-4 text-center mt-8">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">{t('agentSetup.loadingCapabilities')}</p>
                        </div>
                    ) : featuresData && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Channels feature group */}
                            <FeaturePanel 
                                title={t('agentSetup.channels')} 
                                icon={<Plug className="w-5 h-5 text-indigo-500" />}
                                features={featuresData['channel'] || []}
                                onToggle={(id, isEnabled) => toggleFeatureMutation.mutate({ featureId: id, isEnabled })}
                            />
                            
                            {/* Integration features */}
                            <FeaturePanel 
                                title={t('agentSetup.integrations')} 
                                icon={<Link className="w-5 h-5 text-orange-500" />}
                                features={featuresData['integration'] || []}
                                onToggle={(id, isEnabled) => toggleFeatureMutation.mutate({ featureId: id, isEnabled })}
                            />
                            
                            {/* Tool features */}
                            <FeaturePanel 
                                title={t('agentSetup.tools')} 
                                icon={<Wrench className="w-5 h-5 text-blue-500" />}
                                features={featuresData['tool'] || []}
                                onToggle={(id, isEnabled) => toggleFeatureMutation.mutate({ featureId: id, isEnabled })}
                            />
 
                            {/* AI features */}
                            <FeaturePanel 
                                title={t('agentSetup.aiFeatures')} 
                                icon={<Brain className="w-5 h-5 text-teal-500" />}
                                features={featuresData['ai_feature'] || []}
                                onToggle={(id, isEnabled) => toggleFeatureMutation.mutate({ featureId: id, isEnabled })}
                            />
                        </div>
                    )}

                    <div className="flex justify-end pt-4 border-t">
                        <Button 
                            variant="destructive" 
                            onClick={() => {
                                if (confirm(t('agentSetup.deleteConfirm'))) {
                                    deleteAgentMutation.mutate();
                                }
                            }}
                            disabled={deleteAgentMutation.isPending}
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            {t('agentSetup.deleteAgent')}
                        </Button>
                    </div>
                </div>
            )}
            
            {!selectedAgent && !loadingAgents && agentsData?.length === 0 && (
                <div className="text-center py-12 border rounded-lg bg-card">
                    <Bot className="w-12 h-12 mx-auto text-muted-foreground mb-4 opacity-50" />
                    <h3 className="text-lg font-medium mb-1">{t('agentSetup.noAgents')}</h3>
                    <p className="text-muted-foreground mb-4">{t('agentSetup.createFirstAgent')}</p>
                    <Button onClick={handleCreateAgent}>
                        <Plus className="w-4 h-4 mr-2" /> {t('agentSetup.createAgent')}
                    </Button>
                </div>
            )}
            </>
            )}

            {/* Monitor Sináptico Modal */}
            {synapseMonitorOpen && (
                <AgentSynapseMonitor
                    isOpen={synapseMonitorOpen}
                    onClose={() => setSynapseMonitorOpen(false)}
                    companyId={user?.company_id}
                />
            )}
        </div>
    );
}

function FeaturePanel({ 
    title, icon, features, onToggle 
}: { 
    title: string; 
    icon: React.ReactNode; 
    features: AgentFeature[]; 
    onToggle: (id: number, isEnabled: boolean) => void;
}) {
    if (!features.length) return null;

    return (
        <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center gap-2 pb-3 border-b">
                {icon}
                <CardTitle className="text-base">{title}</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
                {features.map((feature) => (
                    <div key={feature.id} className="flex items-start justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-medium">{feature.label || feature.name}</Label>
                            <p className="text-xs text-muted-foreground">{feature.description}</p>
                        </div>
                        <Switch 
                            checked={feature.is_enabled} 
                            onCheckedChange={(checked) => onToggle(feature.id, checked)}
                        />
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
