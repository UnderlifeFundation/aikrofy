'use client';

import * as React from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'next-themes';
import { Sun, Moon, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/shared/language-switcher';
import { usePathname } from 'next/navigation';

export default function PublicLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const isBetaRegister = pathname === '/beta-register';
    const [isInstitutionalHost, setIsInstitutionalHost] = React.useState(false);
    const { t } = useTranslation();
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);

    React.useEffect(() => {
        setMounted(true);
        if (typeof window !== 'undefined') {
            const h = window.location.hostname.toLowerCase();
            if (h.includes('fundacionunderlife.org')) {
                setIsInstitutionalHost(true);
            }
        }
    }, []);

    const isCommunity = pathname?.startsWith('/community') || pathname?.startsWith('/activate') || isInstitutionalHost;

    // If on community or activation page or underlife domain, let the page render its own full-page institutional branding
    if (isCommunity) {
        return <main className="min-h-screen">{children}</main>;
    }

    return (
        <div className="flex min-h-screen flex-col bg-background text-foreground transition-colors duration-300">
            {/* PUBLIC HEADER */}
            {!isBetaRegister && (
                <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
                    <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
                        <div className="flex items-center gap-2">
                            <Link href="/" className="flex items-center gap-2">
                                <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="w-8 h-8" />
                                <span className="text-xl font-bold tracking-tight">
                                    Aikrofy
                                </span>
                            </Link>
                        </div>

                        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
                            <Link href="/#features" className="transition-colors hover:text-foreground">
                                {t('home.nav.features', 'Características')}
                            </Link>
                            <Link href="/#how-it-works" className="transition-colors hover:text-foreground">
                                {t('home.nav.howItWorks', 'Cómo Funciona')}
                            </Link>
                            <Link href="/pricing" className="transition-colors hover:text-foreground">
                                {t('home.nav.pricing', 'Suscripción')}
                            </Link>
                        </nav>

                        <div className="flex items-center gap-3">
                            <LanguageSwitcher />
                            
                            {/* Theme Toggle */}
                            {mounted ? (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                                >
                                    <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                                    <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                                </Button>
                            ) : (
                                <div className="w-9 h-9" />
                            )}

                            <Link href="/login" className="hidden sm:block">
                                <Button variant="ghost" size="sm">
                                    {t('home.hero.signIn', 'Iniciar Sesión')}
                                </Button>
                            </Link>
                            <Link href="/register">
                                <Button size="sm" className="bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/25 hover:shadow-lg hover:shadow-indigo-500/30 transition-all border-0">
                                    {t('auth.register', 'Registrarse')} <ArrowRight className="ml-1 h-4 w-4" />
                                </Button>
                            </Link>
                        </div>
                    </div>
                </header>
            )}

            {/* MAIN CONTENT */}
            <main className="flex-1">
                {children}
            </main>

            {/* PUBLIC FOOTER */}
            {!isBetaRegister && (
                <footer className="border-t py-8 bg-card">
                    <div className="mx-auto max-w-6xl px-4 sm:px-6">
                        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
                            <div className="flex items-center gap-2">
                                <Link href="/" className="flex items-center gap-2">
                                    <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="w-6 h-6" />
                                    <span className="text-sm font-semibold">
                                        Aikrofy
                                    </span>
                                </Link>
                            </div>
                            <div className="flex flex-wrap items-center justify-center gap-6">
                                <Link href="/pricing" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                                    {t('legal.pricingTitle', 'Precios')}
                                </Link>
                                <Link href="/privacy" id="privacy-policy-link" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                                    {t('legal.privacyTitle', 'Política de Privacidad')}
                                </Link>
                                <Link href="/terms" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                                    {t('legal.termsTitle', 'Condiciones del Servicio')}
                                </Link>
                                <Link href="/refunds" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                                    {t('legal.refundsTitle', 'Política de Reembolso')}
                                </Link>
                                <p className="text-xs text-muted-foreground">
                                    © {new Date().getFullYear()} Aikrofy. {t('home.footer.legal', 'Todos los derechos reservados.')}
                                </p>
                            </div>
                        </div>
                    </div>
                </footer>
            )}
        </div>
    );
}
