'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    ShoppingCart,
    Store,
    Check,
    X,
    Loader2,
    Plug,
    Unplug,
    ExternalLink,
    Eye,
    EyeOff,
    ShieldCheck,
    AlertTriangle,
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

interface EcommerceConfigDTO {
    id: number;
    company_id: number;
    platform: string;
    store_url: string;
    is_connected: boolean;
    last_tested_at: string | null;
    last_error: string | null;
    credentials_configured?: string[];
    created_at: string;
    updated_at: string;
}

/* ------------------------------------------------------------------ */
/* Platform logos (inline SVGs for reliability)                         */
/* ------------------------------------------------------------------ */

const PLATFORM_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    shopify: { bg: 'from-[#96bf48]/10 to-[#96bf48]/5', border: 'border-[#96bf48]/30 hover:border-[#96bf48]', text: 'text-[#96bf48]' },
    woocommerce: { bg: 'from-[#9B5C8F]/10 to-[#9B5C8F]/5', border: 'border-[#9B5C8F]/30 hover:border-[#9B5C8F]', text: 'text-[#9B5C8F]' },
    vtex: { bg: 'from-[#F71963]/10 to-[#F71963]/5', border: 'border-[#F71963]/30 hover:border-[#F71963]', text: 'text-[#F71963]' },
    magento: { bg: 'from-[#EE672F]/10 to-[#EE672F]/5', border: 'border-[#EE672F]/30 hover:border-[#EE672F]', text: 'text-[#EE672F]' },
    prestashop: { bg: 'from-[#DF0067]/10 to-[#DF0067]/5', border: 'border-[#DF0067]/30 hover:border-[#DF0067]', text: 'text-[#DF0067]' },
    bigcommerce: { bg: 'from-[#121118]/10 to-[#34313F]/5', border: 'border-[#121118]/30 hover:border-[#121118]', text: 'text-foreground' },
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function EcommerceSettingsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    // Local form state
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');
    const [storeUrl, setStoreUrl] = useState('');
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

    // Fetch available platforms
    const { data: platformsData } = useQuery({
        queryKey: ['ecommerce-platforms'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ platforms: Record<string, PlatformDef> }>('/ecommerce/platforms');
            return data.platforms;
        },
    });

    // Fetch current config
    const { data: configData, isLoading: configLoading } = useQuery({
        queryKey: ['ecommerce-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ config: EcommerceConfigDTO | null }>('/ecommerce/config');
            return data.config;
        },
    });

    // Populate form when config loads
    useEffect(() => {
        if (configData) {
            setSelectedPlatform(configData.platform || '');
            setStoreUrl(configData.store_url || '');
            // Don't populate actual secrets — they're never returned
        }
    }, [configData]);

    // Save mutation
    const saveMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/ecommerce/config', {
                platform: selectedPlatform,
                store_url: storeUrl,
                credentials,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['ecommerce-config'] });
            toast.success(t('ecommerce.configSaved'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    // Test connection mutation
    const testMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/ecommerce/test');
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['ecommerce-config'] });
            if (data.result?.success) {
                toast.success(`${t('ecommerce.connectionSuccess')} ${data.result.store_name ? `(${data.result.store_name})` : ''}`);
            } else {
                toast.error(`${t('ecommerce.connectionFailed')}: ${data.result?.error || 'Unknown error'}`);
            }
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    // Disconnect mutation
    const disconnectMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/ecommerce/disconnect');
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['ecommerce-config'] });
            setSelectedPlatform('');
            setStoreUrl('');
            setCredentials({});
            toast.success(t('ecommerce.disconnected'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
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
            toast.error(t('ecommerce.selectPlatform'));
            return;
        }
        if (!storeUrl) {
            toast.error(t('ecommerce.storeUrl') + ' is required');
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
                    <ShoppingCart className="h-8 w-8 text-primary" />
                    {t('ecommerce.title')}
                </h2>
                <p className="text-muted-foreground mt-1">
                    {t('ecommerce.description')}
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
                                        {t(`ecommerce.platforms.${configData!.platform}`)}
                                    </span>
                                    <Badge variant={isConnected ? 'default' : 'secondary'}
                                        className={isConnected ? 'bg-emerald-500 hover:bg-emerald-600' : ''}>
                                        {isConnected ? t('ecommerce.connected') : t('ecommerce.notConnected')}
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {configData!.store_url}
                                    {configData!.last_tested_at && (
                                        <> · {t('ecommerce.lastTested')}: {new Date(configData!.last_tested_at).toLocaleString()}</>
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
                                {testMutation.isPending ? t('ecommerce.testing') : t('ecommerce.testConnection')}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                    if (confirm(t('ecommerce.disconnectConfirm'))) {
                                        disconnectMutation.mutate();
                                    }
                                }}
                                disabled={disconnectMutation.isPending}
                            >
                                <Unplug className="mr-2 h-4 w-4" />
                                {t('ecommerce.disconnect')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Platform Selection */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Store className="h-5 w-5" />
                        {t('ecommerce.selectPlatform')}
                    </CardTitle>
                    <CardDescription>{t('ecommerce.selectPlatformDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                        {Object.entries(platforms).map(([key, def]) => {
                            const colors = PLATFORM_COLORS[key] || PLATFORM_COLORS.bigcommerce;
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
                                            {t('ecommerce.connected')}
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
                            {t('ecommerce.credentials')} — {currentPlatformDef.label}
                        </CardTitle>
                        <CardDescription>{t('ecommerce.platformHelp.' + selectedPlatform, currentPlatformDef.url_help)}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Store URL */}
                        <div className="space-y-2">
                            <Label htmlFor="store_url">{t('ecommerce.storeUrl')}</Label>
                            <Input
                                id="store_url"
                                value={storeUrl}
                                onChange={(e) => setStoreUrl(e.target.value)}
                                placeholder={t('ecommerce.platformPlaceholder.' + selectedPlatform, currentPlatformDef.url_placeholder)}
                            />
                        </div>

                        <Separator />

                        {/* Dynamic credential fields */}
                        <div className="grid gap-4 md:grid-cols-2">
                            {currentPlatformDef.fields.map((field) => (
                                <div key={field.key} className="space-y-2">
                                    <Label htmlFor={`cred_${field.key}`}>
                                        {t('ecommerce.fields.' + field.key, field.label)}
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
                                                    : t('ecommerce.fields.' + field.key, field.label)
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
                                {saveMutation.isPending ? t('ecommerce.saving') : t('ecommerce.saveConfig')}
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
                                    {testMutation.isPending ? t('ecommerce.testing') : t('ecommerce.testConnection')}
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
                            <ShoppingCart className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold">{t('ecommerce.noConfig')}</h3>
                        <p className="text-sm text-muted-foreground mt-1 max-w-md">
                            {t('ecommerce.setupInstructions')}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
