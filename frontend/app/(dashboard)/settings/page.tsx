'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, User, Building2, Globe, Lock, Eye, EyeOff, Bot, Sparkles, Upload, Trash2, Image as ImageIcon, Volume2, Loader2, Flame, Zap, Coins, Receipt, Shield, Cpu, Key, CheckCircle2, AlertCircle, ExternalLink, SlidersHorizontal, CheckSquare, Square } from 'lucide-react';
import { WORKSPACE_MODULES, DEFAULT_STARTER_MODULES } from '@/components/shared/sidebar';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import { useTranslation } from 'react-i18next';

interface VoiceOption {
    ShortName: string;
    FriendlyName: string;
    Gender: string;
    Locale: string;
    Country?: string;
}

interface CompanySettings {
    id: number;
    name: string;
    logo_url: string | null;
    tax_id: string | null;
    business_type: string | null;
    business_name: string | null;
    country: string | null;
    city: string | null;
    timezone: string | null;
    language: string;
    email: string | null;
    phone: string | null;
    website: string | null;
    instagram: string | null;
    facebook: string | null;
    personal_story: string | null;
    api_key?: string | null;
    agent_name: string | null;
    agent_gender: string | null;
    voice_model: string | null;
    llm_provider: string | null;
    llm_model: string | null;
    llm_routing_mode?: 'core_pool' | 'byok' | string;
    api_keys?: Record<string, string | null>;
    lem_config?: {
        lem_enabled: boolean;
        lem_strict_mode: boolean;
        lem_sensitivity: number;
        is_byok: boolean;
        protection_credits: number;
    };
    enabled_modules?: string[];
    business_category?: string;
}

export default function SettingsPage() {
    const { t, i18n } = useTranslation();
    const queryClient = useQueryClient();
    const user = useAuthStore((s) => s.user);
    const isSuperAdmin = user?.role === 'super_admin';

    const logoInputRef = useRef<HTMLInputElement>(null);
    const [isTestingVoice, setIsTestingVoice] = useState(false);
    const [audioPlayer, setAudioPlayer] = useState<HTMLAudioElement | null>(null);

    const { data: settings, isLoading } = useQuery({
        queryKey: ['company-settings'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: CompanySettings }>('/companies/settings');
            return data.data;
        },
        enabled: !isSuperAdmin,
    });

    const { data: voiceList } = useQuery({
        queryKey: ['available-voices'],
        queryFn: async () => {
            try {
                const { data } = await apiClient.get<{ voices: VoiceOption[] }>('/voice/voices');
                return data.voices || [];
            } catch {
                return [];
            }
        },
        enabled: !isSuperAdmin,
    });

    const { data: transactions = [] } = useQuery({
        queryKey: ['company-transactions'],
        queryFn: async () => {
            try {
                const { data } = await apiClient.get('/billing/transactions');
                return Array.isArray(data) ? data : [];
            } catch {
                return [];
            }
        },
        enabled: !isSuperAdmin,
    });

    const { data: creditData } = useQuery({
        queryKey: ['credit-balance'],
        queryFn: async () => {
            try {
                const { data } = await apiClient.get('/billing/credits');
                return data;
            } catch {
                return { credit_balance: 0 };
            }
        },
        enabled: !isSuperAdmin,
    });

    const creditBalance = creditData?.credit_balance ?? 0;

    const updateUser = useAuthStore(state => state.updateUser);

    const [form, setForm] = useState<Partial<CompanySettings>>({});

    // Populate form when data loads
    const formData = { ...settings, ...form };

    const updateMutation = useMutation({
        mutationFn: async (payload: Partial<CompanySettings>) => {
            const { data } = await apiClient.put('/companies/settings', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['company-settings'] });
            
            // Sync specific globally-needed fields like tax_id or enabled_modules
            if (form.tax_id !== undefined || form.name !== undefined || form.enabled_modules !== undefined) {
                updateUser({
                    tax_id: form.tax_id,
                    name: form.name,
                    company: form.enabled_modules
                        ? ({ ...((user as any)?.company || {}), enabled_modules: form.enabled_modules } as any)
                        : undefined,
                } as any);
                if (form.enabled_modules) {
                    window.dispatchEvent(new CustomEvent('aikrofy:modules-updated', { detail: form.enabled_modules }));
                }
            }
            
            toast.success(t('common.successSettings', { defaultValue: 'Settings saved — your profile has been updated.' }));
            setForm({});
        },
        onError: (error: unknown) => {
            const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error || t('common.error');
            toast.error(message);
        },
    });

    const uploadLogoMutation = useMutation({
        mutationFn: async (file: File) => {
            const formDataUpload = new FormData();
            formDataUpload.append('file', file);
            const { data } = await apiClient.post<{ logo_url: string }>('/companies/logo', formDataUpload, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return data;
        },
        onSuccess: (res) => {
            queryClient.invalidateQueries({ queryKey: ['company-settings'] });
            setForm(prev => ({ ...prev, logo_url: res.logo_url }));
            toast.success(t('settings.logoUpdated', { defaultValue: 'Company logo updated successfully.' }));
        },
        onError: (error: unknown) => {
            const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error || t('common.error');
            toast.error(message);
        }
    });

    const handleLogoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (file.size > 5 * 1024 * 1024) {
                toast.error('El archivo no debe superar los 5MB.');
                return;
            }
            uploadLogoMutation.mutate(file);
        }
    };

    const handleRemoveLogo = () => {
        setForm(prev => ({ ...prev, logo_url: null }));
        updateMutation.mutate({ logo_url: '' as any });
        toast.info(t('settings.logoRemoved', { defaultValue: 'Logo removed.' }));
    };

    const handleTestVoice = async () => {
        setIsTestingVoice(true);
        if (audioPlayer) {
            audioPlayer.pause();
        }
        try {
            const sampleText = t('settings.voiceSampleText', { defaultValue: '¡Hola! Soy tu asistente virtual de inteligencia artificial, lista para atenderte.' });
            const selectedVoice = formData.voice_model === 'smart' ? undefined : (formData.voice_model || undefined);
            
            const response = await apiClient.post('/voice/synthesize', {
                text: sampleText,
                voice: selectedVoice,
                gender: formData.agent_gender || 'female',
                interface_language: formData.language || i18n.language || 'es'
            });

            const audioUrl = response.data.audio_url;
            if (audioUrl) {
                const fullAudioUrl = audioUrl.startsWith('http') ? audioUrl : audioUrl;
                const player = new Audio(fullAudioUrl);
                setAudioPlayer(player);
                player.play().catch(e => console.warn('Audio play block:', e));
            }
        } catch (error) {
            console.error('Test voice error:', error);
            toast.error('No se pudo generar la muestra de voz.');
        } finally {
            setIsTestingVoice(false);
        }
    };

    const handleSave = () => {
        if (Object.keys(form).length === 0) {
            toast.info(t('common.noChanges', { defaultValue: 'No changes to save.' }));
            return;
        }
        updateMutation.mutate(form);
    };

    const handleChange = (field: keyof CompanySettings, value: any) => {
        setForm((prev) => ({ ...prev, [field]: value }));
    };

    const handleApiKeyChange = (provider: string, key: string) => {
        setForm((prev) => ({
            ...prev,
            api_keys: {
                ...(formData.api_keys || {}),
                ...(prev.api_keys || {}),
                [provider]: key,
            },
        }));
    };

    const handleLemConfigChange = (field: string, val: any) => {
        setForm((prev) => ({
            ...prev,
            lem_config: {
                ...(formData.lem_config || {
                    lem_enabled: true,
                    lem_strict_mode: true,
                    lem_sensitivity: 0.20,
                    is_byok: false,
                    protection_credits: 0
                }),
                ...(prev.lem_config || {}),
                [field]: val,
            } as any,
        }));
    };

    const [testingLlmProvider, setTestingLlmProvider] = useState<string | null>(null);
    const testLlmMutation = useMutation({
        mutationFn: async ({ provider, api_key }: { provider: string; api_key?: string }) => {
            const { data } = await apiClient.post('/companies/test-llm-connection', {
                provider,
                api_key: api_key || (formData.api_keys || {})[provider] || undefined,
            });
            return data;
        },
        onSuccess: (data: any) => {
            toast.success(data?.message || 'Conexión verificada exitosamente.');
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.message || 'Error validando credenciales.';
            toast.error(msg);
        },
        onSettled: () => {
            setTestingLlmProvider(null);
        },
    });

    const handleTestLlm = (provider: string) => {
        setTestingLlmProvider(provider);
        const key = (formData.api_keys || {})[provider] || '';
        testLlmMutation.mutate({ provider, api_key: key });
    };

    // --- Password Change State ---
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);

    const changePasswordMutation = useMutation({
        mutationFn: async (payload: { current_password: string; new_password: string }) => {
            const { data } = await apiClient.post('/auth/change-password', payload);
            return data;
        },
        onSuccess: () => {
            toast.success(t('settings.passwordChanged'));
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        },
        onError: (error: unknown) => {
            const message = (error as { response?: { data?: { error?: string } } })?.response?.data?.error || t('common.error');
            toast.error(message);
        },
    });

    const handleChangePassword = () => {
        if (!currentPassword || !newPassword) {
            toast.error(t('settings.fillAllFields'));
            return;
        }
        if (newPassword.length < 6) {
            toast.error(t('settings.passwordMinLength'));
            return;
        }
        if (newPassword !== confirmPassword) {
            toast.error(t('settings.passwordsDoNotMatch'));
            return;
        }
        changePasswordMutation.mutate({
            current_password: currentPassword,
            new_password: newPassword,
        });
    };

    if (isLoading && !isSuperAdmin) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-64 w-full" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{t('settings.title')}</h2>
                    <p className="text-muted-foreground">
                        {isSuperAdmin
                            ? t('settings.descriptionAdmin', { defaultValue: 'Manage your account security.' })
                            : t('settings.description')}
                    </p>
                </div>
                {!isSuperAdmin && (
                    <Button onClick={handleSave} disabled={updateMutation.isPending}>
                        <Save className="mr-2 h-4 w-4" />
                        {updateMutation.isPending ? t('common.saving') : t('common.save')}
                    </Button>
                )}
            </div>

            {/* ===== Company-only sections ===== */}
            {!isSuperAdmin && (
                <>
                    {/* Personalizar Panel y Módulos Activos Card */}
                    <Card className="border-primary/40 bg-primary/5 shadow-sm">
                        <CardHeader>
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                <div>
                                    <CardTitle className="flex items-center gap-2 text-primary">
                                        <SlidersHorizontal className="h-5 w-5" />
                                        Personalizar Panel y Módulos Activos
                                    </CardTitle>
                                    <CardDescription className="mt-1">
                                        Marca con un check (✓) las herramientas que deseas ver en tu menú lateral. El Copiloto IA (Krof) detecta automáticamente los módulos habilitados para asistirte específicamente en ellos sin abrumarte.
                                    </CardDescription>
                                </div>
                                <div className="flex flex-wrap gap-1.5 shrink-0">
                                    <Button
                                        type="button"
                                        size="sm"
                                        variant="outline"
                                        className="h-8 text-xs"
                                        onClick={() => handleChange('enabled_modules', DEFAULT_STARTER_MODULES)}
                                    >
                                        🌱 Esencial + POS
                                    </Button>
                                    <Button
                                        type="button"
                                        size="sm"
                                        variant="outline"
                                        className="h-8 text-xs"
                                        onClick={() =>
                                            handleChange('enabled_modules', WORKSPACE_MODULES.map((m) => m.moduleKey))
                                        }
                                    >
                                        🏢 Activar Todos
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                                {WORKSPACE_MODULES.map((mod) => {
                                    const currentMods =
                                        formData.enabled_modules && formData.enabled_modules.length > 0
                                            ? formData.enabled_modules
                                            : DEFAULT_STARTER_MODULES;
                                    const isLocked = mod.moduleKey === 'dashboard' || mod.moduleKey === 'settings';
                                    const isChecked = isLocked || currentMods.includes(mod.moduleKey);

                                    const toggleMod = () => {
                                        if (isLocked) return;
                                        const nextMods = isChecked
                                            ? currentMods.filter((k) => k !== mod.moduleKey)
                                            : [...currentMods, mod.moduleKey];
                                        handleChange('enabled_modules', nextMods);
                                    };

                                    return (
                                        <div
                                            key={mod.moduleKey}
                                            onClick={toggleMod}
                                            className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer select-none ${
                                                isChecked
                                                    ? 'border-primary/60 bg-background shadow-2xs'
                                                    : 'border-border/60 bg-muted/20 opacity-65 hover:opacity-100'
                                            } ${isLocked ? 'cursor-not-allowed' : ''}`}
                                        >
                                            <div className="mt-0.5 text-primary shrink-0">
                                                {isChecked ? (
                                                    <CheckSquare className="h-4 w-4" />
                                                ) : (
                                                    <Square className="h-4 w-4 text-muted-foreground" />
                                                )}
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="font-semibold text-xs truncate">{mod.defaultLabel}</div>
                                                <div className="text-[10px] text-muted-foreground line-clamp-2 mt-0.5">
                                                    {mod.description}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            <div className="flex items-center justify-between pt-2 border-t text-xs text-muted-foreground">
                                <span>
                                    Haz clic en &ldquo;Guardar&rdquo; arriba a la derecha para aplicar los cambios en tu menú lateral.
                                </span>
                                <Button
                                    type="button"
                                    size="sm"
                                    onClick={handleSave}
                                    disabled={updateMutation.isPending}
                                >
                                    <Save className="h-3.5 w-3.5 mr-1.5" />
                                    Guardar Módulos Activos
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Company Logo Upload Card */}
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <ImageIcon className="h-5 w-5 text-primary" />
                                {t('settings.companyLogo', { defaultValue: 'Logo de la Empresa' })}
                            </CardTitle>
                            <CardDescription>
                                {t('settings.companyLogoDesc', { defaultValue: 'Sube el logo oficial de tu empresa. Se mostrará en el widget de chat, landing pages y cabeceras de atención.' })}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-xl border border-dashed border-border/80 bg-muted/20">
                                <div className="relative h-24 w-24 rounded-2xl bg-card border shadow-sm flex items-center justify-center overflow-hidden shrink-0 group">
                                    {formData.logo_url ? (
                                        <img 
                                            src={formData.logo_url} 
                                            alt="Logo Empresa" 
                                            className="h-full w-full object-contain p-2"
                                            onError={(e) => {
                                                (e.target as HTMLElement).style.display = 'none';
                                            }}
                                        />
                                    ) : (
                                        <div className="flex flex-col items-center justify-center text-muted-foreground">
                                            <ImageIcon className="h-8 w-8 opacity-40" />
                                            <span className="text-[10px] font-semibold mt-1">Sin Logo</span>
                                        </div>
                                    )}
                                </div>
                                <div className="flex-1 space-y-2 text-center sm:text-left">
                                    <div className="flex flex-wrap items-center gap-2 justify-center sm:justify-start">
                                        <input
                                            type="file"
                                            ref={logoInputRef}
                                            onChange={handleLogoFileChange}
                                            accept="image/png,image/jpeg,image/jpg,image/svg+xml,image/webp"
                                            className="hidden"
                                        />
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            onClick={() => logoInputRef.current?.click()}
                                            disabled={uploadLogoMutation.isPending}
                                            className="rounded-lg gap-2"
                                        >
                                            {uploadLogoMutation.isPending ? (
                                                <>
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                    {t('settings.uploadingLogo', { defaultValue: 'Subiendo...' })}
                                                </>
                                            ) : (
                                                <>
                                                    <Upload className="h-4 w-4" />
                                                    {formData.logo_url 
                                                        ? t('settings.changeLogo', { defaultValue: 'Cambiar Logo' }) 
                                                        : t('settings.uploadLogo', { defaultValue: 'Subir Logo' })}
                                                </>
                                            )}
                                        </Button>
                                        {formData.logo_url && (
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                onClick={handleRemoveLogo}
                                                className="text-destructive hover:text-destructive hover:bg-destructive/10 rounded-lg gap-1.5"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                                {t('settings.removeLogo', { defaultValue: 'Quitar' })}
                                            </Button>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {t('settings.logoFormats', { defaultValue: 'Formatos recomendados: PNG o SVG transparente, JPG o WebP (máx. 5MB).' })}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* AI Identity & Voice Configuration */}
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-primary">
                                <Bot className="h-5 w-5" />
                                {t('settings.aiIdentity')}
                            </CardTitle>
                            <CardDescription>
                                {t('settings.aiIdentityDesc')}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="grid gap-6 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="agent_name">{t('settings.agentNameLabel')}</Label>
                                <Input
                                    id="agent_name"
                                    value={formData.agent_name || ''}
                                    onChange={(e) => handleChange('agent_name', e.target.value)}
                                    placeholder="Freya"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="agent_gender">{t('settings.agentGenderLabel')}</Label>
                                <select
                                    id="agent_gender"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    value={formData.agent_gender || 'neutral'}
                                    onChange={(e) => handleChange('agent_gender', e.target.value)}
                                >
                                    <option value="neutral">{t('common.neutral')}</option>
                                    <option value="female">{t('common.female')}</option>
                                    <option value="male">{t('common.male')}</option>
                                </select>
                            </div>

                            {/* TTS Neural Voice Selector & Test Button */}
                            <div className="md:col-span-2 space-y-2 p-4 rounded-xl bg-card border border-border/70">
                                <div className="flex items-center justify-between">
                                    <Label htmlFor="voice_model" className="flex items-center gap-2 text-sm font-semibold">
                                        <Volume2 className="h-4 w-4 text-violet-500" />
                                        {t('settings.ttsVoiceLabel', { defaultValue: 'Motor de Voz TTS (Edge-TTS Neural)' })}
                                    </Label>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={handleTestVoice}
                                        disabled={isTestingVoice}
                                        className="h-8 gap-1.5 text-xs rounded-lg border-violet-500/30 hover:bg-violet-500/10 text-violet-600 dark:text-violet-400"
                                    >
                                        {isTestingVoice ? (
                                            <>
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                {t('settings.testingVoice', { defaultValue: 'Generando muestra...' })}
                                            </>
                                        ) : (
                                            <>
                                                <Volume2 className="h-3.5 w-3.5" />
                                                {t('settings.testVoice', { defaultValue: 'Probar Voz' })}
                                            </>
                                        )}
                                    </Button>
                                </div>
                                <select
                                    id="voice_model"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    value={formData.voice_model || 'smart'}
                                    onChange={(e) => handleChange('voice_model', e.target.value)}
                                >
                                    <option value="smart">
                                        {t('settings.smartVoiceOption', { defaultValue: '⚡ Inteligente / Dinámica (Detecta el idioma del visitante y respeta el género del agente)' })}
                                    </option>
                                    {voiceList && voiceList.filter(v => v.ShortName !== 'smart').map((v) => (
                                        <option key={v.ShortName} value={v.ShortName}>
                                            {v.FriendlyName}
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-muted-foreground">
                                    {t('settings.ttsVoiceDesc', { defaultValue: 'Voz neuronal de alta fidelidad para notas de voz y lectura automática de respuestas en el widget web y canales.' })}
                                </p>
                            </div>

                            <div className="md:col-span-2 space-y-2">
                                <Label htmlFor="personal_story" className="flex items-center gap-1">
                                    <Sparkles className="h-3 w-3 text-primary" />
                                    {t('settings.aiPersonality')}
                                </Label>
                                <textarea
                                    id="personal_story"
                                    className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                    value={formData.personal_story || ''}
                                    onChange={(e) => handleChange('personal_story', e.target.value)}
                                    placeholder={t('settings.aiPersonality')}
                                />
                                <p className="text-xs text-muted-foreground">
                                    {t('settings.personalityHint')}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* AI Engine & BYOK (Bring Your Own Key) + LEM-Ops Deterministic Invariant Arbiter */}
                    <Card className="border-indigo-500/40 bg-gradient-to-br from-card via-indigo-950/5 to-card shadow-sm">
                        <CardHeader>
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                <div>
                                    <CardTitle className="flex items-center gap-2 text-indigo-400">
                                        <Cpu className="h-5 w-5" />
                                        {t('settings.llmTitle', { defaultValue: 'Motor de Inferencia & BYOK (Tus Modelos Favoritos)' })}
                                    </CardTitle>
                                    <CardDescription>
                                        Conecta las API keys de tus proveedores favoritos de IA (OpenAI, Anthropic, Gemini, Groq). Aikrofy no cobra markup por tokens LLM en modo BYOK; la ejecución es supervisada por el motor determinista en silicio LEM-Ops.
                                    </CardDescription>
                                </div>
                                <Link href="/observatory">
                                    <Button variant="outline" size="sm" className="text-xs gap-1.5 border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10">
                                        <Shield className="h-3.5 w-3.5" />
                                        Ver Observatorio AI
                                    </Button>
                                </Link>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* LLM Routing Mode Switch: Core Pool vs BYOK */}
                            <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/20 space-y-3">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold text-white">Modo de Ruteo de Inferencia & Créditos</span>
                                            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                                {formData.llm_routing_mode === 'byok' ? 'Bypass Privado (BYOK)' : 'Fondo Core Oficial'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-0.5">
                                            {formData.llm_routing_mode === 'byok'
                                                ? 'Tus propios modelos privados: Aikrofy deduce únicamente 1 micro-crédito LEM de seguridad anti-alucinaciones por interacción.'
                                                : 'Fondo Core Aikrofy: El medidor total descuenta el consumo combinado (Créditos LEM + Créditos Inferencia LLM).'}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 bg-neutral-900/80 p-1 rounded-lg border border-neutral-800">
                                        <button
                                            type="button"
                                            onClick={() => handleChange('llm_routing_mode', 'core_pool')}
                                            className={`px-3 py-1 text-xs rounded-md font-medium transition cursor-pointer ${
                                                (formData.llm_routing_mode || 'core_pool') === 'core_pool'
                                                    ? 'bg-indigo-600 text-white shadow-sm'
                                                    : 'text-neutral-400 hover:text-white'
                                            }`}
                                        >
                                            Fondo Core
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => handleChange('llm_routing_mode', 'byok')}
                                            className={`px-3 py-1 text-xs rounded-md font-medium transition cursor-pointer ${
                                                formData.llm_routing_mode === 'byok'
                                                    ? 'bg-emerald-600 text-white shadow-sm'
                                                    : 'text-neutral-400 hover:text-white'
                                            }`}
                                        >
                                            BYOK / Privado
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Provider & Model Selectors */}
                            <div className="grid gap-6 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="llm_provider" className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                        Proveedor de IA
                                    </Label>
                                    <select
                                        id="llm_provider"
                                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                        value={formData.llm_provider || 'openai'}
                                        onChange={(e) => handleChange('llm_provider', e.target.value)}
                                    >
                                        <option value="openai">OpenAI (GPT-4o, GPT-5-nano, o1)</option>
                                        <option value="anthropic">Anthropic (Claude 3.5 Sonnet, Opus)</option>
                                        <option value="google">Google Gemini (Gemini 1.5 Pro, Flash)</option>
                                        <option value="groq">Groq (LPU Ultra-Low Latency / Llama 3)</option>
                                        <option value="deepseek">DeepSeek (V3, R1 Reasoning)</option>
                                        <option value="openrouter">OpenRouter (Multi-Model Gateway)</option>
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="llm_model" className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                        Modelo Específico
                                    </Label>
                                    <Input
                                        id="llm_model"
                                        value={formData.llm_model || ''}
                                        onChange={(e) => handleChange('llm_model', e.target.value)}
                                        placeholder="gpt-5-nano / claude-3-5-sonnet-20241022"
                                    />
                                </div>
                            </div>

                            {/* API Key Input + Live Test Connection Button */}
                            <div className="p-4 rounded-xl bg-muted/40 border border-border/80 space-y-3">
                                <div className="flex items-center justify-between">
                                    <Label className="flex items-center gap-2 text-sm font-semibold">
                                        <Key className="h-4 w-4 text-amber-400" />
                                        <span>Clave de API Propia ({formData.llm_provider?.toUpperCase() || 'OPENAI'})</span>
                                    </Label>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        disabled={testingLlmProvider === (formData.llm_provider || 'openai')}
                                        onClick={() => handleTestLlm(formData.llm_provider || 'openai')}
                                        className="h-8 gap-1.5 text-xs border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10 cursor-pointer"
                                    >
                                        {testingLlmProvider === (formData.llm_provider || 'openai') ? (
                                            <>
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                Probando Conexión...
                                            </>
                                        ) : (
                                            <>
                                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                                                Probar Conexión
                                            </>
                                        )}
                                    </Button>
                                </div>

                                <div className="relative">
                                    <Input
                                        type="password"
                                        value={(formData.api_keys || {})[formData.llm_provider || 'openai'] || ''}
                                        onChange={(e) => handleApiKeyChange(formData.llm_provider || 'openai', e.target.value)}
                                        placeholder={`Pega tu clave sk-... de ${formData.llm_provider || 'OpenAI'}`}
                                        className="font-mono text-xs pr-10"
                                    />
                                </div>
                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>
                                        {(formData.api_keys || {})[formData.llm_provider || 'openai'] ? (
                                            <span className="text-emerald-400 font-medium">✓ Clave BYOK configurada (Coste $0 en tokens Aikrofy)</span>
                                        ) : (
                                            <span className="text-neutral-400">Sin clave propia: El consumo usará el fondo de combustible compartido de Aikrofy.</span>
                                        )}
                                    </span>
                                </div>
                            </div>

                            {/* 🛡️ LEM-Ops Deterministic Invariant Arbiter Control */}
                            <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 space-y-4">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-800/80 pb-3">
                                    <div className="flex items-center gap-2">
                                        <Shield className="h-4 w-4 text-emerald-400" />
                                        <span className="text-sm font-semibold text-white">Motor Determinista LEM-Ops (Árbitro C99)</span>
                                    </div>
                                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                                        Latencia &lt; 300 µs • Cero Alucinación
                                    </span>
                                </div>

                                <div className="grid gap-4 sm:grid-cols-2 text-xs">
                                    <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-950/60 border border-neutral-800">
                                        <div className="space-y-0.5">
                                            <div className="font-medium text-neutral-200">Blindaje de Invariantes Pre-LLM</div>
                                            <div className="text-[11px] text-neutral-400">Evalúa la energía E(z, S) antes de llamar al modelo generativo.</div>
                                        </div>
                                        <input
                                            type="checkbox"
                                            checked={formData.lem_config?.lem_enabled ?? true}
                                            onChange={(e) => handleLemConfigChange('lem_enabled', e.target.checked)}
                                            className="h-4 w-4 rounded accent-indigo-500 cursor-pointer"
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-950/60 border border-neutral-800">
                                        <div className="space-y-0.5">
                                            <div className="font-medium text-neutral-200">Modo Estricto (Fail-Closed)</div>
                                            <div className="text-[11px] text-neutral-400">Bloquea respuestas si E(z, S) &gt; 0.20 o hay sospecha de jailbreak.</div>
                                        </div>
                                        <input
                                            type="checkbox"
                                            checked={formData.lem_config?.lem_strict_mode ?? true}
                                            onChange={(e) => handleLemConfigChange('lem_strict_mode', e.target.checked)}
                                            className="h-4 w-4 rounded accent-indigo-500 cursor-pointer"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-neutral-300 font-medium">Umbral de Estabilidad Invariante (τ / tau)</span>
                                        <span className="text-emerald-400 font-mono font-semibold">
                                            {formData.lem_config?.lem_sensitivity ?? 0.20} (Óptimo)
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min="0.05"
                                        max="0.50"
                                        step="0.01"
                                        value={formData.lem_config?.lem_sensitivity ?? 0.20}
                                        onChange={(e) => handleLemConfigChange('lem_sensitivity', parseFloat(e.target.value))}
                                        className="w-full accent-indigo-500 cursor-pointer"
                                    />
                                    <div className="flex justify-between text-[10px] text-neutral-500">
                                        <span>0.05 (Máxima Rigidez C99)</span>
                                        <span>0.20 (Recomendado)</span>
                                        <span>0.50 (Permisivo)</span>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Personal Information */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <User className="h-5 w-5" />
                                {t('settings.personalInfo')}
                            </CardTitle>
                            <CardDescription>{t('settings.personalInfoDesc')}</CardDescription>
                        </CardHeader>
                        <CardContent className="grid gap-6 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="name">{t('common.name')}</Label>
                                <Input
                                    id="name"
                                    value={formData.name || ''}
                                    onChange={(e) => handleChange('name', e.target.value)}
                                    placeholder={t('common.name')}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">{t('common.email')}</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={formData.email || ''}
                                    onChange={(e) => handleChange('email', e.target.value)}
                                    placeholder="you@example.com"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="phone">{t('common.phone')}</Label>
                                <Input
                                    id="phone"
                                    value={formData.phone || ''}
                                    onChange={(e) => handleChange('phone', e.target.value)}
                                    placeholder="+1234567890"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="contact_title">Título / Cargo</Label>
                                <Input
                                    id="contact_title"
                                    value={formData.business_type || ''}
                                    onChange={(e) => handleChange('business_type', e.target.value)}
                                    placeholder="Director General / CEO"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Business Information */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Building2 className="h-5 w-5" />
                                {t('settings.businessInfo')}
                            </CardTitle>
                            <CardDescription>{t('settings.businessInfoDesc')}</CardDescription>
                        </CardHeader>
                        <CardContent className="grid gap-6 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="business_name">{t('settings.businessName')}</Label>
                                <Input
                                    id="business_name"
                                    value={formData.business_name || ''}
                                    onChange={(e) => handleChange('business_name', e.target.value)}
                                    placeholder={t('settings.businessName')}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="tax_id">{t('settings.memberIdLabel', { defaultValue: 'Tax ID / RUC' })}</Label>
                                <Input
                                    id="tax_id"
                                    value={formData.tax_id || ''}
                                    onChange={(e) => handleChange('tax_id', e.target.value)}
                                    placeholder={t('settings.memberIdPlaceholder', { defaultValue: 'Your business identification number' })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="website">{t('settings.website')}</Label>
                                <Input
                                    id="website"
                                    value={formData.website || ''}
                                    onChange={(e) => handleChange('website', e.target.value)}
                                    placeholder="https://yoursite.com"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="instagram">{t('common.contact')} (Social)</Label>
                                <Input
                                    id="instagram"
                                    value={formData.instagram || ''}
                                    onChange={(e) => handleChange('instagram', e.target.value)}
                                    placeholder="@yourhandle"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Localization */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Globe className="h-5 w-5" />
                                {t('settings.localization')}
                            </CardTitle>
                            <CardDescription>{t('settings.localizationDesc')}</CardDescription>
                        </CardHeader>
                        <CardContent className="grid gap-6 md:grid-cols-3">
                            <div className="space-y-2">
                                <Label htmlFor="language">{t('settings.language')}</Label>
                                <select
                                    id="language"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                    value={formData.language || 'en'}
                                    onChange={(e) => handleChange('language', e.target.value)}
                                >
                                    <option value="en">{t('common.english')}</option>
                                    <option value="es">{t('common.spanish')}</option>
                                    <option value="pt">{t('common.portuguese')}</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="country">{t('settings.country')}</Label>
                                <Input
                                    id="country"
                                    value={formData.country || ''}
                                    onChange={(e) => handleChange('country', e.target.value)}
                                    placeholder="Ecuador"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="city">{t('settings.city')}</Label>
                                <Input
                                    id="city"
                                    value={formData.city || ''}
                                    onChange={(e) => handleChange('city', e.target.value)}
                                    placeholder="Quito"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Fuel & AI Credits / Invoicing */}
                    <Card className="border-indigo-500/30 bg-gradient-to-br from-card via-indigo-950/10 to-card shadow-sm overflow-hidden">
                        <CardHeader>
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div>
                                    <CardTitle className="flex items-center gap-2 text-indigo-400">
                                        <Flame className="h-5 w-5 text-amber-400 animate-pulse" />
                                        {t('sidebar.billingCredits', { defaultValue: 'Combustible IA & Facturación' })}
                                    </CardTitle>
                                    <CardDescription>
                                        Saldo prepago de créditos para agentes, llamadas de voz, RAG y comprobantes corporativos.
                                    </CardDescription>
                                </div>
                                <Link href="/pricing">
                                    <Button size="sm" className="bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white font-bold gap-1.5 shadow-md shadow-indigo-500/25 border-0 cursor-pointer">
                                        <Zap className="h-4 w-4 fill-current" />
                                        Recargar Combustible
                                    </Button>
                                </Link>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Balance Bar & Quick Presets */}
                            <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl bg-muted/40 border border-border/80 gap-4">
                                <div>
                                    <div className="text-xs text-muted-foreground uppercase font-semibold tracking-wider">Saldo de Combustible IA</div>
                                    <div className="text-2xl sm:text-3xl font-black text-foreground flex items-center gap-2 mt-0.5">
                                        <Coins className="h-6 w-6 text-amber-400 shrink-0" />
                                        {creditBalance === -1 ? '∞ Ilimitado' : `${(creditBalance || 0).toLocaleString()} Créditos`}
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2 justify-center sm:justify-end">
                                    {[20, 50, 100, 250, 500].map((preset) => (
                                        <Link key={preset} href={`/pricing?amount=${preset}`}>
                                            <Button variant="outline" size="sm" className="text-xs font-semibold hover:border-indigo-500 hover:text-indigo-400 cursor-pointer">
                                                +${preset} USD
                                            </Button>
                                        </Link>
                                    ))}
                                </div>
                            </div>

                            {/* Invoicing Table */}
                            <div className="space-y-2">
                                <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                    <Receipt className="h-3.5 w-3.5" />
                                    Historial de Comprobantes & Recargas
                                </div>
                                {transactions.length === 0 ? (
                                    <div className="p-4 rounded-lg border border-dashed text-center text-xs text-muted-foreground">
                                        No hay comprobantes de recarga registrados aún. Las recargas generarán facturas automáticas con ID aquí.
                                    </div>
                                ) : (
                                    <div className="rounded-lg border overflow-x-auto">
                                        <table className="w-full text-left text-xs min-w-[500px]">
                                            <thead className="bg-muted/50 border-b font-medium text-muted-foreground">
                                                <tr>
                                                    <th className="p-2.5">Factura / Orden</th>
                                                    <th className="p-2.5">Fecha</th>
                                                    <th className="p-2.5">Monto</th>
                                                    <th className="p-2.5">Créditos</th>
                                                    <th className="p-2.5">Estado</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-border/60">
                                                {transactions.map((tx: any) => (
                                                    <tr key={tx.id} className="hover:bg-muted/30">
                                                        <td className="p-2.5 font-mono font-semibold text-foreground">{tx.provider_order_id || `AIK-CRED-${tx.id}`}</td>
                                                        <td className="p-2.5 text-muted-foreground">{tx.created_at ? new Date(tx.created_at).toLocaleDateString() : '-'}</td>
                                                        <td className="p-2.5 font-bold text-foreground">${tx.amount?.toFixed(2)} USD</td>
                                                        <td className="p-2.5 text-amber-400 font-semibold">+{tx.credits_granted?.toLocaleString() || 0}</td>
                                                        <td className="p-2.5">
                                                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                                {tx.status || 'Completado'}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            {/* ===== Security (Password Change) — Available to ALL roles ===== */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Lock className="h-5 w-5" />
                        {t('settings.security')}
                    </CardTitle>
                    <CardDescription>{t('settings.securityDesc')}</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                        <Label htmlFor="current_password">{t('settings.currentPassword')}</Label>
                        <div className="relative">
                            <Input
                                id="current_password"
                                type={showCurrentPassword ? 'text' : 'password'}
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                placeholder="••••••••"
                            />
                            <button
                                type="button"
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                            >
                                {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                    </div>
                    <div /> {/* Spacer for grid alignment */}
                    <div className="space-y-2">
                        <Label htmlFor="new_password">{t('settings.newPassword')}</Label>
                        <div className="relative">
                            <Input
                                id="new_password"
                                type={showNewPassword ? 'text' : 'password'}
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="••••••••"
                            />
                            <button
                                type="button"
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowNewPassword(!showNewPassword)}
                            >
                                {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="confirm_password">{t('settings.confirmPassword')}</Label>
                        <Input
                            id="confirm_password"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="••••••••"
                        />
                    </div>
                    <div className="md:col-span-2 flex justify-end">
                        <Button
                            onClick={handleChangePassword}
                            disabled={changePasswordMutation.isPending}
                            variant="outline"
                        >
                            <Lock className="mr-2 h-4 w-4" />
                            {changePasswordMutation.isPending
                                ? t('common.saving')
                                : t('settings.updatePassword')}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
