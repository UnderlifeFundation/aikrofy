'use client';

import { useTranslation } from 'react-i18next';
import { Flame, ShieldCheck } from 'lucide-react';
import { CreditPurchaseSection } from '@/components/features/billing/CreditPurchaseSection';

export default function SubscribePage() {
    const { t } = useTranslation();

    return (
        <div className="mx-auto max-w-6xl space-y-6 animate-fade-in pb-12">
            {/* Dashboard Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900/60 border border-indigo-500/20 shadow-md">
                <div>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20 mb-2">
                        <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                        <span>{t('credits.fuelStation', { defaultValue: 'Estación de Combustible IA Prepago' })}</span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground">
                        {t('sidebar.billingCredits', { defaultValue: 'Combustible IA & Créditos' })}
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
                        {t('credits.fuelSubtitle', { defaultValue: 'Recarga créditos corporativos para tus agentes autónomos de WhatsApp, llamadas de voz ultra-realistas, RAG y automatizaciones sin suscripción mensual fija.' })}
                    </p>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3.5 py-2 rounded-xl shrink-0">
                    <ShieldCheck className="w-4 h-4" />
                    <span>Facturación B2B 1-Click</span>
                </div>
            </div>

            {/* Main Interactive Credit Purchase / Fuel Tool */}
            <CreditPurchaseSection />
        </div>
    );
}
