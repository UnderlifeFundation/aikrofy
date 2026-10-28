'use client';

import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { Toaster } from 'sonner';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { useTranslation } from 'react-i18next';
import '@/lib/i18n'; // Initialize i18n globally

export function Providers({ children }: { children: React.ReactNode }) {
    const { i18n } = useTranslation();
    const [queryClient] = React.useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 60 * 1000,
                        refetchOnWindowFocus: false,
                    },
                },
            })
    );

    React.useEffect(() => {
        try {
            const savedLng = localStorage.getItem('i18nextLng');
            if (savedLng && savedLng !== i18n.language) {
                i18n.changeLanguage(savedLng);
            }
        } catch (e) {
            console.warn('Unable to access localStorage:', e);
        }

        // Auto-recover from stale Next.js ChunkLoadErrors after deployments
        const handleChunkError = (event: ErrorEvent | PromiseRejectionEvent) => {
            const error = 'error' in event ? event.error : event.reason;
            const message = error?.message || (typeof error === 'string' ? error : '');
            if (
                error?.name === 'ChunkLoadError' ||
                message.includes('Loading chunk') ||
                message.includes('Failed to load chunk') ||
                message.includes('ChunkLoadError')
            ) {
                const reloadKey = 'chunk_reload_' + (error?.message || 'err');
                if (!sessionStorage.getItem(reloadKey)) {
                    sessionStorage.setItem(reloadKey, '1');
                    window.location.reload();
                }
            }
        };

        window.addEventListener('error', handleChunkError);
        window.addEventListener('unhandledrejection', handleChunkError);
        return () => {
            window.removeEventListener('error', handleChunkError);
            window.removeEventListener('unhandledrejection', handleChunkError);
        };
    }, [i18n]);

    return (
        <QueryClientProvider client={queryClient}>
            <NextThemesProvider
                attribute="class"
                defaultTheme="system"
                enableSystem
                disableTransitionOnChange
            >
                <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''}>
                    {children}
                    <Toaster richColors position="top-right" />
                </GoogleOAuthProvider>
            </NextThemesProvider>
        </QueryClientProvider>
    );
}
