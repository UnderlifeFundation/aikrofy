'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    ShieldAlert,
    Key,
    CheckCircle2,
    ExternalLink,
    Loader2,
    Server,
    HeartHandshake,
    Sparkles,
    ArrowRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

export default function CommunityActivationPage() {
    const [token, setToken] = useState('');
    const [isActivating, setIsActivating] = useState(false);
    const [isChecking, setIsChecking] = useState(true);
    const [statusData, setStatusData] = useState<any>(null);

    useEffect(() => {
        apiClient
            .get('/community/status')
            .then((res) => {
                setStatusData(res.data);
                if (res.data?.is_activated && !res.data?.is_community) {
                    // Running on cloud, go to dashboard
                    window.location.href = '/dashboard';
                }
            })
            .catch(() => {
                // Keep activation form
            })
            .finally(() => {
                setIsChecking(false);
            });
    }, []);

    const handleActivate = async (e: React.FormEvent) => {
        e.preventDefault();
        const clean = token.trim();
        if (!clean) {
            toast.error('Por favor ingresa tu Token de Activación Oficial');
            return;
        }
        setIsActivating(true);
        try {
            const res = await apiClient.post('/community/activate', { token: clean });
            if (res.data?.is_activated) {
                toast.success('¡Instancia activada con éxito! Redirigiendo...');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            }
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Token inválido o no reconocido');
        } finally {
            setIsActivating(false);
        }
    };

    if (isChecking) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-100">
                <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
            </div>
        );
    }

    if (statusData?.is_activated) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
                <Card className="max-w-md w-full border-emerald-500/40 bg-slate-900 text-slate-100 text-center">
                    <CardHeader className="pb-3">
                        <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto" />
                        <CardTitle className="text-xl font-bold mt-2 text-white">
                            Instancia Oficial Activada
                        </CardTitle>
                        <CardDescription className="text-xs text-slate-300">
                            {statusData.message}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-2">
                        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-left font-mono text-slate-300">
                            <div><strong>Organización:</strong> {statusData.payload?.org || 'Comunidad'}</div>
                            <div><strong>Responsable:</strong> {statusData.payload?.name || statusData.payload?.email}</div>
                            <div><strong>Edición:</strong> Community Open-Core</div>
                        </div>
                        <Link href="/dashboard" className="block">
                            <Button className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold">
                                Ir al Panel Principal
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-cyan-500/30">
            {/* Header */}
            <div className="border-b border-cyan-500/20 bg-slate-900/60 p-4">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-lg bg-cyan-500 text-slate-950 flex items-center justify-center font-bold">
                            A
                        </div>
                        <span className="font-bold text-white tracking-tight">Aikrofy Community Edition</span>
                    </div>
                    <a
                        href="https://aikrofy.com/community#self-hosted-activation"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
                    >
                        Obtener Token Oficial Gratis
                        <ExternalLink className="h-3 w-3" />
                    </a>
                </div>
            </div>

            {/* Main Center Card */}
            <div className="p-4 flex items-center justify-center my-8">
                <Card className="max-w-lg w-full border-cyan-500/40 bg-slate-900/90 shadow-2xl">
                    <CardHeader className="text-center space-y-2 border-b border-slate-800 pb-5">
                        <div className="h-12 w-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400">
                            <Key className="h-6 w-6" />
                        </div>
                        <CardTitle className="text-2xl font-extrabold text-white">
                            Activa tu Instancia Auto-Hospedada
                        </CardTitle>
                        <CardDescription className="text-xs text-slate-300 max-w-sm mx-auto">
                            Para garantizar la soberanía operativa y la integridad del software, las instancias auto-hospedadas de Aikrofy requieren un <strong>Token de Activación Oficial gratuito</strong> emitido por Fundación Underlife para desbloquear la plataforma.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 space-y-6">
                        <form onSubmit={handleActivate} className="space-y-4">
                            <div className="space-y-1.5">
                                <Label className="text-xs text-slate-200">
                                    Pega tu Token de Activación (<code className="text-cyan-300">AIK-COMM-...</code>) *
                                </Label>
                                <Input
                                    value={token}
                                    onChange={(e) => setToken(e.target.value)}
                                    placeholder="AIK-COMM-eyJhbGciOi..."
                                    className="bg-slate-950 border-slate-700 text-cyan-300 font-mono text-xs h-12"
                                    required
                                    autoFocus
                                />
                            </div>

                            <Button
                                type="submit"
                                disabled={isActivating || !token.trim()}
                                className="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold h-11 text-sm gap-2 cursor-pointer"
                            >
                                {isActivating ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Validando y Desbloqueando...
                                    </>
                                ) : (
                                    <>
                                        <CheckCircle2 className="h-4 w-4" />
                                        Desbloquear Instancia Ahora
                                    </>
                                )}
                            </Button>
                        </form>

                        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2.5 text-xs text-slate-300">
                            <div className="font-semibold text-white flex items-center gap-1.5">
                                <Sparkles className="h-4 w-4 text-emerald-400" />
                                ¿Aún no tienes tu Token de Activación?
                            </div>
                            <p className="leading-relaxed text-slate-400">
                                Es 100% gratuito. Solo debes registrar tu correo en la página oficial para recibir tu token al instante y postular si deseas créditos subvencionados.
                            </p>
                            <div className="pt-1 flex flex-wrap gap-2">
                                <a
                                    href="https://aikrofy.com/community#self-hosted-activation"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 underline"
                                >
                                    Generar mi Token Oficial en aikrofy.com
                                    <ExternalLink className="h-3 w-3" />
                                </a>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Footer */}
            <div className="border-t border-slate-800 p-4 text-center text-xs text-slate-500">
                FUNDACIÓN UNDERLIFE & WEBLIFETECH · Plataforma Aikrofy Community Edition
            </div>
        </div>
    );
}
