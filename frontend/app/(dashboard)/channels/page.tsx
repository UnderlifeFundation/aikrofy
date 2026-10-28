'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Radio,
    Smartphone,
    MessageCircle,
    Mail,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Save,
    ExternalLink,
    QrCode,
    Unplug,
    RefreshCw,
    XCircle,
    Users,
    CreditCard,
    PhoneCall,
    Video,
    Calendar,
    ShieldCheck,
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/lib/api-client';
import { channelsService } from '@/services/channels-service';
import type { Channel } from '@/types';

// ─── Helpers ───────────────────────────────────────────────────────
import { useTranslation } from 'react-i18next';
import { usePlanFeatures } from '@/hooks/use-plan-features';
import { EnterpriseOnboardingModal } from '@/components/features/billing/EnterpriseOnboardingModal';

function StatusBadge({ status }: { status: string }) {
    const { t } = useTranslation();
    if (status === 'active' || status === 'connected') {
        return (
            <Badge variant="outline" className="border-green-500 text-green-600">
                <CheckCircle2 className="mr-1 h-3 w-3" /> {t('channels.connected')}
            </Badge>
        );
    }
    return (
        <Badge variant="outline" className="border-yellow-500 text-yellow-600">
            <AlertCircle className="mr-1 h-3 w-3" /> {t('channels.notConnected')}
        </Badge>
    );
}

export default function ChannelsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    const { data: channels, isLoading } = useQuery({
        queryKey: ['channels'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ channels: Channel[] }>('/channels/');
            return data.channels;
        },
    });

    const whatsappChannel = channels?.find((c) => c.channel_type === 'whatsapp');
    const telegramChannel = channels?.find((c) => c.channel_type === 'telegram');
    const emailChannel = channels?.find((c) => c.channel_type === 'email');

    const saveMutation = useMutation({
        mutationFn: async (payload: {
            id?: number;
            channel_type: string;
            name: string;
            credentials: Record<string, string>;
        }) => {
            if (payload.id) {
                const { data } = await apiClient.put(`/channels/${payload.id}`, {
                    credentials: payload.credentials,
                    status: 'connected',
                    name: payload.name,
                });
                return data;
            }
            const { data } = await apiClient.post('/channels/connect', {
                type: payload.channel_type,
                channel_type: payload.channel_type,
                name: payload.name,
                credentials: payload.credentials,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['channels'] });
            toast.success(t('common.save') + ' ' + t('common.success', { defaultValue: 'Success' }));
        },
        onError: (error: unknown) => {
            const message =
                (error as { response?: { data?: { error?: string } } })?.response?.data?.error ||
                t('common.error', { defaultValue: 'Failed to save channel' });
            toast.error(message);
        },
    });

    const deleteChannelMutation = useMutation({
        mutationFn: async (channelId: number) => {
            const { data } = await apiClient.delete(`/channels/${channelId}`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['channels'] });
            toast.success(t('channels.disconnected'));
        },
        onError: () => {
            toast.error(t('common.error', { defaultValue: 'Error' }));
        },
    });

    const { canUseChannel, canUseIntegration, isLoading: featuresLoading } = usePlanFeatures();

    if (isLoading || featuresLoading) {
        return (
            <div className="mx-auto max-w-3xl space-y-6">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-48 w-full" />
                <Skeleton className="h-48 w-full" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-8 animate-slow-fade">
            <div className="relative overflow-hidden rounded-2xl vivid-gradient p-8 text-white shadow-lg">
                <div className="relative z-10">
                    <h2 className="flex items-center gap-3 text-3xl font-bold tracking-tight">
                        <Radio className="h-8 w-8 text-white/90" />
                        {t('channels.title')}
                    </h2>
                    <p className="mt-2 text-white/80 max-w-2xl">
                        {t('channels.description')}
                    </p>
                </div>
                {/* Decorative elements */}
                <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
                <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-secondary/20 blur-3xl" />
            </div>

            <ChannelGate allowed={canUseChannel('whatsapp')} label="WhatsApp">
                <WhatsAppCard channel={whatsappChannel} />
            </ChannelGate>

            <ChannelGate allowed={canUseChannel('telegram')} label="Telegram">
                <TelegramCard
                    channel={telegramChannel}
                    onSave={(token) =>
                        saveMutation.mutate({
                            id: telegramChannel?.id,
                            channel_type: 'telegram',
                            name: 'Telegram Bot',
                            credentials: { telegram_token: token.trim(), bot_token: token.trim() },
                        })
                    }
                    isSaving={saveMutation.isPending}
                    onDisconnect={() => telegramChannel?.id && deleteChannelMutation.mutate(telegramChannel.id)}
                    isDisconnecting={deleteChannelMutation.isPending}
                />
            </ChannelGate>

            <ChannelGate allowed={canUseChannel('email')} label="Email">
                <EmailCard
                    channel={emailChannel}
                    onSave={(creds) =>
                        saveMutation.mutate({
                            id: emailChannel?.id,
                            channel_type: 'email',
                            name: 'Email SMTP',
                            credentials: creds,
                        })
                    }
                    isSaving={saveMutation.isPending}
                    onDisconnect={() => emailChannel?.id && deleteChannelMutation.mutate(emailChannel.id)}
                    isDisconnecting={deleteChannelMutation.isPending}
                />
            </ChannelGate>

            <ChannelGate allowed={canUseChannel('google')} label="Reuniones">
                <MeetingsAndCalendarCard />
            </ChannelGate>

            <h3 className="text-xl font-bold mt-12 mb-4">{t('common.integrations', { defaultValue: 'Integrations' })}</h3>


            <ChannelGate allowed={canUseIntegration('twilio')} label="Twilio Voice">
                <TwilioVoiceCard />
            </ChannelGate>
            <ChannelGate allowed={canUseChannel('webchat')} label="Webchat">
                <WebchatCard channel={channels?.find((c) => c.channel_type === 'webchat')} />
            </ChannelGate>
        </div>
    );
}

/** Gate wrapper — shows locked overlay when feature is not in the user's plan */
function ChannelGate({ allowed, label, children }: { allowed: boolean; label: string; children: React.ReactNode }) {
    return <>{children}</>;
}

function WhatsAppCard({ channel }: { channel?: Channel }) {
    const { t } = useTranslation();
    const [isConnecting, setIsConnecting] = useState(false);
    const [qrCode, setQrCode] = useState<string | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [connectedPhone, setConnectedPhone] = useState<string | null>(null);
    const [isDisconnecting, setIsDisconnecting] = useState(false);
    const [connectedVerifiedName, setConnectedVerifiedName] = useState<string | null>(null);
    const [connectedProvider, setConnectedProvider] = useState<string>('meta');
    const [provider, setProvider] = useState<string>('meta');

    // Meta state
    const [metaAppId, setMetaAppId] = useState('');
    const [metaConfigId, setMetaConfigId] = useState('');
    const [metaSdkReady, setMetaSdkReady] = useState(false);

    // Meta Embedded Signup — multi-selection state
    const [metaSignupStep, setMetaSignupStep] = useState<'idle' | 'connecting' | 'select_waba' | 'select_phone' | 'done'>('idle');
    const [metaTempToken, setMetaTempToken] = useState('');
    const [metaWabaList, setMetaWabaList] = useState<Array<{ id: string; name: string }>>([]);
    const [metaPhoneList, setMetaPhoneList] = useState<Array<{ id: string; display_phone_number: string; verified_name: string; code_verification_status?: string }>>([]);
    const [metaSelectedWaba, setMetaSelectedWaba] = useState('');

    // Meta Manual Credentials (advanced / developer tab)
    const [metaConnectMode, setMetaConnectMode] = useState<'embedded' | 'manual'>('embedded');
    const [metaManualPhoneId, setMetaManualPhoneId] = useState('');
    const [metaManualToken, setMetaManualToken] = useState('');
    const [metaManualWabaId, setMetaManualWabaId] = useState('');

    // Twilio Credentials
    const [twilioSid, setTwilioSid] = useState('');
    const [twilioToken, setTwilioToken] = useState('');
    const [twilioPhone, setTwilioPhone] = useState('');

    // ─── Load Meta config (app_id, config_id) from backend server ──────────
    useEffect(() => {
        channelsService.getMetaConfig().then((cfg) => {
            if (cfg.app_id) setMetaAppId(cfg.app_id);
            if (cfg.config_id) setMetaConfigId(cfg.config_id);
        }).catch(() => {});
    }, []);

    // ─── Load Meta JS SDK dynamically ───────────────────────────────────────
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const initFB = () => {
            if ((window as any).FB && metaAppId) {
                try {
                    (window as any).FB.init({
                        appId: metaAppId,
                        autoLogAppEvents: true,
                        xfbml: true,
                        version: 'v21.0',
                    });
                } catch (e) {
                    console.warn('FB.init error:', e);
                }
                setMetaSdkReady(true);
            }
        };

        if ((window as any).FB) {
            initFB();
            return;
        }

        (window as any).fbAsyncInit = () => {
            initFB();
        };

        if (!document.getElementById('facebook-jssdk')) {
            const script = document.createElement('script');
            script.id = 'facebook-jssdk';
            script.src = 'https://connect.facebook.net/en_US/sdk.js';
            script.async = true;
            script.defer = true;
            document.head.appendChild(script);
        }
    }, [metaAppId]);

    const codeProcessedRef = useState(false);

    // ─── Process Meta auth code (from postMessage or FB.login callback) ────
    const processMetaCode = async (code: string, waba_id?: string, phone_number_id?: string) => {
        if (codeProcessedRef[0]) return;
        codeProcessedRef[1](true);

        toast.info('Autenticación de Meta recibida. Procesando conexión…');
        setMetaSignupStep('connecting');
        setIsConnecting(true);

        try {
            const result = await channelsService.embeddedSignupMeta({
                code,
                waba_id: waba_id || undefined,
                phone_number_id: phone_number_id || undefined,
            });
            await _handleSignupResult(result);
        } catch (err: any) {
            const msg = err?.response?.data?.error || 'Error al conectar con Meta. Intenta de nuevo.';
            toast.error(msg);
            setMetaSignupStep('idle');
        } finally {
            setIsConnecting(false);
            codeProcessedRef[1](false);
        }
    };

    // ─── Listen for WA_EMBEDDED_SIGNUP postMessage (from FB popup) ──────────
    useEffect(() => {
        const handleMessage = async (event: MessageEvent) => {
            if (
                event.origin !== 'https://www.facebook.com' &&
                event.origin !== 'https://web.facebook.com'
            ) return;
            try {
                const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                if (data.type !== 'WA_EMBEDDED_SIGNUP') return;

                if (data.event === 'FINISH') {
                    const { phone_number_id, waba_id, code } = data.data || {};
                    if (code) {
                        processMetaCode(code, waba_id, phone_number_id);
                    }
                } else if (data.event === 'CANCEL') {
                    setMetaSignupStep('idle');
                    toast.info('Inicio de sesión con Meta cancelado.');
                } else if (data.event === 'ERROR') {
                    setMetaSignupStep('idle');
                    toast.error(`Error en el proceso de Meta: ${data.data?.error_message || 'Desconocido'}`);
                }
            } catch {
                // ignore invalid messages
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    // ─── Check WhatsApp status on mount / channel change ────────────────────
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const result = await channelsService.getWhatsAppStatus();
                setIsConnected(result.connected);
                if (result.phone) setConnectedPhone(result.phone);

                if (channel?.credentials) {
                    if (channel.credentials.provider) setConnectedProvider(channel.credentials.provider);
                    if (channel.credentials.phone_number) setConnectedPhone(channel.credentials.phone_number);
                    if (channel.credentials.verified_name) setConnectedVerifiedName(channel.credentials.verified_name);
                    // Pre-fill manual fields if already connected via meta
                    if (channel.credentials.phone_number_id) setMetaManualPhoneId(channel.credentials.phone_number_id);
                    if (channel.credentials.waba_id) setMetaManualWabaId(channel.credentials.waba_id);
                }
            } catch (error) {
                console.error('Failed to check WhatsApp status:', error);
            }
        };
        checkStatus();
    }, [channel]);

    // ─── QR polling for Baileys ─────────────────────────────────────────────
    useEffect(() => {
        if (!isPolling || !qrCode || provider !== 'baileys') return;
        const interval = setInterval(async () => {
            try {
                const result = await channelsService.getWhatsAppStatus();
                if (result.connected) {
                    setQrCode(null);
                    setIsPolling(false);
                    setIsConnected(true);
                    if (result.phone) setConnectedPhone(result.phone);
                    toast.success(t('common.success', { defaultValue: '¡Conectado!' }));
                } else {
                    try {
                        const qrResult = await channelsService.getWhatsAppQR();
                        if (qrResult.qr) setQrCode(qrResult.qr);
                    } catch { /* ignore */ }
                }
            } catch (error) {
                console.error('WhatsApp status poll error:', error);
            }
        }, 3000);
        return () => clearInterval(interval);
    }, [isPolling, qrCode, t, provider]);

    // ─── Helper: handle result from embedded-signup or select-phone ─────────
    const _handleSignupResult = async (result: any) => {
        if (result.action === 'connected') {
            setIsConnected(true);
            setConnectedPhone(result.phone_number || '');
            setConnectedVerifiedName(result.verified_name || '');
            setConnectedProvider('meta');
            setMetaSignupStep('done');
            const webhookMsg = result.webhook_subscribed
                ? ' Los webhooks se configuraron automáticamente.'
                : ' (Nota: configura manualmente el webhook en Meta).';
            toast.success(`¡Canal de WhatsApp Business conectado! ${result.phone_number}${webhookMsg}`);
        } else if (result.action === 'select_waba') {
            setMetaTempToken(result.access_token);
            setMetaWabaList(result.waba_list);
            setMetaSignupStep('select_waba');
            toast.info('Selecciona tu cuenta de WhatsApp Business.');
        } else if (result.action === 'select_phone') {
            setMetaTempToken(result.access_token);
            setMetaSelectedWaba(result.waba_id);
            setMetaPhoneList(result.phone_numbers);
            setMetaSignupStep('select_phone');
            toast.info('Selecciona el número de teléfono que deseas conectar.');
        }
    };

    // ─── Launch Meta Embedded Signup via FB.login SDK ───────────────────────
    const handleLaunchEmbeddedSignup = () => {
        if (!metaAppId) {
            toast.error('La aplicación de Meta no está configurada en el servidor. Contacta al administrador.');
            return;
        }

        const FB = (window as any).FB;

        if (FB) {
            try {
                FB.init({
                    appId: metaAppId,
                    autoLogAppEvents: true,
                    xfbml: true,
                    version: 'v21.0',
                });
            } catch (e) {
                console.warn('FB.init re-init warning:', e);
            }
        }

        const loginParams: any = {
            response_type: 'code',
            override_default_response_type: true,
            extras: { setup: {} },
        };

        if (metaConfigId) {
            loginParams.config_id = metaConfigId;
        } else {
            loginParams.scope = 'whatsapp_business_management,whatsapp_business_messaging,business_management';
        }

        if (FB && typeof FB.login === 'function') {
            FB.login((response: any) => {
                if (response?.authResponse?.code) {
                    processMetaCode(response.authResponse.code);
                } else if (response?.status === 'connected' && response?.authResponse?.accessToken) {
                    processMetaCode(response.authResponse.accessToken);
                } else {
                    setMetaSignupStep('idle');
                    if (response?.status !== 'unknown' && response) {
                        toast.info('Inicio de sesión con Meta cancelado o fallido.');
                    }
                }
            }, loginParams);
        } else {
            // Fallback: Direct OAuth Popup if SDK fails to initialize or is blocked
            const redirectUri = window.location.origin + '/channels';
            const authUrl = metaConfigId
                ? `https://www.facebook.com/v21.0/dialog/oauth?client_id=${metaAppId}&config_id=${metaConfigId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}`
                : `https://www.facebook.com/v21.0/dialog/oauth?client_id=${metaAppId}&scope=whatsapp_business_management,whatsapp_business_messaging,business_management&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}`;
            window.open(authUrl, 'MetaSignup', 'width=600,height=700');
        }
    };

    // ─── WABA selection handler ──────────────────────────────────────────────
    const handleSelectWaba = async (wabaId: string) => {
        setIsConnecting(true);
        setMetaSignupStep('connecting');
        try {
            const result = await channelsService.embeddedSignupMeta({
                code: metaTempToken,   // backend will treat access_token as direct if no exchange needed
                waba_id: wabaId,
            });
            await _handleSignupResult(result);
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al conectar la cuenta seleccionada.');
            setMetaSignupStep('select_waba');
        } finally {
            setIsConnecting(false);
        }
    };

    // ─── Phone selection handler ─────────────────────────────────────────────
    const handleSelectPhone = async (phoneNumberId: string) => {
        setIsConnecting(true);
        setMetaSignupStep('connecting');
        try {
            const result = await channelsService.selectMetaPhone({
                access_token: metaTempToken,
                waba_id: metaSelectedWaba,
                phone_number_id: phoneNumberId,
            });
            await _handleSignupResult(result);
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al conectar el número seleccionado.');
            setMetaSignupStep('select_phone');
        } finally {
            setIsConnecting(false);
        }
    };

    // ─── Baileys connect ─────────────────────────────────────────────────────
    const handleConnectBaileys = async () => {
        setIsConnecting(true);
        try {
            await channelsService.initWhatsApp();
            setTimeout(async () => {
                try {
                    const qrResult = await channelsService.getWhatsAppQR();
                    if (qrResult.qr) {
                        setQrCode(qrResult.qr);
                        setIsPolling(true);
                    }
                } catch (error) {
                    toast.error(t('common.error', { defaultValue: 'Error generating QR' }));
                }
                setIsConnecting(false);
            }, 2500);
        } catch (error) {
            toast.error(t('common.error', { defaultValue: 'Error' }));
            setIsConnecting(false);
        }
    };

    // ─── Twilio / Manual Meta connect ────────────────────────────────────────
    const handleConnectProvider = async () => {
        setIsConnecting(true);
        try {
            let credentials: any = {};
            if (provider === 'meta') {
                if (!metaManualPhoneId || !metaManualToken) {
                    toast.error('Phone Number ID y Access Token son requeridos.');
                    setIsConnecting(false);
                    return;
                }
                credentials = {
                    phone_number_id: metaManualPhoneId,
                    access_token: metaManualToken,
                    waba_id: metaManualWabaId || undefined,
                };
            } else if (provider === 'twilio') {
                if (!twilioSid || !twilioToken || !twilioPhone) {
                    toast.error('Twilio SID, Token y Número son requeridos.');
                    setIsConnecting(false);
                    return;
                }
                credentials = {
                    account_sid: twilioSid,
                    auth_token: twilioToken,
                    phone_number: twilioPhone,
                };
            }

            const result = await channelsService.connectWhatsApp(provider, credentials);
            if (result) {
                toast.success('¡Conexión de WhatsApp iniciada con éxito!');
                setIsConnected(true);
                if (twilioPhone) setConnectedPhone(twilioPhone);
            }
        } catch (error: any) {
            const msg = error?.response?.data?.error || t('common.error', { defaultValue: 'Error al conectar' });
            toast.error(msg);
        } finally {
            setIsConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        setIsDisconnecting(true);
        try {
            await channelsService.disconnectWhatsApp();
            setQrCode(null);
            setIsPolling(false);
            setIsConnected(false);
            setConnectedPhone(null);
            setConnectedVerifiedName(null);
            setMetaSignupStep('idle');
            toast.success(t('common.success', { defaultValue: 'Desconectado' }));
        } catch (error) {
            toast.error(t('common.error', { defaultValue: 'Error' }));
        } finally {
            setIsDisconnecting(false);
        }
    };

    const handleCancel = () => {
        setQrCode(null);
        setIsPolling(false);
        setIsConnecting(false);
        setMetaSignupStep('idle');
    };

    return (
        <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                        <Smartphone className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base">{t('channels.whatsappTitle')}</CardTitle>
                        <CardDescription>{t('channels.whatsappDesc')}</CardDescription>
                    </div>
                </div>
                <StatusBadge status={isConnected ? 'connected' : 'inactive'} />
            </CardHeader>
            <CardContent>
                {isConnected ? (
                    <div className="space-y-4">
                        <Alert className="bg-green-500/10 border-green-500/20">
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-700 dark:text-green-400">
                                <div className="flex flex-col gap-0.5">
                                    <span>
                                        ✓ {t('channels.connected')}{' '}
                                        {connectedPhone && <strong>{connectedPhone}</strong>}
                                    </span>
                                    {connectedVerifiedName && (
                                        <span className="text-xs opacity-80">
                                            Nombre verificado: <strong>{connectedVerifiedName}</strong>
                                        </span>
                                    )}
                                    <span className="text-xs opacity-60 mt-0.5">
                                        Proveedor: {connectedProvider.toUpperCase()}
                                    </span>
                                </div>
                            </AlertDescription>
                        </Alert>
                        <Button
                            variant="destructive"
                            onClick={handleDisconnect}
                            disabled={isDisconnecting}
                            className="w-full"
                        >
                            {isDisconnecting ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Unplug className="h-4 w-4 mr-2" />
                            )}
                            {isDisconnecting
                                ? t('common.saving', { defaultValue: 'Desconectando...' })
                                : t('common.delete', { defaultValue: 'Desconectar WhatsApp' })}
                        </Button>
                    </div>
                ) : qrCode ? (
                    <div className="space-y-4">
                        <div className="text-center">
                            <div className="bg-white p-4 rounded-lg inline-block shadow-sm border mb-4">
                                <img
                                    src={
                                        qrCode.startsWith('<svg')
                                            ? `data:image/svg+xml;utf8,${encodeURIComponent(qrCode)}`
                                            : qrCode
                                    }
                                    alt="WhatsApp QR Code"
                                    className="w-56 h-56"
                                />
                            </div>
                            <p className="text-xs text-muted-foreground mt-2 flex items-center justify-center gap-1">
                                <RefreshCw className="h-3 w-3 animate-spin" />
                                {t('common.saving', { defaultValue: 'Esperando conexión...' })}
                            </p>
                        </div>
                        <Button variant="outline" onClick={handleCancel} className="w-full">
                            {t('common.cancel', { defaultValue: 'Cancelar' })}
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <Tabs defaultValue="meta" value={provider} onValueChange={(v) => { setProvider(v); setMetaSignupStep('idle'); }} className="w-full">
                            <TabsList className="grid w-full grid-cols-3 mb-4">
                                <TabsTrigger value="meta">
                                    <span className="mr-1.5">✨</span> Meta API
                                </TabsTrigger>
                                <TabsTrigger value="twilio">Twilio</TabsTrigger>
                                <TabsTrigger value="baileys">{t('channels.whatsappTabDirect', { defaultValue: 'Conexión Directa' })}</TabsTrigger>
                            </TabsList>

                            {/* ─── META TAB ─────────────────────────────────────────── */}
                            <TabsContent value="meta" className="space-y-4">
                                <Alert className="bg-emerald-500/10 dark:bg-emerald-500/15 border-emerald-500/30 dark:border-emerald-500/30 p-3.5 rounded-xl shadow-sm [&>svg]:relative [&>svg]:left-0 [&>svg]:top-0 [&>svg~*]:pl-0">
                                    <AlertDescription className="text-xs text-emerald-950 dark:text-emerald-100 leading-relaxed flex items-start gap-2.5 m-0 p-0">
                                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                                        <span>
                                            <strong className="font-semibold text-emerald-900 dark:text-emerald-200">{t('channels.whatsapp.metaAlertTitle', { defaultValue: 'API Oficial de Meta WhatsApp Business' })}:</strong>{' '}
                                            {t('channels.whatsapp.metaAlertDesc', { defaultValue: 'Conecta tu cuenta en segundos mediante el inicio de sesión oficial con Facebook. Sin necesidad de configurar webhooks manualmente.' })}
                                        </span>
                                    </AlertDescription>
                                </Alert>

                                {/* Mode selector */}
                                <div className="grid grid-cols-2 gap-2 p-1 bg-muted/80 rounded-xl border text-xs font-medium">
                                    <button
                                        type="button"
                                        onClick={() => setMetaConnectMode('embedded')}
                                        className={`py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                                            metaConnectMode === 'embedded'
                                                ? 'bg-background shadow-sm text-foreground font-semibold border'
                                                : 'text-muted-foreground hover:text-foreground'
                                        }`}
                                    >
                                        <span>🚀</span> {t('channels.whatsapp.metaTabFacebook', { defaultValue: 'Inicio de Sesión Facebook' })}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setMetaConnectMode('manual')}
                                        className={`py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                                            metaConnectMode === 'manual'
                                                ? 'bg-background shadow-sm text-foreground font-semibold border'
                                                : 'text-muted-foreground hover:text-foreground'
                                        }`}
                                    >
                                        <span>🔑</span> {t('channels.whatsapp.metaTabManual', { defaultValue: 'Credenciales Manuales' })}
                                    </button>
                                </div>

                                {metaConnectMode === 'embedded' ? (
                                    /* ── EMBEDDED SIGNUP PANEL ─────────────────────────── */
                                    <div className="space-y-4 rounded-xl border p-5 bg-card shadow-sm">
                                        {metaSignupStep === 'idle' && (
                                            <>
                                                <div className="space-y-1">
                                                    <h4 className="text-sm font-semibold flex items-center gap-2">
                                                        <span>🚀</span> {t('channels.whatsapp.metaEmbeddedTitle', { defaultValue: 'Meta Embedded Signup (Recomendado)' })}
                                                    </h4>
                                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                                        {t('channels.whatsapp.metaEmbeddedDesc', { defaultValue: 'Haz clic en el botón de abajo para conectar tu cuenta de WhatsApp Business. Se abrirá el asistente oficial de Meta donde podrás seleccionar tu negocio y otorgar los permisos. Todo se configura automáticamente — sin copiar URLs ni claves.' })}
                                                    </p>
                                                </div>
                                                <Button
                                                    type="button"
                                                    id="meta-embedded-signup-btn"
                                                    onClick={handleLaunchEmbeddedSignup}
                                                    disabled={isConnecting}
                                                    className="w-full bg-[#1877F2] hover:bg-[#166fe5] text-white flex items-center justify-center gap-2.5 h-12 text-sm font-semibold shadow-md transition-all rounded-xl"
                                                >
                                                    {isConnecting ? (
                                                        <Loader2 className="h-5 w-5 animate-spin" />
                                                    ) : (
                                                        <svg className="w-5 h-5 fill-current flex-shrink-0" viewBox="0 0 24 24">
                                                            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                                                        </svg>
                                                    )}
                                                    {isConnecting
                                                        ? t('channels.whatsapp.metaProcessing', { defaultValue: 'Procesando…' })
                                                        : t('channels.whatsapp.metaConnectBtn', { defaultValue: 'Conectar cuenta de WhatsApp con Facebook' })}
                                                </Button>
                                                {!metaAppId && (
                                                    <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-2.5 flex items-start gap-1.5">
                                                        <span className="mt-0.5">⚠️</span>
                                                        <span>
                                                            La App de Meta no está configurada en el servidor.
                                                            Solicita al administrador que configure{' '}
                                                            <code className="font-mono bg-amber-100 px-1 rounded">META_APP_ID</code>,{' '}
                                                            <code className="font-mono bg-amber-100 px-1 rounded">META_APP_SECRET</code>{' '}
                                                            y{' '}
                                                            <code className="font-mono bg-amber-100 px-1 rounded">META_CONFIG_ID</code>.
                                                        </span>
                                                    </p>
                                                )}
                                            </>
                                        )}
                                        {metaSignupStep === 'connecting' && (
                                            <div className="flex flex-col items-center gap-3 py-6">
                                                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                                                <p className="text-sm text-muted-foreground text-center">
                                                    Intercambiando credenciales con Meta y configurando tu cuenta…
                                                    <br />
                                                    <span className="text-xs opacity-70">
                                                        Los webhooks se registran automáticamente.
                                                    </span>
                                                </p>
                                            </div>
                                        )}
                                        {metaSignupStep === 'select_waba' && (
                                            <div className="space-y-3">
                                                <h4 className="text-sm font-semibold">
                                                    Selecciona tu cuenta de WhatsApp Business (WABA)
                                                </h4>
                                                <p className="text-xs text-muted-foreground">
                                                    Se encontraron múltiples cuentas. Elige la que deseas conectar.
                                                </p>
                                                <div className="space-y-2">
                                                    {metaWabaList.map((waba) => (
                                                        <button
                                                            key={waba.id}
                                                            type="button"
                                                            disabled={isConnecting}
                                                            onClick={() => handleSelectWaba(waba.id)}
                                                            className="w-full text-left px-4 py-3 rounded-xl border hover:bg-accent hover:border-primary transition-all flex items-center justify-between gap-3 disabled:opacity-50"
                                                        >
                                                            <div>
                                                                <p className="font-medium text-sm">{waba.name}</p>
                                                                <p className="text-xs text-muted-foreground font-mono">ID: {waba.id}</p>
                                                            </div>
                                                            {isConnecting ? (
                                                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                                            ) : (
                                                                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                                                            )}
                                                        </button>
                                                    ))}
                                                </div>
                                                <Button variant="outline" size="sm" className="w-full" onClick={() => setMetaSignupStep('idle')}>
                                                    Cancelar
                                                </Button>
                                            </div>
                                        )}
                                        {metaSignupStep === 'select_phone' && (
                                            <div className="space-y-3">
                                                <h4 className="text-sm font-semibold">
                                                    Selecciona el número de teléfono a conectar
                                                </h4>
                                                <p className="text-xs text-muted-foreground">
                                                    La WABA tiene múltiples números. Elige cuál usar con Aikrofy.
                                                </p>
                                                <div className="space-y-2">
                                                    {metaPhoneList.map((phone) => (
                                                        <button
                                                            key={phone.id}
                                                            type="button"
                                                            disabled={isConnecting}
                                                            onClick={() => handleSelectPhone(phone.id)}
                                                            className="w-full text-left px-4 py-3 rounded-xl border hover:bg-accent hover:border-primary transition-all flex items-center justify-between gap-3 disabled:opacity-50"
                                                        >
                                                            <div>
                                                                <p className="font-medium text-sm">{phone.display_phone_number}</p>
                                                                <p className="text-xs text-muted-foreground">
                                                                    {phone.verified_name}
                                                                    {phone.code_verification_status && (
                                                                        <span className={`ml-2 ${phone.code_verification_status === 'VERIFIED' ? 'text-green-600' : 'text-amber-600'}`}>
                                                                            • {phone.code_verification_status === 'VERIFIED' ? '✓ Verificado' : phone.code_verification_status}
                                                                        </span>
                                                                    )}
                                                                </p>
                                                            </div>
                                                            {isConnecting ? (
                                                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                                            ) : (
                                                                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                                                            )}
                                                        </button>
                                                    ))}
                                                </div>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="w-full"
                                                    onClick={() => setMetaSignupStep(metaWabaList.length > 1 ? 'select_waba' : 'idle')}
                                                >
                                                    ← Volver
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    /* ── MANUAL CREDENTIALS PANEL ──────────────────────── */
                                    <div className="space-y-3 rounded-xl border p-4 bg-card shadow-sm">
                                        <div className="space-y-1">
                                            <h4 className="text-sm font-semibold flex items-center gap-2">
                                                <span>🔑</span> Credenciales Manuales (Avanzado)
                                            </h4>
                                            <p className="text-xs text-muted-foreground">
                                                Ingresa directamente tus credenciales de la API de WhatsApp Cloud.
                                                Los webhooks se suscribirán automáticamente si proporcionas el WABA ID.
                                            </p>
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="meta-manual-phone-id">Phone Number ID</Label>
                                            <Input
                                                id="meta-manual-phone-id"
                                                placeholder="e.g. 109283746500001"
                                                value={metaManualPhoneId}
                                                onChange={(e) => setMetaManualPhoneId(e.target.value)}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="meta-manual-token">Access Token (Token de acceso permanente)</Label>
                                            <Input
                                                id="meta-manual-token"
                                                type="password"
                                                placeholder="EAAB..."
                                                value={metaManualToken}
                                                onChange={(e) => setMetaManualToken(e.target.value)}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="meta-manual-waba-id">
                                                WABA ID (opcional — para auto-webhook)
                                            </Label>
                                            <Input
                                                id="meta-manual-waba-id"
                                                placeholder="e.g. 102290129340398"
                                                value={metaManualWabaId}
                                                onChange={(e) => setMetaManualWabaId(e.target.value)}
                                            />
                                            <p className="text-[11px] text-muted-foreground">
                                                Al proporcionar el WABA ID, los webhooks se suscriben automáticamente.
                                            </p>
                                        </div>
                                        <Button
                                            onClick={handleConnectProvider}
                                            disabled={isConnecting || !metaManualPhoneId || !metaManualToken}
                                            className="w-full bg-green-600 hover:bg-green-700 text-white mt-2"
                                        >
                                            {isConnecting ? (
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            ) : (
                                                <Save className="h-4 w-4 mr-2" />
                                            )}
                                            Guardar Credenciales Meta
                                        </Button>
                                    </div>
                                )}
                             </TabsContent>

                            {/* ─── TWILIO TAB ───────────────────────────────────────── */}
                            <TabsContent value="twilio" className="space-y-3">
                                <Alert className="bg-blue-50/50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20 p-3.5 rounded-xl shadow-sm [&>svg]:relative [&>svg]:left-0 [&>svg]:top-0 [&>svg~*]:pl-0">
                                    <AlertDescription className="text-blue-700 dark:text-blue-300 text-xs leading-relaxed flex items-start gap-2.5 m-0 p-0">
                                        <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                                        <span>
                                            <strong className="font-semibold text-blue-900 dark:text-blue-200">{t('channels.whatsapp.twilioAlertTitle', { defaultValue: 'API Estable (Twilio)' })}:</strong>{' '}
                                            {t('channels.whatsapp.twilioAlertDesc', { defaultValue: 'Conexión empresarial confiable que habilita flujos interactivos dinámicos, envío de archivos y plantillas aprobadas.' })}
                                        </span>
                                    </AlertDescription>
                                </Alert>
                                <div className="space-y-2">
                                    <Label htmlFor="twilio-sid">Account SID</Label>
                                    <Input id="twilio-sid" placeholder="AC..." value={twilioSid} onChange={(e) => setTwilioSid(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="twilio-token">Auth Token</Label>
                                    <Input id="twilio-token" type="password" placeholder="********" value={twilioToken} onChange={(e) => setTwilioToken(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="twilio-phone">Twilio Phone</Label>
                                    <Input id="twilio-phone" placeholder="whatsapp:+1..." value={twilioPhone} onChange={(e) => setTwilioPhone(e.target.value)} />
                                </div>
                                <Button
                                    onClick={handleConnectProvider}
                                    disabled={isConnecting || !twilioSid || !twilioToken || !twilioPhone}
                                    className="w-full bg-green-600 hover:bg-green-700 text-white"
                                >
                                    {isConnecting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                                    Connect Twilio
                                </Button>
                            </TabsContent>

                            {/* ─── QR SCAN TAB ──────────────────────────────────────── */}
                            <TabsContent value="baileys" className="space-y-4">
                                <Alert className="bg-red-50/50 border-red-200">
                                    <AlertDescription className="text-red-700 text-xs">
                                        <strong>{t('channels.whatsapp.qrAlertTitle', { defaultValue: 'API No Oficial (QR Scan)' })}:</strong>{' '}
                                        {t('channels.whatsapp.qrAlertDesc', { defaultValue: 'Este método limita las capacidades del agente en WhatsApp y utiliza una API no oficial (Open Source). Úselo con precaución; Meta podría bloquear su número si detecta spam o mensajes fraudulentos. Las opciones de flujos dinámicos y catálogos interactivos están deshabilitadas.' })}
                                    </AlertDescription>
                                </Alert>
                                <Button
                                    onClick={handleConnectBaileys}
                                    disabled={isConnecting}
                                    className="w-full bg-green-600 hover:bg-green-700 text-white"
                                >
                                    {isConnecting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <QrCode className="h-4 w-4 mr-2" />}
                                    {isConnecting ? t('common.saving', { defaultValue: 'Generando QR...' }) : t('channels.connectWhatsapp')}
                                </Button>
                            </TabsContent>
                        </Tabs>

                        <div className="mt-4 text-xs text-muted-foreground bg-muted/40 p-4 rounded-xl border border-dashed">
                            <span className="font-semibold text-foreground">💡 {t('channels.whatsapp.legendTitle', { defaultValue: 'Leyenda de Capacidades Dinámicas en WhatsApp:' })}</span>
                            <ul className="list-disc pl-5 mt-1.5 space-y-1">
                                <li>{t('channels.whatsapp.legendOfficial', { defaultValue: 'Twilio / Meta API (Oficial): Soporta WhatsApp Flows dinámicos, envío y recepción de carruseles de productos, notas de voz, respuestas interactivas estructuradas y transacciones en tiempo real de alta confiabilidad sin riesgo de bloqueo.' })}</li>
                                <li>{t('channels.whatsapp.legendUnofficial', { defaultValue: 'QR Scan (No Oficial): Solo soporta envío de texto básico y archivos multimedia simples. Las capacidades de comercio electrónico integrado y menús dinámicos no están disponibles.' })}</li>
                            </ul>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function TelegramCard({
    channel,
    onSave,
    isSaving,
    onDisconnect,
    isDisconnecting,
}: {
    channel?: Channel;
    onSave: (token: string) => void;
    isSaving: boolean;
    onDisconnect: () => void;
    isDisconnecting: boolean;
}) {
    const { t } = useTranslation();
    const [token, setToken] = useState(channel?.credentials?.telegram_token || channel?.credentials?.bot_token || '');

    useEffect(() => {
        if (channel?.credentials) {
            const tok = channel.credentials.telegram_token || channel.credentials.bot_token || '';
            if (tok) setToken(tok);
        }
    }, [channel]);

    const isConnected = channel?.status === 'active' || channel?.status === 'connected';

    return (
        <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
                        <MessageCircle className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base">{t('channels.telegramTitle')}</CardTitle>
                        <CardDescription>{t('channels.telegramDesc')}</CardDescription>
                    </div>
                </div>
                <StatusBadge status={channel?.status || 'inactive'} />
            </CardHeader>
            <CardContent className="space-y-4">
                {isConnected ? (
                    <div className="space-y-4">
                        <Alert className="bg-green-500/10 border-green-500/20">
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-700 dark:text-green-400">
                                ✓ {t('channels.connected')} {channel?.credentials?.bot_username ? `(@${channel.credentials.bot_username})` : ''}
                            </AlertDescription>
                        </Alert>
                        <Button
                            variant="destructive"
                            onClick={onDisconnect}
                            disabled={isDisconnecting}
                            className="w-full"
                        >
                            {isDisconnecting ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Unplug className="h-4 w-4 mr-2" />
                            )}
                            {t('channels.disconnect')}
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className="space-y-2">
                            <Label htmlFor="telegram_token">{t('common.token', { defaultValue: 'Bot Token' })}</Label>
                            <Input
                                id="telegram_token"
                                type="password"
                                placeholder={t('channels.telegramTokenPlaceholder')}
                                value={token}
                                onChange={(e) => setToken(e.target.value)}
                            />
                            <p className="text-xs text-muted-foreground">
                                {t('channels.getTokenHelp')}{' '}
                                <a
                                    href="https://t.me/BotFather"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary underline"
                                >
                                    @BotFather
                                    <ExternalLink className="ml-0.5 inline h-3 w-3" />
                                </a>
                            </p>
                        </div>
                        <Button
                            onClick={() => onSave(token)}
                            disabled={!token.trim() || isSaving}
                            className="w-full"
                        >
                            {isSaving ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="mr-2 h-4 w-4" />
                            )}
                            {channel ? t('common.save') : t('channels.connectTelegram')}
                        </Button>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

function EmailCard({
    channel,
    onSave,
    isSaving,
    onDisconnect,
    isDisconnecting,
}: {
    channel?: Channel;
    onSave: (creds: Record<string, string>) => void;
    isSaving: boolean;
    onDisconnect: () => void;
    isDisconnecting: boolean;
}) {
    const { t } = useTranslation();
    const [host, setHost] = useState(channel?.credentials?.smtp_host || '');
    const [port, setPort] = useState(channel?.credentials?.smtp_port ? String(channel.credentials.smtp_port) : '587');
    const [user, setUser] = useState(channel?.credentials?.email_user || channel?.credentials?.smtp_user || (channel as any)?.email_address || '');
    const [pass, setPass] = useState(channel?.credentials?.email_pass || channel?.credentials?.smtp_password || '');

    useEffect(() => {
        if (channel?.credentials) {
            if (channel.credentials.smtp_host) setHost(channel.credentials.smtp_host);
            if (channel.credentials.smtp_port) setPort(String(channel.credentials.smtp_port));
            if (channel.credentials.email_user || channel.credentials.smtp_user) {
                setUser(channel.credentials.email_user || channel.credentials.smtp_user);
            }
            if (channel.credentials.email_pass || channel.credentials.smtp_password) {
                setPass(channel.credentials.email_pass || channel.credentials.smtp_password);
            }
        } else if ((channel as any)?.email_address) {
            setUser((channel as any).email_address);
        }
    }, [channel]);

    const isConnected = channel?.status === 'active' || channel?.status === 'connected';

    return (
        <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900/30">
                        <Mail className="h-5 w-5 text-orange-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base">{t('channels.emailTitle')}</CardTitle>
                        <CardDescription>{t('channels.emailDesc')}</CardDescription>
                    </div>
                </div>
                <StatusBadge status={channel?.status || 'inactive'} />
            </CardHeader>
            <CardContent className="space-y-4">
                {isConnected ? (
                    <div className="space-y-4">
                        <Alert className="bg-green-500/10 border-green-500/20">
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-700 dark:text-green-400">
                                <div className="flex flex-col gap-0.5">
                                    <span>✓ {t('channels.connected')} {(channel as any)?.email_address ? <strong>({(channel as any).email_address})</strong> : ''}</span>
                                    {channel?.credentials?.smtp_host && (
                                        <span className="text-xs opacity-75">
                                            Host: {channel.credentials.smtp_host}:{channel.credentials.smtp_port || 587}
                                        </span>
                                    )}
                                </div>
                            </AlertDescription>
                        </Alert>
                        <Button
                            variant="destructive"
                            onClick={onDisconnect}
                            disabled={isDisconnecting}
                            className="w-full"
                        >
                            {isDisconnecting ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Unplug className="h-4 w-4 mr-2" />
                            )}
                            {t('channels.disconnect')}
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="smtp_host">{t('common.host', { defaultValue: 'SMTP Host' })}</Label>
                                <Input
                                    id="smtp_host"
                                    placeholder="smtp.gmail.com"
                                    value={host}
                                    onChange={(e) => setHost(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="smtp_port">{t('common.port', { defaultValue: 'Port' })}</Label>
                                <Input
                                    id="smtp_port"
                                    placeholder="587"
                                    value={port}
                                    onChange={(e) => setPort(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="smtp_user">{t('common.user', { defaultValue: 'Email / Username' })}</Label>
                                <Input
                                    id="smtp_user"
                                    placeholder="you@gmail.com"
                                    value={user}
                                    onChange={(e) => setUser(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="smtp_pass">{t('common.password')}</Label>
                                <Input
                                    id="smtp_pass"
                                    type="password"
                                    placeholder="••••••••"
                                    value={pass}
                                    onChange={(e) => setPass(e.target.value)}
                                />
                            </div>
                        </div>
                        <Button
                            onClick={() =>
                                onSave({
                                    smtp_host: host.trim(),
                                    smtp_port: port.trim(),
                                    smtp_user: user.trim(),
                                    smtp_password: pass,
                                    email_user: user.trim(),
                                    email_pass: pass,
                                    from_email: user.trim(),
                                })
                            }
                            disabled={!host.trim() || !user.trim() || !pass.trim() || isSaving}
                            className="w-full"
                        >
                            {isSaving ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="mr-2 h-4 w-4" />
                            )}
                            {channel ? t('common.save') : t('channels.connectEmail')}
                        </Button>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

function MeetingsAndCalendarCard() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    // Zoom form state
    const [zoomAccountId, setZoomAccountId] = useState('');
    const [zoomClientId, setZoomClientId] = useState('');
    const [zoomClientSecret, setZoomClientSecret] = useState('');
    const [zoomAccessToken, setZoomAccessToken] = useState('');

    // Teams form state
    const [teamsTenantId, setTeamsTenantId] = useState('common');
    const [teamsClientId, setTeamsClientId] = useState('');
    const [teamsClientSecret, setTeamsClientSecret] = useState('');
    const [teamsAccessToken, setTeamsAccessToken] = useState('');

    // Fetch unified meeting status
    const { data: meetingStatus, isLoading } = useQuery({
        queryKey: ['meetings-status'],
        queryFn: async () => {
            const { data } = await apiClient.get<{
                active_provider: string;
                providers: {
                    google: { name: string; connected: boolean; calendar_id?: string };
                    teams: { name: string; connected: boolean; tenant_id?: string };
                    zoom: { name: string; connected: boolean; account_id?: string };
                };
            }>('/integrations/meetings/status');
            return data;
        },
    });

    const activeProvider = meetingStatus?.active_provider || 'google';
    const isGoogleConnected = !!meetingStatus?.providers?.google?.connected;
    const isTeamsConnected = !!meetingStatus?.providers?.teams?.connected;
    const isZoomConnected = !!meetingStatus?.providers?.zoom?.connected;

    // Google calendars query
    const { data: calendarData, isLoading: isLoadingCalendars } = useQuery({
        queryKey: ['google-calendars'],
        queryFn: async () => {
            const { data } = await apiClient.get<{
                calendars: Array<{ id: string; name: string }>;
            }>('/auth/google/calendars');
            return data;
        },
        enabled: isGoogleConnected,
    });

    // Set active provider mutation
    const setProviderMutation = useMutation({
        mutationFn: async (provider: string) => {
            const { data } = await apiClient.post('/integrations/meetings/provider', { provider });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings-status'] });
            queryClient.invalidateQueries({ queryKey: ['company-settings'] });
            toast.success('Proveedor de reuniones actualizado con éxito.');
        },
        onError: () => {
            toast.error('Error al actualizar el proveedor de reuniones.');
        },
    });

    // Save calendar selection
    const saveCalendarMutation = useMutation({
        mutationFn: async (calendar_id: string) => {
            const { data } = await apiClient.post('/auth/google/config', { calendar_id });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings-status'] });
            toast.success('Calendario guardado correctamente.');
        },
        onError: () => {
            toast.error('Error al guardar el calendario.');
        },
    });

    // Connect Zoom mutation
    const connectZoomMutation = useMutation({
        mutationFn: async (payload: { account_id?: string; client_id?: string; client_secret?: string; access_token?: string }) => {
            const { data } = await apiClient.post('/integrations/meetings/zoom/connect', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings-status'] });
            toast.success('¡Zoom conectado exitosamente!');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al conectar Zoom.');
        },
    });

    // Connect Teams mutation
    const connectTeamsMutation = useMutation({
        mutationFn: async (payload: { tenant_id?: string; client_id?: string; client_secret?: string; access_token?: string }) => {
            const { data } = await apiClient.post('/integrations/meetings/teams/connect', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings-status'] });
            toast.success('¡Microsoft Teams conectado exitosamente!');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al conectar Microsoft Teams.');
        },
    });

    // Disconnect mutation
    const disconnectMutation = useMutation({
        mutationFn: async (provider: string) => {
            const { data } = await apiClient.post('/integrations/meetings/disconnect', { provider });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings-status'] });
            queryClient.invalidateQueries({ queryKey: ['company-settings'] });
            toast.success('Canal desconectado.');
        },
        onError: () => {
            toast.error('Error al desconectar.');
        },
    });

    // Handle Google Login
    const handleGoogleLogin = async () => {
        try {
            const res = await apiClient.get<any>('/auth/google/login');
            const authUrl = res.data?.data?.authorization_url || res.data?.authorization_url || res.data?.url;
            if (authUrl) {
                window.location.href = authUrl;
            } else {
                toast.error('No se pudo generar la URL de autenticación de Google.');
            }
        } catch {
            toast.error('Error iniciando sesión con Google.');
        }
    };

    if (isLoading) {
        return (
            <Card className="glass-card shadow-lg p-6">
                <div className="flex items-center gap-3">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Cargando proveedores de reuniones...</p>
                </div>
            </Card>
        );
    }

    const isCurrentActiveConnected =
        (activeProvider === 'google' && isGoogleConnected) ||
        (activeProvider === 'teams' && isTeamsConnected) ||
        (activeProvider === 'zoom' && isZoomConnected);

    return (
        <Card className="glass-card shadow-lg hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
                        <Video className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <CardTitle className="text-base">Reuniones y Calendario (Videoconferencias)</CardTitle>
                        <CardDescription>
                            Elige el proveedor que usará tu agente IA para agendar citas y generar salas automáticas.
                        </CardDescription>
                    </div>
                </div>
                <StatusBadge status={isCurrentActiveConnected ? 'active' : 'inactive'} />
            </CardHeader>
            <CardContent className="space-y-6">
                <Tabs defaultValue={activeProvider} onValueChange={(val) => setProviderMutation.mutate(val)}>
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="google" className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-red-500" />
                            Google Meet
                            {isGoogleConnected && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 ml-1" />}
                        </TabsTrigger>
                        <TabsTrigger value="teams" className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-purple-600" />
                            Microsoft Teams
                            {isTeamsConnected && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 ml-1" />}
                        </TabsTrigger>
                        <TabsTrigger value="zoom" className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-blue-500" />
                            Zoom
                            {isZoomConnected && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 ml-1" />}
                        </TabsTrigger>
                    </TabsList>

                    {/* ─── GOOGLE MEET TAB ────────────────────────────────────────── */}
                    <TabsContent value="google" className="space-y-4 pt-4">
                        {isGoogleConnected ? (
                            <div className="space-y-4">
                                <Alert className="bg-green-500/10 border-green-500/20">
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    <AlertDescription className="text-green-700 dark:text-green-400">
                                        ✓ Conectado a Google Calendar & Google Meet
                                    </AlertDescription>
                                </Alert>

                                <div className="space-y-2">
                                    <Label className="flex items-center gap-1.5">
                                        <Calendar className="h-4 w-4 text-muted-foreground" />
                                        Calendario Activo
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Selecciona el calendario donde tu agente IA programará las citas y generará enlaces de Google Meet.
                                    </p>
                                    {isLoadingCalendars ? (
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            Cargando calendarios disponibles...
                                        </div>
                                    ) : (
                                        <select
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                            value={meetingStatus?.providers?.google?.calendar_id || 'primary'}
                                            onChange={(e) => saveCalendarMutation.mutate(e.target.value)}
                                            disabled={saveCalendarMutation.isPending}
                                        >
                                            <option value="primary">Calendario Principal (primary)</option>
                                            {calendarData?.calendars?.map((cal) => (
                                                <option key={cal.id} value={cal.id}>
                                                    {cal.name}
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                </div>

                                <Button
                                    variant="destructive"
                                    onClick={() => disconnectMutation.mutate('google')}
                                    disabled={disconnectMutation.isPending}
                                    className="w-full mt-2"
                                >
                                    {disconnectMutation.isPending ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <Unplug className="h-4 w-4 mr-2" />
                                    )}
                                    Desconectar Google Meet
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <p className="text-sm text-muted-foreground">
                                    Permite a tus clientes agendar reuniones automáticamente. El agente verificará disponibilidad y creará la sala en Google Meet en segundos.
                                </p>
                                <Button onClick={handleGoogleLogin} variant="outline" className="w-full flex items-center justify-center gap-2">
                                    <svg className="h-4 w-4" viewBox="0 0 24 24">
                                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                    </svg>
                                    Iniciar Sesión con Google
                                </Button>
                            </div>
                        )}
                    </TabsContent>

                    {/* ─── MICROSOFT TEAMS TAB ────────────────────────────────────── */}
                    <TabsContent value="teams" className="space-y-4 pt-4">
                        {isTeamsConnected ? (
                            <div className="space-y-4">
                                <Alert className="bg-green-500/10 border-green-500/20">
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    <AlertDescription className="text-green-700 dark:text-green-400">
                                        ✓ Microsoft Teams Conectado (Tenant: {meetingStatus?.providers?.teams?.tenant_id || 'Empresarial'})
                                    </AlertDescription>
                                </Alert>
                                <Button
                                    variant="destructive"
                                    onClick={() => disconnectMutation.mutate('teams')}
                                    disabled={disconnectMutation.isPending}
                                    className="w-full"
                                >
                                    <Unplug className="h-4 w-4 mr-2" />
                                    Desconectar Microsoft Teams
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <p className="text-xs text-muted-foreground">
                                    Conecta Microsoft Entra ID (Azure) para generar salas en Microsoft Teams automáticamente.
                                </p>
                                <div className="space-y-2">
                                    <Label htmlFor="teams-tenant">Tenant ID (Directorio de Azure)</Label>
                                    <Input
                                        id="teams-tenant"
                                        placeholder="common o tu Directory ID"
                                        value={teamsTenantId}
                                        onChange={(e) => setTeamsTenantId(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="teams-client-id">Application (Client) ID</Label>
                                    <Input
                                        id="teams-client-id"
                                        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                        value={teamsClientId}
                                        onChange={(e) => setTeamsClientId(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="teams-secret">Client Secret</Label>
                                    <Input
                                        id="teams-secret"
                                        type="password"
                                        placeholder="Valor del secreto en Azure"
                                        value={teamsClientSecret}
                                        onChange={(e) => setTeamsClientSecret(e.target.value)}
                                    />
                                </div>
                                <Button
                                    onClick={() =>
                                        connectTeamsMutation.mutate({
                                            tenant_id: teamsTenantId,
                                            client_id: teamsClientId,
                                            client_secret: teamsClientSecret,
                                            access_token: teamsAccessToken,
                                        })
                                    }
                                    disabled={connectTeamsMutation.isPending || (!teamsClientId && !teamsAccessToken)}
                                    className="w-full bg-purple-600 hover:bg-purple-700 text-white"
                                >
                                    {connectTeamsMutation.isPending ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <Save className="h-4 w-4 mr-2" />
                                    )}
                                    Conectar Microsoft Teams
                                </Button>
                            </div>
                        )}
                    </TabsContent>

                    {/* ─── ZOOM TAB ───────────────────────────────────────────────── */}
                    <TabsContent value="zoom" className="space-y-4 pt-4">
                        {isZoomConnected ? (
                            <div className="space-y-4">
                                <Alert className="bg-green-500/10 border-green-500/20">
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    <AlertDescription className="text-green-700 dark:text-green-400">
                                        ✓ Zoom Conectado exitosamente
                                    </AlertDescription>
                                </Alert>
                                <Button
                                    variant="destructive"
                                    onClick={() => disconnectMutation.mutate('zoom')}
                                    disabled={disconnectMutation.isPending}
                                    className="w-full"
                                >
                                    <Unplug className="h-4 w-4 mr-2" />
                                    Desconectar Zoom
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <p className="text-xs text-muted-foreground">
                                    Configura tu aplicación <strong>Server-to-Server OAuth</strong> desde Zoom App Marketplace.
                                </p>
                                <div className="space-y-2">
                                    <Label htmlFor="zoom-account-id">Account ID</Label>
                                    <Input
                                        id="zoom-account-id"
                                        placeholder="ID de tu cuenta de Zoom"
                                        value={zoomAccountId}
                                        onChange={(e) => setZoomAccountId(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="zoom-client-id">Client ID</Label>
                                    <Input
                                        id="zoom-client-id"
                                        placeholder="Client ID de Zoom Marketplace"
                                        value={zoomClientId}
                                        onChange={(e) => setZoomClientId(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="zoom-client-secret">Client Secret</Label>
                                    <Input
                                        id="zoom-client-secret"
                                        type="password"
                                        placeholder="Client Secret de Zoom Marketplace"
                                        value={zoomClientSecret}
                                        onChange={(e) => setZoomClientSecret(e.target.value)}
                                    />
                                </div>
                                <Button
                                    onClick={() =>
                                        connectZoomMutation.mutate({
                                            account_id: zoomAccountId,
                                            client_id: zoomClientId,
                                            client_secret: zoomClientSecret,
                                            access_token: zoomAccessToken,
                                        })
                                    }
                                    disabled={
                                        connectZoomMutation.isPending ||
                                        (!zoomAccessToken && (!zoomAccountId || !zoomClientId || !zoomClientSecret))
                                    }
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                                >
                                    {connectZoomMutation.isPending ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <Save className="h-4 w-4 mr-2" />
                                    )}
                                    Conectar Zoom
                                </Button>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}

// --- NEW INTEGRATIONS ---


function TwilioVoiceCard() {
    const { t } = useTranslation();
    const [showEnterpriseModal, setShowEnterpriseModal] = useState(false);

    return (
        <>
            <Card className="glass-card shadow-lg border-indigo-500/30 bg-slate-900/60 relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-900/30 border border-purple-500/30 text-purple-400">
                            <PhoneCall className="h-5 w-5" />
                        </div>
                        <div>
                            <CardTitle className="text-base flex items-center gap-2">
                                {t('channels.twilio.title', { defaultValue: 'Canal de Llamadas de Voz con IA' })}
                                <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 text-[10px] uppercase font-bold">
                                    Exclusivo Enterprise (Próximamente)
                                </Badge>
                            </CardTitle>
                            <CardDescription>
                                {t('channels.twilio.desc', { defaultValue: 'Telefonía autónoma, llamadas entrantes/salientes y transcripción STT en tiempo real.' })}
                            </CardDescription>
                        </div>
                    </div>
                    <Badge variant="outline" className="border-slate-700 text-slate-400 text-xs">
                        Bloqueado en Beta
                    </Badge>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Alert className="bg-indigo-950/40 border-indigo-500/30 text-slate-300">
                        <PhoneCall className="h-4 w-4 text-indigo-400" />
                        <AlertDescription className="text-xs text-slate-300 leading-relaxed">
                            El canal de llamadas de voz y telefonía autónoma está reservado para clientes con infraestructura dedicada <strong>Enterprise</strong> para garantizar los más altos estándares de latencia (&lt;200ms) y cumplimiento de telecomunicaciones.
                        </AlertDescription>
                    </Alert>

                    <div className="p-4 rounded-xl bg-slate-950/50 border border-white/5 space-y-3 opacity-60 pointer-events-none select-none">
                        <div className="space-y-1.5">
                            <Label className="text-xs">Twilio / SIP Trunk SID</Label>
                            <Input placeholder="AC••••••••••••••••••••••••••••••••" disabled value="" />
                        </div>
                        <div className="space-y-1.5">
                            <Label className="text-xs">Auth Token / Secret</Label>
                            <Input type="password" placeholder="••••••••••••••••••••••••" disabled value="" />
                        </div>
                        <div className="space-y-1.5">
                            <Label className="text-xs">Número de Teléfono Asignado</Label>
                            <Input placeholder="+1 (800) •••-••••" disabled value="" />
                        </div>
                    </div>

                    <Button
                        type="button"
                        onClick={() => setShowEnterpriseModal(true)}
                        className="w-full py-5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-95 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/20 cursor-pointer"
                    >
                        🎙️ Solicitar Activación de Voz Enterprise
                    </Button>
                </CardContent>
            </Card>

            <EnterpriseOnboardingModal
                isOpen={showEnterpriseModal}
                onClose={() => setShowEnterpriseModal(false)}
                defaultNeed="voice_ai"
            />
        </>
    );
}

function WebchatCard({ channel }: { channel?: any }) {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [baseUrl, setBaseUrl] = useState('');

    useEffect(() => {
        if (typeof window !== 'undefined') {
            setBaseUrl(window.location.origin);
        }
    }, []);

    const widgetId = channel?.credentials?.widget_id;
    const isConnected = channel?.status === 'connected' || channel?.status === 'active';

    const generateMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/channels/connect', {
                type: 'webchat',
                name: 'Web Chat Widget',
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['channels'] });
            toast.success(t('common.success', { defaultValue: 'Widget ID generated successfully' }));
        },
        onError: (err: any) => {
            toast.error(err.response?.data?.error || t('common.error'));
        }
    });

    const copySnippet = () => {
        const snippet = `<script src="${baseUrl}/widget.js" data-widget-id="${widgetId}"></script>`;
        navigator.clipboard.writeText(snippet);
        toast.success(t('common.copied', { defaultValue: 'Snippet copied to clipboard' }));
    };

    const disconnectChannel = async () => {
        if (!channel?.id) return;
        try {
            await apiClient.delete(`/channels/${channel.id}`);
            queryClient.invalidateQueries({ queryKey: ['channels'] });
            toast.success(t('channels.disconnected'));
        } catch (err) {
            toast.error(t('common.error'));
        }
    };

    return (
        <Card className="border-blue-100 shadow-sm">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <MessageCircle className="h-5 w-5 text-blue-500" />
                        {t('channels.webchatTitle', { defaultValue: 'Web Chat Widget' })}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <StatusBadge status={channel?.status || 'disconnected'} />
                        {channel?.id && (
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50" onClick={disconnectChannel}>
                                <Unplug className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
                <CardDescription>
                    {t('channels.webchatDesc', { defaultValue: 'Embed a chat widget on your website to interact with customers.' })}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {!widgetId ? (
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-100 dark:border-blue-800 text-center">
                        <p className="text-sm text-blue-700 dark:text-blue-300 mb-4">
                            {t('channels.noWidgetId', { defaultValue: "You haven't generated a widget ID yet. Click the button below to get started." })}
                        </p>
                        <Button
                            onClick={() => generateMutation.mutate()}
                            disabled={generateMutation.isPending}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                        >
                            {generateMutation.isPending ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <QrCode className="mr-2 h-4 w-4" />
                            )}
                            {t('channels.generateWidget', { defaultValue: 'Generate Widget ID' })}
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                                {t('channels.yourWidgetId', { defaultValue: 'Your Widget ID' })}
                            </Label>
                            <div className="flex items-center gap-2">
                                <Input value={widgetId} readOnly className="font-mono text-sm bg-muted/50" />
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => {
                                        navigator.clipboard.writeText(widgetId);
                                        toast.success(t('common.copied', { defaultValue: 'Copied' }));
                                    }}
                                >
                                    <Save className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                                {t('channels.installationSnippet', { defaultValue: 'Installation Snippet' })}
                            </Label>
                            <div className="relative group">
                                <code className="text-[10px] break-all block bg-muted p-3 rounded-md border font-mono leading-relaxed">
                                    {`<script src="${baseUrl}/widget.js" data-widget-id="${widgetId}"></script>`}
                                </code>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    className="absolute top-2 right-2 h-7 px-2 text-[10px]"
                                    onClick={copySnippet}
                                >
                                    {t('common.copy')}
                                </Button>
                            </div>
                        </div>

                        {isConnected ? (
                            <Alert className="bg-green-50 dark:bg-green-900/20 border-green-100 dark:border-green-800">
                                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                                <AlertDescription className="text-xs text-green-700 dark:text-green-300">
                                    {t('channels.widgetDetected', { defaultValue: 'Widget detected and active on your site.' })}
                                </AlertDescription>
                            </Alert>
                        ) : (
                            <div className="flex items-center gap-2 text-xs text-yellow-600 justify-center py-2">
                                <RefreshCw className="h-3 w-3 animate-spin" />
                                {t('channels.waitingWidget', { defaultValue: 'Waiting for installation to be detected...' })}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
