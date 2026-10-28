'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import {
    LayoutDashboard,
    Users,
    Bot,
    FileText,
    Settings,
    Radio,
    CreditCard,
    ShieldCheck,
    ChevronLeft,
    MessageSquare,
    BarChart3,
    ContactRound,
    ShoppingCart,
    Server,
    Database,
    Cpu,
    Mic,
    Sparkles,
    QrCode,
    FileCode,
    Building2,
    Globe,
    Package,
    Image as ImageIcon,
    Atom,
    Barcode,
    SlidersHorizontal,
    CheckSquare,
    Square,
    X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/store/use-auth-store';
import apiClient from '@/lib/api-client';
import { toast } from 'sonner';

export interface NavItem {
    titleKey: string;
    defaultLabel: string;
    href: string;
    icon: React.ElementType;
    moduleKey: string;
    category: 'Esenciales' | 'Ventas & POS' | 'Marketing & Contenido' | 'Organización & Equipo' | 'Integraciones Avanzadas';
    description: string;
}

// Master catalog of all workspace modules in Aikrofy
export const WORKSPACE_MODULES: NavItem[] = [
    {
        titleKey: 'sidebar.dashboard',
        defaultLabel: 'Panel Principal',
        href: '/dashboard',
        icon: LayoutDashboard,
        moduleKey: 'dashboard',
        category: 'Esenciales',
        description: 'Métricas clave, resumen diario y estado general de tu negocio.',
    },
    {
        titleKey: 'POS & Inventario IA',
        defaultLabel: 'POS & Inventario IA',
        href: '/pos',
        icon: Barcode,
        moduleKey: 'pos',
        category: 'Ventas & POS',
        description: 'Punto de Venta nativo, códigos de barras EAN-13, QR adhesivos y stock conectado a WhatsApp.',
    },
    {
        titleKey: 'sidebar.chat',
        defaultLabel: 'Bandeja de Chats IA',
        href: '/chat',
        icon: MessageSquare,
        moduleKey: 'chat',
        category: 'Esenciales',
        description: 'Conversaciones en tiempo real de WhatsApp, Webchat y redes sociales.',
    },
    {
        titleKey: 'sidebar.contacts',
        defaultLabel: 'Clientes y Prospectos',
        href: '/contacts',
        icon: ContactRound,
        moduleKey: 'contacts',
        category: 'Ventas & POS',
        description: 'Directorio CRM nativo de clientes, teléfonos, etiquetas e historial.',
    },
    {
        titleKey: 'sidebar.channels',
        defaultLabel: 'Canales (WhatsApp/Web)',
        href: '/channels',
        icon: Radio,
        moduleKey: 'channels',
        category: 'Esenciales',
        description: 'Vinculación por QR con WhatsApp, Webchat embebible y Telegram.',
    },
    {
        titleKey: 'sidebar.agentSetup',
        defaultLabel: 'Agentes de IA',
        href: '/agents',
        icon: Bot,
        moduleKey: 'agents',
        category: 'Esenciales',
        description: 'Personalidad, reglas de atención, tono de voz y habilidades de tus agentes.',
    },
    {
        titleKey: 'sidebar.magicOnboarding',
        defaultLabel: 'Entrenamiento por Voz',
        href: '/onboarding',
        icon: Mic,
        moduleKey: 'onboarding',
        category: 'Esenciales',
        description: 'Configura tu negocio hablando por micrófono en 60 segundos.',
    },
    {
        titleKey: 'sidebar.documents',
        defaultLabel: 'Base de Conocimiento (PDF)',
        href: '/documents',
        icon: FileText,
        moduleKey: 'documents',
        category: 'Esenciales',
        description: 'Sube catálogos PDF, manuales o listas de precios para entrenar a tu IA (RAG).',
    },
    {
        titleKey: 'sidebar.campaigns',
        defaultLabel: 'Campañas & QR Dinámicos',
        href: '/campaigns',
        icon: QrCode,
        moduleKey: 'campaigns',
        category: 'Marketing & Contenido',
        description: 'Generador de códigos QR dinámicos para ferias, empaques y campañas.',
    },
    {
        titleKey: 'sidebar.landingPages',
        defaultLabel: 'Páginas de Ventas (Landing)',
        href: '/landing-pages',
        icon: Sparkles,
        moduleKey: 'landing_pages',
        category: 'Marketing & Contenido',
        description: 'Crea micro-sitios web con agente de IA integrado.',
    },
    {
        titleKey: 'sidebar.mediaLibrary',
        defaultLabel: 'Galería Multimedia',
        href: '/media',
        icon: ImageIcon,
        moduleKey: 'media',
        category: 'Marketing & Contenido',
        description: 'Fotos y videos de tus productos que el agente envía por WhatsApp.',
    },
    {
        titleKey: 'sidebar.templates',
        defaultLabel: 'Plantillas WhatsApp',
        href: '/templates',
        icon: FileCode,
        moduleKey: 'whatsapp_templates',
        category: 'Marketing & Contenido',
        description: 'Mensajes pre-aprobados y plantillas de notificación.',
    },
    {
        titleKey: 'sidebar.payments',
        defaultLabel: 'Pasarelas de Pago',
        href: '/settings/payments',
        icon: CreditCard,
        moduleKey: 'payments',
        category: 'Ventas & POS',
        description: 'Cobros con tarjeta, PayPal, Stripe y links de pago en el chat.',
    },
    {
        titleKey: 'sidebar.analytics',
        defaultLabel: 'Analítica de Negocio',
        href: '/analytics',
        icon: BarChart3,
        moduleKey: 'analytics',
        category: 'Ventas & POS',
        description: 'Estadísticas de conversión, horarios pico y rendimiento de agentes.',
    },
    {
        titleKey: 'sidebar.krofStudio',
        defaultLabel: 'Copiloto Ejecutivo (Krof)',
        href: '/admin-chat',
        icon: Sparkles,
        moduleKey: 'krof_studio',
        category: 'Esenciales',
        description: 'Sala de comando conversacional para controlar toda tu cuenta con IA.',
    },
    {
        titleKey: 'sidebar.departments',
        defaultLabel: 'Departamentos',
        href: '/departments',
        icon: Building2,
        moduleKey: 'departments',
        category: 'Organización & Equipo',
        description: 'Enrutamiento entre áreas (Ventas, Soporte, Contabilidad).',
    },
    {
        titleKey: 'sidebar.employees',
        defaultLabel: 'Equipo y Colaboradores',
        href: '/employees',
        icon: Users,
        moduleKey: 'employees',
        category: 'Organización & Equipo',
        description: 'Registra vendedores u operadores autorizados por WhatsApp y Web.',
    },
    {
        titleKey: 'sidebar.ecommerce',
        defaultLabel: 'Conector Shopify / Woo',
        href: '/settings/ecommerce',
        icon: ShoppingCart,
        moduleKey: 'ecommerce',
        category: 'Integraciones Avanzadas',
        description: 'Sincronización con tiendas externas Shopify o WooCommerce.',
    },
    {
        titleKey: 'sidebar.crm',
        defaultLabel: 'Conector CRM Externo',
        href: '/settings/crm',
        icon: Database,
        moduleKey: 'crm',
        category: 'Integraciones Avanzadas',
        description: 'Sincronización con HubSpot, Salesforce, Pipedrive o Zoho.',
    },
    {
        titleKey: 'sidebar.erp',
        defaultLabel: 'Conector ERP / Contable',
        href: '/settings/erp',
        icon: Server,
        moduleKey: 'erp',
        category: 'Integraciones Avanzadas',
        description: 'Integración con Odoo, SAP Business One, NetSuite o APIs contables.',
    },
    {
        titleKey: 'sidebar.mcp',
        defaultLabel: 'Servidores MCP',
        href: '/settings/mcp',
        icon: Cpu,
        moduleKey: 'mcp',
        category: 'Integraciones Avanzadas',
        description: 'Conecta herramientas externas mediante Model Context Protocol.',
    },
    {
        titleKey: 'sidebar.observatory',
        defaultLabel: 'Observatorio & Telemetría',
        href: '/observatory',
        icon: Atom,
        moduleKey: 'observatory',
        category: 'Integraciones Avanzadas',
        description: 'Monitoreo cognitivo avanzado y trazabilidad de agentes.',
    },
    {
        titleKey: 'sidebar.marketplaceStore',
        defaultLabel: 'Marketplace de Skills',
        href: '/marketplace',
        icon: Package,
        moduleKey: 'marketplace',
        category: 'Integraciones Avanzadas',
        description: 'Instala habilidades pre-entrenadas por industria.',
    },
    {
        titleKey: 'sidebar.agencyPortal',
        defaultLabel: 'Portal de Agencia',
        href: '/agency',
        icon: Building2,
        moduleKey: 'agency',
        category: 'Organización & Equipo',
        description: 'Gestión multi-empresa para agencias y consultores.',
    },
    {
        titleKey: 'sidebar.settings',
        defaultLabel: 'Configuración & LLMs',
        href: '/settings',
        icon: Settings,
        moduleKey: 'settings',
        category: 'Esenciales',
        description: 'Llaves API propias (BYOK), datos de empresa y personalización del panel.',
    },
];

// Default starter modules when none are loaded yet
export const DEFAULT_STARTER_MODULES = [
    'dashboard',
    'pos',
    'chat',
    'contacts',
    'channels',
    'agents',
    'documents',
    'campaigns',
    'krof_studio',
    'settings',
];

// Super Admin-only navigation
const adminItems = [
    { titleKey: 'sidebar.adminDashboard', href: '/admin/dashboard', icon: ShieldCheck },
    { titleKey: 'sidebar.geoAnalytics', href: '/admin/geo-analytics', icon: Globe },
    { titleKey: 'sidebar.betaManagement', href: '/admin/beta', icon: Users },
    { titleKey: 'sidebar.platformAgent', href: '/admin/platform-agent', icon: Bot },
    { titleKey: 'sidebar.systemKnowledge', href: '/admin/documents', icon: FileText },
    { titleKey: 'sidebar.billing', href: '/admin/billing', icon: CreditCard },
];

interface SidebarProps {
    collapsed: boolean;
    onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
    const pathname = usePathname();
    const { t } = useTranslation();
    const user = useAuthStore((s) => s.user);
    const updateUser = useAuthStore((s) => s.updateUser);
    const isSuperAdmin = user?.role === 'super_admin';

    const companyEnabledModules: string[] | undefined = (user as any)?.company?.enabled_modules;
    const [enabledModules, setEnabledModules] = useState<string[]>(
        companyEnabledModules && companyEnabledModules.length > 0
            ? companyEnabledModules
            : DEFAULT_STARTER_MODULES
    );
    const [customizerOpen, setCustomizerOpen] = useState(false);
    const [savingModules, setSavingModules] = useState(false);

    // Sync enabled_modules from backend settings on mount & listen for custom events from Settings page
    useEffect(() => {
        let mounted = true;
        apiClient
            .get('/companies/settings')
            .then((res) => {
                const remoteModules = res.data?.data?.enabled_modules;
                if (mounted && Array.isArray(remoteModules) && remoteModules.length > 0) {
                    // Always include krof_studio if agents is active so users have full copilot access
                    const merged = remoteModules.includes('krof_studio')
                        ? remoteModules
                        : [...remoteModules, 'krof_studio'];
                    setEnabledModules(merged);
                }
            })
            .catch(() => {
                // Keep defaults on error
            });

        const handleModulesChanged = (ev: Event) => {
            const customEv = ev as CustomEvent<string[]>;
            if (Array.isArray(customEv.detail)) {
                setEnabledModules(customEv.detail);
            }
        };
        window.addEventListener('aikrofy:modules-updated', handleModulesChanged);
        return () => {
            mounted = false;
            window.removeEventListener('aikrofy:modules-updated', handleModulesChanged);
        };
    }, []);

    const toggleModuleCheck = (moduleKey: string) => {
        if (moduleKey === 'dashboard' || moduleKey === 'settings') return; // Core locked
        setEnabledModules((prev) =>
            prev.includes(moduleKey) ? prev.filter((k) => k !== moduleKey) : [...prev, moduleKey]
        );
    };

    const handleSaveModules = async () => {
        setSavingModules(true);
        try {
            await apiClient.put('/companies/settings', {
                enabled_modules: enabledModules,
            });
            updateUser({
                company: {
                    ...((user as any)?.company || {}),
                    enabled_modules: enabledModules,
                } as any,
            });
            window.dispatchEvent(new CustomEvent('aikrofy:modules-updated', { detail: enabledModules }));
            toast.success('Panel personalizado guardado. El Copiloto IA ahora reconoce tus módulos activos.');
            setCustomizerOpen(false);
        } catch {
            toast.error('No se pudo guardar la personalización del panel');
        } finally {
            setSavingModules(false);
        }
    };

    const getOnboardingId = (href: string) => {
        if (href === '/dashboard') return 'onboarding-nav-dashboard';
        if (href === '/agents') return 'onboarding-nav-agents';
        if (href === '/channels') return 'onboarding-nav-channels';
        if (href === '/documents') return 'onboarding-nav-documents';
        if (href === '/chat') return 'onboarding-nav-chat';
        if (href === '/settings/crm') return 'onboarding-nav-crm';
        if (href === '/settings/ecommerce') return 'onboarding-nav-ecommerce';
        if (href === '/settings/erp') return 'onboarding-nav-erp';
        if (href === '/settings/payments') return 'onboarding-nav-payments';
        if (href === '/settings/mcp') return 'onboarding-nav-mcp';
        return undefined;
    };

    const renderNavItem = (item: { titleKey: string; defaultLabel?: string; href: string; icon: React.ElementType }) => {
        const isActive =
            pathname === item.href ||
            (item.href !== '/dashboard' && item.href !== '/admin/dashboard' && pathname.startsWith(item.href + '/'));

        const label = item.titleKey.includes('.')
            ? t(item.titleKey, { defaultValue: item.defaultLabel || item.titleKey.split('.').pop() })
            : item.titleKey;

        return (
            <Link key={item.href} href={item.href} id={getOnboardingId(item.href)}>
                <span
                    className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground font-semibold shadow-xs'
                            : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
                        collapsed && 'justify-center px-2'
                    )}
                >
                    <item.icon className="h-4 w-4 shrink-0" />
                    {!collapsed && <span className="truncate">{label}</span>}
                </span>
            </Link>
        );
    };

    const visibleCompanyItems = WORKSPACE_MODULES.filter((item) => {
        if (item.href === '/agency') {
            return (user?.role === 'agency' || user?.role === 'super_admin') && enabledModules.includes('agency');
        }
        if (item.moduleKey === 'dashboard' || item.moduleKey === 'settings') {
            return true;
        }
        return enabledModules.includes(item.moduleKey);
    });

    const categoriesOrder: Array<NavItem['category']> = [
        'Esenciales',
        'Ventas & POS',
        'Marketing & Contenido',
        'Organización & Equipo',
        'Integraciones Avanzadas',
    ];

    return (
        <>
            <aside
                className={cn(
                    'relative flex h-screen flex-col border-r bg-sidebar transition-all duration-300',
                    collapsed ? 'w-16' : 'w-64'
                )}
            >
                {/* Toggle Button mounted on the border */}
                <Button
                    variant="outline"
                    size="icon"
                    onClick={onToggle}
                    className="absolute top-8 right-0 z-50 h-6 w-6 -translate-y-1/2 translate-x-1/2 rounded-full border bg-background shadow-md hover:bg-accent flex items-center justify-center"
                >
                    <ChevronLeft className={cn('h-3.5 w-3.5 transition-transform', collapsed && 'rotate-180')} />
                </Button>

                {/* Logo */}
                <div className="flex h-16 items-center border-b px-4">
                    <div className="flex items-center gap-2">
                        <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="w-8 h-8 shrink-0" />
                        {!collapsed && (
                            <div className="flex flex-col">
                                <span className="text-lg font-bold tracking-tight leading-tight">Aikrofy</span>
                                {isSuperAdmin && (
                                    <span className="text-[10px] uppercase font-bold tracking-wider text-amber-500">
                                        Super Admin
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 space-y-1 overflow-y-auto p-2 scrollbar-thin">
                    {isSuperAdmin && (
                        <div className="space-y-1 mb-3">
                            {!collapsed && (
                                <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5">
                                    <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                                    {t('sidebar.superAdminSection', { defaultValue: 'Super Admin' })}
                                </div>
                            )}
                            {collapsed && <div className="h-px bg-border my-2 mx-1" />}
                            {adminItems.map(renderNavItem)}
                        </div>
                    )}

                    <div className="space-y-1">
                        {isSuperAdmin && !collapsed && (
                            <div className="px-3 py-1.5 pt-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5 border-t mt-3">
                                <LayoutDashboard className="h-3.5 w-3.5 text-primary" />
                                {t('sidebar.companySection', { defaultValue: 'Operaciones & CRM' })}
                            </div>
                        )}
                        {isSuperAdmin && collapsed && <div className="h-px bg-border my-2 mx-1" />}
                        {visibleCompanyItems.map(renderNavItem)}
                    </div>
                </nav>

                {/* Footer: Personalizar Panel Button */}
                <div className="border-t p-2">
                    <button
                        type="button"
                        onClick={() => setCustomizerOpen(true)}
                        title="Personalizar Panel y Módulos Activos"
                        className={cn(
                            'w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium text-primary bg-primary/10 hover:bg-primary/20 transition-colors',
                            collapsed && 'justify-center px-2'
                        )}
                    >
                        <SlidersHorizontal className="h-4 w-4 shrink-0" />
                        {!collapsed && (
                            <div className="flex items-center justify-between w-full">
                                <span>Personalizar Panel</span>
                                <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                                    {visibleCompanyItems.length}/{WORKSPACE_MODULES.length}
                                </Badge>
                            </div>
                        )}
                    </button>
                </div>
            </aside>

            {/* Modal: Personalizar Panel (Checkboxes for Modules) */}
            {customizerOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
                    <div className="bg-background border rounded-xl shadow-2xl max-w-3xl w-full max-h-[88vh] flex flex-col overflow-hidden">
                        <div className="p-5 border-b flex items-start justify-between gap-4">
                            <div>
                                <h2 className="text-lg font-bold flex items-center gap-2">
                                    <SlidersHorizontal className="h-5 w-5 text-primary" />
                                    Personalizar Panel y Módulos Activos
                                </h2>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Marca con un check (✓) únicamente los módulos que deseas ver en tu menú lateral. El Copiloto IA (Krof) detectará automáticamente tus herramientas activas para ayudarte a gestionarlas sin abrumarte.
                                </p>
                            </div>
                            <Button size="icon" variant="ghost" onClick={() => setCustomizerOpen(false)}>
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-5 space-y-6">
                            <div className="flex flex-wrap gap-2 items-center justify-between bg-muted/40 p-3 rounded-lg">
                                <span className="text-xs font-medium">
                                    Preajustes rápidos según el tamaño de tu operación:
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-xs"
                                        onClick={() => setEnabledModules(DEFAULT_STARTER_MODULES)}
                                    >
                                        🌱 Esencial (Emprendedor / Artesano + POS)
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-xs"
                                        onClick={() =>
                                            setEnabledModules([
                                                ...DEFAULT_STARTER_MODULES,
                                                'landing_pages',
                                                'media',
                                                'payments',
                                                'analytics',
                                                'employees',
                                            ])
                                        }
                                    >
                                        🚀 PyME en Crecimiento
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-xs"
                                        onClick={() => setEnabledModules(WORKSPACE_MODULES.map((m) => m.moduleKey))}
                                    >
                                        🏢 Activar Todos ({WORKSPACE_MODULES.length})
                                    </Button>
                                </div>
                            </div>

                            {categoriesOrder.map((cat) => {
                                const itemsInCat = WORKSPACE_MODULES.filter((m) => m.category === cat);
                                return (
                                    <div key={cat} className="space-y-2.5">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-primary border-b pb-1">
                                            {cat}
                                        </h3>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                                            {itemsInCat.map((mod) => {
                                                const isChecked =
                                                    mod.moduleKey === 'dashboard' ||
                                                    mod.moduleKey === 'settings' ||
                                                    enabledModules.includes(mod.moduleKey);
                                                const isLocked =
                                                    mod.moduleKey === 'dashboard' || mod.moduleKey === 'settings';

                                                return (
                                                    <div
                                                        key={mod.moduleKey}
                                                        onClick={() => !isLocked && toggleModuleCheck(mod.moduleKey)}
                                                        className={cn(
                                                            'flex items-start gap-3 p-3 rounded-lg border text-left transition-all cursor-pointer select-none',
                                                            isChecked
                                                                ? 'border-primary/60 bg-primary/5'
                                                                : 'border-border opacity-70 hover:opacity-100',
                                                            isLocked && 'cursor-not-allowed opacity-90'
                                                        )}
                                                    >
                                                        <div className="mt-0.5 text-primary">
                                                            {isChecked ? (
                                                                <CheckSquare className="h-4 w-4" />
                                                            ) : (
                                                                <Square className="h-4 w-4 text-muted-foreground" />
                                                            )}
                                                        </div>
                                                        <div className="min-w-0 flex-1">
                                                            <div className="flex items-center gap-1.5 font-semibold text-xs">
                                                                <mod.icon className="h-3.5 w-3.5 text-muted-foreground" />
                                                                <span>{mod.defaultLabel}</span>
                                                                {isLocked && (
                                                                    <Badge variant="outline" className="text-[9px] h-4 px-1">
                                                                        Fijo
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                                                                {mod.description}
                                                            </p>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        <div className="p-4 border-t bg-muted/20 flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">
                                {enabledModules.length} módulos seleccionados
                            </span>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => setCustomizerOpen(false)}>
                                    Cancelar
                                </Button>
                                <Button size="sm" onClick={handleSaveModules} disabled={savingModules}>
                                    {savingModules ? 'Guardando...' : 'Guardar y Actualizar Panel'}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
