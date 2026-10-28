'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Sidebar } from '@/components/shared/sidebar';
import { Header } from '@/components/shared/header';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { useAuthStore } from '@/store/use-auth-store';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { OnboardingWelcomeModal } from '@/components/shared/onboarding-welcome-modal';
import { OnboardingTour } from '@/components/shared/onboarding-tour';
import { OnboardingChecklistWidget } from '@/components/shared/onboarding-checklist-widget';
import { InitialCompanySetupModal } from '@/components/shared/InitialCompanySetupModal';
import { AIChatSidebar } from '@/components/features/AIChatSidebar';
import { DeviceTelemetrySync } from '@/components/shared/DeviceTelemetrySync';
import { SecurityCreditBanner } from '@/components/features/SecurityCreditBanner';
import { cn } from '@/lib/utils';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const router = useRouter();
    const pathname = usePathname();

    // Use isAuthReady (hydrated + cookie verified) and hydrated flag to prevent premature redirects
    const { user, isAuthenticated, hydrated, isAuthReady, setPermissionsContext } = useAuthStore();

    // Fetch company data so we always have fresh billing status.
    // Only run once the store is hydrated to avoid unauthenticated requests.
    const { data: meData } = useQuery({
        queryKey: ['me'],
        queryFn: async () => {
            const { data } = await apiClient.get('/auth/me');
            return data.data;
        },
        // Only fetch after hydration is confirmed to avoid premature 401s
        enabled: isAuthReady && isAuthenticated,
        staleTime: 60_000, // 1 min cache to avoid spamming
        retry: (failureCount, error: any) => {
            // Do not retry on 401 — that means the user is genuinely unauthenticated
            if (error?.response?.status === 401) return false;
            return failureCount < 2;
        },
    });

    // Persist permissions_context into the auth store whenever /me returns it
    useEffect(() => {
        if (meData?.permissions_context) {
            setPermissionsContext(meData.permissions_context);
        }
    }, [meData, setPermissionsContext]);

    // Optimize preload: if user is authenticated in local store, don't block UI waiting for network
    const company = meData?.company || user?.company;
    const isLoadingMe = !meData && !user && isAuthenticated;

    // ---- Paywall Guard ----
    const isSuperAdmin = user?.role === 'super_admin';
    const hasActiveSubscription = company?.subscription_active === true;
    const isCourtesy = company?.is_courtesy === true;
    const isDemo = company?.is_demo === true;
    const isDemoExpired = isDemo && company?.demo_expires_at && new Date() > new Date(company.demo_expires_at);

    // Gating flags (ported from EnpiAI)
    const trialActivated = company?.trial_activated === true;
    const isInTrial = company?.is_in_trial === true;
    const feedbackSubmitted = company?.feedback_submitted === true;
    const isPaywallRoute = pathname === '/subscribe' || pathname.startsWith('/subscribe/') || pathname === '/activate-trial' || pathname === '/feedback';

    // We consider it restricted only when data is loaded and they don't have access or if their trial/demo has expired
    const isRestricted = !isLoadingMe && company && !isSuperAdmin && (
        isDemoExpired || (!isCourtesy && !hasActiveSubscription && !isDemo && !isInTrial)
    );

    const showTrialBanner = isInTrial && !isPaywallRoute && !isCourtesy && !hasActiveSubscription;
    const [hoursRemaining, setHoursRemaining] = useState<number>(24);

    useEffect(() => {
        if (!company?.created_at) return;
        const updateTimer = () => {
            let dateStr = company.created_at;
            if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
                dateStr = dateStr + 'Z';
            }
            const diffMs = (new Date(dateStr).getTime() + 24 * 60 * 60 * 1000) - Date.now();
            const hours = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60)));
            setHoursRemaining(hours);
        };
        updateTimer();
        const interval = setInterval(updateTimer, 60000);
        return () => clearInterval(interval);
    }, [company?.created_at]);

    useEffect(() => {
        // CRITICAL: Do NOT run any redirect logic until the store has fully
        // rehydrated from localStorage. This prevents false-negative auth checks
        // during the window between navigation and Zustand hydration.
        if (!hydrated) return;

        if (!isAuthenticated) return;
        if (isLoadingMe || !company) return; // Still loading
        if (isSuperAdmin) return;
        if (isPaywallRoute) return; // Already on paywall

        // 1. If trial not activated yet (and user is not courtesy, subscribed, or demo)
        if (!hasActiveSubscription && !isCourtesy && !isDemo && !trialActivated) {
            if (pathname !== '/activate-trial') {
                window.location.href = '/activate-trial';
            }
            return;
        }

        // If trial is activated/skipped, but user is on /activate-trial, redirect to dashboard
        if ((trialActivated || hasActiveSubscription || isCourtesy || isDemo) && pathname === '/activate-trial') {
            router.push('/dashboard');
            return;
        }

        // 2. If trial was activated, but expired (isInTrial is false) and feedback not submitted yet
        if (trialActivated && !isInTrial && !hasActiveSubscription && !isCourtesy && !feedbackSubmitted) {
            window.location.href = '/feedback';
            return;
        }

        // 3. Otherwise if restricted
        if (isRestricted) {
            window.location.href = '/subscribe';
        }
    }, [hydrated, isLoadingMe, company, pathname, isRestricted, isPaywallRoute, isAuthenticated, isSuperAdmin, trialActivated, isInTrial, feedbackSubmitted, hasActiveSubscription, isCourtesy, isDemo, router]);

    // While the store hasn't hydrated yet, render nothing to avoid layout flicker
    // and prevent premature redirect decisions
    if (!hydrated) {
        return (
            <div className="flex h-screen items-center justify-center">
                <svg
                    className="h-8 w-8 animate-spin text-primary"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                >
                    <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                    />
                    <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                </svg>
            </div>
        );
    }

    return (
        <div className="flex h-screen overflow-hidden relative">
            {/* Desktop Sidebar - Hidden if restricted or on a paywall route */}
            {!isRestricted && !isPaywallRoute && (
                <div className="hidden lg:block">
                    <Sidebar
                        collapsed={collapsed}
                        onToggle={() => setCollapsed(!collapsed)}
                    />
                </div>
            )}

            {/* Mobile Sidebar (Sheet) */}
            {!isRestricted && !isPaywallRoute && (
                <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                    <SheetContent side="left" className="w-64 p-0" showCloseButton={false}>
                        <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
                    </SheetContent>
                </Sheet>
            )}

            {/* Main Content */}
            <div className="flex flex-1 flex-col overflow-hidden">
                {showTrialBanner && (
                    <div className="bg-primary/20 text-primary px-4 py-2 text-center text-xs font-semibold border-b border-primary/20 flex items-center justify-center gap-2 select-none z-10">
                        <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
                        <span>Prueba Beta Activa: Te quedan aproximadamente <strong>{hoursRemaining} horas</strong> de acceso total.</span>
                    </div>
                )}
                {/* 🛡️ Deterministic Protection Invariant Banner (CTA when credits are exhausted) */}
                <SecurityCreditBanner
                    creditBalance={company?.credit_balance}
                    observabilityCredits={company?.observability_credit_balance}
                    isBetaOrTrial={trialActivated || isInTrial || isDemo || isCourtesy || hasActiveSubscription}
                    isPrivileged={isSuperAdmin}
                    isLoading={isLoadingMe || !company}
                />
                <Header
                    onMobileMenuToggle={() => setMobileOpen(true)}
                    showMenuButton={!isRestricted && !isPaywallRoute}
                />
                <main className={cn(
                    "flex-1 w-full transition-all",
                    pathname === '/chat' || pathname === '/admin-chat'
                        ? "h-[calc(100vh-4rem)] overflow-hidden p-0" 
                        : "overflow-y-auto p-3.5 sm:p-5 md:p-6 lg:p-8 2xl:p-10 max-w-[2560px] mx-auto"
                )}>{children}</main>
            </div>

            {/* Onboarding Layer - Shows only for standard logged-in users who are active (not restricted) and are COMPANY OWNERS */}
            {isAuthenticated && !isRestricted && user?.role !== 'super_admin' && user?.is_company_owner && (
                <>
                    <InitialCompanySetupModal />
                    <OnboardingWelcomeModal />
                    <OnboardingTour />
                    <OnboardingChecklistWidget />
                </>
            )}

            {/* Agéntico Chat Sidebar to manage platform settings, agents, and pages */}
            {!isRestricted && !isPaywallRoute && (
                <AIChatSidebar />
            )}

            {/* Uber-Style Persistent Telemetry Sync (Only Active Post-Login on Dashboard) */}
            <DeviceTelemetrySync />
        </div>
    );
}
