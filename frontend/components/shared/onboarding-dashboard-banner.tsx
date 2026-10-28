'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, Sparkles, ArrowRight, Play, X, Check } from 'lucide-react';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useAuthStore } from '@/store/use-auth-store';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export function OnboardingDashboardBanner() {
    const { t } = useTranslation();
    const { user } = useAuthStore();
    const { completedSteps, startTour } = useOnboardingStore();
    const [dismissed, setDismissed] = useState(false);
    
    // Check local storage for banner dismissal state
    useEffect(() => {
        const value = localStorage.getItem('pymai-onboarding-banner-dismissed');
        if (value === 'true') {
            setDismissed(true);
        }
    }, []);

    const handleDismiss = () => {
        localStorage.setItem('pymai-onboarding-banner-dismissed', 'true');
        setDismissed(true);
    };

    if (!user?.is_company_owner || dismissed) return null;

    const totalSteps = 5;
    const completedCount = ['agents', 'channels', 'documents', 'chat', 'integrations'].filter(
        step => completedSteps.includes(step)
    ).length;
    const progressPercent = Math.round((completedCount / totalSteps) * 100);
    const isFinished = completedCount === totalSteps;

    return (
        <Card className="hidden md:block relative overflow-hidden border-none rounded-2xl bg-gradient-to-r from-indigo-950 via-purple-950 to-indigo-900 text-white p-6 shadow-xl transition-all duration-300">
            {/* Background elements */}
            <div className="absolute right-0 top-0 w-80 h-full opacity-20 pointer-events-none bg-[radial-gradient(circle_at_top_right,rgba(139,92,246,0.5),transparent_70%)]" />
            <div className="absolute left-1/3 -bottom-10 w-60 h-40 opacity-10 pointer-events-none bg-pink-500 rounded-full blur-3xl" />
            
            <button 
                onClick={handleDismiss}
                className="absolute right-4 top-4 p-1 rounded-full text-white/50 hover:text-white hover:bg-white/10 transition-colors"
            >
                <X className="h-4 w-4" />
            </button>

            <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                {/* Greeting & Info */}
                <div className="space-y-3 max-w-xl">
                    <div className="flex items-center gap-2">
                        <span className="flex h-6 items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-pink-300 bg-pink-500/10 px-2 py-0.5 rounded-full border border-pink-500/20">
                            <Sparkles className="h-3 w-3 text-pink-400" />
                            Guía de Activación
                        </span>
                        <span className="text-xs text-white/70">
                            {completedCount} de {totalSteps} tareas listas
                        </span>
                    </div>

                    <div className="space-y-1">
                        <h3 className="text-xl font-bold tracking-tight md:text-2xl">
                            {isFinished 
                                ? '¡Excelente! Tu Asistente de IA está totalmente configurado' 
                                : 'Activa tu Asistente Digital en pocos minutos'
                            }
                        </h3>
                        <p className="text-sm text-white/80 leading-relaxed">
                            {isFinished 
                                ? 'Has habilitado las capacidades de agentes, canales de comunicación y base de conocimientos. Tu negocio ya opera con IA 360°.'
                                : 'Completa los pasos básicos de configuración para habilitar la atención al cliente, agendamientos automatizados y pagos conversacionales en tiempo real.'
                            }
                        </p>
                    </div>

                    {!isFinished && (
                        <div className="flex flex-wrap gap-2 pt-1 text-xs">
                            <Link href="/agents" className="flex items-center gap-1 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors text-white">
                                {completedSteps.includes('agents') ? <Check className="h-3 w-3 text-green-400" /> : <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                                Configurar Chef
                            </Link>
                            <Link href="/channels" className="flex items-center gap-1 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors text-white">
                                {completedSteps.includes('channels') ? <Check className="h-3 w-3 text-green-400" /> : <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                                Conectar WhatsApp
                            </Link>
                            <Link href="/documents" className="flex items-center gap-1 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors text-white">
                                {completedSteps.includes('documents') ? <Check className="h-3 w-3 text-green-400" /> : <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                                Subir PDFs
                            </Link>
                        </div>
                    )}
                </div>

                {/* Progress Circle & Actions */}
                <div className="flex flex-row md:flex-col items-center gap-4 w-full md:w-auto shrink-0 border-t md:border-t-0 border-white/10 pt-4 md:pt-0">
                    <div className="flex items-center gap-4">
                        {/* Radial Progress */}
                        <div className="relative h-16 w-16 flex items-center justify-center">
                            <svg className="absolute w-full h-full transform -rotate-90">
                                <circle 
                                    cx="32" 
                                    cy="32" 
                                    r="28" 
                                    stroke="rgba(255,255,255,0.08)" 
                                    strokeWidth="5" 
                                    fill="transparent" 
                                />
                                <circle 
                                    cx="32" 
                                    cy="32" 
                                    r="28" 
                                    stroke="url(#gradient)" 
                                    strokeWidth="5" 
                                    fill="transparent" 
                                    strokeDasharray={`${2 * Math.PI * 28}`}
                                    strokeDashoffset={`${2 * Math.PI * 28 * (1 - progressPercent / 100)}`}
                                    className="transition-all duration-500 ease-out"
                                />
                                <defs>
                                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor="#8b5cf6" />
                                        <stop offset="100%" stopColor="#ec4899" />
                                    </linearGradient>
                                </defs>
                            </svg>
                            <span className="text-sm font-bold">{progressPercent}%</span>
                        </div>

                        <div>
                            <div className="text-xs text-white/60">Estado</div>
                            <div className="text-sm font-bold">
                                {isFinished ? '100% Configurado' : 'Configuración Pendiente'}
                            </div>
                        </div>
                    </div>

                    {!isFinished && (
                        <Button 
                            onClick={() => startTour(0)}
                            className="w-full md:w-auto bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 border-none text-white text-xs font-semibold shadow-lg shadow-indigo-500/10 px-4 h-9 rounded-lg"
                        >
                            <Play className="h-3 w-3 mr-1.5" />
                            Comenzar Tour
                            <ArrowRight className="h-3.5 w-3.5 ml-1" />
                        </Button>
                    )}
                </div>
            </div>
        </Card>
    );
}
