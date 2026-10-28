'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { RotateCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function ErrorBoundary({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Unhandled Next.js Application Error:', error);

        // Auto-recover from stale chunks or server action mismatches after deployments
        const msg = error?.message || '';
        if (
            msg.includes('Failed to find Server Action') ||
            msg.includes('ChunkLoadError') ||
            msg.includes('Loading chunk')
        ) {
            const lastReload = sessionStorage.getItem('aikrofy_last_action_reload');
            const now = Date.now();
            if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
                sessionStorage.setItem('aikrofy_last_action_reload', now.toString());
                window.location.reload();
            }
        }
    }, [error]);

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background text-foreground">
            <div className="w-full max-w-md p-8 rounded-3xl border border-border/80 bg-card shadow-2xl text-center space-y-6">
                <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                    <RotateCw className="w-8 h-8 animate-spin-slow" />
                </div>

                <div className="space-y-2">
                    <h2 className="text-2xl font-bold tracking-tight">Ocurrió un problema temporal</h2>
                    <p className="text-sm text-muted-foreground">
                        La plataforma ha recibido una actualización. Puedes recargar para continuar con la versión más reciente.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                    <Button
                        onClick={() => {
                            if (typeof window !== 'undefined') window.location.reload();
                            else reset();
                        }}
                        className="flex-1 bg-primary text-primary-foreground font-semibold rounded-xl h-11"
                    >
                        <RotateCw className="w-4 h-4 mr-2" />
                        Recargar Página
                    </Button>
                    <Link href="/" className="flex-1">
                        <Button variant="outline" className="w-full rounded-xl h-11 border-border/80">
                            <Home className="w-4 h-4 mr-2" />
                            Inicio
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
}
