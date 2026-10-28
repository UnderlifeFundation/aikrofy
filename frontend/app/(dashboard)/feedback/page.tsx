'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Star, MessageSquareCode, Send, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { cn } from '@/lib/utils';

export default function FeedbackPage() {
    const router = useRouter();
    const queryClient = useQueryClient();

    const [step, setStep] = useState<number>(1);
    const [rating, setRating] = useState<number>(0);
    const [hoverRating, setHoverRating] = useState<number>(0);
    const [q1, setQ1] = useState<string>('');
    const [q2, setQ2] = useState<string>('');
    const [q3, setQ3] = useState<string>('');
    const [comments, setComments] = useState<string>('');

    const feedbackMutation = useMutation({
        mutationFn: async (payload: any) => {
            const { data } = await apiClient.post('/companies/submit-feedback', payload);
            return data;
        },
        onSuccess: () => {
            toast.success('¡Muchas gracias por tu retroalimentación! Redirigiendo a planes de suscripción...');
            queryClient.invalidateQueries({ queryKey: ['me'] });
            router.push('/subscribe');
        },
        onError: (error: any) => {
            const message = error?.response?.data?.error || 'Ocurrió un error al enviar el feedback. Inténtalo de nuevo.';
            toast.error(message);
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (rating === 0) {
            toast.warning('Por favor, selecciona una calificación de estrellas.');
            setStep(1);
            return;
        }
        if (!q1 || !q2 || !q3) {
            toast.warning('Por favor, responde a todas las preguntas de usabilidad.');
            setStep(2);
            return;
        }

        feedbackMutation.mutate({
            rating,
            answers: {
                usability_ease: q1,
                most_useful_tool: q2,
                business_impact: q3
            },
            comments
        });
    };

    const nextStep = () => {
        if (step === 1 && rating === 0) {
            toast.warning('Por favor, selecciona una calificación antes de continuar.');
            return;
        }
        if (step === 2 && (!q1 || !q2 || !q3)) {
            toast.warning('Por favor, responde a las 3 preguntas antes de continuar.');
            return;
        }
        setStep((prev) => prev + 1);
    };

    const prevStep = () => {
        setStep((prev) => prev - 1);
    };

    const steps = [
        { id: 1, label: 'Experiencia', icon: Star },
        { id: 2, label: 'Preguntas', icon: MessageSquareCode },
        { id: 3, label: 'Sugerencias', icon: Sparkles }
    ];

    const isStep2Complete = q1.trim().length > 0 && q2.trim().length > 0 && q3.trim().length > 0;

    return (
        <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
            <Card className="w-full max-w-2xl shadow-2xl border-primary/20 bg-background/60 backdrop-blur-md overflow-hidden">
                <div className="h-2 w-full bg-muted">
                    <div 
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${(step / 3) * 100}%` }}
                    />
                </div>

                <CardHeader className="text-center pt-8 pb-4">
                    <CardTitle className="text-2xl font-bold flex items-center justify-center gap-2">
                        <MessageSquareCode className="h-6 w-6 text-primary" />
                        Retroalimentación de la Fase Beta
                    </CardTitle>
                    <CardDescription className="text-sm max-w-md mx-auto mt-1">
                        Tu opinión es indispensable para pulir los detalles de Aikrofy antes del lanzamiento comercial. Ayúdanos respondiendo estas breves preguntas.
                    </CardDescription>
                </CardHeader>

                <div className="flex justify-center gap-8 mb-6 px-8">
                    {steps.map((s) => {
                        const Icon = s.icon;
                        const active = step === s.id;
                        const completed = step > s.id;
                        return (
                            <div key={s.id} className="flex flex-col items-center gap-1.5">
                                <div className={cn(
                                    "h-10 w-10 rounded-full flex items-center justify-center border transition-all duration-300",
                                    active && "border-primary bg-primary/10 text-primary scale-110",
                                    completed && "border-primary bg-primary text-primary-foreground",
                                    !active && !completed && "border-muted text-muted-foreground"
                                )}>
                                    <Icon className="h-5 w-5" />
                                </div>
                                <span className={cn(
                                    "text-xs font-semibold tracking-wide",
                                    active ? "text-primary" : "text-muted-foreground"
                                )}>{s.label}</span>
                            </div>
                        );
                    })}
                </div>

                <form onSubmit={handleSubmit}>
                    <CardContent className="px-8 py-4 min-h-[220px]">
                        {step === 1 && (
                            <div className="space-y-6 flex flex-col items-center py-4">
                                <Label className="text-base text-center">¿Cómo calificarías tu experiencia general con Aikrofy?</Label>
                                <div className="flex gap-2">
                                    {[1, 2, 3, 4, 5].map((star) => (
                                        <button
                                            key={star}
                                            type="button"
                                            className="transition-transform duration-150 hover:scale-125 focus:outline-none"
                                            onClick={() => setRating(star)}
                                            onMouseEnter={() => setHoverRating(star)}
                                            onMouseLeave={() => setHoverRating(0)}
                                        >
                                            <Star className={cn(
                                                "h-10 w-10 transition-colors duration-200",
                                                (hoverRating || rating) >= star 
                                                    ? "fill-primary text-primary" 
                                                    : "text-muted"
                                            )} />
                                        </button>
                                    ))}
                                </div>
                                {rating > 0 && (
                                    <p className="text-sm font-semibold text-primary">
                                        Calificación seleccionada: {rating} de 5 estrellas
                                    </p>
                                )}
                            </div>
                        )}

                        {step === 2 && (
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="q1" className="text-sm font-medium">1. ¿Qué tan amigable e intuitivo te pareció configurar tus agentes?</Label>
                                    <Textarea
                                        id="q1"
                                        placeholder="Ej: Fue sencillo, aunque los menús de integraciones de CRM tienen demasiadas opciones..."
                                        value={q1}
                                        onChange={(e) => setQ1(e.target.value)}
                                        className="h-20"
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="q2" className="text-sm font-medium">2. ¿Cuál consideras que es la habilidad (skill) o herramienta de agente más valiosa?</Label>
                                    <Textarea
                                        id="q2"
                                        placeholder="Ej: La integración con WhatsApp y la habilidad de pagos automáticos..."
                                        value={q2}
                                        onChange={(e) => setQ2(e.target.value)}
                                        className="h-20"
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="q3" className="text-sm font-medium">3. ¿Qué impacto estimas que tendrá Aikrofy en la eficiencia de tu negocio?</Label>
                                    <Textarea
                                        id="q3"
                                        placeholder="Ej: Ahorraremos unas 4 horas diarias en atención a clientes recurrentes..."
                                        value={q3}
                                        onChange={(e) => setQ3(e.target.value)}
                                        className="h-20"
                                        required
                                    />
                                </div>
                            </div>
                        )}

                        {step === 3 && (
                            <div className="space-y-4 py-2">
                                <div className="space-y-2">
                                    <Label htmlFor="comments" className="text-base">¿Tienes sugerencias adicionales, comentarios de rendimiento o críticas constructivas?</Label>
                                    <Textarea
                                        id="comments"
                                        placeholder="Ej: Nos encantaría ver soporte oficial para llamadas en tiempo real de LiveKit a bajo costo, y mejores visualizaciones en los gráficos del dashboard."
                                        value={comments}
                                        onChange={(e) => setComments(e.target.value)}
                                        className="h-32"
                                    />
                                </div>
                                <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg text-xs text-primary font-medium">
                                    Al presionar enviar, guardaremos tus respuestas de forma confidencial para retroalimentación del equipo de desarrollo, y habilitaremos tu redirección para seleccionar tu plan definitivo de suscripción.
                                </div>
                            </div>
                        )}
                    </CardContent>

                    <CardFooter className="px-8 pb-8 flex justify-between gap-4 pt-4 border-t border-white/5">
                        {step > 1 ? (
                            <Button 
                                type="button" 
                                variant="outline" 
                                onClick={prevStep}
                                disabled={feedbackMutation.isPending}
                            >
                                <ChevronLeft className="mr-2 h-4 w-4" />
                                Atrás
                            </Button>
                        ) : (
                            <div />
                        )}

                        {step < 3 ? (
                            <Button 
                                type="button" 
                                onClick={nextStep}
                            >
                                Siguiente
                                <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        ) : (
                            <Button 
                                type="submit" 
                                disabled={feedbackMutation.isPending || !isStep2Complete}
                                className="shadow-lg shadow-primary/20 hover:scale-[1.01] active:scale-[0.99] transition-all duration-300"
                            >
                                {feedbackMutation.isPending ? 'Enviando...' : 'Enviar Retroalimentación'}
                                <Send className="ml-2 h-4 w-4" />
                            </Button>
                        )}
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
