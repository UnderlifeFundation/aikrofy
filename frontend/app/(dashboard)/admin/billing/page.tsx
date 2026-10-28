'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    CreditCard,
    Plus,
    Users,
    Zap,
    Coins,
    Key,
    Loader2,
    ShieldCheck,
    CheckCircle2,
    Package,
    Pencil,
    Trash2,
    X,
    Save,
    CalendarClock,
    Clock,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import { Plan, Company } from '@/types';

export default function AdminBillingPage() {
    const router = useRouter();
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const user = useAuthStore((s) => s.user);
    const [isPlanDialogOpen, setIsPlanDialogOpen] = useState(false);
    const [isCourtesyDialogOpen, setIsCourtesyDialogOpen] = useState(false);
    const [editingPlanId, setEditingPlanId] = useState<number | null>(null);

    // Guard
    useEffect(() => {
        if (user && user.role !== 'super_admin') {
            router.replace('/dashboard');
        }
    }, [user, router]);

    // Default features template
    const defaultFeatures = {
        max_agents: 1,
        max_documents: 10,
        max_leads: 100,
        monthly_credits: 1000,
        channels: ['whatsapp'] as string[],
        integrations: [] as string[],
        rag_enabled: true,
        analytics_enabled: false,
        voice_enabled: false,
        scheduling_enabled: true,
        payments_enabled: false,
    };

    // Form States
    const [planData, setPlanData] = useState({
        name: '',
        description: '',
        amount: 29.99,
        features: { ...defaultFeatures }
    });

    const [editData, setEditData] = useState<{
        name: string;
        description: string;
        price_monthly: number;
        features: typeof defaultFeatures;
    }>({ name: '', description: '', price_monthly: 0, features: { ...defaultFeatures } });

    const [courtesyData, setCourtesyData] = useState({
        name: '',
        email: ''
    });

    // Membership config state: { [companyId]: { mode, amount, type, demoDays } }
    const [courtesyCreditConfig, setCourtesyCreditConfig] = useState<Record<number, { mode: 'unlimited' | 'limited'; amount: number; type?: 'courtesy' | 'demo'; demoDays?: number }>>({});

    // Fetch ALL plans
    const { data: plans, isLoading } = useQuery({
        queryKey: ['admin-plans'],
        queryFn: async () => {
            const { data } = await apiClient.get<Plan[]>('/admin/plans');
            return data;
        },
        enabled: user?.role === 'super_admin',
    });

    // Create Plan
    const createPlanMutation = useMutation({
        mutationFn: async (data: typeof planData) => {
            await apiClient.post('/admin/plans', data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
            toast.success(t('admin.planCreated'));
            setIsPlanDialogOpen(false);
            setPlanData({ 
                name: '', 
                description: '', 
                amount: 29.99, 
                features: { ...defaultFeatures }
            });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('admin.planCreateError'));
        }
    });

    // Update Plan
    const updatePlanMutation = useMutation({
        mutationFn: async ({ id, data }: { id: number; data: typeof editData }) => {
            await apiClient.put(`/admin/plans/${id}`, {
                name: data.name,
                description: data.description,
                amount: data.price_monthly,
                features: data.features
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
            toast.success(t('admin.planUpdated'));
            setEditingPlanId(null);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || error.message || t('admin.planUpdateError'));
        }
    });

    // Delete (Deactivate) Plan
    const deletePlanMutation = useMutation({
        mutationFn: async (planId: number) => {
            await apiClient.delete(`/admin/plans/${planId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
            toast.success(t('admin.planDeactivated'));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('admin.planDeleteError'));
        }
    });

    // Fetch ALL Tenants
    const { data: tenants, isLoading: isLoadingTenants } = useQuery({
        queryKey: ['admin-tenants'],
        queryFn: async () => {
            const { data } = await apiClient.get<Company[]>('/admin/tenants');
            return data;
        },
        enabled: user?.role === 'super_admin',
    });

    // Toggle Courtesy / Demo License
    const toggleCourtesyMutation = useMutation({
        mutationFn: async ({ id, is_courtesy, is_demo, demo_days, credit_mode, credit_amount }: { id: number, is_courtesy: boolean, is_demo?: boolean, demo_days?: number, credit_mode?: string, credit_amount?: number }) => {
            await apiClient.patch(`/admin/tenants/${id}/courtesy`, { is_courtesy, is_demo, demo_days, credit_mode, credit_amount });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
            toast.success(t('admin.membershipUpdated', { defaultValue: 'Membership updated successfully.' }));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('admin.courtesyToggleError'));
        }
    });
    
    // Toggle Agency Mode (Multi-tenant capabilities)
    const toggleAgencyMutation = useMutation({
        mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
            await apiClient.patch(`/admin/tenants/${id}/agency`, { enabled });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
            toast.success('Facultad de Agencia actualizada con éxito');
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || 'Error al actualizar el modo agencia');
        }
    });

    // Delete Tenant
    const deleteTenantMutation = useMutation({
        mutationFn: async (id: number) => {
            await apiClient.delete(`/admin/tenants/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
            toast.success(t('admin.deleteCompanySuccess'));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('admin.deleteCompanyError'));
        }
    });

    const startEditing = (plan: Plan) => {
        setEditingPlanId(plan.id);
        const pf = (plan.features || {}) as any;
        setEditData({
            name: plan.name,
            description: plan.description || '',
            price_monthly: plan.price_monthly,
            features: {
                max_agents: pf.max_agents ?? 1,
                max_documents: pf.max_documents ?? 10,
                max_leads: pf.max_leads ?? 100,
                monthly_credits: pf.monthly_credits ?? 100,
                channels: pf.channels ?? ['whatsapp'],
                integrations: pf.integrations ?? [],
                rag_enabled: pf.rag_enabled ?? true,
                analytics_enabled: pf.analytics_enabled ?? false,
                voice_enabled: pf.voice_enabled ?? false,
                scheduling_enabled: pf.scheduling_enabled ?? true,
                payments_enabled: pf.payments_enabled ?? false,
            }
        });
    };

    const cancelEditing = () => {
        setEditingPlanId(null);
    };

    const saveEditing = () => {
        if (editingPlanId) {
            updatePlanMutation.mutate({ id: editingPlanId, data: editData });
        }
    };

    if (user?.role !== 'super_admin') {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <p className="text-lg text-muted-foreground">{t('common.accessDenied')}</p>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-6xl space-y-8">
            {/* Header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
                        <CreditCard className="h-7 w-7 text-primary" />
                        {t('admin.billingTitle')}
                    </h2>
                    <p className="text-muted-foreground">
                        {t('admin.billingDescription')}
                    </p>
                </div>
                <div className="flex gap-2">
                    {/* New Plan Dialog */}
                    <Dialog open={isPlanDialogOpen} onOpenChange={setIsPlanDialogOpen}>
                        <DialogTrigger asChild>
                            <Button className="gap-2">
                                <Plus className="h-4 w-4" />
                                {t('admin.newPlan')}
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                            <form onSubmit={(e) => {
                                e.preventDefault();
                                createPlanMutation.mutate(planData);
                            }}>
                                <DialogHeader>
                                    <DialogTitle>{t('admin.createPlanTitle')}</DialogTitle>
                                    <DialogDescription>
                                        {t('admin.createPlanDescription')}
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid gap-5 py-4">
                                    {/* Basic Info */}
                                    <div className="grid gap-2">
                                        <Label htmlFor="p-name">{t('admin.planName')}</Label>
                                        <Input id="p-name" placeholder={t('admin.planNamePlaceholder')} required value={planData.name} onChange={e => setPlanData({...planData, name: e.target.value})} />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="p-desc">{t('admin.planDescription')}</Label>
                                        <Textarea id="p-desc" placeholder={t('admin.planDescriptionPlaceholder')} value={planData.description} onChange={e => setPlanData({...planData, description: e.target.value})} />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="p-amount">{t('admin.monthlyPrice')}</Label>
                                            <Input id="p-amount" type="number" step="0.01" required value={planData.amount} onChange={e => setPlanData({...planData, amount: parseFloat(e.target.value)})} />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label>{t('admin.frequency')}</Label>
                                            <Badge variant="secondary" className="w-fit mt-2">{t('admin.monthly')}</Badge>
                                        </div>
                                    </div>

                                    {/* Limits */}
                                    <div className="border rounded-lg p-4 space-y-3">
                                        <h4 className="font-semibold text-sm flex items-center gap-2"><Zap className="h-4 w-4 text-primary" />{t('admin.planLimits', { defaultValue: 'Plan Limits' })}</h4>
                                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                            <div className="space-y-1">
                                                <Label className="text-xs">{t('planFeatures.max_agents', { defaultValue: 'Max Agents' })}</Label>
                                                <Input type="number" min={1} value={planData.features.max_agents} onChange={e => setPlanData({...planData, features: {...planData.features, max_agents: parseInt(e.target.value) || 1}})} className="h-8" />
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs">{t('planFeatures.max_documents', { defaultValue: 'Max Documents' })}</Label>
                                                <Input type="number" min={1} value={planData.features.max_documents} onChange={e => setPlanData({...planData, features: {...planData.features, max_documents: parseInt(e.target.value) || 1}})} className="h-8" />
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs">{t('planFeatures.max_leads', { defaultValue: 'Max Leads' })}</Label>
                                                <Input type="number" min={1} value={planData.features.max_leads} onChange={e => setPlanData({...planData, features: {...planData.features, max_leads: parseInt(e.target.value) || 1}})} className="h-8" />
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs flex items-center gap-1"><Coins className="h-3 w-3" />{t('planFeatures.monthly_credits', { defaultValue: 'Monthly Credits' })}</Label>
                                                <Input type="number" min={0} value={planData.features.monthly_credits} onChange={e => setPlanData({...planData, features: {...planData.features, monthly_credits: parseInt(e.target.value) || 0}})} className="h-8" />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Channels */}
                                    <div className="border rounded-lg p-4 space-y-3">
                                        <h4 className="font-semibold text-sm">{t('admin.planChannels', { defaultValue: 'Channels' })}</h4>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                            {['whatsapp', 'telegram', 'email', 'google', 'webchat'].map(ch => (
                                                <label key={ch} className="flex items-center gap-2 text-sm cursor-pointer">
                                                    <input type="checkbox" checked={planData.features.channels.includes(ch)} onChange={e => {
                                                        const channels = e.target.checked ? [...planData.features.channels, ch] : planData.features.channels.filter(c => c !== ch);
                                                        setPlanData({...planData, features: {...planData.features, channels}});
                                                    }} className="rounded border-gray-300" />
                                                    <span className="capitalize">{t(`planFeatures.channel_${ch}`, { defaultValue: ch })}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Integrations */}
                                    <div className="border rounded-lg p-4 space-y-3">
                                        <h4 className="font-semibold text-sm">{t('admin.planIntegrations', { defaultValue: 'Integrations' })}</h4>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                            {['crm', 'paypal', 'twilio'].map(ig => (
                                                <label key={ig} className="flex items-center gap-2 text-sm cursor-pointer">
                                                    <input type="checkbox" checked={planData.features.integrations.includes(ig)} onChange={e => {
                                                        const integrations = e.target.checked ? [...planData.features.integrations, ig] : planData.features.integrations.filter(i => i !== ig);
                                                        setPlanData({...planData, features: {...planData.features, integrations}});
                                                    }} className="rounded border-gray-300" />
                                                    <span className="capitalize">{t(`planFeatures.integration_${ig}`, { defaultValue: ig })}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Capabilities */}
                                    <div className="border rounded-lg p-4 space-y-3">
                                        <h4 className="font-semibold text-sm">{t('admin.planCapabilities', { defaultValue: 'Capabilities' })}</h4>
                                        <div className="grid grid-cols-2 gap-3">
                                            {([
                                                ['rag_enabled', 'RAG / Knowledge Base'],
                                                ['analytics_enabled', 'Analytics Dashboard'],
                                                ['voice_enabled', 'Voice Calls'],
                                                ['scheduling_enabled', 'Scheduling / Calendar'],
                                                ['payments_enabled', 'Payment Processing'],
                                            ] as const).map(([key, label]) => (
                                                <div key={key} className="flex items-center justify-between gap-2">
                                                    <Label className="text-xs font-normal">{t(`planFeatures.${key}`, { defaultValue: label })}</Label>
                                                    <Switch checked={(planData.features as any)[key]} onCheckedChange={val => setPlanData({...planData, features: {...planData.features, [key]: val}})} />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button type="submit" disabled={createPlanMutation.isPending}>
                                        {createPlanMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t('admin.createPlanButton')}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {/* Plans Table */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        {t('admin.plansTitle')}
                    </CardTitle>
                    <CardDescription>
                        {t('admin.plansDescription')}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : !plans?.length ? (
                        <div className="text-center py-12 text-muted-foreground">
                            {t('admin.noPlans')}
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t('common.name')}</TableHead>
                                    <TableHead>{t('common.description')}</TableHead>
                                    <TableHead>{t('common.price')}</TableHead>
                                    <TableHead>{t('common.status')}</TableHead>
                                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {plans.map((plan) => (
                                    <TableRow key={plan.id}>
                                        <TableCell className="font-medium">
                                            {editingPlanId === plan.id ? (
                                                <Input
                                                    value={editData.name}
                                                    onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                                                    className="h-8 w-40"
                                                />
                                            ) : t(`planNames.${plan.name}`, plan.name)}
                                        </TableCell>
                                        <TableCell className="max-w-[400px]">
                                            {editingPlanId === plan.id ? (
                                                <div className="flex flex-col gap-3">
                                                    <Input value={editData.description} onChange={(e) => setEditData({ ...editData, description: e.target.value })} className="h-8" placeholder={t('admin.shortDescription')} />
                                                    {/* Inline Feature Editor */}
                                                    <div className="border rounded-lg p-3 space-y-3 bg-muted/30">
                                                        <div className="grid grid-cols-4 gap-2">
                                                            {(['max_agents', 'max_documents', 'max_leads', 'monthly_credits'] as const).map(k => (
                                                                <div key={k} className="space-y-0.5">
                                                                    <Label className="text-[10px]">{t(`planFeatures.${k}`, { defaultValue: k.replace(/_/g, ' ') })}</Label>
                                                                    <Input type="number" min={0} value={(editData.features as any)[k]} onChange={e => setEditData({...editData, features: {...editData.features, [k]: parseInt(e.target.value) || 0}})} className="h-7 text-xs" />
                                                                </div>
                                                            ))}
                                                        </div>
                                                        <div className="flex flex-wrap gap-2 pt-1">
                                                            {['whatsapp','telegram','email','google','webchat'].map(ch => (
                                                                <label key={ch} className="flex items-center gap-1 text-[10px] cursor-pointer">
                                                                    <input type="checkbox" checked={editData.features.channels.includes(ch)} onChange={e => { const channels = e.target.checked ? [...editData.features.channels, ch] : editData.features.channels.filter(c => c !== ch); setEditData({...editData, features: {...editData.features, channels}}); }} className="rounded" />
                                                                    <span className="capitalize">{ch}</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                        <div className="flex flex-wrap gap-2">
                                                            {['crm','paypal','twilio'].map(ig => (
                                                                <label key={ig} className="flex items-center gap-1 text-[10px] cursor-pointer">
                                                                    <input type="checkbox" checked={editData.features.integrations.includes(ig)} onChange={e => { const integrations = e.target.checked ? [...editData.features.integrations, ig] : editData.features.integrations.filter(i => i !== ig); setEditData({...editData, features: {...editData.features, integrations}}); }} className="rounded" />
                                                                    <span className="capitalize">{ig}</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                        <div className="grid grid-cols-2 gap-1">
                                                            {(['rag_enabled','analytics_enabled','voice_enabled','scheduling_enabled','payments_enabled'] as const).map(k => (
                                                                <div key={k} className="flex items-center justify-between">
                                                                    <span className="text-[10px] capitalize">{k.replace(/_enabled/, '')}</span>
                                                                    <Switch checked={(editData.features as any)[k]} onCheckedChange={val => setEditData({...editData, features: {...editData.features, [k]: val}})} />
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="flex flex-col gap-1">
                                                    <span className="truncate block font-semibold text-sm">
                                                        {t(`planDescriptions.${plan.name}`, plan.description || '—')}
                                                    </span>
                                                    {plan.features && (
                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                            {Object.entries(plan.features as any).map(([k, v]) => (
                                                                <Badge key={k} variant="outline" className="text-[10px] py-0 h-5 px-1.5 font-normal">
                                                                    {t(`planFeatures.${k.replace(/ /g, '_')}`, k.replace(/_/g, ' '))}: {
                                                                        Array.isArray(v) ? (v as string[]).join(', ') :
                                                                        typeof v === 'boolean' ? (v ? '✓' : '✗') : String(v)
                                                                    }
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {editingPlanId === plan.id ? (
                                                <Input
                                                    type="number"
                                                    step="0.01"
                                                    value={editData.price_monthly}
                                                    onChange={(e) => setEditData({ ...editData, price_monthly: parseFloat(e.target.value) })}
                                                    className="h-8 w-24"
                                                />
                                            ) : `$${plan.price_monthly}${t('common.perMonth')}`}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={plan.is_active ? "outline" : "secondary"} className={plan.is_active ? "text-green-600 border-green-600" : ""}>
                                                {plan.is_active ? t('common.active') : t('common.inactive')}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {editingPlanId === plan.id ? (
                                                <div className="flex justify-end gap-1">
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        onClick={saveEditing}
                                                        disabled={updatePlanMutation.isPending}
                                                        className="h-8 w-8 text-green-600"
                                                    >
                                                        {updatePlanMutation.isPending
                                                            ? <Loader2 className="h-4 w-4 animate-spin" />
                                                            : <Save className="h-4 w-4" />
                                                        }
                                                    </Button>
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        onClick={cancelEditing}
                                                        className="h-8 w-8"
                                                    >
                                                        <X className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="flex justify-end gap-1">
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        onClick={() => startEditing(plan)}
                                                        className="h-8 w-8"
                                                    >
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                    {plan.is_active && (
                                                        <Button
                                                            size="icon"
                                                            variant="ghost"
                                                            className="h-8 w-8 text-destructive hover:text-destructive"
                                                            onClick={() => {
                                                                if (confirm(t('admin.deactivatePlanConfirm', { name: plan.name }))) {
                                                                    deletePlanMutation.mutate(plan.id);
                                                                }
                                                            }}
                                                            disabled={deletePlanMutation.isPending}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    )}
                                                </div>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Super Admin Token & Credit Consumption Breakdown across all Channels */}
            <AdminCreditsBreakdownSection />

            {/* Tenants Table */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        {t('admin.companiesTitle')}
                    </CardTitle>
                    <CardDescription>
                        {t('admin.companiesDescription')}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoadingTenants ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : !tenants?.length ? (
                        <div className="text-center py-12 text-muted-foreground">
                            {t('admin.noCompanies')}
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t('admin.company')}</TableHead>
                                    <TableHead>{t('common.email')}</TableHead>
                                    <TableHead>{t('admin.currentPlan')}</TableHead>
                                    <TableHead>{t('admin.subscription')}</TableHead>
                                    <TableHead>{t('admin.agencyMode', { defaultValue: 'Modo Agencia' })}</TableHead>
                                    <TableHead>{t('admin.membershipType', { defaultValue: 'Membership' })}</TableHead>
                                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {tenants.map((dist) => (
                                    <TableRow key={dist.id}>
                                        <TableCell>
                                            <div className="font-medium">{dist.name}</div>
                                            <div className="text-xs text-muted-foreground">
                                                {t('admin.registered')}: {new Date(dist.created_at).toLocaleDateString()}
                                            </div>
                                        </TableCell>
                                        <TableCell>{dist.user_email || dist.email || '—'}</TableCell>
                                        <TableCell>
                                            {dist.plan_name ? (
                                                <Badge variant="outline">{dist.plan_name}</Badge>
                                            ) : (
                                                <span className="text-muted-foreground">—</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {dist.subscription_active ? (
                                                <Badge className="bg-green-500 tracking-wide text-[10px] uppercase">{t('common.active')}</Badge>
                                            ) : (
                                                <Badge variant="secondary" className="tracking-wide text-[10px] uppercase">{t('common.inactive')}</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex flex-col gap-1.5">
                                                <div className="flex items-center gap-2">
                                                    <Switch
                                                        checked={Boolean((dist as any).is_agency)}
                                                        onCheckedChange={(checked) => {
                                                            toggleAgencyMutation.mutate({ id: dist.id, enabled: checked });
                                                        }}
                                                        disabled={toggleAgencyMutation.isPending}
                                                    />
                                                    <span className={`text-xs font-semibold ${Boolean((dist as any).is_agency) ? 'text-violet-600 dark:text-violet-400' : 'text-muted-foreground'}`}>
                                                        {Boolean((dist as any).is_agency) ? '🏢 Agencia' : 'Estándar'}
                                                    </span>
                                                </div>
                                                {Boolean((dist as any).is_agency) && (
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="text-[10px] text-muted-foreground">Cupo:</span>
                                                        <select
                                                            className="text-[11px] border border-border rounded px-1.5 py-0.5 bg-background text-foreground"
                                                            defaultValue={String((dist as any).agency_max_companies ?? 10)}
                                                            onChange={(e) => {
                                                                const val = parseInt(e.target.value);
                                                                apiClient.patch(`/admin/tenants/${dist.id}/agency`, { 
                                                                    enabled: true, 
                                                                    max_companies: val 
                                                                }).then(() => {
                                                                    queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
                                                                    toast.success(`Cupo actualizado: ${val === -1 ? 'Ilimitado' : val + ' empresas'}`);
                                                                });
                                                            }}
                                                        >
                                                            <option value="3">Starter (3)</option>
                                                            <option value="10">Pro (10)</option>
                                                            <option value="25">Scale (25)</option>
                                                            <option value="-1">Enterprise (∞)</option>
                                                        </select>
                                                    </div>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {(() => {
                                                const currentType = courtesyCreditConfig[dist.id]?.type ?? (dist.is_demo ? 'demo' : (dist.is_courtesy ? 'courtesy' : undefined));
                                                const derivedAmount = dist.credit_balance === -1 ? 1000 : (dist.credit_balance || 500);
                                                const config = courtesyCreditConfig[dist.id] || { mode: (dist.credit_balance === -1 ? 'unlimited' : 'limited') as 'unlimited' | 'limited', amount: derivedAmount, type: currentType, demoDays: 7 };
                                                
                                                const setConfig = (patch: Partial<typeof config>) => {
                                                    setCourtesyCreditConfig(prev => ({...prev, [dist.id]: { ...config, ...prev[dist.id], ...patch }}));
                                                };
                                                
                                                const handleSave = () => {
                                                    const finalType = courtesyCreditConfig[dist.id]?.type ?? currentType;
                                                    const c = courtesyCreditConfig[dist.id] || config;
                                                    toggleCourtesyMutation.mutate({
                                                        id: dist.id,
                                                        is_courtesy: finalType === 'courtesy',
                                                        is_demo: finalType === 'demo',
                                                        demo_days: c.demoDays || 7,
                                                        credit_mode: finalType === 'courtesy' ? c.mode : 'limited',
                                                        credit_amount: c.amount || 500,
                                                    });
                                                };
                                                
                                                return (
                                                    <div className="flex flex-col gap-2 min-w-[200px]">
                                                        {/* Status badges */}
                                                        <div className="flex items-center gap-1.5">
                                                            {dist.is_demo && (
                                                                <Badge variant="outline" className="text-[10px] py-0 h-5 border-amber-500 text-amber-600">
                                                                    <Clock className="h-2.5 w-2.5 mr-0.5" />
                                                                    Demo
                                                                </Badge>
                                                            )}
                                                            {dist.is_courtesy && !dist.is_demo && (
                                                                <Badge variant="outline" className="text-[10px] py-0 h-5 border-blue-500 text-blue-600">
                                                                    <ShieldCheck className="h-2.5 w-2.5 mr-0.5" />
                                                                    {t('admin.courtesy', { defaultValue: 'Courtesy' })}
                                                                </Badge>
                                                            )}
                                                            {dist.is_demo && dist.demo_expires_at && (
                                                                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                                                                    <CalendarClock className="h-2.5 w-2.5" />
                                                                    {new Date(dist.demo_expires_at) < new Date() 
                                                                        ? <span className="text-destructive font-semibold">{t('admin.demoExpired', { defaultValue: 'Expired' })}</span>
                                                                        : new Date(dist.demo_expires_at).toLocaleDateString()}
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Type selector */}
                                                        <select
                                                            className="h-7 text-[11px] rounded-md border bg-background px-1.5 w-full"
                                                            value={currentType || 'none'}
                                                            onChange={e => {
                                                                const val = e.target.value as 'none' | 'courtesy' | 'demo';
                                                                setConfig({ type: val === 'none' ? undefined : val });
                                                                if (val === 'none') {
                                                                    toggleCourtesyMutation.mutate({ id: dist.id, is_courtesy: false, is_demo: false });
                                                                }
                                                            }}
                                                        >
                                                            <option value="none">{t('admin.membershipNone', { defaultValue: '— None —' })}</option>
                                                            <option value="courtesy">{t('admin.membershipCourtesy', { defaultValue: '🛡️ Courtesy (Permanent)' })}</option>
                                                            <option value="demo">{t('admin.membershipDemo', { defaultValue: '⏳ Demo (Time-Limited)' })}</option>
                                                        </select>

                                                        {/* Courtesy sub-controls */}
                                                        {currentType === 'courtesy' && (
                                                            <div className="flex items-center gap-1.5 flex-wrap">
                                                                <select
                                                                    className="h-7 text-[10px] rounded-md border bg-background px-1.5"
                                                                    value={config.mode}
                                                                    onChange={e => setConfig({ mode: e.target.value as any })}
                                                                >
                                                                    <option value="unlimited">{t('admin.courtesyUnlimited', { defaultValue: '∞ Unlimited' })}</option>
                                                                    <option value="limited">{t('admin.courtesyLimited', { defaultValue: 'Limited' })}</option>
                                                                </select>
                                                                {config.mode === 'limited' && (
                                                                    <Input type="number" min={1} className="h-7 w-20 text-[10px]" placeholder="Credits" value={config.amount} onChange={e => setConfig({ amount: parseInt(e.target.value) || 0 })} />
                                                                )}
                                                                <Button size="sm" variant="outline" className="h-7 text-[10px] px-2" onClick={handleSave} disabled={toggleCourtesyMutation.isPending}>
                                                                    {toggleCourtesyMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                                                                </Button>
                                                            </div>
                                                        )}

                                                        {/* Demo sub-controls */}
                                                        {currentType === 'demo' && (
                                                            <div className="flex items-center gap-1.5 flex-wrap">
                                                                <div className="flex items-center gap-1">
                                                                    <CalendarClock className="h-3 w-3 text-muted-foreground" />
                                                                    <Input type="number" min={1} max={365} className="h-7 w-16 text-[10px]" placeholder="Days" value={config.demoDays ?? 7} onChange={e => setConfig({ demoDays: parseInt(e.target.value) || 7 })} />
                                                                    <span className="text-[10px] text-muted-foreground">{t('admin.days', { defaultValue: 'days' })}</span>
                                                                </div>
                                                                <div className="flex items-center gap-1">
                                                                    <Coins className="h-3 w-3 text-muted-foreground" />
                                                                    <Input type="number" min={1} className="h-7 w-20 text-[10px]" placeholder="Credits" value={config.amount} onChange={e => setConfig({ amount: parseInt(e.target.value) || 0 })} />
                                                                </div>
                                                                <Button size="sm" variant="outline" className="h-7 text-[10px] px-2" onClick={handleSave} disabled={toggleCourtesyMutation.isPending}>
                                                                    {toggleCourtesyMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                                                                </Button>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })()}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                size="icon"
                                                variant="ghost"
                                                className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                                onClick={() => {
                                                    if (confirm(t('admin.deleteCompanyConfirm', { name: dist.name }))) {
                                                        deleteTenantMutation.mutate(dist.id);
                                                    }
                                                }}
                                                disabled={deleteTenantMutation.isPending}
                                            >
                                                {deleteTenantMutation.isPending && deleteTenantMutation.variables === dist.id ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <Trash2 className="h-4 w-4" />
                                                )}
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Info Cards */}
            <div className="grid gap-6 md:grid-cols-2">
                <Card className="bg-green-500/5 border-green-500/10 shadow-none">
                    <CardHeader>
                        <CardTitle className="text-sm flex items-center gap-2 text-green-700">
                            <ShieldCheck className="h-4 w-4" />
                            System Status
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                            <span className="font-medium">All systems operational</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Infrastructure is running normally. Multi-tenant isolation is active.
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-blue-500/5 border-blue-500/10 shadow-none">
                    <CardHeader>
                        <CardTitle className="text-sm flex items-center gap-2 text-blue-700">
                            <Users className="h-4 w-4" />
                            {t('admin.courtesyTitle')}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm leading-relaxed">
                            {t('admin.courtesyNote')}
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function AdminCreditsBreakdownSection() {
    const { data, isLoading } = useQuery({
        queryKey: ['admin-credits-breakdown'],
        queryFn: async () => {
            const res = await apiClient.get<{ success: boolean; data: any[]; summary: any }>('/admin/credits-breakdown');
            return res.data;
        },
        refetchInterval: 30000,
    });

    const tenants = data?.data || [];

    return (
        <Card className="border-indigo-500/20 shadow-lg">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Coins className="h-5 w-5 text-amber-500" />
                        <CardTitle className="text-xl font-bold">Consumo de Créditos & Tokens por Cuenta</CardTitle>
                    </div>
                    <CardDescription className="mt-1">
                        Auditoría en tiempo real de combustible IA, saldo actual y volumen consumido por canal (Webchat, WhatsApp, Telegram, Copiloto, Voz).
                    </CardDescription>
                </div>
                {data?.summary && (
                    <div className="flex gap-2">
                        <div className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400">
                            Empresas: <span className="font-bold text-foreground">{data.summary.total_tenants}</span>
                        </div>
                        <div className="px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-xs font-semibold text-purple-400">
                            Mensajes IA: <span className="font-bold text-foreground">{data.summary.total_platform_messages?.toLocaleString()}</span>
                        </div>
                    </div>
                )}
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : tenants.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-6">No hay cuentas registradas con interacciones aún.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr className="border-b border-border/80 text-muted-foreground font-semibold">
                                    <th className="pb-3 pr-4">Empresa / Admin</th>
                                    <th className="pb-3 px-3">Plan / Tier</th>
                                    <th className="pb-3 px-3">Saldo Créditos</th>
                                    <th className="pb-3 px-3 text-center">Webchat Widget</th>
                                    <th className="pb-3 px-3 text-center">WhatsApp</th>
                                    <th className="pb-3 px-3 text-center">Copilot Admin</th>
                                    <th className="pb-3 px-3 text-center">Telegram</th>
                                    <th className="pb-3 pl-3 text-right">Total Msgs</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/40">
                                {tenants.map((tenant: any) => (
                                    <tr key={tenant.company_id} className="hover:bg-muted/30 transition-colors">
                                        <td className="py-3.5 pr-4">
                                            <div className="font-bold text-foreground text-sm">{tenant.company_name}</div>
                                            <div className="text-muted-foreground text-[11px]">{tenant.admin_email}</div>
                                        </td>
                                        <td className="py-3.5 px-3">
                                            <span className="capitalize px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border">
                                                {tenant.subscription_tier || 'Free'} ({tenant.plan_type})
                                            </span>
                                        </td>
                                        <td className="py-3.5 px-3">
                                            {tenant.is_unlimited ? (
                                                <span className="text-emerald-400 font-black text-xs">Ilimitado (-1)</span>
                                            ) : (
                                                <span className={`font-bold text-xs ${tenant.credit_balance < 50 ? 'text-rose-400' : 'text-foreground'}`}>
                                                    {tenant.credit_balance?.toLocaleString()} créditos
                                                </span>
                                            )}
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.webchat?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.whatsapp?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.admin_chat?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 px-3 text-center">
                                            <span className="font-mono font-medium">{tenant.channels?.telegram?.messages || 0}</span>
                                        </td>
                                        <td className="py-3.5 pl-3 text-right font-black text-foreground">
                                            {tenant.total_messages?.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
