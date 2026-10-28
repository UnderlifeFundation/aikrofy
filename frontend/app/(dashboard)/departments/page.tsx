'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Building2,
    Plus,
    Trash2,
    Loader2,
    Users,
    Pencil,
    Save,
    X,
    Shield,
    Database,
    Lock,
    Unlock,
    Info,
    CheckCircle2,
    AlertCircle,
    UserPlus,
    Server,
    BarChart2,
    ShoppingCart,
    ShieldCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
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

interface Department {
    id: number;
    company_id: number;
    name: string;
    description: string | null;
    pinecone_namespace: string;
    restrict_conversations: boolean;
    data_access_level?: string;
    allowed_integrations?: string[];
    is_active: boolean;
    employee_count: number;
    created_at: string;
}

interface QuotaUsage {
    departments: {
        used: number;
        limit: number;
        available: number;
        at_limit: boolean;
    };
    employees: {
        used: number;
        limit: number;
        available: number;
        at_limit: boolean;
    };
    plan: string;
}

export default function DepartmentsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [editingDept, setEditingDept] = useState<Department | null>(null);
    const [newDept, setNewDept] = useState({
        name: '',
        description: '',
        pinecone_namespace: '',
        restrict_conversations: false,
        data_access_level: 'internal',
        allowed_integrations: ['erp', 'crm', 'ecommerce'] as string[],
    });
    const [editForm, setEditForm] = useState({
        name: '',
        description: '',
        pinecone_namespace: '',
        restrict_conversations: false,
        data_access_level: 'internal',
        allowed_integrations: [] as string[],
    });

    // Fetch departments list
    const { data: deptData, isLoading } = useQuery({
        queryKey: ['departments'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ departments: Department[]; total: number }>('/departments/');
            return data;
        },
    });

    // Fetch quota usage
    const { data: quotaData } = useQuery({
        queryKey: ['departments-quota'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ quota: QuotaUsage }>('/departments/usage');
            return data.quota;
        },
    });

    // Create Department mutation
    const createMutation = useMutation({
        mutationFn: async (payload: typeof newDept) => {
            const { data } = await apiClient.post('/departments/', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['departments'] });
            queryClient.invalidateQueries({ queryKey: ['departments-quota'] });
            toast.success(t('departments.createdSuccess'));
            setIsCreateOpen(false);
            setNewDept({
                name: '',
                description: '',
                pinecone_namespace: '',
                restrict_conversations: false,
                data_access_level: 'internal',
                allowed_integrations: ['erp', 'crm', 'ecommerce'],
            });
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.error || t('common.error');
            if (error?.response?.status === 402) {
                toast.error(`${t('departments.deptLimitReached')}: ${msg}`);
            } else {
                toast.error(msg);
            }
        },
    });

    // Update Department mutation
    const updateMutation = useMutation({
        mutationFn: async ({ id, ...payload }: typeof editForm & { id: number }) => {
            const { data } = await apiClient.put(`/departments/${id}`, payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['departments'] });
            toast.success(t('departments.updatedSuccess'));
            setEditingDept(null);
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.error || t('common.error'));
        },
    });

    // Delete Department mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await apiClient.delete(`/departments/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['departments'] });
            queryClient.invalidateQueries({ queryKey: ['departments-quota'] });
            toast.success(t('departments.deletedSuccess'));
        },
        onError: () => toast.error(t('common.error')),
    });

    const startEdit = (dept: Department) => {
        setEditingDept(dept);
        setEditForm({
            name: dept.name,
            description: dept.description || '',
            pinecone_namespace: dept.pinecone_namespace || '',
            restrict_conversations: dept.restrict_conversations,
            data_access_level: dept.data_access_level || 'internal',
            allowed_integrations: dept.allowed_integrations || ['erp', 'crm', 'ecommerce'],
        });
    };

    if (isLoading) {
        return (
            <div className="space-y-6 max-w-6xl mx-auto">
                <Skeleton className="h-10 w-64" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Skeleton className="h-28" />
                    <Skeleton className="h-28" />
                    <Skeleton className="h-28" />
                </div>
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    const departments = deptData?.departments || [];
    const deptQuota = quotaData?.departments;
    const empQuota = quotaData?.employees;

    return (
        <div className="space-y-8 max-w-6xl mx-auto pb-12">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
                        <Building2 className="h-7 w-7 text-primary" />
                        {t('departments.title')}
                    </h2>
                    <p className="text-muted-foreground mt-1">
                        {t('departments.description')}
                    </p>
                </div>

                <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                    <DialogTrigger asChild>
                        <Button disabled={deptQuota?.at_limit}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t('departments.createBtn')}
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-lg">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <Building2 className="h-5 w-5 text-primary" />
                                {t('departments.createTitle')}
                            </DialogTitle>
                            <DialogDescription>
                                {t('departments.createDesc')}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="dept-name">{t('common.name')} *</Label>
                                <Input
                                    id="dept-name"
                                    value={newDept.name}
                                    onChange={(e) => setNewDept((p) => ({ ...p, name: e.target.value }))}
                                    placeholder="Ventas / Soporte / HR"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="dept-desc">{t('common.description')}</Label>
                                <Textarea
                                    id="dept-desc"
                                    value={newDept.description}
                                    onChange={(e) => setNewDept((p) => ({ ...p, description: e.target.value }))}
                                    placeholder="Breve descripción"
                                    rows={3}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="dept-ns" className="flex items-center gap-1.5">
                                     <Database className="h-4 w-4 text-muted-foreground" />
                                     {t('departments.customNs')}
                                 </Label>
                                 <Input
                                     id="dept-ns"
                                     value={newDept.pinecone_namespace}
                                     onChange={(e) => setNewDept((p) => ({ ...p, pinecone_namespace: e.target.value }))}
                                     placeholder="Auto-generated if empty"
                                 />
                                 <p className="text-xs text-muted-foreground">
                                     {t('departments.autoNsNotice')}
                                 </p>
                             </div>

                            {/* Data Access Level RBAC */}
                            <div className="space-y-2 pt-2 border-t">
                                <Label className="flex items-center gap-1.5 text-sm font-semibold">
                                    <ShieldCheck className="h-4 w-4 text-primary" />
                                    Nivel de Acceso y Sensibilidad de Datos
                                </Label>
                                <Select
                                    value={newDept.data_access_level}
                                    onValueChange={(val) => setNewDept((p) => ({ ...p, data_access_level: val }))}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Seleccionar nivel" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="public">Público (Accesible para toda la empresa)</SelectItem>
                                        <SelectItem value="internal">Interno (Solo miembros del departamento)</SelectItem>
                                        <SelectItem value="confidential">Confidencial (Requiere permisos explícitos)</SelectItem>
                                        <SelectItem value="restricted">Restringido (Solo administradores / Dueño)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Allowed Integrations RBAC */}
                            <div className="space-y-2 pt-2 border-t">
                                <Label className="text-sm font-semibold">Integraciones y Recursos Habilitados</Label>
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { id: 'erp', label: 'ERP', icon: Server },
                                        { id: 'crm', label: 'CRM', icon: BarChart2 },
                                        { id: 'ecommerce', label: 'E-Commerce', icon: ShoppingCart },
                                    ].map((res) => {
                                        const isChecked = newDept.allowed_integrations.includes(res.id);
                                        const Icon = res.icon;
                                        return (
                                            <button
                                                key={res.id}
                                                type="button"
                                                onClick={() => {
                                                    setNewDept((p) => ({
                                                        ...p,
                                                        allowed_integrations: isChecked
                                                            ? p.allowed_integrations.filter((x) => x !== res.id)
                                                            : [...p.allowed_integrations, res.id],
                                                    }));
                                                }}
                                                className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                                                    isChecked
                                                        ? 'border-primary bg-primary/10 text-primary font-bold'
                                                        : 'border-border text-muted-foreground hover:bg-muted/50'
                                                }`}
                                            >
                                                <Icon className="h-3.5 w-3.5" />
                                                {res.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="flex items-center justify-between pt-2 border-t">
                                <div className="space-y-0.5">
                                    <Label className="text-sm font-medium flex items-center gap-1.5">
                                        <Lock className="h-4 w-4 text-amber-500" />
                                        {t('departments.restrictConv')}
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t('departments.restrictConvDesc')}
                                    </p>
                                </div>
                                <Switch
                                    checked={newDept.restrict_conversations}
                                    onCheckedChange={(val) => setNewDept((p) => ({ ...p, restrict_conversations: val }))}
                                />
                            </div>
                        </div>

                        <DialogFooter>
                            <DialogClose asChild>
                                <Button variant="outline">{t('common.cancel')}</Button>
                            </DialogClose>
                            <Button
                                onClick={() => createMutation.mutate(newDept)}
                                disabled={!newDept.name.trim() || createMutation.isPending}
                            >
                                {createMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <Plus className="h-4 w-4 mr-2" />
                                )}
                                {t('common.create')}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Quota Overview Cards */}
            {quotaData && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="bg-card/50 border-border">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
                                <span>{t('departments.usedDepts')}</span>
                                <Building2 className="h-4 w-4 text-primary" />
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {deptQuota?.used} / {deptQuota?.limit}
                            </div>
                            <Progress
                                value={((deptQuota?.used || 0) / (deptQuota?.limit || 1)) * 100}
                                className="h-2 mt-2"
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                                {deptQuota?.at_limit
                                    ? t('departments.deptLimitReached')
                                    : t('departments.availableDepts', { count: deptQuota?.available })}
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="bg-card/50 border-border">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
                                <span>{t('departments.registeredEmployees')}</span>
                                <Users className="h-4 w-4 text-blue-500" />
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {empQuota?.used} / {empQuota?.limit}
                            </div>
                            <Progress
                                value={((empQuota?.used || 0) / (empQuota?.limit || 1)) * 100}
                                className="h-2 mt-2"
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                                {t('departments.availableEmpSlots', { count: empQuota?.available })}
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="bg-card/50 border-border">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
                                <span>{t('departments.subTier')}</span>
                                <Shield className="h-4 w-4 text-emerald-500" />
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold uppercase text-primary">
                                {quotaData.plan}
                            </div>
                            <p className="text-xs text-muted-foreground mt-3">
                                {t('departments.multiTenantNotice')}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Department List */}
            {departments.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {departments.map((dept) => {
                        const isEditing = editingDept?.id === dept.id;

                        return (
                            <Card key={dept.id} className="relative overflow-hidden border-border/80 hover:border-primary/40 transition-all">
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div className="space-y-1">
                                            <CardTitle className="flex items-center gap-2 text-xl flex-wrap">
                                                <Building2 className="h-5 w-5 text-primary" />
                                                {dept.name}
                                                {dept.restrict_conversations && (
                                                    <Badge variant="outline" className="border-amber-500/40 text-amber-600 text-xs gap-1">
                                                        <Lock className="h-3 w-3" /> {t('departments.privateBadge')}
                                                    </Badge>
                                                )}
                                                {dept.data_access_level && (
                                                    <Badge variant="secondary" className="text-xs uppercase font-semibold">
                                                        {dept.data_access_level}
                                                    </Badge>
                                                )}
                                            </CardTitle>
                                            <CardDescription className="line-clamp-2">
                                                {dept.description || '—'}
                                            </CardDescription>
                                        </div>

                                        <div className="flex items-center gap-1">
                                            <Button variant="ghost" size="icon" onClick={() => startEdit(dept)}>
                                                <Pencil className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-destructive hover:text-destructive"
                                                onClick={() => {
                                                    if (confirm(t('departments.deleteConfirm', { name: dept.name }))) {
                                                        deleteMutation.mutate(dept.id);
                                                    }
                                                }}
                                                disabled={deleteMutation.isPending}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                </CardHeader>

                                <CardContent className="space-y-4">
                                    <div className="bg-muted/40 p-3 rounded-lg space-y-2 text-sm">
                                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Database className="h-3.5 w-3.5 text-primary" /> {t('departments.ragNamespaceLabel')}
                                            </span>
                                            <code className="font-mono bg-background px-1.5 py-0.5 rounded border text-[11px]">
                                                {dept.pinecone_namespace}
                                            </code>
                                        </div>

                                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Users className="h-3.5 w-3.5 text-blue-500" /> {t('departments.integratedEmployees')}
                                            </span>
                                            <Badge variant="secondary" className="font-bold">
                                                {dept.employee_count}
                                            </Badge>
                                        </div>

                                        {dept.allowed_integrations && dept.allowed_integrations.length > 0 && (
                                            <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t border-border/50">
                                                <span>Recursos:</span>
                                                <div className="flex gap-1">
                                                    {dept.allowed_integrations.map((slug) => (
                                                        <Badge key={slug} variant="outline" className="text-[10px] uppercase">
                                                            {slug}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {isEditing && (
                                        <Dialog open={true} onOpenChange={() => setEditingDept(null)}>
                                            <DialogContent className="max-w-lg">
                                                <DialogHeader>
                                                    <DialogTitle>{t('departments.editDeptTitle', { name: dept.name })}</DialogTitle>
                                                </DialogHeader>
                                                <div className="space-y-4 py-4">
                                                    <div className="space-y-2">
                                                        <Label>{t('common.name')}</Label>
                                                        <Input
                                                            value={editForm.name}
                                                            onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label>{t('common.description')}</Label>
                                                        <Textarea
                                                            value={editForm.description}
                                                            onChange={(e) => setEditForm((p) => ({ ...p, description: e.target.value }))}
                                                            rows={3}
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label>{t('departments.customNs')}</Label>
                                                        <Input
                                                            value={editForm.pinecone_namespace}
                                                            onChange={(e) => setEditForm((p) => ({ ...p, pinecone_namespace: e.target.value }))}
                                                        />
                                                    </div>

                                                    {/* Data Access Level RBAC Edit */}
                                                    <div className="space-y-2 pt-2 border-t">
                                                        <Label className="flex items-center gap-1.5 text-sm font-semibold">
                                                            <ShieldCheck className="h-4 w-4 text-primary" />
                                                            Nivel de Acceso y Sensibilidad
                                                        </Label>
                                                        <Select
                                                            value={editForm.data_access_level}
                                                            onValueChange={(val) => setEditForm((p) => ({ ...p, data_access_level: val }))}
                                                        >
                                                            <SelectTrigger>
                                                                <SelectValue placeholder="Seleccionar nivel" />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="public">Público (Toda la empresa)</SelectItem>
                                                                <SelectItem value="internal">Interno (Solo el departamento)</SelectItem>
                                                                <SelectItem value="confidential">Confidencial (Con permisos)</SelectItem>
                                                                <SelectItem value="restricted">Restringido (Solo admin/owner)</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </div>

                                                    {/* Allowed Integrations RBAC Edit */}
                                                    <div className="space-y-2 pt-2 border-t">
                                                        <Label className="text-sm font-semibold">Integraciones Habilitadas</Label>
                                                        <div className="grid grid-cols-3 gap-2">
                                                            {[
                                                                { id: 'erp', label: 'ERP', icon: Server },
                                                                { id: 'crm', label: 'CRM', icon: BarChart2 },
                                                                { id: 'ecommerce', label: 'E-Commerce', icon: ShoppingCart },
                                                            ].map((res) => {
                                                                const isChecked = editForm.allowed_integrations?.includes(res.id);
                                                                const Icon = res.icon;
                                                                return (
                                                                    <button
                                                                        key={res.id}
                                                                        type="button"
                                                                        onClick={() => {
                                                                            setEditForm((p) => ({
                                                                                ...p,
                                                                                allowed_integrations: isChecked
                                                                                    ? (p.allowed_integrations || []).filter((x) => x !== res.id)
                                                                                    : [...(p.allowed_integrations || []), res.id],
                                                                            }));
                                                                        }}
                                                                        className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                                                                            isChecked
                                                                                ? 'border-primary bg-primary/10 text-primary font-bold'
                                                                                : 'border-border text-muted-foreground hover:bg-muted/50'
                                                                        }`}
                                                                    >
                                                                        <Icon className="h-3.5 w-3.5" />
                                                                        {res.label}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center justify-between pt-2 border-t">
                                                        <Label>{t('departments.restrictConv')}</Label>
                                                        <Switch
                                                            checked={editForm.restrict_conversations}
                                                            onCheckedChange={(v) => setEditForm((p) => ({ ...p, restrict_conversations: v }))}
                                                        />
                                                    </div>
                                                </div>
                                                <DialogFooter>
                                                    <Button variant="outline" onClick={() => setEditingDept(null)}>
                                                        {t('common.cancel')}
                                                    </Button>
                                                    <Button
                                                        onClick={() => updateMutation.mutate({ id: dept.id, ...editForm })}
                                                        disabled={updateMutation.isPending}
                                                    >
                                                        {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                                        {t('common.save')}
                                                    </Button>
                                                </DialogFooter>
                                            </DialogContent>
                                        </Dialog>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            ) : (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <Building2 className="h-16 w-16 text-muted-foreground/20 mb-4" />
                        <h3 className="text-xl font-semibold mb-1">{t('departments.noDeptsTitle')}</h3>
                        <p className="text-muted-foreground mb-6 max-w-md">
                            {t('departments.noDeptsDesc')}
                        </p>
                        <Button onClick={() => setIsCreateOpen(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t('departments.createFirstDept')}
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
