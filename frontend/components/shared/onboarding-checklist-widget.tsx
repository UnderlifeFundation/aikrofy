'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { 
    CheckCircle2, 
    Circle, 
    ChevronUp, 
    ChevronDown, 
    Sparkles, 
    Bot, 
    Radio, 
    FileText, 
    MessageSquare, 
    Database, 
    PlayCircle,
    PartyPopper,
    X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useAuthStore } from '@/store/use-auth-store';
import apiClient from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface DashboardOverview {
    overview: {
        total_conversations: number;
    };
    channels: {
        connected: number;
    };
    documents: {
        total: number;
        indexed: number;
    };
    agents: {
        total: number;
    };
    integrations: {
        google_calendar?: { connected: boolean };
        google_sheets?: { connected: boolean };
        crm?: { connected: boolean };
        ecommerce?: { connected: boolean };
        erp?: { connected: boolean };
        payments?: { connected: boolean };
    };
}

export function OnboardingChecklistWidget() {
    const { t } = useTranslation();
    const router = useRouter();
    const { user } = useAuthStore();
    const { 
        completedSteps, 
        setCompletedSteps, 
        checklistExpanded, 
        setChecklistExpanded, 
        hasCompletedTour,
        hasDismissedWidget,
        dismissWidget,
        setHasCompletedTour,
        startTour 
    } = useOnboardingStore();

    const [isLocallyDismissed, setIsLocallyDismissed] = useState(false);

    if (!user?.is_company_owner) return null;

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const userId = user?.id || 'guest';
        const dismissed = localStorage.getItem(`aikrofy_onboarding_dismissed_${userId}`) === 'true';
        if (dismissed) {
            setIsLocallyDismissed(true);
            setHasCompletedTour(true);
        }
    }, [user?.id, setHasCompletedTour]);

    const handleDismissPermanently = (e?: React.MouseEvent) => {
        e?.stopPropagation();
        const userId = user?.id || 'guest';
        if (typeof window !== 'undefined') {
            localStorage.setItem(`aikrofy_onboarding_dismissed_${userId}`, 'true');
        }
        dismissWidget();
        setIsLocallyDismissed(true);
        setHasCompletedTour(true);
        setChecklistExpanded(false);
    };
    
    // Fetch live dashboard state to automatically validate steps
    const { data: dashboard } = useQuery<DashboardOverview>({
        queryKey: ['analytics-dashboard'],
        queryFn: async () => {
            const { data } = await apiClient.get('/analytics/dashboard');
            return data;
        },
        enabled: !isLocallyDismissed && !hasDismissedWidget && !hasCompletedTour,
        refetchInterval: 2_000, // Refresh every 2s for instant real-time completion feedback
    });

    useEffect(() => {
        if (!dashboard) return;

        const liveCompleted: string[] = [];

        // 1. Agent configuration check
        if (dashboard.agents?.total > 0) {
            liveCompleted.push('agents');
        }

        // 2. Channel connected check
        if (dashboard.channels?.connected > 0) {
            liveCompleted.push('channels');
        }

        // 3. Document uploaded check (indexed or total uploaded)
        if (dashboard.documents?.total > 0 || dashboard.documents?.indexed > 0) {
            liveCompleted.push('documents');
        }

        // 4. Chat playground check
        if (dashboard.overview?.total_conversations > 0) {
            liveCompleted.push('chat');
        }

        // 5. Integrations check (Google Calendar, CRM, Sheets, Ecommerce, ERP, or Payments)
        if (
            dashboard.integrations?.google_calendar?.connected || 
            dashboard.integrations?.crm?.connected || 
            dashboard.integrations?.google_sheets?.connected ||
            dashboard.integrations?.ecommerce?.connected ||
            dashboard.integrations?.erp?.connected ||
            dashboard.integrations?.payments?.connected
        ) {
            liveCompleted.push('integrations');
        }

        setCompletedSteps(liveCompleted);
    }, [dashboard]);

    const checklistItems = [
        {
            key: 'agents',
            title: t('onboarding.stepAgents'),
            desc: t('onboarding.stepAgentsDesc'),
            href: '/agents',
            icon: Bot,
        },
        {
            key: 'channels',
            title: t('onboarding.stepChannels'),
            desc: t('onboarding.stepChannelsDesc'),
            href: '/channels',
            icon: Radio,
        },
        {
            key: 'documents',
            title: t('onboarding.stepDocuments'),
            desc: t('onboarding.stepDocumentsDesc'),
            href: '/documents',
            icon: FileText,
        },
        {
            key: 'chat',
            title: t('onboarding.stepChat'),
            desc: t('onboarding.stepChatDesc'),
            href: '/chat',
            icon: MessageSquare,
        },
        {
            key: 'integrations',
            title: t('onboarding.stepIntegrations'),
            desc: t('onboarding.stepIntegrationsDesc'),
            href: '/settings/crm',
            icon: Database,
        },
    ];

    const completedCount = checklistItems.filter(item => completedSteps.includes(item.key)).length;
    const progressPercent = Math.round((completedCount / checklistItems.length) * 100);
    const allCompleted = completedCount === checklistItems.length;

    const handleItemClick = (href: string) => {
        router.push(href);
    };

    const isOlderThan2Days = user?.created_at 
        ? (Date.now() - new Date(user.created_at).getTime() > 2 * 24 * 60 * 60 * 1000) 
        : false;

    if (hasCompletedTour || allCompleted || hasDismissedWidget || isLocallyDismissed || isOlderThan2Days) return null;

    return (
        <div className="fixed bottom-24 right-6 z-[9000] flex flex-col items-end gap-3 pointer-events-none">
            {/* Expanded panel */}
            {checklistExpanded && (
                <Card className="w-80 sm:w-96 shadow-2xl border bg-card/95 backdrop-blur-md overflow-hidden rounded-2xl animate-fade-in pointer-events-auto select-none">
                    {/* Header */}
                    <div className="p-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-indigo-200 animate-pulse" />
                            <div>
                                <h4 className="font-bold text-sm tracking-tight">{t('onboarding.checklistTitle')}</h4>
                                <p className="text-[10px] text-indigo-100">{completedCount} de {checklistItems.length} completados</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                onClick={() => setChecklistExpanded(false)}
                                className="text-white hover:bg-white/10 rounded-full h-8 w-8"
                                title="Minimizar"
                            >
                                <ChevronDown className="h-4 w-4" />
                            </Button>
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                onClick={handleDismissPermanently}
                                className="text-white hover:bg-white/10 rounded-full h-8 w-8"
                                title="Cerrar permanentemente"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-1.5 w-full bg-muted/40 relative">
                        <div 
                            className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-500 ease-out"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>

                    {/* Step list */}
                    <div className="p-4 max-h-[350px] overflow-y-auto space-y-3">
                        {allCompleted ? (
                            <div className="text-center py-6 px-4 space-y-3">
                                <div className="h-12 w-12 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center mx-auto animate-bounce">
                                    <PartyPopper className="h-6 w-6" />
                                </div>
                                <div className="space-y-1">
                                    <h5 className="font-bold text-sm text-foreground">{t('onboarding.congratulations')}</h5>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        {t('onboarding.allStepsCompleted')}
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-2.5">
                                {checklistItems.map((item, idx) => {
                                    const isDone = completedSteps.includes(item.key);
                                    const StepIcon = item.icon;
                                    
                                    return (
                                        <button
                                            key={item.key}
                                            onClick={() => handleItemClick(item.href)}
                                            className={cn(
                                                "w-full flex items-start gap-3 p-2.5 rounded-xl text-left border transition-all duration-300",
                                                isDone 
                                                    ? "bg-green-500/5 border-green-500/20 hover:bg-green-500/10" 
                                                    : "bg-muted/10 border-border/80 hover:bg-muted/50 hover:border-indigo-500/30"
                                            )}
                                        >
                                            <div className="mt-0.5 shrink-0">
                                                {isDone ? (
                                                    <CheckCircle2 className="h-5 w-5 text-green-500 fill-green-500/10" />
                                                ) : (
                                                    <Circle className="h-5 w-5 text-muted-foreground/60" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-1.5">
                                                    <StepIcon className={cn(
                                                        "h-3.5 w-3.5 shrink-0",
                                                        isDone ? "text-green-500" : "text-indigo-500"
                                                    )} />
                                                    <h5 className={cn(
                                                        "font-semibold text-xs leading-none text-foreground truncate",
                                                        isDone && "line-through text-muted-foreground"
                                                    )}>
                                                        {item.title}
                                                    </h5>
                                                </div>
                                                <p className="text-[10px] text-muted-foreground leading-normal mt-1 truncate">
                                                    {item.desc}
                                                </p>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-3 border-t bg-muted/20 flex justify-between items-center text-xs">
                        <button 
                            onClick={() => startTour(0)}
                            className="flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-semibold transition-colors"
                        >
                            <PlayCircle className="h-4 w-4" />
                            Reiniciar Tour
                        </button>
                        <button
                            onClick={handleDismissPermanently}
                            className="text-[11px] text-muted-foreground hover:text-foreground underline transition-colors cursor-pointer"
                        >
                            No volver a mostrar
                        </button>
                    </div>
                </Card>
            )}

            {/* Toggle trigger badge with quick dismiss */}
            <div className="flex items-center gap-1.5 pointer-events-auto">
                <button
                    onClick={() => setChecklistExpanded(!checklistExpanded)}
                    className={cn(
                        "flex items-center gap-2 px-4 py-3 rounded-full font-bold shadow-2xl transition-all duration-300 border hover:scale-105 active:scale-95 text-white cursor-pointer",
                        allCompleted 
                            ? "bg-gradient-to-r from-emerald-500 to-green-600 border-emerald-400"
                            : "bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 border-indigo-400"
                    )}
                >
                    {allCompleted ? (
                        <CheckCircle2 className="h-5 w-5" />
                    ) : (
                        <Sparkles className="h-5 w-5 animate-pulse" />
                    )}
                    <span className="text-xs">
                        {allCompleted ? '¡Activación Lista!' : `${progressPercent}% Activado`}
                    </span>
                    {checklistExpanded ? (
                        <ChevronDown className="h-4 w-4 shrink-0" />
                    ) : (
                        <ChevronUp className="h-4 w-4 shrink-0" />
                    )}
                </button>
                <button
                    onClick={handleDismissPermanently}
                    className="h-8 w-8 rounded-full bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-white border border-white/10 flex items-center justify-center shadow-lg transition-all cursor-pointer"
                    title="Cerrar y no volver a mostrar"
                >
                    <X className="h-3.5 w-3.5" />
                </button>
            </div>
        </div>
    );
}
