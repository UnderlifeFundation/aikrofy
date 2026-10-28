'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Sparkles, ShieldCheck, Zap, Heart, Award, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { useOnboardingStore } from '@/store/use-onboarding-store';

export default function ActivateTrialPage() {
    const router = useRouter();
    const queryClient = useQueryClient();

    const activateMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/companies/activate-trial');
            return data;
        },
        onSuccess: async () => {
            toast.success('¡Prueba gratuita activada con éxito! Bienvenido a Aikrofy.');
            // Reset onboarding state so they see the welcome modal and tour on dashboard
            useOnboardingStore.getState().reset();
            // Invalidate 'me' query to sync settings immediately
            await queryClient.invalidateQueries({ queryKey: ['me'] });
            router.push('/dashboard');
        },
        onError: (error: any) => {
            const message = error?.response?.data?.error || 'No se pudo activar la prueba. Inténtalo más tarde.';
            toast.error(message);
        }
    });

    return (
        <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
            <Card className="w-full max-w-2xl overflow-hidden shadow-2xl border-primary/20 bg-background/60 backdrop-blur-md">
                {/* Visual Header Banner */}
                <div className="relative h-48 w-full bg-gradient-to-br from-primary via-primary/80 to-secondary flex flex-col items-center justify-center text-white p-6 text-center">
                    <div className="absolute top-4 right-4 bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-semibold tracking-wider uppercase">
                        Fase Beta Privada
                    </div>
                    <Sparkles className="h-12 w-12 text-white mb-2 animate-pulse" />
                    <h1 className="text-3xl font-extrabold tracking-tight">Aikrofy</h1>
                    <p className="text-sm opacity-90 mt-1 font-medium">Fuerza Laboral Inteligente 360° para tu Negocio</p>
                </div>

                <CardHeader className="text-center pt-8">
                    <CardTitle className="text-2xl font-bold">¡Bienvenido a la Era de los Agentes Autónomos!</CardTitle>
                    <CardDescription className="text-sm max-w-lg mx-auto mt-2 leading-relaxed">
                        Estamos en una fase de pruebas limitada. Brindamos acceso gratuito temporal a empresas seleccionadas que deseen automatizar ventas, agenda y soporte, y darnos su opinión sobre el sistema.
                    </CardDescription>
                </CardHeader>

                <CardContent className="space-y-6 px-8 py-4">
                    {/* Benefits Grid */}
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="flex gap-3 items-start p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/20 transition-all duration-300">
                            <ShieldCheck className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-semibold text-sm">Sin Tarjetas de Crédito</h3>
                                <p className="text-xs text-muted-foreground mt-0.5">Habilita la prueba sin ingresar ningún dato bancario o de pago.</p>
                            </div>
                        </div>

                        <div className="flex gap-3 items-start p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/20 transition-all duration-300">
                            <Heart className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-semibold text-sm">24 Horas de Acceso Total</h3>
                                <p className="text-xs text-muted-foreground mt-0.5">Prueba todas las funcionalidades de voz, RAG, y agentes ilimitados.</p>
                            </div>
                        </div>

                        <div className="flex gap-3 items-start p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/20 transition-all duration-300">
                            <Zap className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-semibold text-sm">Integraciones Activas</h3>
                                <p className="text-xs text-muted-foreground mt-0.5">Conecta WhatsApp, CRM y pasarelas de pago al instante.</p>
                            </div>
                        </div>

                        <div className="flex gap-3 items-start p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/20 transition-all duration-300">
                            <Award className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-semibold text-sm">Fase Beta Exclusiva</h3>
                                <p className="text-xs text-muted-foreground mt-0.5">Únete al grupo pionero de optimización de procesos de negocio con IA.</p>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-lg bg-primary/10 p-4 border border-primary/20 text-center text-sm text-primary font-medium">
                        Tu única contribución es darnos retroalimentación al finalizar tu prueba para seguir perfeccionando Aikrofy.
                    </div>
                </CardContent>

                <CardFooter className="flex flex-col gap-3 px-8 pb-8">
                    <Button 
                        size="lg" 
                        className="w-full text-md font-semibold py-6 shadow-lg shadow-primary/20 hover:scale-[1.01] active:scale-[0.99] transition-all duration-300"
                        onClick={() => activateMutation.mutate()}
                        disabled={activateMutation.isPending}
                    >
                        {activateMutation.isPending ? 'Activando...' : 'Habilitar prueba gratuita de 24 horas'}
                        <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
