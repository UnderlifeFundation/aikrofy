'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Server,
    Check,
    Loader2,
    Plug,
    Unplug,
    ExternalLink,
    Eye,
    EyeOff,
    ShieldCheck,
    AlertTriangle,
    Database,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface PlatformField {
    key: string;
    label: string;
    type: 'text' | 'password';
    required: boolean;
}

interface PlatformDef {
    label: string;
    fields: PlatformField[];
    url_placeholder: string;
    url_help: string;
}

interface ERPConfigDTO {
    id: number;
    company_id: number;
    platform: string;
    erp_url: string;
    is_connected: boolean;
    last_tested_at: string | null;
    last_error: string | null;
    credentials_configured?: string[];
    custom_schema?: object | null;
    created_at: string;
    updated_at: string;
}

/* ------------------------------------------------------------------ */
/* Platform brand colors                                               */
/* ------------------------------------------------------------------ */

const PLATFORM_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    sap_b1: { bg: 'from-[#0070F2]/10 to-[#0070F2]/5', border: 'border-[#0070F2]/30 hover:border-[#0070F2]', text: 'text-[#0070F2]' },
    netsuite: { bg: 'from-[#C74634]/10 to-[#C74634]/5', border: 'border-[#C74634]/30 hover:border-[#C74634]', text: 'text-[#C74634]' },
    odoo: { bg: 'from-[#714B67]/10 to-[#714B67]/5', border: 'border-[#714B67]/30 hover:border-[#714B67]', text: 'text-[#714B67]' },
    dynamics_bc: { bg: 'from-[#0078D4]/10 to-[#0078D4]/5', border: 'border-[#0078D4]/30 hover:border-[#0078D4]', text: 'text-[#0078D4]' },
    contifico: { bg: 'from-[#FF6F00]/10 to-[#FF6F00]/5', border: 'border-[#FF6F00]/30 hover:border-[#FF6F00]', text: 'text-[#FF6F00]' },
    mysql: { bg: 'from-[#00758F]/10 to-[#00758F]/5', border: 'border-[#00758F]/30 hover:border-[#00758F]', text: 'text-[#00758F]' },
};


/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function ERPSettingsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    // Local form state
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');
    const [erpUrl, setErpUrl] = useState('');
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

    // Fetch available platforms
    const { data: platformsData } = useQuery({
        queryKey: ['erp-platforms'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ platforms: Record<string, PlatformDef> }>('/erp/platforms');
            return data.platforms;
        },
    });

    // Fetch current config
    const { data: configData, isLoading: configLoading } = useQuery({
        queryKey: ['erp-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ config: ERPConfigDTO | null }>('/erp/config');
            return data.config;
        },
    });

    // Populate form when config loads
    useEffect(() => {
        if (configData) {
            setSelectedPlatform(configData.platform || '');
            setErpUrl(configData.erp_url || '');
        }
    }, [configData]);

    // Save mutation
    const saveMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/erp/config', {
                platform: selectedPlatform,
                erp_url: erpUrl,
                credentials,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['erp-config'] });
            toast.success(t('erp.configSaved'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || t('common.error'));
        },
    });

    // Test connection mutation
    const testMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/erp/test');
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['erp-config'] });
            if (data.result?.success) {
                toast.success(`${t('erp.connectionSuccess')} ${data.result.company_name ? `(${data.result.company_name})` : ''}`);
            } else {
                toast.error(`${t('erp.connectionFailed')}: ${data.result?.error || 'Unknown error'}`);
            }
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || t('common.error'));
        },
    });

    // Disconnect mutation
    const disconnectMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/erp/disconnect');
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['erp-config'] });
            setSelectedPlatform('');
            setErpUrl('');
            setCredentials({});
            toast.success(t('erp.disconnected'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || t('common.error'));
        },
    });

    const platforms = platformsData || {};
    const currentPlatformDef = platforms[selectedPlatform];
    const isConfigured = !!configData;
    const isConnected = configData?.is_connected;

    const handleCredentialChange = (key: string, value: string) => {
        setCredentials((prev) => ({ ...prev, [key]: value }));
    };

    const toggleSecret = (key: string) => {
        setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const handleSave = () => {
        if (!selectedPlatform) {
            toast.error(t('erp.selectPlatform'));
            return;
        }
        if (!erpUrl) {
            toast.error(t('erp.erpUrl') + ' is required');
            return;
        }
        saveMutation.mutate();
    };

    if (configLoading) {
        return (
            <div className="mx-auto max-w-4xl space-y-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-8">
            {/* Header */}
            <div>
                <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <Server className="h-8 w-8 text-primary" />
                    {t('erp.title')}
                </h2>
                <p className="text-muted-foreground mt-1">
                    {t('erp.description')}
                </p>
            </div>

            {/* Connection Status Banner */}
            {isConfigured && (
                <Card className={`border-2 ${isConnected ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-amber-500/50 bg-amber-500/5'}`}>
                    <CardContent className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-3">
                            {isConnected ? (
                                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20">
                                    <ShieldCheck className="h-5 w-5 text-emerald-500" />
                                </div>
                            ) : (
                                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/20">
                                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                                </div>
                            )}
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold">
                                        {t(`erp.platforms.${configData!.platform}`)}
                                    </span>
                                    <Badge variant={isConnected ? 'default' : 'secondary'}
                                        className={isConnected ? 'bg-emerald-500 hover:bg-emerald-600' : ''}>
                                        {isConnected ? t('erp.connected') : t('erp.notConnected')}
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {configData!.erp_url}
                                    {configData!.last_tested_at && (
                                        <> · {t('erp.lastTested')}: {new Date(configData!.last_tested_at).toLocaleString()}</>
                                    )}
                                </p>
                                {configData!.last_error && !isConnected && (
                                    <p className="text-xs text-destructive mt-1">{configData!.last_error}</p>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => testMutation.mutate()}
                                disabled={testMutation.isPending}
                            >
                                {testMutation.isPending ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Plug className="mr-2 h-4 w-4" />
                                )}
                                {testMutation.isPending ? t('erp.testing') : t('erp.testConnection')}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                    if (confirm(t('erp.disconnectConfirm'))) {
                                        disconnectMutation.mutate();
                                    }
                                }}
                                disabled={disconnectMutation.isPending}
                            >
                                <Unplug className="mr-2 h-4 w-4" />
                                {t('erp.disconnect')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Platform Selection */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5" />
                        {t('erp.selectPlatform')}
                    </CardTitle>
                    <CardDescription>{t('erp.selectPlatformDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                        {Object.entries(platforms).map(([key, def]) => {
                            const colors = PLATFORM_COLORS[key] || PLATFORM_COLORS.sap_b1;
                            const isSelected = selectedPlatform === key;
                            return (
                                <button
                                    key={key}
                                    onClick={() => {
                                        setSelectedPlatform(key);
                                        setCredentials({});
                                    }}
                                    className={`
                                        relative flex flex-col items-center gap-2 rounded-xl border-2 p-5
                                        bg-gradient-to-br transition-all duration-200
                                        ${colors.bg} ${colors.border}
                                        ${isSelected
                                            ? 'ring-2 ring-primary ring-offset-2 ring-offset-background border-primary shadow-lg scale-[1.02]'
                                            : 'hover:shadow-md hover:scale-[1.01]'
                                        }
                                    `}
                                >
                                    {isSelected && (
                                        <div className="absolute -right-1 -top-1 rounded-full bg-primary p-0.5">
                                            <Check className="h-3 w-3 text-primary-foreground" />
                                        </div>
                                    )}
                                    <span className={`text-sm font-semibold ${isSelected ? 'text-primary' : colors.text}`}>
                                        {def.label}
                                    </span>
                                    {configData?.platform === key && configData?.is_connected && (
                                        <Badge variant="default" className="bg-emerald-500 text-xs hover:bg-emerald-600">
                                            {t('erp.connected')}
                                        </Badge>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Credentials Form — only if a platform is selected */}
            {selectedPlatform && currentPlatformDef && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ExternalLink className="h-5 w-5" />
                            {t('erp.credentials')} — {currentPlatformDef.label}
                        </CardTitle>
                        <CardDescription>{t('erp.platformHelp.' + selectedPlatform, currentPlatformDef.url_help)}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* ERP URL */}
                        <div className="space-y-2">
                            <Label htmlFor="erp_url">{t('erp.erpUrl')}</Label>
                            <Input
                                id="erp_url"
                                value={erpUrl}
                                onChange={(e) => setErpUrl(e.target.value)}
                                placeholder={t('erp.platformPlaceholder.' + selectedPlatform, currentPlatformDef.url_placeholder)}
                            />
                        </div>

                        <Separator />

                        {/* Dynamic credential fields */}
                        <div className="grid gap-4 md:grid-cols-2">
                            {currentPlatformDef.fields.map((field) => (
                                <div key={field.key} className="space-y-2">
                                    <Label htmlFor={`cred_${field.key}`}>
                                        {t('erp.fields.' + field.key, field.label)}
                                        {field.required && <span className="text-destructive ml-1">*</span>}
                                    </Label>
                                    <div className="relative">
                                        <Input
                                            id={`cred_${field.key}`}
                                            type={field.type === 'password' && !showSecrets[field.key] ? 'password' : 'text'}
                                            value={credentials[field.key] || ''}
                                            onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                                            placeholder={
                                                configData?.credentials_configured?.includes(field.key)
                                                    ? '••••••••  (configured)'
                                                    : t('erp.fields.' + field.key, field.label)
                                            }
                                        />
                                        {field.type === 'password' && (
                                            <button
                                                type="button"
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                                onClick={() => toggleSecret(field.key)}
                                            >
                                                {showSecrets[field.key] ? (
                                                    <EyeOff className="h-4 w-4" />
                                                ) : (
                                                    <Eye className="h-4 w-4" />
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3 pt-2">
                            <Button
                                onClick={handleSave}
                                disabled={saveMutation.isPending}
                                className="min-w-[180px]"
                            >
                                {saveMutation.isPending ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Check className="mr-2 h-4 w-4" />
                                )}
                                {saveMutation.isPending ? t('erp.saving') : t('erp.saveConfig')}
                            </Button>

                            {isConfigured && configData?.platform === selectedPlatform && (
                                <Button
                                    variant="outline"
                                    onClick={() => testMutation.mutate()}
                                    disabled={testMutation.isPending}
                                >
                                    {testMutation.isPending ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Plug className="mr-2 h-4 w-4" />
                                    )}
                                    {testMutation.isPending ? t('erp.testing') : t('erp.testConnection')}
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Empty state — no platform selected and no config */}
            {!selectedPlatform && !isConfigured && (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="rounded-full bg-muted p-4 mb-4">
                            <Server className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold">{t('erp.noConfig')}</h3>
                        <p className="text-sm text-muted-foreground mt-1 max-w-md">
                            {t('erp.setupInstructions')}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
