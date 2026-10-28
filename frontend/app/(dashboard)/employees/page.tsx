'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Users,
    Plus,
    Trash2,
    Loader2,
    Phone,
    Mail,
    MessageSquare,
    PhoneCall,
    CheckCircle2,
    XCircle,
    Pencil,
    Save,
    X,
    Building2,
    Monitor,
    MessageCircle,
    ShieldCheck,
    ShieldAlert,
    RotateCcw,
    Database,
    ShoppingCart,
    BarChart2,
    Bot,
    BookOpen,
    Crown,
    Lock,
    FileSpreadsheet,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import BulkUploadDialog from '@/components/shared/bulk-upload-dialog';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
    DialogClose,
} from '@/components/ui/dialog';
import apiClient from '@/lib/api-client';
import { usePermissions } from '@/hooks/use-permissions';
import { useAuthStore } from '@/store/use-auth-store';


// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface EffectivePermissions {
    department_level: {
        access_tier: string;
        can_view_department_conversations: boolean;
        can_upload_department_rag: boolean;
    };
    integrations: {
        erp: {
            enabled: boolean;
            read_products: boolean;
            read_stock: boolean;
            read_prices: boolean;
            create_orders: boolean;
            read_invoices_financials: boolean;
        };
        crm: {
            enabled: boolean;
            read_contacts: boolean;
            write_contacts: boolean;
            read_deals: boolean;
            modify_deals: boolean;
        };
        ecommerce: {
            enabled: boolean;
            view_catalog: boolean;
            manage_inventory: boolean;
            view_orders: boolean;
        };
        databases_and_mcp: {
            can_query_direct_db: boolean;
            can_trigger_mcp_actions: boolean;
        };
    };
    channels_and_agentic: {
        can_receive_calls: boolean;
        can_receive_messages: boolean;
        can_receive_escalations: boolean;
        can_override_agent_responses: boolean;
        can_manage_skills: boolean;
    };
}

interface Employee {
    id: number;
    name: string;
    email: string | null;
    phone: string | null;
    role: string;
    department: string | null;
    department_id: number | null;
    user_id: number | null;
    has_web_access: boolean;
    is_available: boolean;
    can_receive_calls: boolean;
    can_receive_messages: boolean;
    created_at?: string;
    permissions?: Record<string, any>;
    /** Role of the linked web user account, if any. */
    linked_user_role?: string;
    /** True if the linked web user account is the company owner (root). */
    linked_user_is_owner?: boolean;
}

interface Department {
    id: number;
    name: string;
}

const ROLES = [
    { value: 'general', label: 'General' },
    { value: 'manager', label: 'Manager' },
    { value: 'sales', label: 'Sales' },
    { value: 'support', label: 'Support' },
    { value: 'admin', label: 'Admin' },
];

// ─────────────────────────────────────────────────────────────────────────────
// Permission Switch Row
// ─────────────────────────────────────────────────────────────────────────────

function PermSwitch({
    label,
    checked,
    onChange,
    description,
}: {
    label: string;
    checked: boolean;
    onChange: (v: boolean) => void;
    description?: string;
}) {
    return (
        <div className="flex items-center justify-between py-1.5">
            <div className="space-y-0.5">
                <p className="text-sm font-medium leading-none">{label}</p>
                {description && (
                    <p className="text-xs text-muted-foreground">{description}</p>
                )}
            </div>
            <Switch checked={checked} onCheckedChange={onChange} />
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Employee Permissions Modal
// ─────────────────────────────────────────────────────────────────────────────

function EmployeePermissionsModal({ employee }: { employee: Employee }) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);

    const { data: permData, isLoading } = useQuery({
        queryKey: ['employee-permissions', employee.id],
        queryFn: async () => {
            const { data } = await apiClient.get<{
                effective_permissions: EffectivePermissions;
                role: string;
                custom_overrides: Record<string, any>;
            }>(`/employees/${employee.id}/permissions`);
            return data;
        },
        enabled: open,
    });

    const [localPerms, setLocalPerms] = useState<EffectivePermissions | null>(null);
    const effective = localPerms ?? permData?.effective_permissions ?? null;

    // Sync local state when remote data loads
    if (permData && !localPerms) {
        setLocalPerms(JSON.parse(JSON.stringify(permData.effective_permissions)));
    }

    const patchMutation = useMutation({
        mutationFn: async (permissions: EffectivePermissions) => {
            const { data } = await apiClient.patch(`/employees/${employee.id}/permissions`, {
                permissions,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employee-permissions', employee.id] });
            queryClient.invalidateQueries({ queryKey: ['employees'] });
            toast.success('Permisos actualizados correctamente');
            setOpen(false);
            setLocalPerms(null);
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al actualizar permisos');
        },
    });

    const resetMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.patch(`/employees/${employee.id}/permissions`, {
                reset_to_role_preset: true,
            });
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['employee-permissions', employee.id] });
            setLocalPerms(data.effective_permissions);
            toast.success('Permisos restablecidos al preset del rol');
        },
        onError: () => toast.error('Error al restablecer permisos'),
    });

    function setP(
        section: keyof EffectivePermissions,
        subsection: string | null,
        key: string,
        value: boolean
    ) {
        if (!effective) return;
        const updated = JSON.parse(JSON.stringify(effective)) as EffectivePermissions;
        if (subsection) {
            (updated[section] as any)[subsection][key] = value;
        } else {
            (updated[section] as any)[key] = value;
        }
        setLocalPerms(updated);
    }

    return (
        <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setLocalPerms(null); }}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" title="Gestionar permisos">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5 text-primary" />
                        Permisos de {employee.name}
                    </DialogTitle>
                    <DialogDescription>
                        Rol actual: <span className="font-semibold capitalize">{employee.role}</span>
                        {' '}— los permisos controlan el acceso a recursos integrados y herramientas agénticas.
                    </DialogDescription>
                </DialogHeader>

                {isLoading || !effective ? (
                    <div className="space-y-3 py-4">
                        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
                    </div>
                ) : (
                    <div className="space-y-5 py-2">

                        {/* ── ERP ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <Database className="h-4 w-4 text-orange-500" />
                                <h4 className="font-semibold text-sm">ERP (SAP / Odoo / Dynamics / Contífico)</h4>
                                <Switch
                                    checked={effective.integrations.erp.enabled}
                                    onCheckedChange={(v) => setP('integrations', 'erp', 'enabled', v)}
                                    className="ml-auto"
                                />
                            </div>
                            {effective.integrations.erp.enabled && (
                                <div className="pl-2 space-y-1 border-l-2 border-orange-200">
                                    <PermSwitch label="Leer Productos" checked={effective.integrations.erp.read_products} onChange={(v) => setP('integrations', 'erp', 'read_products', v)} />
                                    <PermSwitch label="Ver Stock / Inventario" checked={effective.integrations.erp.read_stock} onChange={(v) => setP('integrations', 'erp', 'read_stock', v)} />
                                    <PermSwitch label="Ver Precios" checked={effective.integrations.erp.read_prices} onChange={(v) => setP('integrations', 'erp', 'read_prices', v)} />
                                    <PermSwitch label="Crear Órdenes de Compra/Venta" checked={effective.integrations.erp.create_orders} onChange={(v) => setP('integrations', 'erp', 'create_orders', v)} />
                                    <PermSwitch
                                        label="Ver Facturas y Datos Financieros"
                                        description="⚠️ Datos sensibles: balance, costos, márgenes"
                                        checked={effective.integrations.erp.read_invoices_financials}
                                        onChange={(v) => setP('integrations', 'erp', 'read_invoices_financials', v)}
                                    />
                                </div>
                            )}
                        </div>

                        {/* ── CRM ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <BarChart2 className="h-4 w-4 text-blue-500" />
                                <h4 className="font-semibold text-sm">CRM (HubSpot / Salesforce / Pipedrive)</h4>
                                <Switch
                                    checked={effective.integrations.crm.enabled}
                                    onCheckedChange={(v) => setP('integrations', 'crm', 'enabled', v)}
                                    className="ml-auto"
                                />
                            </div>
                            {effective.integrations.crm.enabled && (
                                <div className="pl-2 space-y-1 border-l-2 border-blue-200">
                                    <PermSwitch label="Leer Contactos" checked={effective.integrations.crm.read_contacts} onChange={(v) => setP('integrations', 'crm', 'read_contacts', v)} />
                                    <PermSwitch label="Crear / Editar Contactos" checked={effective.integrations.crm.write_contacts} onChange={(v) => setP('integrations', 'crm', 'write_contacts', v)} />
                                    <PermSwitch label="Ver Oportunidades / Deals" checked={effective.integrations.crm.read_deals} onChange={(v) => setP('integrations', 'crm', 'read_deals', v)} />
                                    <PermSwitch label="Modificar Deals (mover etapas, editar)" checked={effective.integrations.crm.modify_deals} onChange={(v) => setP('integrations', 'crm', 'modify_deals', v)} />
                                </div>
                            )}
                        </div>

                        {/* ── E-Commerce ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <ShoppingCart className="h-4 w-4 text-green-500" />
                                <h4 className="font-semibold text-sm">E-Commerce (Shopify / WooCommerce / VTEX)</h4>
                                <Switch
                                    checked={effective.integrations.ecommerce.enabled}
                                    onCheckedChange={(v) => setP('integrations', 'ecommerce', 'enabled', v)}
                                    className="ml-auto"
                                />
                            </div>
                            {effective.integrations.ecommerce.enabled && (
                                <div className="pl-2 space-y-1 border-l-2 border-green-200">
                                    <PermSwitch label="Ver Catálogo de Productos" checked={effective.integrations.ecommerce.view_catalog} onChange={(v) => setP('integrations', 'ecommerce', 'view_catalog', v)} />
                                    <PermSwitch label="Gestionar Inventario (actualizar stock)" checked={effective.integrations.ecommerce.manage_inventory} onChange={(v) => setP('integrations', 'ecommerce', 'manage_inventory', v)} />
                                    <PermSwitch label="Ver Órdenes de Clientes" checked={effective.integrations.ecommerce.view_orders} onChange={(v) => setP('integrations', 'ecommerce', 'view_orders', v)} />
                                </div>
                            )}
                        </div>

                        {/* ── Databases & MCP ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <Bot className="h-4 w-4 text-purple-500" />
                                <h4 className="font-semibold text-sm">Bases de Datos Directas & MCP Agéntico</h4>
                            </div>
                            <div className="pl-2 space-y-1 border-l-2 border-purple-200">
                                <PermSwitch
                                    label="Consultar BD Directo (SQL personalizado)"
                                    description="⚠️ Acceso avanzado: solo para técnicos"
                                    checked={effective.integrations.databases_and_mcp.can_query_direct_db}
                                    onChange={(v) => setP('integrations', 'databases_and_mcp', 'can_query_direct_db', v)}
                                />
                                <PermSwitch
                                    label="Ejecutar Acciones MCP (herramientas agénticas avanzadas)"
                                    description="⚠️ Permite a los agentes ejecutar acciones automatizadas"
                                    checked={effective.integrations.databases_and_mcp.can_trigger_mcp_actions}
                                    onChange={(v) => setP('integrations', 'databases_and_mcp', 'can_trigger_mcp_actions', v)}
                                />
                            </div>
                        </div>

                        {/* ── Canales y Agentes ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <MessageSquare className="h-4 w-4 text-cyan-500" />
                                <h4 className="font-semibold text-sm">Canales y Sistema Agéntico</h4>
                            </div>
                            <div className="pl-2 space-y-1 border-l-2 border-cyan-200">
                                <PermSwitch label="Recibir Llamadas" checked={effective.channels_and_agentic.can_receive_calls} onChange={(v) => setP('channels_and_agentic', null, 'can_receive_calls', v)} />
                                <PermSwitch label="Recibir Mensajes (WhatsApp / Webchat)" checked={effective.channels_and_agentic.can_receive_messages} onChange={(v) => setP('channels_and_agentic', null, 'can_receive_messages', v)} />
                                <PermSwitch label="Recibir Escalaciones del Agente IA" checked={effective.channels_and_agentic.can_receive_escalations} onChange={(v) => setP('channels_and_agentic', null, 'can_receive_escalations', v)} />
                                <PermSwitch
                                    label="Anular Respuestas del Agente"
                                    description="Permite editar o rechazar respuestas generadas por la IA"
                                    checked={effective.channels_and_agentic.can_override_agent_responses}
                                    onChange={(v) => setP('channels_and_agentic', null, 'can_override_agent_responses', v)}
                                />
                                <PermSwitch
                                    label="Gestionar Skills del Agente"
                                    description="Habilitar / deshabilitar habilidades del agente departamental"
                                    checked={effective.channels_and_agentic.can_manage_skills}
                                    onChange={(v) => setP('channels_and_agentic', null, 'can_manage_skills', v)}
                                />
                            </div>
                        </div>

                        {/* ── RAG / Departamento ── */}
                        <div className="rounded-lg border p-4 space-y-3">
                            <div className="flex items-center gap-2 mb-2">
                                <BookOpen className="h-4 w-4 text-amber-500" />
                                <h4 className="font-semibold text-sm">Base de Conocimiento (RAG / Departamento)</h4>
                            </div>
                            <div className="pl-2 space-y-1 border-l-2 border-amber-200">
                                <PermSwitch
                                    label="Ver Conversaciones del Departamento"
                                    checked={effective.department_level.can_view_department_conversations}
                                    onChange={(v) => setP('department_level', null, 'can_view_department_conversations', v)}
                                />
                                <PermSwitch
                                    label="Subir Documentos al RAG Departamental"
                                    description="Agrega documentos a la base de conocimiento vectorial del departamento"
                                    checked={effective.department_level.can_upload_department_rag}
                                    onChange={(v) => setP('department_level', null, 'can_upload_department_rag', v)}
                                />
                            </div>
                        </div>
                    </div>
                )}

                <DialogFooter className="flex-col sm:flex-row gap-2 pt-4 border-t">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => resetMutation.mutate()}
                        disabled={resetMutation.isPending}
                        className="gap-1 text-muted-foreground"
                    >
                        {resetMutation.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                            <RotateCcw className="h-3 w-3" />
                        )}
                        Restablecer al Rol
                    </Button>
                    <div className="flex gap-2 ml-auto">
                        <DialogClose asChild>
                            <Button variant="outline" onClick={() => setLocalPerms(null)}>Cancelar</Button>
                        </DialogClose>
                        <Button
                            onClick={() => effective && patchMutation.mutate(effective)}
                            disabled={patchMutation.isPending || !effective}
                        >
                            {patchMutation.isPending ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Save className="h-4 w-4 mr-2" />
                            )}
                            Guardar Permisos
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────

export default function EmployeesPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { isOwner, isAdmin, canGrantWebAccess, canManageAdmins, canManageEmployees } = usePermissions();
    const { user } = useAuthStore();
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<Partial<Employee>>({});
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isBulkUploadOpen, setIsBulkUploadOpen] = useState(false);
    const [newEmployee, setNewEmployee] = useState({
        name: '',
        email: '',
        phone: '',
        role: 'general',
        department_id: '',
        has_web_access: false,
        web_email: '',
        web_password: '',
    });

    const { data: departments } = useQuery({
        queryKey: ['departments-select'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ departments: Department[] }>('/departments/');
            return data.departments;
        },
    });

    const { data: employees, isLoading } = useQuery({
        queryKey: ['employees'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ employees: Employee[] }>('/employees/');
            return data.employees;
        },
    });

    const createMutation = useMutation({
        mutationFn: async (payload: typeof newEmployee) => {
            const { data } = await apiClient.post('/employees/', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employees'] });
            toast.success(t('employees.addedSuccess'));
            setIsCreateOpen(false);
            setNewEmployee({
                name: '',
                email: '',
                phone: '',
                role: 'general',
                department_id: '',
                has_web_access: false,
                web_email: '',
                web_password: '',
            });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.error || t('common.error'));
        },
    });

    const updateMutation = useMutation({
        mutationFn: async ({ id, ...payload }: Partial<Employee> & { id: number }) => {
            const { data } = await apiClient.put(`/employees/${id}`, payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employees'] });
            toast.success(t('employees.updatedSuccess'));
            setEditingId(null);
            setEditForm({});
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await apiClient.delete(`/employees/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employees'] });
            toast.success(t('employees.removedSuccess'));
        },
        onError: () => toast.error(t('common.error')),
    });

    const startEdit = (emp: Employee) => {
        setEditingId(emp.id);
        setEditForm({
            name: emp.name,
            email: emp.email || '',
            phone: emp.phone || '',
            role: emp.role,
            department_id: emp.department_id,
            has_web_access: emp.has_web_access,
            is_available: emp.is_available,
            can_receive_calls: emp.can_receive_calls,
            can_receive_messages: emp.can_receive_messages,
            permissions: emp.permissions || {},
        });
    };

    if (isLoading) {
        return (
            <div className="space-y-6 w-full max-w-[1920px] mx-auto">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    // Default to true for any non-employee (admins, owners, or while loading context) so buttons are never blocked inadvertently
    const hasEmployeeManagementPermission = canManageEmployees || isOwner || isAdmin || (user?.role !== 'employee');

    return (
        <div className="space-y-6 md:space-y-8 w-full max-w-[1920px] mx-auto pb-12">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="flex items-center gap-2 text-2xl sm:text-3xl font-bold tracking-tight">
                        <Users className="h-6 w-6 sm:h-7 sm:w-7 text-primary shrink-0" />
                        {t('employees.title')}
                    </h2>
                    <p className="text-sm sm:text-base text-muted-foreground mt-0.5">
                        {t('employees.description')}
                    </p>
                </div>

                {hasEmployeeManagementPermission && (
                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsBulkUploadOpen(true)}
                        className="gap-1.5 h-9"
                    >
                        <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                        <span className="inline">Importar CSV / Excel</span>
                    </Button>

                    <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                        <DialogTrigger asChild>
                            <Button size="sm" className="gap-1.5 h-9 bg-primary hover:bg-primary/90 text-primary-foreground">
                                <Plus className="h-4 w-4" />
                                {t('employees.addEmployee')}
                            </Button>
                        </DialogTrigger>
                    <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>{t('employees.addTeamMember')}</DialogTitle>
                            <DialogDescription>
                                {t('employees.addTeamMemberDesc')}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="emp-name">{t('common.name')} *</Label>
                                <Input
                                    id="emp-name"
                                    value={newEmployee.name}
                                    onChange={(e) => setNewEmployee((p) => ({ ...p, name: e.target.value }))}
                                    placeholder="John Doe"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="emp-email">{t('common.email')}</Label>
                                    <Input
                                        id="emp-email"
                                        type="email"
                                        value={newEmployee.email}
                                        onChange={(e) => setNewEmployee((p) => ({ ...p, email: e.target.value }))}
                                        placeholder="john@company.com"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="emp-phone">{t('employees.phone')}</Label>
                                    <Input
                                        id="emp-phone"
                                        value={newEmployee.phone}
                                        onChange={(e) => setNewEmployee((p) => ({ ...p, phone: e.target.value }))}
                                        placeholder="+1234567890"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>{t('employees.role')}</Label>
                                    <Select
                                        value={newEmployee.role}
                                        onValueChange={(val) => setNewEmployee((p) => ({ ...p, role: val }))}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {ROLES.map((r) => (
                                                <SelectItem key={r.value} value={r.value}>
                                                    {t(`common.roles.${r.value}`)}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>{t('employees.department')}</Label>
                                    <Select
                                        value={newEmployee.department_id}
                                        onValueChange={(val) => setNewEmployee((p) => ({ ...p, department_id: val }))}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="Sin departamento" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {departments?.map((d) => (
                                                <SelectItem key={d.id} value={String(d.id)}>
                                                    {d.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Web Access Toggle — Owner only */}
                            {canGrantWebAccess ? (
                            <div className="space-y-3 pt-2 border-t">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <Label className="text-sm font-medium flex items-center gap-1.5">
                                            <Crown className="h-3.5 w-3.5 text-amber-500" />
                                            Permitir Acceso a Interfaz Web
                                        </Label>
                                        <p className="text-xs text-muted-foreground">
                                            Si se habilita, se creará una cuenta para que el usuario pueda iniciar sesión en el panel web.
                                        </p>
                                    </div>
                                    <Switch
                                        checked={newEmployee.has_web_access}
                                        onCheckedChange={(val) => setNewEmployee((p) => ({ ...p, has_web_access: val }))}
                                    />
                                </div>

                                {newEmployee.has_web_access && (
                                    <div className="grid grid-cols-2 gap-4 bg-muted/40 p-3 rounded-lg">
                                        <div className="space-y-1">
                                            <Label htmlFor="web-email" className="text-xs">Correo de Acceso Web *</Label>
                                            <Input
                                                id="web-email"
                                                type="email"
                                                value={newEmployee.web_email}
                                                onChange={(e) => setNewEmployee((p) => ({ ...p, web_email: e.target.value }))}
                                                placeholder="email@empresa.com"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label htmlFor="web-pass" className="text-xs">Contraseña Web *</Label>
                                            <Input
                                                id="web-pass"
                                                type="password"
                                                value={newEmployee.web_password}
                                                onChange={(e) => setNewEmployee((p) => ({ ...p, web_password: e.target.value }))}
                                                placeholder="Mínimo 8 caracteres"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                            ) : (
                            <div className="pt-2 border-t">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/40 rounded-lg p-3">
                                    <Lock className="h-3.5 w-3.5 shrink-0" />
                                    <span>Solo el <strong>propietario de la cuenta</strong> puede habilitar el acceso al panel web para los empleados.</span>
                                </div>
                            </div>
                            )}
                        </div>
                        <DialogFooter>
                            <DialogClose asChild>
                                <Button variant="outline">{t('common.cancel')}</Button>
                            </DialogClose>
                            <Button
                                onClick={() => createMutation.mutate(newEmployee)}
                                disabled={!newEmployee.name.trim() || createMutation.isPending}
                            >
                                {createMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <Plus className="h-4 w-4 mr-2" />
                                )}
                                {t('employees.addEmployee')}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
                </div>
                )}
            </div>

            {/* Employee List */}
            {employees && employees.length > 0 ? (
                <div className="space-y-4">
                    {employees.map((emp) => {
                        const isEditing = editingId === emp.id;

                        return (
                            <Card key={emp.id} className="overflow-hidden">
                                <CardContent className="p-6">
                                    {isEditing ? (
                                        /* EDIT MODE */
                                        <div className="space-y-4">
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                <div className="space-y-1">
                                                    <Label className="text-xs">{t('common.name')}</Label>
                                                    <Input
                                                        value={editForm.name || ''}
                                                        onChange={(e) =>
                                                            setEditForm((p) => ({ ...p, name: e.target.value }))
                                                        }
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs">{t('common.email')}</Label>
                                                    <Input
                                                        value={(editForm.email as string) || ''}
                                                        onChange={(e) =>
                                                            setEditForm((p) => ({ ...p, email: e.target.value }))
                                                        }
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs">{t('employees.phone')}</Label>
                                                    <Input
                                                        value={(editForm.phone as string) || ''}
                                                        onChange={(e) =>
                                                            setEditForm((p) => ({ ...p, phone: e.target.value }))
                                                        }
                                                    />
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                <div className="space-y-1">
                                                    <Label className="text-xs">{t('employees.role')}</Label>
                                                    <Select
                                                        value={editForm.role || 'general'}
                                                        onValueChange={(val) =>
                                                            setEditForm((p) => ({ ...p, role: val }))
                                                        }
                                                    >
                                                        <SelectTrigger>
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {ROLES.map((r) => (
                                                                <SelectItem key={r.value} value={r.value}>
                                                                    {t(`common.roles.${r.value}`)}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs">{t('employees.department')}</Label>
                                                    <Select
                                                        value={editForm.department_id ? String(editForm.department_id) : 'none'}
                                                        onValueChange={(val) =>
                                                            setEditForm((p) => ({ ...p, department_id: val === 'none' ? null : Number(val) }))
                                                        }
                                                    >
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Sin departamento" />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="none">Sin departamento</SelectItem>
                                                            {departments?.map((d) => (
                                                                <SelectItem key={d.id} value={String(d.id)}>
                                                                    {d.name}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="flex items-center gap-2 pt-5">
                                                    <Switch
                                                        checked={editForm.is_available ?? true}
                                                        onCheckedChange={(v) =>
                                                            setEditForm((p) => ({ ...p, is_available: v }))
                                                        }
                                                    />
                                                    <span className="text-sm font-medium">{t('employees.available')}</span>
                                                </div>
                                                {canGrantWebAccess ? (
                                                <div className="flex items-center gap-2 pt-5">
                                                    <Switch
                                                        checked={editForm.has_web_access ?? false}
                                                        onCheckedChange={(v) =>
                                                            setEditForm((p) => ({ ...p, has_web_access: v }))
                                                        }
                                                    />
                                                    <span className="text-sm font-medium flex items-center gap-1">
                                                        <Crown className="h-3 w-3 text-amber-500" /> Acceso Web
                                                    </span>
                                                </div>
                                                ) : (
                                                <div className="flex items-center gap-2 pt-5 opacity-60 cursor-not-allowed" title="Solo el propietario puede cambiar el acceso web">
                                                    <Switch checked={editForm.has_web_access ?? false} disabled />
                                                    <span className="text-sm font-medium flex items-center gap-1">
                                                        <Lock className="h-3 w-3" /> Acceso Web
                                                    </span>
                                                </div>
                                                )}
                                            </div>

                                            {/* Direct Permission Checks in Edit Mode */}
                                            <div className="p-3.5 bg-muted/40 rounded-xl space-y-3 border border-border">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                                        <ShieldCheck className="h-4 w-4 text-primary" />
                                                        Permisos y Canales Habilitados
                                                    </div>
                                                    <div className="text-[11px] text-muted-foreground">
                                                        (O usa el escudo 🛡️ para la matriz completa de 20+ permisos)
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-background border">
                                                        <Switch
                                                            checked={editForm.can_receive_calls ?? true}
                                                            onCheckedChange={(v) =>
                                                                setEditForm((p) => ({ ...p, can_receive_calls: v }))
                                                            }
                                                        />
                                                        <span className="text-xs font-semibold">{t('employees.calls')}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-background border">
                                                        <Switch
                                                            checked={editForm.can_receive_messages ?? true}
                                                            onCheckedChange={(v) =>
                                                                setEditForm((p) => ({ ...p, can_receive_messages: v }))
                                                            }
                                                        />
                                                        <span className="text-xs font-semibold">{t('employees.messages')}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-background border">
                                                        <Switch
                                                            checked={editForm.permissions?.integrations?.erp?.enabled ?? (editForm.role !== 'general')}
                                                            onCheckedChange={(v) =>
                                                                setEditForm((p) => ({
                                                                    ...p,
                                                                    permissions: {
                                                                        ...(p.permissions || {}),
                                                                        integrations: {
                                                                            ...(p.permissions?.integrations || {}),
                                                                            erp: { ...(p.permissions?.integrations?.erp || {}), enabled: v }
                                                                        }
                                                                    }
                                                                }))
                                                            }
                                                        />
                                                        <span className="text-xs font-semibold">Acceso ERP</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-background border">
                                                        <Switch
                                                            checked={editForm.permissions?.integrations?.crm?.enabled ?? (editForm.role !== 'general')}
                                                            onCheckedChange={(v) =>
                                                                setEditForm((p) => ({
                                                                    ...p,
                                                                    permissions: {
                                                                        ...(p.permissions || {}),
                                                                        integrations: {
                                                                            ...(p.permissions?.integrations || {}),
                                                                            crm: { ...(p.permissions?.integrations?.crm || {}), enabled: v }
                                                                        }
                                                                    }
                                                                }))
                                                            }
                                                        />
                                                        <span className="text-xs font-semibold">Acceso CRM</span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => {
                                                        setEditingId(null);
                                                        setEditForm({});
                                                    }}
                                                >
                                                    <X className="h-4 w-4 mr-1" /> {t('common.cancel')}
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={() =>
                                                        updateMutation.mutate({
                                                            id: emp.id,
                                                            ...editForm,
                                                        })
                                                    }
                                                    disabled={updateMutation.isPending}
                                                >
                                                    {updateMutation.isPending ? (
                                                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                                    ) : (
                                                        <Save className="h-4 w-4 mr-1" />
                                                    )}
                                                    {t('common.save')}
                                                </Button>
                                            </div>
                                        </div>
                                    ) : (
                                        /* VIEW MODE */
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                            <div className="flex items-start sm:items-center gap-3 sm:gap-4">
                                                <div className="flex h-10 w-10 sm:h-12 sm:w-12 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-base sm:text-lg">
                                                    {emp.name.charAt(0).toUpperCase()}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                                                        <h3 className="font-semibold text-sm sm:text-base truncate">{emp.name}</h3>
                                                        <Badge variant="secondary" className="capitalize text-[11px] sm:text-xs">
                                                            {t(`common.roles.${emp.role}`)}
                                                        </Badge>
                                                        {emp.department && (
                                                            <Badge variant="outline" className="text-[11px] sm:text-xs border-primary/30 text-primary gap-1">
                                                                <Building2 className="h-3 w-3" /> {emp.department}
                                                            </Badge>
                                                        )}
                                                        {emp.has_web_access ? (
                                                            <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[11px] sm:text-xs gap-1">
                                                                <Monitor className="h-3 w-3" /> Acceso Web
                                                            </Badge>
                                                        ) : (
                                                            <Badge variant="outline" className="text-[11px] sm:text-xs text-muted-foreground gap-1">
                                                                <MessageCircle className="h-3 w-3" /> Mensajería Only
                                                            </Badge>
                                                        )}
                                                        {emp.is_available ? (
                                                            <Badge
                                                                variant="outline"
                                                                className="border-green-500/30 text-green-600 text-[11px] sm:text-xs"
                                                            >
                                                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                                                {t('employees.available')}
                                                            </Badge>
                                                        ) : (
                                                            <Badge
                                                                variant="outline"
                                                                className="border-red-500/30 text-red-600 text-[11px] sm:text-xs"
                                                            >
                                                                <XCircle className="h-3 w-3 mr-1" />
                                                                {t('employees.unavailable')}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs sm:text-sm text-muted-foreground">
                                                        {emp.email && (
                                                            <span className="flex items-center gap-1 break-all">
                                                                <Mail className="h-3 w-3 shrink-0" />
                                                                {emp.email}
                                                            </span>
                                                        )}
                                                        {emp.phone && (
                                                            <span className="flex items-center gap-1 shrink-0">
                                                                <Phone className="h-3 w-3 shrink-0" />
                                                                {emp.phone}
                                                            </span>
                                                        )}
                                                        {emp.can_receive_calls && (
                                                            <span className="flex items-center gap-1 text-green-600 shrink-0">
                                                                <PhoneCall className="h-3 w-3 shrink-0" /> {t('employees.calls')}
                                                            </span>
                                                        )}
                                                        {emp.can_receive_messages && (
                                                            <span className="flex items-center gap-1 text-blue-600 shrink-0">
                                                                <MessageSquare className="h-3 w-3 shrink-0" /> {t('employees.messages')}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-end gap-1 shrink-0 border-t sm:border-t-0 pt-2 sm:pt-0">
                                                {/* Owner crown badge */}
                                                {emp.linked_user_is_owner && (
                                                    <span title="Propietario de la cuenta" className="flex items-center px-2">
                                                        <Crown className="h-4 w-4 text-amber-500" />
                                                    </span>
                                                )}

                                                {/* Permissions button — always visible for admins */}
                                                {canManageEmployees && <EmployeePermissionsModal employee={emp} />}

                                                {/* Edit button — hide if target is the company owner or an admin and viewer is not owner */}
                                                {canManageEmployees && (emp.linked_user_is_owner ? isOwner : (emp.linked_user_role === 'admin' ? canManageAdmins : true)) && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => startEdit(emp)}
                                                    >
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                )}

                                                {/* Delete button — hide if target is owner, or if target is admin and viewer is not owner */}
                                                {canManageEmployees && !emp.linked_user_is_owner && (emp.linked_user_role === 'admin' ? canManageAdmins : true) && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => {
                                                            if (
                                                                confirm(
                                                                    t('employees.removeConfirm', { name: emp.name })
                                                                )
                                                            )
                                                                deleteMutation.mutate(emp.id);
                                                        }}
                                                        disabled={deleteMutation.isPending}
                                                        className="text-destructive hover:text-destructive"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            ) : (
                <Card>
                    <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <Users className="h-16 w-16 text-muted-foreground/20 mb-4" />
                        <h3 className="text-xl font-semibold mb-1">{t('employees.noMembers')}</h3>
                        <p className="text-muted-foreground mb-6 max-w-md">
                            {t('employees.noMembersDesc')}
                        </p>
                        <Button onClick={() => setIsCreateOpen(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t('employees.addFirst')}
                        </Button>
                    </CardContent>
                </Card>
            )}

            {/* Bulk Upload Modal */}
            <BulkUploadDialog
                open={isBulkUploadOpen}
                onOpenChange={setIsBulkUploadOpen}
                defaultEntity="empleados"
                invalidateKeys={['employees']}
            />
        </div>
    );
}
