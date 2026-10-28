'use client';

import { useEffect, useState, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { ChevronRight, ChevronLeft, X, Check } from 'lucide-react';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useAuthStore } from '@/store/use-auth-store';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface TourStep {
    targetId: string;
    route: string;
    titleKey: string;
    descKey: string;
    placement: 'right' | 'left' | 'bottom' | 'top';
}

const TOUR_STEPS: TourStep[] = [
    {
        targetId: 'onboarding-nav-dashboard',
        route: '/dashboard',
        titleKey: 'onboarding.tour.step0Title',
        descKey: 'onboarding.tour.step0Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-agents',
        route: '/agents',
        titleKey: 'onboarding.tour.step1Title',
        descKey: 'onboarding.tour.step1Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-channels',
        route: '/channels',
        titleKey: 'onboarding.tour.step2Title',
        descKey: 'onboarding.tour.step2Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-documents',
        route: '/documents',
        titleKey: 'onboarding.tour.step3Title',
        descKey: 'onboarding.tour.step3Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-chat',
        route: '/chat',
        titleKey: 'onboarding.tour.step4Title',
        descKey: 'onboarding.tour.step4Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-crm',
        route: '/settings/crm',
        titleKey: 'onboarding.tour.step5Title',
        descKey: 'onboarding.tour.step5Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-ecommerce',
        route: '/settings/ecommerce',
        titleKey: 'onboarding.tour.step6Title',
        descKey: 'onboarding.tour.step6Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-erp',
        route: '/settings/erp',
        titleKey: 'onboarding.tour.step7Title',
        descKey: 'onboarding.tour.step7Desc',
        placement: 'right',
    },
    {
        targetId: 'onboarding-nav-payments',
        route: '/settings/payments',
        titleKey: 'onboarding.tour.step8Title',
        descKey: 'onboarding.tour.step8Desc',
        placement: 'right',
    }
];

export function OnboardingTour() {
    const { t } = useTranslation();
    const router = useRouter();
    const pathname = usePathname();
    const { user } = useAuthStore();
    const { isTourActive, tourStepIndex, nextTourStep, prevTourStep, stopTour, setHasCompletedTour } = useOnboardingStore();

    if (!user?.is_company_owner) return null;

    const finishTour = () => {
        setHasCompletedTour(true);
        stopTour();
    };

    const [coords, setCoords] = useState<{ top: number; left: number; width: number; height: number } | null>(null);
    const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
    const [isNavigating, setIsNavigating] = useState(false);
    const tooltipRef = useRef<HTMLDivElement>(null);

    const currentStep = TOUR_STEPS[tourStepIndex];

    // Handle routing if step route doesn't match current route
    useEffect(() => {
        if (!isTourActive || !currentStep) return;

        if (pathname !== currentStep.route) {
            setIsNavigating(true);
            setCoords(null);
            router.push(currentStep.route);
        } else {
            // Give the DOM a tiny bit of time to settle after route match
            const timer = setTimeout(() => {
                setIsNavigating(false);
                updateSpotlight();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [isTourActive, tourStepIndex, pathname]);

    // Recalculate spotlight positioning
    const updateSpotlight = () => {
        if (!isTourActive || !currentStep || isNavigating) return;

        const element = document.getElementById(currentStep.targetId);
        if (!element) {
            // Target element not found yet, retry or hide spotlight and show centered tooltip
            setCoords(null);
            return;
        }

        const rect = element.getBoundingClientRect();
        setCoords({
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height
        });
    };

    // Listen to resize/scroll events to keep spotlight aligned
    useEffect(() => {
        if (!isTourActive) return;

        window.addEventListener('resize', updateSpotlight);
        window.addEventListener('scroll', updateSpotlight, true);

        return () => {
            window.removeEventListener('resize', updateSpotlight);
            window.removeEventListener('scroll', updateSpotlight, true);
        };
    }, [isTourActive, tourStepIndex, isNavigating]);

    // Update spotlight when the page changes or when navigating stops
    useEffect(() => {
        if (isTourActive && !isNavigating) {
            // Retry a few times in case elements render asynchronously
            const intervals = [100, 500, 1000, 2000].map(delay => 
                setTimeout(updateSpotlight, delay)
            );
            return () => intervals.forEach(clearTimeout);
        }
    }, [isTourActive, isNavigating, tourStepIndex]);

    // Position the tooltip card based on the target element coordinates and window size
    useEffect(() => {
        if (!isTourActive) return;

        if (isNavigating || !coords) {
            // Center the tooltip on screen when navigating or when element is not found
            setTooltipStyle({
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '380px',
                maxWidth: '90vw',
            });
            return;
        }

        const tooltipWidth = tooltipRef.current?.offsetWidth || 380;
        const tooltipHeight = tooltipRef.current?.offsetHeight || 180;
        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;

        // Mobile fallback: position fixed at the bottom
        if (screenWidth < 768) {
            setTooltipStyle({
                position: 'fixed',
                bottom: '16px',
                left: '16px',
                right: '16px',
                margin: '0 auto',
                width: 'auto',
                maxWidth: 'calc(100vw - 32px)',
            });
            return;
        }

        let top = 0;
        let left = 0;

        // Calculate placement based on element rect and placement configuration
        if (currentStep.placement === 'right') {
            left = coords.left + coords.width + 16;
            top = coords.top + (coords.height - tooltipHeight) / 2;

            // Prevent clipping on right boundary
            if (left + tooltipWidth > screenWidth) {
                left = coords.left - tooltipWidth - 16; // Try left
                if (left < 0) { // Center as fallback
                    left = (screenWidth - tooltipWidth) / 2;
                    top = coords.top + coords.height + 16;
                }
            }
        } else if (currentStep.placement === 'bottom') {
            left = coords.left + (coords.width - tooltipWidth) / 2;
            top = coords.top + coords.height + 16;
        } else if (currentStep.placement === 'left') {
            left = coords.left - tooltipWidth - 16;
            top = coords.top + (coords.height - tooltipHeight) / 2;
        } else { // top
            left = coords.left + (coords.width - tooltipWidth) / 2;
            top = coords.top - tooltipHeight - 16;
        }

        // Prevent clipping vertically
        if (top < 16) top = 16;
        if (top + tooltipHeight > screenHeight) top = screenHeight - tooltipHeight - 16;
        if (left < 16) left = 16;
        if (left + tooltipWidth > screenWidth) left = screenWidth - tooltipWidth - 16;

        setTooltipStyle({
            position: 'fixed',
            top: `${top}px`,
            left: `${left}px`,
            width: `${tooltipWidth}px`,
            transform: 'none',
        });
    }, [isTourActive, coords, isNavigating, tourStepIndex]);

    if (!isTourActive) return null;

    const handleNext = () => {
        if (tourStepIndex < TOUR_STEPS.length - 1) {
            nextTourStep();
        } else {
            finishTour();
        }
    };

    const handleBack = () => {
        if (tourStepIndex > 0) {
            prevTourStep();
        }
    };

    const progressPercentage = ((tourStepIndex + 1) / TOUR_STEPS.length) * 100;

    return (
        <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
            {/* Screen masking layer */}
            <div className="absolute inset-0 bg-black/40 pointer-events-auto transition-opacity duration-300" onClick={finishTour} />

            {/* Spotlight cut-out ring */}
            {coords && !isNavigating && (
                <div
                    className="absolute z-50 rounded-xl border-2 border-primary ring-[4px] ring-primary/45 shadow-[0_0_0_9999px_rgba(15,15,25,0.65)] transition-all duration-300 pointer-events-none ease-out"
                    style={{
                        top: `${coords.top - 6}px`,
                        left: `${coords.left - 6}px`,
                        width: `${coords.width + 12}px`,
                        height: `${coords.height + 12}px`,
                    }}
                />
            )}

            {/* Tooltip Card container */}
            <div 
                ref={tooltipRef}
                style={tooltipStyle}
                className="absolute z-[10000] pointer-events-auto transition-all duration-300 ease-out"
            >
                <Card className="p-5 border-none shadow-2xl bg-card rounded-2xl relative overflow-hidden">
                    {/* Tiny visual accent bar */}
                    <div 
                        className="absolute top-0 left-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-300"
                        style={{ width: `${progressPercentage}%` }}
                    />
                    
                    <button 
                        onClick={finishTour}
                        className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors p-1 hover:bg-muted/80 rounded-full"
                    >
                        <X className="h-4 w-4" />
                    </button>

                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                                {t('common.step')} {tourStepIndex + 1} / {TOUR_STEPS.length}
                            </span>
                            {isNavigating && (
                                <span className="text-[11px] text-indigo-500 animate-pulse font-medium">
                                    Navegando...
                                </span>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <h4 className="font-bold text-foreground text-base">
                                {t(currentStep.titleKey)}
                            </h4>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                {t(currentStep.descKey)}
                            </p>
                        </div>

                        <div className="flex items-center justify-between pt-2">
                            <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={finishTour}
                                className="text-xs text-muted-foreground hover:text-foreground"
                            >
                                {t('onboarding.tour.skip')}
                            </Button>

                            <div className="flex items-center gap-2">
                                <Button 
                                    variant="outline" 
                                    size="sm" 
                                    disabled={tourStepIndex === 0}
                                    onClick={handleBack}
                                    className="h-8 px-2 text-xs"
                                >
                                    <ChevronLeft className="h-4.5 w-4.5" />
                                    {t('onboarding.tour.back')}
                                </Button>
                                <Button 
                                    size="sm" 
                                    onClick={handleNext}
                                    className="h-8 px-3 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
                                >
                                    {tourStepIndex === TOUR_STEPS.length - 1 ? (
                                        <>
                                            {t('onboarding.tour.finish')}
                                            <Check className="h-3.5 w-3.5 ml-1" />
                                        </>
                                    ) : (
                                        <>
                                            {t('onboarding.tour.next')}
                                            <ChevronRight className="h-3.5 w-3.5 ml-1" />
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
