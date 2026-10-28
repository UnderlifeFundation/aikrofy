'use client';

import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Moon, Sun, LogOut, Menu, User as UserIcon, Zap, Play, Square, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { useAuthStore } from '@/store/use-auth-store';
import { LanguageSwitcher } from './language-switcher';
import { AgencyWorkspaceSwitcher } from './AgencyWorkspaceSwitcher';
import apiClient from '@/lib/api-client';

interface HeaderProps {
    onMobileMenuToggle: () => void;
    showMenuButton?: boolean;
}

export function Header({ onMobileMenuToggle, showMenuButton = true }: HeaderProps) {
    const router = useRouter();
    const { t } = useTranslation();
    const { theme, setTheme } = useTheme();
    const user = useAuthStore((s) => s.user);
    const logout = useAuthStore((s) => s.logout);
    const queryClient = useQueryClient();
    const [isToggling, setIsToggling] = useState(false);

    // Fetch demo status for sales email
    const { data: demoStatus, refetch: refetchDemoStatus } = useQuery({
        queryKey: ['demo-status'],
        queryFn: async () => {
            const { data } = await apiClient.get('/demo/status');
            return data;
        },
        enabled: user?.email === 'test@weblifetech.com',
        refetchInterval: (data: any) => {
            // Safe fallback checking if running is true
            const status = data?.state?.data ?? data;
            return status?.running ? 3000 : false;
        },
    });

    const handleToggleDemo = async () => {
        setIsToggling(true);
        const action = demoStatus?.running ? 'stop' : 'start';
        try {
            const { data } = await apiClient.post('/demo/toggle', { action });
            toast.success(data.message || `Simulación ${action === 'start' ? 'iniciada' : 'detenida'}.`);
            await refetchDemoStatus();
            queryClient.invalidateQueries();
        } catch (error: any) {
            toast.error(error.response?.data?.error || 'Error al cambiar el estado de la simulación');
        } finally {
            setIsToggling(false);
        }
    };

    // Fetch credit balance
    const { data: creditData } = useQuery({
        queryKey: ['credit-balance'],
        queryFn: async () => {
            const { data } = await apiClient.get('/billing/credits');
            return data;
        },
        refetchInterval: 30000, // Refresh every 30 seconds
        enabled: !!user,
    });

    const creditBalance = creditData?.credit_balance ?? 0;
    const isCourtesy = creditData?.is_courtesy ?? false;

    // Color logic for credit indicator
    const getCreditColor = () => {
        if (isCourtesy) return 'text-violet-500 border-violet-500/30 bg-violet-500/10';
        if (creditBalance <= 0) return 'text-red-500 border-red-500/30 bg-red-500/10 animate-pulse';
        if (creditBalance < 20) return 'text-amber-500 border-amber-500/30 bg-amber-500/10';
        return 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10';
    };

    const handleLogout = () => {
        logout();
        router.push('/login');
    };

    const initials = user?.name
        ? user.name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
        : 'U';

    return (
        <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-background/80 px-4 backdrop-blur-sm">
            {/* Mobile menu button */}
            {showMenuButton && (
                <Button
                    variant="ghost"
                    size="icon"
                    className="lg:hidden"
                    onClick={onMobileMenuToggle}
                >
                    <Menu className="h-5 w-5" />
                </Button>
            )}

            {/* Agency Workspace Switcher */}
            <AgencyWorkspaceSwitcher />

            {/* Spacer */}
            <div className="flex-1" />

            {/* Right side actions */}
            <div className="flex items-center gap-2">
                {/* Sales Demo Toggle (restricted to test@weblifetech.com) - Hidden temporarily */}
                {false && user?.email === 'test@weblifetech.com' && (
                    <div className="flex items-center gap-2 mr-2">
                        {demoStatus?.running && (
                            <span className="relative flex h-2.5 w-2.5">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                            </span>
                        )}
                        <Button
                            variant={demoStatus?.running ? "destructive" : "default"}
                            size="sm"
                            disabled={isToggling}
                            onClick={handleToggleDemo}
                            className={`gap-1.5 h-9 font-semibold text-xs transition-all duration-300 ${
                                demoStatus?.running 
                                    ? "bg-red-600 hover:bg-red-700 text-white animate-pulse" 
                                    : "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white shadow-md shadow-indigo-500/20"
                            }`}
                        >
                            {demoStatus?.running ? (
                                <>
                                    <Square className="h-3.5 w-3.5 fill-current" />
                                    <span>Detener Simulación</span>
                                </>
                            ) : (
                                <>
                                    <Play className="h-3.5 w-3.5 fill-current" />
                                    <span>Iniciar Simulación</span>
                                </>
                            )}
                        </Button>
                    </div>
                )}

                {/* Credit Counter Widget */}
                {user && user.role !== 'super_admin' && (
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className={`gap-1.5 h-9 px-3 font-semibold text-xs border transition-all hover:scale-[1.02] active:scale-95 cursor-pointer shadow-sm ${getCreditColor()}`}
                                    onClick={() => router.push('/pricing')}
                                    id="credit-counter-widget"
                                >
                                    <Zap className="h-3.5 w-3.5 fill-current" />
                                    {creditBalance === -1 ? (
                                        <span>∞</span>
                                    ) : (
                                        <span>{creditBalance.toLocaleString()} {t('credits.credits', 'créditos')}</span>
                                    )}
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="p-3 max-w-xs space-y-2">
                                <div className="text-xs">
                                    {isCourtesy ? (
                                        <p className="font-semibold text-violet-400">
                                            {t('subscribe.membership.courtesy', 'Cuenta de Cortesía')}
                                        </p>
                                    ) : null}
                                    <p className="font-bold text-foreground">
                                        {creditBalance === -1 
                                            ? t('admin.courtesyUnlimited', '∞ Créditos Ilimitados')
                                            : `⚡ ${creditBalance.toLocaleString()} ${t('credits.remaining', 'créditos restantes')}`
                                        }
                                    </p>
                                    <p className="text-[11px] text-muted-foreground mt-0.5">
                                        {t('credits.topUpDescription', 'Combustible para conversaciones, llamadas de voz y búsquedas de IA.')}
                                    </p>
                                </div>
                                {creditBalance !== -1 && (
                                    <Button
                                        size="sm"
                                        className="w-full h-7 text-[11px] font-bold bg-gradient-to-r from-indigo-500 to-violet-600 text-white hover:opacity-90 border-0"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            router.push('/pricing');
                                        }}
                                    >
                                        ⚡ {t('credits.lowBalance', 'Recargar Combustible IA')}
                                    </Button>
                                )}
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                )}

                {/* Language Switcher */}
                <LanguageSwitcher />

                {/* Theme toggle */}
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                >
                    <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                    <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                </Button>

                {/* User menu */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="flex items-center gap-2 px-2">
                            <Avatar className="h-8 w-8">
                                <AvatarFallback className="text-xs">{initials}</AvatarFallback>
                            </Avatar>
                            <span className="hidden text-sm font-medium md:inline-block">
                                {user?.name}
                            </span>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuItem onClick={() => router.push('/settings')}>
                            <UserIcon className="mr-2 h-4 w-4" />
                            {t('common.profile')}
                        </DropdownMenuItem>
                        {user && user.role !== 'super_admin' && (
                            <DropdownMenuItem onClick={() => router.push('/pricing')} className="text-indigo-400 font-medium cursor-pointer">
                                <Zap className="mr-2 h-4 w-4 text-amber-400 fill-amber-400" />
                                {t('sidebar.billingCredits', 'Combustible IA')}
                            </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={handleLogout}>
                            <LogOut className="mr-2 h-4 w-4" />
                            {t('common.logOut')}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </header>
    );
}

