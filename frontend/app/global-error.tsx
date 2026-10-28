'use client';

import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Global Application Error:', error);
        const msg = error?.message || '';
        if (
            msg.includes('Failed to find Server Action') ||
            msg.includes('ChunkLoadError') ||
            msg.includes('Loading chunk')
        ) {
            const lastReload = sessionStorage.getItem('aikrofy_global_reload');
            const now = Date.now();
            if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
                sessionStorage.setItem('aikrofy_global_reload', now.toString());
                window.location.reload();
            }
        }
    }, [error]);

    return (
        <html lang="es">
            <body className="min-h-screen flex items-center justify-center p-4 bg-slate-950 text-white font-sans">
                <div className="w-full max-w-md p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl text-center space-y-5">
                    <div className="mx-auto w-14 h-14 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-2xl font-bold">
                        !
                    </div>
                    <h2 className="text-xl font-bold">Actualización en curso</h2>
                    <p className="text-sm text-slate-400 leading-relaxed">
                        Se ha detectado una versión actualizada de la aplicación. Haz clic abajo para recargar.
                    </p>
                    <button
                        onClick={() => {
                            if (typeof window !== 'undefined') window.location.reload();
                            else reset();
                        }}
                        className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-all"
                    >
                        Recargar Página
                    </button>
                </div>
            </body>
        </html>
    );
}
