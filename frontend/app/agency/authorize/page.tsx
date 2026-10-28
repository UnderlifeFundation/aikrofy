'use client';

import React, { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { ShieldCheck, Building2, CheckCircle2, XCircle, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

function AuthorizeAgencyContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [hasResponded, setHasResponded] = useState(false);
  const [responseMessage, setResponseMessage] = useState('');
  const [responseSuccess, setResponseSuccess] = useState(false);

  // Fetch details about the invitation
  const { data, isLoading, error } = useQuery({
    queryKey: ['invitation-details', token],
    queryFn: async () => {
      if (!token) throw new Error('Token no proporcionado');
      const res = await axios.get(`/api/agency/invitation-details?token=${token}`);
      return res.data;
    },
    enabled: Boolean(token),
    retry: false,
  });

  const respondMutation = useMutation({
    mutationFn: async (action: 'accept' | 'reject') => {
      const res = await axios.post('/api/agency/respond-invitation', {
        token,
        action,
      });
      return res.data;
    },
    onSuccess: (data, variables) => {
      setHasResponded(true);
      setResponseSuccess(variables === 'accept');
      setResponseMessage(data.message || (variables === 'accept' ? 'Vinculación autorizada con éxito.' : 'Has rechazado la solicitud.'));
      if (variables === 'accept') {
        toast.success('¡Vinculación aprobada exitosamente!');
      } else {
        toast.info('Solicitud rechazada.');
      }
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.error || 'Error al procesar la solicitud');
    },
  });

  if (!token) {
    return (
      <Card className="max-w-md w-full border-border bg-card shadow-2xl rounded-3xl text-center p-6">
        <div className="w-12 h-12 rounded-2xl bg-destructive/10 text-destructive flex items-center justify-center mx-auto mb-4">
          <XCircle className="w-6 h-6" />
        </div>
        <CardTitle className="text-xl font-bold text-foreground">{t('agency.authorize.invalidLinkTitle', 'Enlace Inválido')}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground mt-2">
          {t('agency.authorize.invalidLinkDesc', 'No se encontró ningún token de vinculación en la dirección solicitada.')}
        </CardDescription>
        <CardFooter className="pt-6 justify-center">
          <Button onClick={() => router.push('/dashboard')} variant="outline" className="text-xs">
            {t('agency.authorize.goToMainDashboard', 'Ir al Panel Principal')}
          </Button>
        </CardFooter>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="max-w-md w-full border-border bg-card shadow-2xl rounded-3xl text-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-violet-600 mx-auto mb-4" />
        <p className="text-sm text-muted-foreground font-medium">{t('agency.authorize.checkingLink', 'Verificando enlace de autorización seguro...')}</p>
      </Card>
    );
  }

  if (error || !data?.success) {
    return (
      <Card className="max-w-md w-full border-border bg-card shadow-2xl rounded-3xl text-center p-6">
        <div className="w-12 h-12 rounded-2xl bg-destructive/10 text-destructive flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <CardTitle className="text-xl font-bold text-foreground">{t('agency.authorize.unavailableTitle', 'Solicitud no disponible')}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground mt-2">
          {(error as any)?.response?.data?.error || t('agency.authorize.unavailableDesc', 'Este enlace de invitación ya ha sido utilizado o ha expirado.')}
        </CardDescription>
        <CardFooter className="pt-6 justify-center">
          <Button onClick={() => router.push('/dashboard')} variant="outline" className="text-xs">
            {t('agency.authorize.goToAikrofy', 'Ir a Aikrofy')}
          </Button>
        </CardFooter>
      </Card>
    );
  }

  const { agency, company, status, is_active } = data;

  if (hasResponded) {
    return (
      <Card className="max-w-lg w-full border-border bg-card shadow-2xl rounded-3xl p-8 text-center space-y-6 animate-fade-in">
        <div className={`w-16 h-16 rounded-3xl ${responseSuccess ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' : 'bg-muted text-muted-foreground'} flex items-center justify-center mx-auto`}>
          {responseSuccess ? <CheckCircle2 className="w-8 h-8" /> : <XCircle className="w-8 h-8" />}
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black text-foreground tracking-tight">
            {responseSuccess ? t('agency.authorize.authorizedSuccessTitle', '¡Vinculación Autorizada!') : t('agency.authorize.rejectedTitle', 'Solicitud Rechazada')}
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {responseMessage}
          </p>
        </div>
        <div className="pt-4">
          <Button onClick={() => router.push('/dashboard')} className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs px-6 py-2.5 rounded-xl">
            {t('agency.authorize.continueDashboard', 'Continuar a mi Panel')}
          </Button>
        </div>
      </Card>
    );
  }

  if (status === 'active' || is_active) {
    return (
      <Card className="max-w-md w-full border-border bg-card shadow-2xl rounded-3xl text-center p-8 space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <CardTitle className="text-xl font-bold text-foreground">{t('agency.authorize.alreadyLinkedTitle', 'Ya Vinculada')}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {t('agency.authorize.alreadyLinkedDesc', { agency: agency?.name, defaultValue: `Tu empresa ya se encuentra administrada por ${agency?.name}.` })}
        </CardDescription>
        <CardFooter className="pt-4 justify-center">
          <Button onClick={() => router.push('/dashboard')} variant="outline" className="text-xs">
            {t('agency.authorize.goToAccount', 'Ir a mi Cuenta')}
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="max-w-lg w-full border border-violet-500/30 bg-card shadow-2xl rounded-3xl p-6 sm:p-8 space-y-6">
      <div className="space-y-2">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20">
          <ShieldCheck className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
          <span>{t('agency.authorize.protocolBadge', 'Aikrofy Multi-Tenant Protocol')}</span>
        </div>
        <h1 className="text-2xl font-black text-foreground tracking-tight">
          {t('agency.authorize.pageTitle', 'Solicitud de Delegación de Agencia')}
        </h1>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {t('agency.authorize.pageSubtitle', 'Una agencia socia solicita vincularse a tu cuenta para asistirte en la gestión operativa de tus agentes IA y canales.')}
        </p>
      </div>

      <div className="p-4 rounded-2xl bg-muted/40 border border-border space-y-3">
        <div className="flex items-center justify-between text-xs pb-2 border-b border-border">
          <span className="text-muted-foreground font-semibold">{t('agency.authorize.requestingAgency', 'Agencia Solicitante:')}</span>
          <span className="font-bold text-foreground">{agency.name}</span>
        </div>
        <div className="flex items-center justify-between text-xs pb-2 border-b border-border">
          <span className="text-muted-foreground font-semibold">{t('agency.authorize.agencyEmail', 'Correo de la Agencia:')}</span>
          <span className="font-mono text-muted-foreground">{agency.email}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground font-semibold">{t('agency.authorize.targetCompany', 'Tu Empresa Destino:')}</span>
          <span className="font-bold text-violet-600 dark:text-violet-400">{company.name}</span>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-violet-500/5 border border-violet-500/20 space-y-2">
        <p className="text-xs font-bold text-foreground flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-violet-600" />
          <span>{t('agency.authorize.guaranteeTitle', 'Garantía de Aislamiento e Independencia')}</span>
        </p>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          {t('agency.authorize.guaranteeDesc', 'Tu empresa mantiene en todo momento el 100% de la propiedad sobre sus datos, chats, documentos y agentes. Podrás revocar o desvincular el acceso de la agencia en cualquier momento desde tu panel sin perder nada de información.')}
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <Button
          onClick={() => respondMutation.mutate('reject')}
          disabled={respondMutation.isPending}
          variant="outline"
          className="sm:w-1/2 border-border text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
        >
          {respondMutation.isPending && respondMutation.variables === 'reject' ? t('agency.authorize.rejecting', 'Rechazando...') : t('agency.authorize.reject', 'Rechazar Solicitud')}
        </Button>
        <Button
          onClick={() => respondMutation.mutate('accept')}
          disabled={respondMutation.isPending}
          className="sm:w-1/2 bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs shadow-lg shadow-violet-600/30 gap-1.5 cursor-pointer"
        >
          {respondMutation.isPending && respondMutation.variables === 'accept' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <span>{t('agency.authorize.authorize', 'Autorizar Gestión')}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}

export default function AuthorizeAgencyPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Suspense fallback={
        <div className="text-center p-8">
          <Loader2 className="w-8 h-8 animate-spin text-violet-600 mx-auto" />
        </div>
      }>
        <AuthorizeAgencyContent />
      </Suspense>
    </div>
  );
}
