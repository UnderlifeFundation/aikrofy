'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
    Users,
    CheckCircle,
    XCircle,
    Clock,
    Sparkles,
    Shield,
    Mail,
    Phone,
    Building2,
    Briefcase,
    Key,
    Coins,
    Search,
    RefreshCw,
    Trash2
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import apiClient from '@/lib/api-client';
import type { BetaLead, PlatformConfig } from '@/types';

export default function AdminBetaPage() {
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedLead, setSelectedLead] = useState<BetaLead | null>(null);
    const [creditsToGrant, setCreditsToGrant] = useState<number>(1500);
    const [approvalModalOpen, setApprovalModalOpen] = useState(false);
    const [approvalResult, setApprovalResult] = useState<{ tempPassword?: string; emailSent?: boolean } | null>(null);

    // Fetch Beta status / config
    const { data: config } = useQuery({
        queryKey: ['admin-platform-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: PlatformConfig }>('/admin/config');
            return data.data;
        }
    });

    // Toggle Beta Mode Mutation
    const toggleBetaMutation = useMutation({
        mutationFn: async (enabled: boolean) => {
            await apiClient.put('/admin/config', { beta_mode: enabled });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-platform-config'] });
            toast.success('Estado del Modo Beta actualizado');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al actualizar el modo Beta');
        }
    });

    // Fetch Beta Leads
    const { data: leads = [], isLoading } = useQuery({
        queryKey: ['admin-beta-leads'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: BetaLead[] }>('/beta/leads');
            return data.data;
        }
    });

    // Approve Lead Mutation
    const approveMutation = useMutation({
        mutationFn: async ({ leadId, credits }: { leadId: number; credits: number }) => {
            const { data } = await apiClient.post(`/beta/leads/${leadId}/approve`, { credits });
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['admin-beta-leads'] });
            setApprovalResult({
                tempPassword: data.temp_password,
                emailSent: data.email_sent
            });
            toast.success('Prospecto aprobado correctamente');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al aprobar prospecto');
        }
    });

    // Reject Lead Mutation
    const rejectMutation = useMutation({
        mutationFn: async (leadId: number) => {
            await apiClient.post(`/beta/leads/${leadId}/reject`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-beta-leads'] });
            toast.info('Prospecto marcado como rechazado');
        }
    });

    // Reactivate Lead Mutation
    const reactivateMutation = useMutation({
        mutationFn: async (leadId: number) => {
            await apiClient.post(`/beta/leads/${leadId}/reactivate`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-beta-leads'] });
            toast.success('Prospecto reactivado a Pendiente');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al reactivar prospecto');
        }
    });

    // Delete Lead Mutation
    const deleteMutation = useMutation({
        mutationFn: async (leadId: number) => {
            await apiClient.delete(`/beta/leads/${leadId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-beta-leads'] });
            toast.success('Prospecto eliminado permanentemente');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al eliminar prospecto');
        }
    });

    const filteredLeads = leads.filter(l =>
        l.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.contact_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.industry.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const pendingCount = leads.filter(l => l.status === 'pending').length;
    const approvedCount = leads.filter(l => l.status === 'approved').length;

    return (
        <div className="space-y-8">
            {/* Header & Controls */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <h2 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
                        <Sparkles className="h-7 w-7 text-indigo-500" />
                        Gestión de Beta Privada y Prospectos
                    </h2>
                    <p className="text-muted-foreground">
                        Controla el acceso restrictivo a la plataforma y gestiona las solicitudes del formulario de descubrimiento.
                    </p>
                </div>

                {/* Beta Switch Box */}
                <Card className="border-indigo-500/20 bg-indigo-500/5 sm:w-auto">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div>
                            <div className="text-sm font-semibold flex items-center gap-1.5">
                                <Shield className="h-4 w-4 text-indigo-500" />
                                Modo Beta Privada
                            </div>
                            <div className="text-xs text-muted-foreground">
                                {config?.beta_mode ? 'Restringido a cuentas aprobadas' : 'Registro abierto al público'}
                            </div>
                        </div>
                        <Switch
                            checked={config?.beta_mode || false}
                            onCheckedChange={(checked) => toggleBetaMutation.mutate(checked)}
                        />
                    </CardContent>
                </Card>
            </div>

            {/* Metrics Cards */}
            <div className="grid gap-4 sm:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Solicitudes Pendientes</CardTitle>
                        <Clock className="h-5 w-5 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{pendingCount}</div>
                        <p className="text-xs text-muted-foreground">Esperando revisión y aprobación</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Accesos Aprobados</CardTitle>
                        <CheckCircle className="h-5 w-5 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{approvedCount}</div>
                        <p className="text-xs text-muted-foreground">Empresas invitadas a la Beta</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Total Solicitudes</CardTitle>
                        <Users className="h-5 w-5 text-indigo-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{leads.length}</div>
                        <p className="text-xs text-muted-foreground">Prospectos descubiertos</p>
                    </CardContent>
                </Card>
            </div>

            {/* Prospect Table List */}
            <Card>
                <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <CardTitle className="text-lg font-bold">Solicitudes de Registro Beta</CardTitle>
                        <CardDescription>Prospectos empresariales que completaron el formulario dinámico</CardDescription>
                    </div>

                    <div className="relative w-full sm:w-72">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Buscar empresa, contacto o email..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-9"
                        />
                    </div>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="p-8 text-center text-muted-foreground">Cargando prospectos...</div>
                    ) : filteredLeads.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">No se encontraron solicitudes registradas.</div>
                    ) : (
                        <div className="space-y-4">
                            {filteredLeads.map((lead) => (
                                <div key={lead.id} className="flex flex-col gap-4 rounded-xl border p-4 hover:border-indigo-500/30 transition-all sm:flex-row sm:items-center sm:justify-between bg-card">
                                    <div className="space-y-1.5 flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-bold text-base flex items-center gap-1.5">
                                                <Building2 className="h-4 w-4 text-indigo-500" />
                                                {lead.company_name}
                                            </span>
                                            <Badge variant="outline" className="text-xs">
                                                {lead.industry}
                                            </Badge>
                                            <Badge variant="secondary" className="text-xs">
                                                {lead.employee_count} emp.
                                            </Badge>
                                            {lead.status === 'pending' && <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20">Pendiente</Badge>}
                                            {lead.status === 'approved' && <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Aprobado</Badge>}
                                            {lead.status === 'rejected' && <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20">Rechazado</Badge>}
                                        </div>

                                        <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                                            <span className="flex items-center gap-1">
                                                <Users className="h-3.5 w-3.5" /> {lead.contact_name} ({lead.role_in_company})
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Mail className="h-3.5 w-3.5" /> {lead.email}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Phone className="h-3.5 w-3.5" /> {lead.phone}
                                            </span>
                                        </div>

                                        {/* Discovery details */}
                                        <div className="mt-2 rounded-lg bg-accent/40 p-3 text-xs space-y-1.5">
                                            {lead.products_services && (
                                                <p><strong>Productos/Servicios:</strong> {lead.products_services}</p>
                                            )}
                                            {lead.ai_experience && (
                                                <p>
                                                    <strong>Nivel Adopción IA:</strong>{' '}
                                                    <span className="capitalize">
                                                        {lead.ai_experience === 'none' ? 'Nivel Inicial / Primera Vez (ChatGPT puntual)' :
                                                         lead.ai_experience === 'intermediate' ? 'Nivel Intermedio (Make, Zapier, Chatbots)' :
                                                         lead.ai_experience === 'advanced' ? 'Nivel Avanzado (Flujos automatizados / Agentes)' :
                                                         lead.ai_experience}
                                                    </span>
                                                </p>
                                            )}
                                            {lead.ai_results_satisfaction && (
                                                <p>
                                                    <strong>Resultados / Exp. Previa:</strong>{' '}
                                                    <span>
                                                        {lead.ai_results_satisfaction === 'positive' ? 'Altamente Positiva (Se cumplieron expectativas)' :
                                                         lead.ai_results_satisfaction === 'neutral' ? 'Media / Parcial (Se logró algo pero falta inteligencia)' :
                                                         lead.ai_results_satisfaction === 'negative' ? 'Frustrante / Deficiente (No funcionó)' :
                                                         lead.ai_results_satisfaction === 'not_applicable' ? 'No hemos aplicado IA aún' :
                                                         lead.ai_results_satisfaction}
                                                    </span>
                                                </p>
                                            )}
                                            {lead.ai_expectations && (
                                                <p><strong>Expectativas IA:</strong> {lead.ai_expectations}</p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex items-center gap-2 shrink-0">
                                        {lead.status === 'pending' && (
                                            <>
                                                <Button
                                                    size="sm"
                                                    className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1"
                                                    onClick={() => {
                                                        setSelectedLead(lead);
                                                        setApprovalResult(null);
                                                        setApprovalModalOpen(true);
                                                    }}
                                                >
                                                    <CheckCircle className="h-4 w-4" /> Aprobar Acceso
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    title="Rechazar solicitud"
                                                    className="text-rose-500 hover:text-rose-600 hover:bg-rose-50"
                                                    onClick={() => rejectMutation.mutate(lead.id)}
                                                >
                                                    <XCircle className="h-4 w-4" />
                                                </Button>
                                            </>
                                        )}
                                        {lead.status === 'rejected' && (
                                            <>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    title="Reactivar y pasar a Pendiente"
                                                    className="text-indigo-500 hover:text-indigo-600 hover:bg-indigo-50 gap-1 text-xs"
                                                    onClick={() => reactivateMutation.mutate(lead.id)}
                                                >
                                                    <RefreshCw className="h-3.5 w-3.5" /> Reactivar
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    title="Eliminar registro permanentemente"
                                                    className="text-rose-500 hover:text-rose-600 hover:bg-rose-50"
                                                    onClick={() => {
                                                        if (confirm(`¿Seguro que deseas borrar permanentemente el registro de ${lead.company_name}?`)) {
                                                            deleteMutation.mutate(lead.id);
                                                        }
                                                    }}
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </>
                                        )}
                                        {lead.status === 'approved' && (
                                            <div className="flex items-center gap-3">
                                                <div className="text-xs text-emerald-500 font-semibold flex items-center gap-1">
                                                    <Coins className="h-4 w-4" /> {lead.credits_granted} créditos
                                                </div>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    title="Eliminar de la lista"
                                                    className="text-muted-foreground hover:text-rose-500"
                                                    onClick={() => {
                                                        if (confirm(`¿Seguro que deseas eliminar permanentemente la solicitud de ${lead.company_name}?`)) {
                                                            deleteMutation.mutate(lead.id);
                                                        }
                                                    }}
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Approval Modal */}
            <Dialog open={approvalModalOpen} onOpenChange={setApprovalModalOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-indigo-500" />
                            Aprobar Acceso a la Beta
                        </DialogTitle>
                        <DialogDescription>
                            Habilitarás el acceso para <strong className="text-foreground">{selectedLead?.company_name}</strong> ({selectedLead?.email}).
                        </DialogDescription>
                    </DialogHeader>

                    {!approvalResult ? (
                        <div className="space-y-4 py-3">
                            <div className="space-y-2">
                                <label className="text-sm font-semibold flex items-center gap-1.5">
                                    <Coins className="h-4 w-4 text-amber-500" />
                                    Créditos de Bienvenida Asignados
                                </label>
                                <Input
                                    type="number"
                                    value={creditsToGrant}
                                    onChange={(e) => setCreditsToGrant(Number(e.target.value))}
                                    placeholder="100"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Se otorgarán estos créditos a la empresa recién creada.
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4 py-3">
                            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 space-y-2">
                                <div className="font-semibold text-emerald-500 text-sm flex items-center gap-1.5">
                                    <CheckCircle className="h-4 w-4" /> ¡Acceso Aprobado Exitosamente!
                                </div>
                                <div className="text-xs space-y-1">
                                    <p><strong>Contraseña Provisional:</strong> <code className="bg-background px-1.5 py-0.5 rounded font-mono text-sm">{approvalResult.tempPassword}</code></p>
                                    <p><strong>Correo Enviado:</strong> {approvalResult.emailSent ? 'Sí (Notificación con credenciales)' : 'No (Configura el canal email)'}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        {!approvalResult ? (
                            <Button
                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
                                onClick={() => {
                                    if (selectedLead) {
                                        approveMutation.mutate({ leadId: selectedLead.id, credits: creditsToGrant });
                                    }
                                }}
                                disabled={approveMutation.isPending}
                            >
                                {approveMutation.isPending ? 'Aprobando...' : 'Confirmar Aprobación & Crear Cuenta'}
                            </Button>
                        ) : (
                            <Button className="w-full" onClick={() => setApprovalModalOpen(false)}>
                                Cerrar
                            </Button>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
