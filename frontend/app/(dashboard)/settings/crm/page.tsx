'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Server,
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
    Database,
    Code,
    Sparkles
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
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

interface CRMConfigDTO {
    id: number;
    company_id: number;
    platform: string;
    crm_url: string | null;
    is_connected: boolean;
    last_tested_at: string | null;
    last_error: string | null;
    credentials_configured?: string[];
    custom_schema?: any;
    created_at: string;
    updated_at: string;
}

/* ------------------------------------------------------------------ */
/* Platform styling                                                    */
/* ------------------------------------------------------------------ */

const PLATFORM_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    hubspot: { bg: 'from-orange-500/10 to-orange-500/5', border: 'border-orange-500/30 hover:border-orange-500', text: 'text-orange-500' },
    salesforce: { bg: 'from-sky-500/10 to-sky-500/5', border: 'border-sky-500/30 hover:border-sky-500', text: 'text-sky-500' },
    pipedrive: { bg: 'from-emerald-500/10 to-emerald-500/5', border: 'border-emerald-500/30 hover:border-emerald-500', text: 'text-emerald-500' },
    zoho: { bg: 'from-red-500/10 to-red-500/5', border: 'border-red-500/30 hover:border-red-500', text: 'text-red-500' },
    dynamics_365: { bg: 'from-violet-500/10 to-violet-500/5', border: 'border-violet-500/30 hover:border-violet-500', text: 'text-violet-500' },
    custom: { bg: 'from-slate-500/10 to-slate-500/5', border: 'border-slate-500/30 hover:border-slate-500', text: 'text-foreground' },
};

export default function CRMSettingsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    // Local form state
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');
    const [crmUrl, setCrmUrl] = useState('');
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
    
    // AI Code-First custom mapping tools
    const [customPayloadSample, setCustomPayloadSample] = useState('');
    const [targetMappingEntity, setTargetMappingEntity] = useState('Contact');
    const [mappingLoading, setMappingLoading] = useState(false);
    const [generatedMapping, setGeneratedMapping] = useState<any>(null);

    // Fetch available platforms
    const { data: platformsData } = useQuery({
        queryKey: ['crm-platforms'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ platforms: Record<string, PlatformDef> }>('/crm/platforms');
            return data.platforms;
        },
    });

    // Fetch current config
    const { data: configData, isLoading: configLoading } = useQuery({
        queryKey: ['crm-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ config: CRMConfigDTO | null }>('/crm/config');
            return data.config;
        },
    });

    // Populate form when config loads
    useEffect(() => {
        if (configData) {
            setSelectedPlatform(configData.platform || '');
            setCrmUrl(configData.crm_url || '');
        }
    }, [configData]);

    // Save mutation
    const saveMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/crm/config', {
                platform: selectedPlatform,
                crm_url: crmUrl,
                credentials,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['crm-config'] });
            toast.success(t('crm.configSaved', 'CRM configuration saved.'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    // Test connection mutation
    const testMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/crm/test');
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['crm-config'] });
            if (data.result?.success) {
                toast.success(`${t('crm.connectionSuccess', 'Connection successful!')} (${data.result.crm_name})`);
            } else {
                toast.error(`${t('crm.connectionFailed', 'Connection failed')}: ${data.result?.error || 'Unknown error'}`);
            }
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    // Disconnect mutation
    const disconnectMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/crm/disconnect');
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['crm-config'] });
            setSelectedPlatform('');
            setCrmUrl('');
            setCredentials({});
            setGeneratedMapping(null);
            toast.success(t('crm.disconnected', 'CRM disconnected.'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        },
    });

    const handleAIGenerateMapping = async () => {
        if (!customPayloadSample.trim()) {
            toast.error('Please paste a sample JSON payload first.');
            return;
        }
        try {
            const parsed = JSON.parse(customPayloadSample);
            setMappingLoading(true);
            const { data } = await apiClient.post('/crm/generate-mapping', {
                sample_payload: parsed,
                entity: targetMappingEntity
            });
            setMappingLoading(false);
            if (data.success) {
                setGeneratedMapping(data.mapping);
                // Auto-fill credential fields or custom mapping parameters
                setCredentials(prev => ({
                    ...prev,
                    mappings: JSON.stringify({
                        ...(prev.mappings ? JSON.parse(prev.mappings) : {}),
                        [targetMappingEntity]: data.mapping
                    }, null, 2)
                }));
                toast.success(`AI successfully generated mapping for ${targetMappingEntity}!`);
            }
        } catch (e: any) {
            setMappingLoading(false);
            toast.error('Invalid JSON structure. Please check your sample payload.');
        }
    };

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
            toast.error(t('crm.selectPlatform', 'Select Platform'));
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
                    <Database className="h-8 w-8 text-primary" />
                    {t('crm.title', 'CRM Integration')}
                </h2>
                <p className="text-muted-foreground mt-1">
                    {t('crm.description', 'Connect your Customer Relationship Management system to allow AI agents to manage leads, contacts, accounts, and deal stages automatically.')}
                </p>
            </div>

            {/* Connection Banner */}
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
                                        {platforms[configData!.platform]?.label || configData!.platform}
                                    </span>
                                    <Badge variant={isConnected ? 'default' : 'secondary'}
                                        className={isConnected ? 'bg-emerald-500 hover:bg-emerald-600' : ''}>
                                        {isConnected ? t('crm.connected', 'Connected') : t('crm.notConnected', 'Not Connected')}
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {configData!.crm_url || 'Cloud SaaS Endpoint'}
                                    {configData!.last_tested_at && (
                                        <> · {t('crm.lastTested', 'Last tested')}: {new Date(configData!.last_tested_at).toLocaleString()}</>
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
                                {testMutation.isPending ? t('crm.testing', 'Testing...') : t('crm.testConnection', 'Test Connection')}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                    if (confirm(t('crm.disconnectConfirm', 'Are you sure you want to disconnect?'))) {
                                        disconnectMutation.mutate();
                                    }
                                }}
                                disabled={disconnectMutation.isPending}
                            >
                                <Unplug className="mr-2 h-4 w-4" />
                                {t('crm.disconnect', 'Disconnect CRM')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Platform Selection */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Server className="h-5 w-5" />
                        {t('crm.selectPlatform', 'Select Platform')}
                    </CardTitle>
                    <CardDescription>{t('crm.selectPlatformDesc', 'Choose your CRM platform to get started.')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                        {Object.entries(platforms).map(([key, def]) => {
                            const colors = PLATFORM_COLORS[key] || PLATFORM_COLORS.custom;
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
                                            {t('crm.connected', 'Connected')}
                                        </Badge>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Credentials & Config Form */}
            {selectedPlatform && currentPlatformDef && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ExternalLink className="h-5 w-5" />
                            {t('crm.credentials', 'Credentials')} — {currentPlatformDef.label}
                        </CardTitle>
                        <CardDescription>{t('crm.platformHelp.' + selectedPlatform, currentPlatformDef.url_help)}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* URL field (Only if not fixed SaaS api like HubSpot) */}
                        {selectedPlatform !== 'hubspot' && (
                            <div className="space-y-2">
                                <Label htmlFor="crm_url">{t('crm.crmUrl', 'CRM URL / Endpoint')}</Label>
                                <Input
                                    id="crm_url"
                                    value={crmUrl}
                                    onChange={(e) => setCrmUrl(e.target.value)}
                                    placeholder={t('crm.platformPlaceholder.' + selectedPlatform, currentPlatformDef.url_placeholder)}
                                />
                            </div>
                        )}

                        <Separator />

                        {/* Dynamic fields */}
                        <div className="grid gap-4 md:grid-cols-2">
                            {currentPlatformDef.fields.map((field) => (
                                <div key={field.key} className="space-y-2">
                                    <Label htmlFor={`cred_${field.key}`}>
                                        {t('crm.fields.' + field.key, field.label)}
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
                                                    ? '•••••••• (configured)'
                                                    : t('crm.fields.' + field.key, field.label)
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

                        {/* Custom platform tools */}
                        {selectedPlatform === 'custom' && (
                            <div className="mt-6 border-t pt-6 space-y-6">
                                <h3 className="text-lg font-semibold flex items-center gap-2">
                                    <Sparkles className="h-5 w-5 text-amber-500 animate-pulse" />
                                    AI-Driven Code-First Mapping Engine
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    Provide a sample JSON payload from your database/API response and select a canonical entity. Our AI will automatically deduce dot-notation paths for mapping.
                                </p>
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label>Target Canonical Entity</Label>
                                            <select
                                                value={targetMappingEntity}
                                                onChange={(e) => setTargetMappingEntity(e.target.value)}
                                                className="w-full border rounded-md p-2 bg-background"
                                            >
                                                <option value="Contact">Contact (Person)</option>
                                                <option value="Lead">Lead</option>
                                                <option value="Account">Account (Company)</option>
                                                <option value="Deal">Deal (Opportunity)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Raw JSON Response Sample</Label>
                                        <Textarea
                                            value={customPayloadSample}
                                            onChange={(e) => setCustomPayloadSample(e.target.value)}
                                            rows={6}
                                            placeholder='{\n  "fname": "Alice",\n  "lname": "Smith",\n  "contacts": {\n    "primary_email": "alice@gmail.com"\n  }\n}'
                                            className="font-mono text-xs"
                                        />
                                    </div>
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        onClick={handleAIGenerateMapping}
                                        disabled={mappingLoading}
                                        className="w-full flex items-center justify-center gap-2"
                                    >
                                        {mappingLoading ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Code className="h-4 w-4" />
                                        )}
                                        Generate Mapping via AI
                                    </Button>

                                    {generatedMapping && (
                                        <div className="bg-muted p-4 rounded-lg space-y-2 border">
                                            <div className="text-sm font-semibold flex justify-between items-center">
                                                <span>Resolved AI Mapping Paths:</span>
                                                <Badge variant="default">JSON Code-First</Badge>
                                            </div>
                                            <pre className="text-xs font-mono bg-background p-2 rounded border max-h-40 overflow-y-auto">
                                                {JSON.stringify(generatedMapping, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

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
                                {saveMutation.isPending ? t('crm.saving', 'Saving...') : t('crm.saveConfig', 'Save Configuration')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Empty state */}
            {!selectedPlatform && !isConfigured && (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="rounded-full bg-muted p-4 mb-4">
                            <Server className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold">{t('crm.noConfig', 'No CRM system connected yet.')}</h3>
                        <p className="text-sm text-muted-foreground mt-1 max-w-md">
                            {t('crm.setupInstructions', 'Select a CRM platform and enter your credentials to enable conversational contact, lead, and pipeline stage management.')}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
