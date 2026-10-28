'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Phone, Mail, Calendar, MessageSquare, Send, Trash2,
    FileText, CreditCard, CalendarCheck, StickyNote, Bot,
    BotOff, Pencil, Briefcase, UserCheck, MapPin, Award, Check, X
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import apiClient from '@/lib/api-client';

// ── Types ──────────────────────────────────

interface TimelineEvent {
    type: 'message' | 'appointment' | 'payment' | 'note';
    id: number;
    timestamp: string;
    content?: string;
    title?: string;
    status?: string;
    role?: string;
    channel?: string;
    is_user?: boolean;
    amount?: number;
    currency?: string;
    description?: string;
    author?: string;
    meet_link?: string;
}

interface ContactData {
    id: number;
    first_name: string;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    status: string;
    is_ai_active: boolean;
    ident_number: string | null;
    city: string | null;
    country: string | null;
    work_company: string | null;
    buying_role: string | null;
    lead_score: number;
    funnel_stage_id: number | null;
    created_at: string;
    timeline: TimelineEvent[];
    activity?: {
        total_conversations: number;
        last_active: string | null;
        first_contact_channel?: string | null;
        first_contact_at?: string | null;
        latest_contact_channel?: string | null;
        channels_used: string[];
        touchpoints?: {
            conversation_id: number;
            channel: string;
            started_at: string | null;
            last_message_at: string | null;
            total_messages: number;
        }[];
    };
}

interface Stage {
    id: number;
    name: string;
    sort_order: number;
}

interface ContactDetailsDrawerProps {
    contactId: number | null;
    isOpen?: boolean;
    onClose: () => void;
    onUpdate?: () => void;
    onUpdated?: () => void;
}

export default function ContactDetailsDrawer({ contactId, isOpen, onClose, onUpdate, onUpdated }: ContactDetailsDrawerProps) {
    const handleUpdate = onUpdate || onUpdated;
    const effectiveIsOpen = isOpen !== undefined ? isOpen : Boolean(contactId);
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [noteContent, setNoteContent] = useState('');
    const [activeTab, setActiveTab] = useState('profile');
    const [isEditing, setIsEditing] = useState(false);

    // Edit Form State
    const [editForm, setEditForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        ident_number: '',
        city: '',
        country: '',
        work_company: '',
        buying_role: '',
    });

    // 1. Fetch Contact Details
    const { data: contact, isLoading, error } = useQuery({
        queryKey: ['customer-drawer-detail', contactId],
        queryFn: async () => {
            if (!contactId) return null;
            const { data } = await apiClient.get<{ data: ContactData }>(`/customers/${contactId}`);
            return data.data;
        },
        enabled: !!contactId && isOpen,
    });

    // 2. Fetch Funnel Stages for Manual Move
    const { data: stages } = useQuery<Stage[]>({
        queryKey: ['funnel-stages'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ stages: Stage[] }>('/crm/stages');
            return data.stages;
        },
        enabled: isOpen,
    });

    // Populate Edit Form when Contact is fetched
    useEffect(() => {
        if (contact) {
            setEditForm({
                first_name: contact.first_name || '',
                last_name: contact.last_name || '',
                email: contact.email || '',
                phone: contact.phone || '',
                ident_number: contact.ident_number || '',
                city: contact.city || '',
                country: contact.country || '',
                work_company: contact.work_company || '',
                buying_role: contact.buying_role || '',
            });
        }
        setIsEditing(false);
    }, [contact]);

    // 3. Add Note Mutation
    const addNoteMutation = useMutation({
        mutationFn: async (content: string) => {
            if (!contactId) return null;
            return apiClient.post(`/customers/${contactId}/notes`, { content });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-drawer-detail', contactId] });
            setNoteContent('');
            toast.success(t('contacts.noteAdded', { defaultValue: 'Note added successfully' }));
            handleUpdate?.();
        },
        onError: () => toast.error(t('common.error')),
    });

    // 4. Toggle AI Automated Responses Mutation
    const toggleAiMutation = useMutation({
        mutationFn: async (isActive: boolean) => {
            if (!contactId) return null;
            return apiClient.patch(`/customers/${contactId}/toggle-ai`, { is_ai_active: isActive });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-drawer-detail', contactId] });
            toast.success(t('common.success'));
            handleUpdate?.();
        },
        onError: () => toast.error(t('common.error')),
    });

    // 5. Move Funnel Stage Mutation
    const moveLeadMutation = useMutation({
        mutationFn: async (stageId: number | null) => {
            if (!contactId) return null;
            return apiClient.post('/crm/stages/move', { customer_id: contactId, stage_id: stageId });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-drawer-detail', contactId] });
            toast.success(t('contacts.stageMoved', { defaultValue: 'Lead funnel stage updated' }));
            handleUpdate?.();
        },
        onError: () => toast.error(t('common.error')),
    });

    // 6. Update Customer Fields Mutation
    const updateCustomerMutation = useMutation({
        mutationFn: async (formData: typeof editForm) => {
            if (!contactId) return null;
            return apiClient.patch(`/customers/${contactId}`, formData);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-drawer-detail', contactId] });
            setIsEditing(false);
            toast.success(t('common.success'));
            handleUpdate?.();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error'));
        },
    });

    // 7. Delete Customer Mutation
    const deleteCustomerMutation = useMutation({
        mutationFn: async () => {
            if (!contactId) return null;
            return apiClient.delete(`/customers/${contactId}`);
        },
        onSuccess: () => {
            toast.success(t('common.success'));
            onClose();
            handleUpdate?.();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error'));
        },
    });

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'message': return <MessageSquare className="h-4 w-4 text-blue-500" />;
            case 'appointment': return <CalendarCheck className="h-4 w-4 text-green-500" />;
            case 'payment': return <CreditCard className="h-4 w-4 text-purple-500" />;
            case 'note': return <StickyNote className="h-4 w-4 text-amber-500" />;
            default: return <FileText className="h-4 w-4 text-muted-foreground" />;
        }
    };

    const initials = contact ? `${contact.first_name?.[0] || ''}${contact.last_name?.[0] || ''}`.toUpperCase() : '';
    const fullName = contact ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || contact.phone || t('contacts.noName') : '';

    return (
        <Sheet open={effectiveIsOpen} onOpenChange={(open) => !open && onClose()}>
            <SheetContent side="right" className="sm:max-w-xl md:max-w-2xl w-full h-full overflow-y-auto p-0 flex flex-col bg-background border-l shadow-2xl">
                <SheetHeader className="p-6 border-b bg-muted/20 shrink-0">
                    <div className="flex justify-between items-center pr-6">
                        <div>
                            <SheetTitle className="text-xl font-bold flex items-center gap-2">
                                <UserCheck className="h-5 w-5 text-primary" />
                                {t('contacts.sheetTitle', { defaultValue: 'Prospect Details' })}
                            </SheetTitle>
                            <SheetDescription>
                                {t('contacts.sheetDesc', { defaultValue: 'View and update prospect profiling data, score, and timeline.' })}
                            </SheetDescription>
                        </div>
                    </div>
                </SheetHeader>

                <div className="flex-1 overflow-y-auto min-h-0">
                    {isLoading ? (
                        <div className="p-6 space-y-6">
                            <div className="flex items-center gap-4">
                                <Skeleton className="h-16 w-16 rounded-full" />
                                <div className="space-y-2 flex-1">
                                    <Skeleton className="h-6 w-1/3" />
                                    <Skeleton className="h-4 w-1/4" />
                                </div>
                            </div>
                            <Skeleton className="h-48 w-full rounded-2xl" />
                            <Skeleton className="h-64 w-full rounded-2xl" />
                        </div>
                    ) : error || !contact ? (
                        <div className="p-12 text-center text-muted-foreground">
                            <p>{t('contacts.notFound', { defaultValue: 'Contact not found' })}</p>
                            <Button variant="outline" size="sm" onClick={onClose} className="mt-4">
                                {t('common.close', { defaultValue: 'Close' })}
                            </Button>
                        </div>
                    ) : (
                        <div className="p-6 space-y-6">
                            {/* Profile Header Block */}
                            <div className="flex flex-col sm:flex-row items-center sm:items-start justify-between gap-4 p-5 rounded-2xl border bg-card/50">
                                <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
                                    <Avatar className="h-16 w-16 ring-2 ring-primary/10">
                                        <AvatarFallback className="text-xl font-bold bg-primary/5 text-primary">{initials}</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <h2 className="text-lg font-bold text-foreground">{fullName}</h2>
                                        <div className="flex flex-wrap justify-center sm:justify-start gap-1.5 mt-1.5">
                                            <Badge variant="secondary" className="capitalize text-[10px] py-0.5 px-2">
                                                {contact.status || 'lead'}
                                            </Badge>
                                            
                                            {/* Lead Score Badge */}
                                            <Badge 
                                                className={`text-[10px] py-0.5 px-2 border-0 font-bold ${
                                                    contact.lead_score >= 80 
                                                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' 
                                                        : contact.lead_score >= 50 
                                                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                                                            : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                                                }`}
                                            >
                                                <Award className="h-3 w-3 mr-1 shrink-0" />
                                                {contact.lead_score} pts
                                            </Badge>
                                        </div>
                                    </div>
                                </div>

                                {/* Channel & Actions */}
                                <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => {
                                            const phone = contact.phone?.replace(/\D/g, '');
                                            if (phone) window.open(`https://wa.me/${phone}`, '_blank');
                                            else toast.error(t('contacts.noPhone'));
                                        }}
                                        className="h-9 px-3 text-xs"
                                    >
                                        WhatsApp
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => {
                                            if (contact.email) window.location.href = `mailto:${contact.email}`;
                                            else toast.error(t('contacts.noEmail'));
                                        }}
                                        className="h-9 px-3 text-xs"
                                    >
                                        Email
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => {
                                            if (confirm(t('common.confirmDelete'))) {
                                                deleteCustomerMutation.mutate();
                                            }
                                        }}
                                        disabled={deleteCustomerMutation.isPending}
                                        className="h-9 w-9 text-destructive hover:bg-destructive/10 rounded-lg shrink-0"
                                        title="Eliminar prospecto"
                                    >
                                        <Trash2 className="h-4.5 w-4.5" />
                                    </Button>
                                </div>
                            </div>

                            {/* Details & Actions Tabs */}
                            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                                <TabsList className="grid w-full grid-cols-3">
                                    <TabsTrigger value="profile" className="text-xs">{t('contacts.profileTitle', 'Perfil')}</TabsTrigger>
                                    <TabsTrigger value="timeline" className="text-xs">{t('contacts.timeline', 'Historial')}</TabsTrigger>
                                    <TabsTrigger value="notes" className="text-xs">{t('contacts.notes', 'Notas')}</TabsTrigger>
                                </TabsList>

                                {/* ── Tab: Profile ── */}
                                <TabsContent value="profile" className="mt-4 space-y-4">
                                    <Card>
                                        <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0">
                                            <div>
                                                <CardTitle className="text-sm font-bold">{t('contacts.detailsCardTitle', 'Información del Prospecto')}</CardTitle>
                                                <CardDescription className="text-xs">{t('contacts.detailsCardDesc', 'Detalles demográficos, de origen y nivel B2B.')}</CardDescription>
                                            </div>
                                            {!isEditing && (
                                                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)} className="h-8 text-xs gap-1.5">
                                                    <Pencil className="h-3.5 w-3.5" />
                                                    {t('common.edit', 'Editar')}
                                                </Button>
                                            )}
                                        </CardHeader>
                                        <CardContent className="pt-4 space-y-4">
                                            {isEditing ? (
                                                /* Edit Form View */
                                                <div className="space-y-3">
                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.firstName', 'Nombre')}</Label>
                                                            <Input
                                                                value={editForm.first_name}
                                                                onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.lastName', 'Apellido')}</Label>
                                                            <Input
                                                                value={editForm.last_name}
                                                                onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('common.email', 'Correo Electrónico')}</Label>
                                                            <Input
                                                                type="email"
                                                                value={editForm.email}
                                                                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('common.phone', 'Teléfono')}</Label>
                                                            <Input
                                                                value={editForm.phone}
                                                                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.workCompany', 'Empresa / Trabajo')}</Label>
                                                            <Input
                                                                value={editForm.work_company}
                                                                onChange={(e) => setEditForm({ ...editForm, work_company: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.buyingRole', 'Cargo / Rol de Compra')}</Label>
                                                            <Input
                                                                value={editForm.buying_role}
                                                                onChange={(e) => setEditForm({ ...editForm, buying_role: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="space-y-1">
                                                        <Label className="text-xs font-semibold">{t('contacts.dni', 'Identificación (DNI / RUT)')}</Label>
                                                        <Input
                                                            value={editForm.ident_number}
                                                            onChange={(e) => setEditForm({ ...editForm, ident_number: e.target.value })}
                                                            className="h-8.5 text-xs"
                                                        />
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.city', 'Ciudad')}</Label>
                                                            <Input
                                                                value={editForm.city}
                                                                onChange={(e) => setEditForm({ ...editForm, city: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <Label className="text-xs font-semibold">{t('contacts.country', 'País')}</Label>
                                                            <Input
                                                                value={editForm.country}
                                                                onChange={(e) => setEditForm({ ...editForm, country: e.target.value })}
                                                                className="h-8.5 text-xs"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="flex gap-2 justify-end pt-3">
                                                        <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)} className="h-8 text-xs">
                                                            {t('common.cancel', 'Cancelar')}
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            onClick={() => updateCustomerMutation.mutate(editForm)}
                                                            disabled={updateCustomerMutation.isPending}
                                                            className="h-8 text-xs gap-1"
                                                        >
                                                            {updateCustomerMutation.isPending ? t('common.saving') : t('common.save', 'Guardar')}
                                                        </Button>
                                                    </div>
                                                </div>
                                            ) : (
                                                /* Read Only View */
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.email', 'Email')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><Mail className="h-3.5 w-3.5 text-muted-foreground" /> {contact.email || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.phone', 'Teléfono')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><Phone className="h-3.5 w-3.5 text-muted-foreground" /> {contact.phone || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.workCompany', 'Empresa')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><Briefcase className="h-3.5 w-3.5 text-muted-foreground" /> {contact.work_company || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.buyingRole', 'Rol / Cargo')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><UserCheck className="h-3.5 w-3.5 text-muted-foreground" /> {contact.buying_role || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.dni', 'Identificación (DNI)')}</span>
                                                        <span className="font-medium">{contact.ident_number || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.location', 'Ubicación')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5 text-muted-foreground" /> {`${contact.city || ''}${contact.city && contact.country ? ', ' : ''}${contact.country || ''}` || '—'}</span>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <span className="text-xs text-muted-foreground block">{t('contacts.registeredAtLabel', 'Fecha de Registro')}</span>
                                                        <span className="font-medium flex items-center gap-1.5"><Calendar className="h-3.5 w-3.5 text-muted-foreground" /> {contact.created_at ? format(new Date(contact.created_at), 'PPP p') : '—'}</span>
                                                    </div>
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>

                                    {/* Multi-channel Touchpoints Card */}
                                    <Card>
                                        <CardHeader className="pb-3 border-b">
                                            <CardTitle className="text-sm font-bold flex items-center justify-between">
                                                <span>{t('contacts.touchpointsTitle', 'Puntos de Contacto e Historial Multicanal')}</span>
                                                <div className="flex items-center gap-1.5">
                                                    {(contact.activity?.channels_used || []).map((ch) => (
                                                        <Badge key={ch} variant="secondary" className="capitalize text-[10px] py-0.5 px-2 font-semibold">
                                                            {ch}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </CardTitle>
                                            <CardDescription className="text-xs">
                                                {contact.activity?.first_contact_channel 
                                                    ? `Primer contacto por ${contact.activity.first_contact_channel.toUpperCase()}${contact.activity.latest_contact_channel && contact.activity.latest_contact_channel !== contact.activity.first_contact_channel ? ` • Último por ${contact.activity.latest_contact_channel.toUpperCase()}` : ''}`
                                                    : 'Canales utilizados y procedencia de las conversaciones.'}
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent className="pt-4 space-y-3">
                                            {(!contact.activity?.touchpoints || contact.activity.touchpoints.length === 0) ? (
                                                <p className="text-xs text-muted-foreground">Sin conversaciones registradas.</p>
                                            ) : (
                                                <div className="space-y-2">
                                                    {contact.activity.touchpoints.map((tp, idx) => (
                                                        <div key={tp.conversation_id || idx} className="flex items-center justify-between p-2.5 rounded-xl border bg-muted/20 text-xs">
                                                            <div className="flex items-center gap-2">
                                                                <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-wider">
                                                                    {tp.channel}
                                                                </Badge>
                                                                <span className="text-muted-foreground font-medium">
                                                                    {tp.started_at ? format(new Date(tp.started_at), 'dd/MM/yyyy HH:mm') : '—'}
                                                                </span>
                                                            </div>
                                                            <span className="text-[11px] text-muted-foreground">
                                                                {tp.total_messages} {tp.total_messages === 1 ? 'mensaje' : 'mensajes'}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>

                                    {/* Funnel Stage Selector */}
                                    <Card>
                                        <CardHeader className="pb-3 border-b">
                                            <CardTitle className="text-sm font-bold">{t('contacts.stageCardTitle', 'Estado del Embudo (Fase Kanban)')}</CardTitle>
                                            <CardDescription className="text-xs">{t('contacts.stageCardDesc', 'Mueve de fase al contacto en el embudo manualmente.')}</CardDescription>
                                        </CardHeader>
                                        <CardContent className="pt-4 space-y-4">
                                            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                                                <div className="space-y-1">
                                                    <Label className="text-xs font-semibold block">{t('contacts.stageLabel', 'Fase Actual')}</Label>
                                                    <span className="text-xs text-muted-foreground">Los agentes autónomos mueven esto según interacciones.</span>
                                                </div>
                                                <Select
                                                    value={contact.funnel_stage_id?.toString() || 'unassigned'}
                                                    onValueChange={(val) => {
                                                        const id = val === 'unassigned' ? null : parseInt(val);
                                                        moveLeadMutation.mutate(id);
                                                    }}
                                                    disabled={moveLeadMutation.isPending}
                                                >
                                                    <SelectTrigger className="w-[200px] h-9">
                                                        <SelectValue placeholder="Sin Asignar" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="unassigned">{t('contacts.unassigned', 'Sin Asignar')}</SelectItem>
                                                        {stages?.map((stage) => (
                                                            <SelectItem key={stage.id} value={stage.id.toString()}>
                                                                {stage.name}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* AI Automated Status */}
                                    <Card>
                                        <CardContent className="p-5 flex items-center justify-between">
                                            <div className="space-y-0.5">
                                                <Label className="text-sm font-semibold flex items-center gap-1.5">
                                                    {contact.is_ai_active ? <Bot className="h-4 w-4 text-primary" /> : <BotOff className="h-4 w-4 text-muted-foreground" />}
                                                    {t('contacts.aiResponses', 'Respuestas Inteligentes AI')}
                                                </Label>
                                                <p className="text-xs text-muted-foreground">{t('contacts.aiDescription', 'Permite que el agente responda automáticamente a este usuario.')}</p>
                                            </div>
                                            <Switch
                                                checked={contact.is_ai_active ?? true}
                                                onCheckedChange={(checked) => toggleAiMutation.mutate(checked)}
                                                disabled={toggleAiMutation.isPending}
                                            />
                                        </CardContent>
                                    </Card>
                                </TabsContent>

                                {/* ── Tab: Timeline ── */}
                                <TabsContent value="timeline" className="mt-4">
                                    <Card>
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-sm font-bold">{t('contacts.timelineTitle', 'Línea de Tiempo de Interacciones')}</CardTitle>
                                            <CardDescription className="text-xs">{t('contacts.timelineDesc', 'Mensajes, citas, pagos y notas registradas en orden cronológico.')}</CardDescription>
                                        </CardHeader>
                                        <CardContent>
                                            {(!contact.timeline || contact.timeline.length === 0) ? (
                                                <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed text-muted-foreground text-xs">
                                                    <p>{t('contacts.noInteractions', 'No hay interacciones registradas aún.')}</p>
                                                </div>
                                            ) : (
                                                <div className="relative border-l pl-4 ml-2 space-y-5 py-2">
                                                    {contact.timeline.slice(0, 30).map((event, idx) => (
                                                        <div key={`${event.type}-${event.id}-${idx}`} className="relative flex gap-3 items-start">
                                                            {/* Line connector dot */}
                                                            <div className="absolute -left-[23px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-background border">
                                                                <span className="h-2 w-2 rounded-full bg-primary" />
                                                            </div>

                                                            <div className="mt-0.5 p-1 rounded bg-muted/65 shrink-0">{getEventIcon(event.type)}</div>
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center gap-1.5">
                                                                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                                                            {event.type === 'message' 
                                                                                ? (event.is_user ? t('contacts.client', 'Cliente') : t('contacts.agent', 'Agente AI')) 
                                                                                : (t(`contacts.${event.type}`) || event.type)}
                                                                        </span>
                                                                        {event.channel && (
                                                                            <Badge variant="outline" className="text-[9px] py-0 px-1.5 h-4 capitalize font-medium">
                                                                                {event.channel}
                                                                            </Badge>
                                                                        )}
                                                                    </div>
                                                                    <time className="text-[10px] text-muted-foreground">
                                                                        {format(new Date(event.timestamp), 'dd/MM/yy HH:mm')}
                                                                    </time>
                                                                </div>
                                                                <p className="text-xs mt-1 text-foreground break-words font-medium">
                                                                    {event.content || event.title || event.description || `${event.amount} ${event.currency}`}
                                                                </p>
                                                                {event.meet_link && (
                                                                    <a href={event.meet_link} target="_blank" rel="noreferrer" className="text-[10px] text-blue-500 hover:underline mt-1 inline-block">
                                                                        🔗 Google Meet Link
                                                                    </a>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                </TabsContent>

                                {/* ── Tab: Notes ── */}
                                <TabsContent value="notes" className="mt-4 space-y-4">
                                    <Card>
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-sm font-bold">{t('contacts.notes', 'Notas Internas')}</CardTitle>
                                            <CardDescription className="text-xs">{t('contacts.addNote', 'Agrega notas para el equipo o registro del prospecto.')}</CardDescription>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            <div className="space-y-2">
                                                <Textarea
                                                    placeholder={t('contacts.notePlaceholder', 'Escribe una nota interna para este prospecto...')}
                                                    value={noteContent}
                                                    onChange={(e) => setNoteContent(e.target.value)}
                                                    className="min-h-[90px] text-xs"
                                                />
                                            </div>
                                            <Button
                                                onClick={() => addNoteMutation.mutate(noteContent)}
                                                disabled={!noteContent.trim() || addNoteMutation.isPending}
                                                className="w-full h-8.5 text-xs gap-1.5"
                                            >
                                                {addNoteMutation.isPending ? t('common.saving') : <><Send className="h-3.5 w-3.5" /> {t('contacts.addNote', 'Agregar Nota')}</>}
                                            </Button>
                                        </CardContent>
                                    </Card>

                                    {/* List of internal notes */}
                                    <div className="space-y-3">
                                        {contact.timeline?.filter(e => e.type === 'note').length === 0 ? (
                                            <div className="flex h-24 items-center justify-center rounded-2xl border border-dashed text-muted-foreground text-xs">
                                                <p>{t('contacts.noNotes', 'No hay notas registradas para este contacto.')}</p>
                                            </div>
                                        ) : (
                                            contact.timeline?.filter(e => e.type === 'note').map((note) => (
                                                <Card key={note.id} className="bg-muted/10">
                                                    <CardContent className="pt-4 pb-4">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
                                                                {note.author || t('contacts.system', 'Sistema')}
                                                            </span>
                                                            <time className="text-[10px] text-muted-foreground">
                                                                {format(new Date(note.timestamp), 'dd/MM/yyyy HH:mm')}
                                                            </time>
                                                        </div>
                                                        <p className="text-xs whitespace-pre-wrap text-foreground font-medium">{note.content}</p>
                                                    </CardContent>
                                                </Card>
                                            ))
                                        )}
                                    </div>
                                </TabsContent>
                            </Tabs>
                        </div>
                    )}
                </div>

                <div className="p-4 border-t bg-muted/10 shrink-0 flex justify-end">
                    <Button variant="outline" size="sm" onClick={onClose} className="h-9 text-xs">
                        {t('common.close', { defaultValue: 'Cerrar' })}
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    );
}
