'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import {
  Building2, Plus, ShieldCheck, Zap,
  ArrowRight, Link as LinkIcon, Mail, CheckCircle2,
  Clock, Unlink, AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';

export default function AgencyDashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [isCreating, setIsCreating] = useState(false);
  const [isLinking, setIsLinking] = useState(false);
  
  // Provisioning state
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyEmail, setNewCompanyEmail] = useState('');
  const [newCompanyPhone, setNewCompanyPhone] = useState('');
  const [newCompanyIndustry, setNewCompanyIndustry] = useState('Comercio / Servicios');

  // Linking state
  const [linkEmail, setLinkEmail] = useState('');

  // Fetch agency portfolio
  const { data, isLoading } = useQuery({
    queryKey: ['agency-companies'],
    queryFn: async () => {
      const res = await apiClient.get('/agency/companies');
      return res.data;
    },
    enabled: !!user,
  });

  // Provision new company under standard platform quotas
  const createCompanyMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/agency/companies', {
        name: newCompanyName,
        email: newCompanyEmail,
        phone: newCompanyPhone,
        industry: newCompanyIndustry,
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success(t('agency.toastNewCompanySuccess', '¡Nueva empresa cliente dada de alta con cuota estándar de la plataforma!'));
      setIsCreating(false);
      setNewCompanyName('');
      setNewCompanyEmail('');
      setNewCompanyPhone('');
      queryClient.invalidateQueries({ queryKey: ['agency-companies'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.error || t('agency.toastNewCompanyError', 'Error al aprovisionar empresa cliente'));
    },
  });

  // Invite existing registered company
  const inviteCompanyMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/agency/invite-company', {
        email: linkEmail.trim(),
      });
      return res.data;
    },
    onSuccess: (res: any) => {
      toast.success(res.message || t('agency.toastInviteSuccess', 'Solicitud de vinculación enviada por correo'));
      setIsLinking(false);
      setLinkEmail('');
      queryClient.invalidateQueries({ queryKey: ['agency-companies'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.error || t('agency.toastInviteError', 'Error al enviar invitación'));
    },
  });

  // Unlink company
  const unlinkCompanyMutation = useMutation({
    mutationFn: async (companyId: number) => {
      const res = await apiClient.post(`/agency/companies/${companyId}/unlink`);
      return res.data;
    },
    onSuccess: () => {
      toast.success(t('agency.toastUnlinkSuccess', 'Empresa desvinculada exitosamente. Los datos del cliente permanecen intactos.'));
      queryClient.invalidateQueries({ queryKey: ['agency-companies'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.error || t('agency.toastUnlinkError', 'Error al desvincular empresa'));
    },
  });

  const switchCompany = async (companyId: number, companyName: string) => {
    try {
      await apiClient.post(`/agency/companies/${companyId}/switch`);
      localStorage.setItem('aikrofy_active_company_id', String(companyId));
      toast.success(t('agency.toastSwitchSuccess', { name: companyName, defaultValue: `Accediendo al panel de: ${companyName}` }));
      queryClient.invalidateQueries();
      router.push('/dashboard');
    } catch {
      toast.error(t('agency.toastSwitchError', 'No se pudo cambiar al espacio de la empresa'));
    }
  };

  const companies: any[] = data?.companies || [];
  const activeCompanies = companies.filter((c) => c.is_active && c.status !== 'pending_approval');
  const pendingCompanies = companies.filter((c) => c.status === 'pending_approval');
  const totalCreditsAllocated = activeCompanies.reduce((acc, c) => acc + (c.credit_balance || 0), 0);

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl border border-violet-500/20 bg-gradient-to-r from-violet-500/10 via-purple-500/5 to-slate-500/10 dark:from-violet-950/40 dark:via-purple-900/10 dark:to-slate-950/80 shadow-xl">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20">
            <ShieldCheck className="w-4 h-4 text-violet-600 dark:text-violet-400" />
            <span>{t('agency.badge', 'Licencia Multiempresa • Portal de Agencia')}</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-black text-foreground tracking-tight">
            {t('agency.title', 'Gestión Multicuenta de Clientes')}
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl font-normal leading-relaxed">
            {t('agency.subtitle', 'Administra empresas clientes de forma centralizada con aislamiento total (Row-Level Multi-tenant Isolation). Las empresas pueden aprovisionarse bajo tu gestión o autorizar vinculación manteniendo su cuenta intacta.')}
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap shrink-0">
          <Button
            onClick={() => {
              setIsLinking(true);
              setIsCreating(false);
            }}
            variant="outline"
            className="border-violet-500/30 hover:bg-violet-500/10 text-violet-700 dark:text-violet-300 font-semibold text-xs gap-2 px-3.5 py-2.5 rounded-xl cursor-pointer"
          >
            <LinkIcon className="w-4 h-4" />
            <span>{t('agency.linkExisting', 'Vincular Empresa Existente')}</span>
          </Button>
          <Button
            onClick={() => {
              setIsCreating(true);
              setIsLinking(false);
            }}
            className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs gap-2 px-4 py-2.5 rounded-xl shadow-lg shadow-violet-600/30 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{t('agency.provisionNew', 'Dar de Alta Empresa')}</span>
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-card border border-border shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold">
            <span>{t('agency.managedCompanies', 'Empresas Administradas')}</span>
            <Building2 className="w-4 h-4 text-violet-600 dark:text-violet-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-foreground">{activeCompanies.length}</div>
          <p className="text-[11px] text-muted-foreground">{t('agency.managedCompaniesDesc', 'Instancias tenant activas bajo gestión')}</p>
        </div>

        <div className="p-5 rounded-2xl bg-card border border-border shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold">
            <span>{t('agency.pendingRequests', 'Solicitudes Pendientes')}</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-amber-600 dark:text-amber-400">
            {pendingCompanies.length}
          </div>
          <p className="text-[11px] text-muted-foreground">{t('agency.pendingRequestsDesc', 'Esperando confirmación por correo')}</p>
        </div>

        <div className="p-5 rounded-2xl bg-card border border-border shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold">
            <span>{t('agency.walletCredits', 'Combustible IA en Cartera')}</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-amber-600 dark:text-amber-400">
            {totalCreditsAllocated.toLocaleString()}
          </div>
          <p className="text-[11px] text-muted-foreground">{t('agency.walletCreditsDesc', 'Créditos de combustible distribuidos')}</p>
        </div>
      </div>

      {/* Quota Usage Bar */}
      {data?.home_company?.agency_max_companies > 0 && (
        <div className="p-4 rounded-2xl bg-card border border-border shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted-foreground">{t('agency.quotaUsed', 'Cupo de Empresas Utilizado')}</span>
            <span className="text-xs font-bold text-foreground">
              {activeCompanies.length} / {data?.home_company?.agency_max_companies === -1 ? '∞' : data?.home_company?.agency_max_companies}
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                data?.home_company?.agency_max_companies !== -1 && 
                activeCompanies.length / data?.home_company?.agency_max_companies >= 0.9
                  ? 'bg-red-500'
                  : activeCompanies.length / data?.home_company?.agency_max_companies >= 0.7
                  ? 'bg-amber-500'
                  : 'bg-violet-600'
              }`}
              style={{
                width: data?.home_company?.agency_max_companies === -1 
                  ? '30%' 
                  : `${Math.min(100, (activeCompanies.length / data?.home_company?.agency_max_companies) * 100)}%`
              }}
            />
          </div>
          {data?.home_company?.agency_max_companies !== -1 && 
           activeCompanies.length >= data?.home_company?.agency_max_companies && (
            <p className="text-[11px] text-red-500 mt-1 font-semibold">
              {t('agency.quotaLimitReached', '⚠️ Has alcanzado el límite de tu plan. Contacta a soporte para ampliar tu cupo.')}
            </p>
          )}
        </div>
      )}

      {/* Modal / Inline Link Existing Company */}
      {isLinking && (
        <div className="p-6 sm:p-8 rounded-3xl border border-violet-500/30 bg-card space-y-5 shadow-xl animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-violet-600 dark:text-violet-400" />
              <span>{t('agency.linkModalTitle', 'Solicitar Vinculación a Empresa Registrada')}</span>
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsLinking(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t('agency.cancel', 'Cancelar')}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed">
            {t('agency.linkModalDesc', 'Ingresa el correo electrónico con el que la empresa cliente ya está registrada en Aikrofy. Le enviaremos un correo formal con un enlace cifrado seguro para que el propietario autorice la administración de su cuenta.')}
          </p>

          <div className="space-y-2 max-w-md">
            <Label className="text-xs text-muted-foreground font-semibold">{t('agency.companyEmailLabel', 'Correo de la Empresa Cliente')}</Label>
            <Input
              type="email"
              value={linkEmail}
              onChange={(e) => setLinkEmail(e.target.value)}
              placeholder={t('agency.companyEmailPlaceholder', 'cliente@empresa.com')}
              className="bg-background border-border text-xs text-foreground"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLinking(false)}
              className="border-border text-foreground text-xs"
            >
              {t('agency.cancel', 'Cancelar')}
            </Button>
            <Button
              size="sm"
              onClick={() => inviteCompanyMutation.mutate()}
              disabled={!linkEmail.trim() || inviteCompanyMutation.isPending}
              className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs px-4 cursor-pointer gap-1.5"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>{inviteCompanyMutation.isPending ? t('agency.sendingRequest', 'Enviando solicitud...') : t('agency.sendLinkRequest', 'Enviar Solicitud de Vinculación')}</span>
            </Button>
          </div>
        </div>
      )}

      {/* Modal / Inline Provisioning */}
      {isCreating && (
        <div className="p-6 sm:p-8 rounded-3xl border border-violet-500/30 bg-card space-y-6 shadow-xl animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Building2 className="w-5 h-5 text-violet-600 dark:text-violet-400" />
              <span>{t('agency.provisionModalTitle', 'Aprovisionar Nueva Empresa Cliente')}</span>
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCreating(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t('agency.cancel', 'Cancelar')}
            </Button>
          </div>

          <div className="p-3.5 rounded-xl bg-muted/40 border border-border text-xs text-muted-foreground flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-violet-600 shrink-0" />
            <span>{t('agency.provisionNotice', 'La empresa se creará con el aislamiento total y la cuota estándar oficial de la plataforma asignada a tu licencia de agencia.')}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground font-semibold">{t('agency.companyNameLabel', 'Nombre de la Empresa o Marca')}</Label>
              <Input
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                placeholder={t('agency.companyNamePlaceholder', 'ej: Hotel & Spa Paraíso')}
                className="bg-background border-border text-xs text-foreground"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground font-semibold">{t('agency.companyContactEmailLabel', 'Correo Electrónico de Contacto')}</Label>
              <Input
                type="email"
                value={newCompanyEmail}
                onChange={(e) => setNewCompanyEmail(e.target.value)}
                placeholder="contacto@empresa.com"
                className="bg-background border-border text-xs text-foreground"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground font-semibold">{t('agency.companyPhoneLabel', 'Teléfono / WhatsApp')}</Label>
              <Input
                value={newCompanyPhone}
                onChange={(e) => setNewCompanyPhone(e.target.value)}
                placeholder="+54 9 11 1234 5678"
                className="bg-background border-border text-xs text-foreground"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground font-semibold">{t('agency.companyIndustryLabel', 'Industria o Rubro')}</Label>
              <Input
                value={newCompanyIndustry}
                onChange={(e) => setNewCompanyIndustry(e.target.value)}
                placeholder={t('agency.companyIndustryPlaceholder', 'Comercio, Salud, Inmobiliaria...')}
                className="bg-background border-border text-xs text-foreground"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCreating(false)}
              className="border-border text-foreground text-xs"
            >
              {t('agency.cancel', 'Cancelar')}
            </Button>
            <Button
              size="sm"
              onClick={() => createCompanyMutation.mutate()}
              disabled={!newCompanyName.trim() || createCompanyMutation.isPending}
              className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs px-4 cursor-pointer"
            >
              {createCompanyMutation.isPending ? t('agency.creating', 'Creando...') : t('agency.createAndConnect', 'Crear y Conectar Empresa')}
            </Button>
          </div>
        </div>
      )}

      {/* Companies Portfolio Grid */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-foreground">{t('agency.portfolioTitle', 'Cartera de Empresas Vinculadas')}</h2>

        {companies.length === 0 ? (
          <div className="text-center py-16 bg-card rounded-2xl border border-border space-y-3">
            <Building2 className="w-10 h-10 text-muted-foreground mx-auto" />
            <p className="text-muted-foreground text-sm font-medium">{t('agency.noCompanies', 'No hay empresas vinculadas a tu cuenta de agencia todavía.')}</p>
            <div className="flex justify-center gap-3 pt-2">
              <Button
                onClick={() => setIsLinking(true)}
                variant="outline"
                size="sm"
                className="border-violet-500/30 text-xs font-semibold cursor-pointer"
              >
                {t('agency.linkExisting', 'Vincular Empresa Existente')}
              </Button>
              <Button
                onClick={() => setIsCreating(true)}
                size="sm"
                className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold cursor-pointer"
              >
                {t('agency.provisionNew', 'Dar de Alta Empresa')}
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {companies.map((comp) => {
              const compId = comp.company_id || comp.id;
              const isPending = comp.status === 'pending_approval';

              return (
                <div
                  key={compId}
                  className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/40 transition-all flex flex-col justify-between space-y-4 shadow-sm"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-600 dark:text-violet-300 flex items-center justify-center font-bold text-sm">
                          {comp.company_name?.charAt(0) || 'E'}
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-foreground line-clamp-1">{comp.company_name}</h3>
                          <p className="text-[11px] text-muted-foreground font-mono">ID: #{compId}</p>
                        </div>
                      </div>
                      {isPending ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {t('agency.statusPending', 'Pendiente')}
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          {t('agency.statusActive', 'Activa')}
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border text-xs">
                      <div>
                        <span className="text-[10px] text-muted-foreground uppercase font-bold block">{t('agency.aiFuel', 'Combustible IA')}</span>
                        <span className="text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {comp.credit_balance?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground uppercase font-bold block">{t('agency.managementRole', 'Rol de Gestión')}</span>
                        <span className="text-foreground font-semibold capitalize">
                          {comp.role_in_client || 'Admin'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    {!isPending ? (
                      <Button
                        onClick={() => switchCompany(compId, comp.company_name)}
                        variant="outline"
                        className="flex-1 hover:bg-violet-600 hover:text-white border-border text-foreground text-xs font-semibold py-2 rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <span>{t('agency.enterWorkspace', 'Entrar al Espacio')}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Button>
                    ) : (
                      <Button
                        disabled
                        variant="outline"
                        className="flex-1 border-border text-muted-foreground text-xs font-semibold py-2 rounded-xl opacity-70"
                      >
                        <span>{t('agency.waitingAuth', 'Esperando Autorización')}</span>
                      </Button>
                    )}

                    <Button
                      onClick={() => {
                        if (confirm(t('agency.unlinkConfirm', { name: comp.company_name, defaultValue: `¿Deseas desvincular a "${comp.company_name}"? La empresa conservará todos sus datos intactos.` }))) {
                          unlinkCompanyMutation.mutate(compId);
                        }
                      }}
                      variant="ghost"
                      size="icon"
                      title={t('agency.unlinkCompany', 'Desvincular Empresa')}
                      className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 h-9 w-9 rounded-xl shrink-0"
                    >
                      <Unlink className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

