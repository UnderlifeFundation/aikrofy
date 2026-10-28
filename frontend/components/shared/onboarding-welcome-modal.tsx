'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, Play, Compass, X } from 'lucide-react';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useAuthStore } from '@/store/use-auth-store';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export function OnboardingWelcomeModal() {
    const { t } = useTranslation();
    const { hasSeenWelcome, setHasSeenWelcome, startTour } = useOnboardingStore();
    const { user } = useAuthStore();
    const [open, setOpen] = useState(false);

    const isOlderThan2Days = user?.created_at 
        ? (Date.now() - new Date(user.created_at).getTime() > 2 * 24 * 60 * 60 * 1000) 
        : false;

    const WELCOME_KEY = `aikrofy_welcome_seen_${user?.id || 'guest'}`;

    useEffect(() => {
        if (!user?.is_company_owner) {
            setHasSeenWelcome(true);
            return;
        }
        if (isOlderThan2Days) {
            setHasSeenWelcome(true);
            return;
        }
        const locallySeen = typeof window !== 'undefined' ? localStorage.getItem(WELCOME_KEY) : null;
        if (locallySeen || hasSeenWelcome) {
            setHasSeenWelcome(true);
            return;
        }

        // Show welcome modal if the user has not seen it yet
        const timer = setTimeout(() => {
            setOpen(true);
        }, 1200);
        return () => clearTimeout(timer);
    }, [hasSeenWelcome, isOlderThan2Days, user?.is_company_owner, user?.id, setHasSeenWelcome, WELCOME_KEY]);

    if (!user?.is_company_owner) return null;

    const handleStartTour = () => {
        setOpen(false);
        setHasSeenWelcome(true);
        if (typeof window !== 'undefined') {
            localStorage.setItem(WELCOME_KEY, 'true');
        }
        // Start tour after a brief delay to let modal closing transition finish
        setTimeout(() => {
            startTour(0);
        }, 300);
    };

    const handleDismiss = () => {
        setOpen(false);
        setHasSeenWelcome(true);
        if (typeof window !== 'undefined') {
            localStorage.setItem(WELCOME_KEY, 'true');
        }
    };

    return (
        <Dialog open={open} onOpenChange={(isOpen) => {
            if (!isOpen) handleDismiss();
        }}>
            <DialogContent showCloseButton={false} className="sm:max-w-[500px] p-0 overflow-hidden border-none bg-card shadow-2xl rounded-2xl">
                {/* Visual Header with Premium Gradient */}
                <div className="relative overflow-hidden p-8 text-white h-48 flex flex-col justify-end bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500">
                    <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
                    <div className="absolute -left-10 -bottom-10 h-32 w-32 rounded-full bg-pink-400/20 blur-2xl" />
                    
                    <button 
                        onClick={handleDismiss} 
                        className="absolute right-4 top-4 rounded-full p-1.5 bg-black/10 hover:bg-black/20 text-white/80 hover:text-white transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>

                    <div className="relative z-10 flex items-center gap-3">
                        <div className="bg-white/20 p-2.5 rounded-xl border border-white/20 backdrop-blur-md shadow-inner">
                            <Bot className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-200">Aikrofy Platform</span>
                            <h2 className="text-2xl font-extrabold leading-tight text-white mt-0.5">
                                {t('onboarding.welcomeTitle')}
                            </h2>
                        </div>
                    </div>
                </div>

                {/* Content Area */}
                <div className="p-6 space-y-6">
                    <div className="space-y-2">
                        <h3 className="text-lg font-bold text-foreground">
                            {t('onboarding.welcomeSubtitle')}
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                            {t('onboarding.welcomeDesc')}
                        </p>
                    </div>

                    {/* Features overview */}
                    <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="flex gap-2.5 p-3 rounded-xl border bg-muted/30">
                            <span className="text-lg">🤖</span>
                            <div>
                                <h4 className="font-semibold text-foreground">Configura Chefs</h4>
                                <p className="text-muted-foreground mt-0.5">Habilita herramientas con checkboxes.</p>
                            </div>
                        </div>
                        <div className="flex gap-2.5 p-3 rounded-xl border bg-muted/30">
                            <span className="text-lg">💬</span>
                            <div>
                                <h4 className="font-semibold text-foreground">Integra Canales</h4>
                                <p className="text-muted-foreground mt-0.5">WhatsApp y Telegram con un QR.</p>
                            </div>
                        </div>
                        <div className="flex gap-2.5 p-3 rounded-xl border bg-muted/30">
                            <span className="text-lg">📚</span>
                            <div>
                                <h4 className="font-semibold text-foreground">Memoria Vectorial</h4>
                                <p className="text-muted-foreground mt-0.5">Sube PDFs para respuestas RAG.</p>
                            </div>
                        </div>
                        <div className="flex gap-2.5 p-3 rounded-xl border bg-muted/30">
                            <span className="text-lg">💳</span>
                            <div>
                                <h4 className="font-semibold text-foreground">CRM & Pagos</h4>
                                <p className="text-muted-foreground mt-0.5">Ventas y cobros automatizados.</p>
                            </div>
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="flex flex-col sm:flex-row gap-3 pt-2">
                        <Button 
                            onClick={handleStartTour} 
                            className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold shadow-md shadow-indigo-500/10 h-11 rounded-xl transition-all duration-300 hover:scale-[1.02]"
                        >
                            <Play className="h-4 w-4 mr-2" />
                            {t('onboarding.startTour')}
                        </Button>
                        <Button 
                            onClick={handleDismiss} 
                            variant="outline" 
                            className="flex-1 border-border/80 hover:bg-muted/50 h-11 rounded-xl"
                        >
                            <Compass className="h-4 w-4 mr-2 text-muted-foreground" />
                            {t('onboarding.exploreOnOwn')}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
