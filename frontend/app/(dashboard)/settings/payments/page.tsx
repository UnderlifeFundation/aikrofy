'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { toast } from 'sonner';
import { 
    Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Eye, EyeOff, Key, Globe, Table as TableIcon, CheckCircle2, AlertTriangle, Trash2, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface ProviderField {
    key: string;
    label: string;
    type: string;
    required: boolean;
}

interface ProviderDef {
    label: string;
    fields: ProviderField[];
    url_placeholder?: string;
    url_help?: string;
}

interface PaymentConfigDTO {
    id: number;
    gateway_provider: string;
    api_endpoint: string | null;
    sandbox_mode: boolean;
    is_connected: boolean;
    last_tested_at: string | null;
    last_error: string | null;
    config_payload: Record<string, any>;
}

interface TransactionDTO {
    id: number;
    customer_name: string | null;
    customer_email: string | null;
    amount: string;
    currency: string;
    status: string;
    description: string | null;
    created_at: string;
}

// Brand styling classes per provider
const PROVIDER_THEMES: Record<string, { bg: string; border: string; text: string }> = {
    stripe: { bg: 'from-[#635BFF]/10 to-[#635BFF]/5', border: 'border-[#635BFF]/30 hover:border-[#635BFF]', text: 'text-[#635BFF]' },
    paypal: { bg: 'from-[#003087]/10 to-[#0079C1]/5', border: 'border-[#003087]/30 hover:border-[#003087]', text: 'text-[#0079C1]' },
    mercadopago: { bg: 'from-[#00B1EA]/10 to-[#00B1EA]/5', border: 'border-[#00B1EA]/30 hover:border-[#00B1EA]', text: 'text-[#00B1EA]' },
    kushki: { bg: 'from-[#0A2540]/10 to-[#0A2540]/5', border: 'border-[#0A2540]/30 hover:border-[#0A2540]', text: 'text-[#0A2540]' },
    nuvei: { bg: 'from-[#00A19B]/10 to-[#00A19B]/5', border: 'border-[#00A19B]/30 hover:border-[#00A19B]', text: 'text-[#00A19B]' },
    dlocal_go: { bg: 'from-[#002855]/10 to-[#002855]/5', border: 'border-[#002855]/30 hover:border-[#002855]', text: 'text-[#002855]' },
    authorize_net: { bg: 'from-[#2F6497]/10 to-[#2F6497]/5', border: 'border-[#2F6497]/30 hover:border-[#2F6497]', text: 'text-[#2F6497]' },
    custom: { bg: 'from-[#121118]/10 to-[#34313F]/5', border: 'border-[#121118]/30 hover:border-[#121118]', text: 'text-foreground' },
};

export default function PaymentsSettingsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    // Local form state
    const [selectedProvider, setSelectedProvider] = useState<string>('');
    const [apiEndpoint, setApiEndpoint] = useState('');
    const [sandboxMode, setSandboxMode] = useState(true);
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [configPayload, setConfigPayload] = useState<Record<string, any>>({});
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

    // Fetch providers schema
    const { data: providersData } = useQuery({
        queryKey: ['payment-providers'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ providers: Record<string, ProviderDef> }>('/payment-gateways/providers');
            return data.providers;
        }
    });

    // Fetch current active config
    const { data: configData, isLoading: configLoading } = useQuery({
        queryKey: ['payment-gateway-config'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ config: PaymentConfigDTO | null }>('/payment-gateways/config');
            return data.config;
        }
    });

    // Fetch transactions history log
    const { data: transactionsData } = useQuery({
        queryKey: ['payment-transactions'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ transactions: TransactionDTO[] }>('/payment-gateways/transactions');
            return data.transactions;
        }
    });

    // Populate local states when configuration loaded
    useEffect(() => {
        if (configData) {
            setSelectedProvider(configData.gateway_provider || '');
            setApiEndpoint(configData.api_endpoint || '');
            setSandboxMode(configData.sandbox_mode);
            setConfigPayload(configData.config_payload || {});
        }
    }, [configData]);

    const handleCredentialChange = (key: string, value: string) => {
        setCredentials(prev => ({ ...prev, [key]: value }));
    };

    const handleConfigPayloadChange = (key: string, value: string) => {
        setConfigPayload(prev => ({ ...prev, [key]: value }));
    };

    const toggleSecret = (key: string) => {
        setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // Save configuration mutation
    const saveMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/payment-gateways/config', {
                gateway_provider: selectedProvider,
                api_endpoint: apiEndpoint,
                credentials,
                config_payload: configPayload,
                sandbox_mode: sandboxMode,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['payment-gateway-config'] });
            toast.success(t('payments.configSaved'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        }
    });

    // Test connectivity mutation
    const testMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/payment-gateways/test');
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['payment-gateway-config'] });
            if (data.result?.success) {
                toast.success(t('payments.connectionSuccess'));
            } else {
                toast.error(`${t('payments.connectionFailed')}: ${data.result?.error || 'Unknown error'}`);
            }
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        }
    });

    // Disconnect mutation
    const disconnectMutation = useMutation({
        mutationFn: async () => {
            const { data } = await apiClient.post('/payment-gateways/disconnect');
            return data;
        },
        onSuccess: () => {
            setSelectedProvider('');
            setApiEndpoint('');
            setCredentials({});
            setConfigPayload({});
            queryClient.invalidateQueries({ queryKey: ['payment-gateway-config'] });
            toast.success(t('payments.disconnected'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('common.error'));
        }
    });

    const handleSave = () => {
        if (!selectedProvider) {
            toast.error(t('payments.selectProvider'));
            return;
        }
        saveMutation.mutate();
    };

    const handleDisconnect = () => {
        if (confirm(t('payments.disconnectConfirm'))) {
            disconnectMutation.mutate();
        }
    };

    if (configLoading) {
        return (
            <div className="flex h-96 items-center justify-center">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const currentProviderDef = providersData ? providersData[selectedProvider] : null;
    const isConnected = configData?.is_connected && configData.gateway_provider === selectedProvider;

    return (
        <div className="space-y-8 p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/75 bg-clip-text">
                    {t('payments.title')}
                </h1>
                <p className="text-muted-foreground text-lg">
                    {t('payments.description')}
                </p>
            </div>

            {/* Current Active Connection Banner */}
            {configData && (
                <div className={`rounded-xl border p-4 bg-gradient-to-br ${PROVIDER_THEMES[configData.gateway_provider]?.bg || 'from-muted to-muted/50'} ${PROVIDER_THEMES[configData.gateway_provider]?.border || 'border-border'}`}>
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <Badge className="text-xs uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 py-1">
                                {t('payments.active')}
                            </Badge>
                            <div>
                                <h2 className="text-lg font-semibold flex items-center gap-2">
                                    {configData.gateway_provider.toUpperCase()} 
                                    {isConnected ? (
                                        <CheckCircle2 className="h-5 w-5 text-emerald-500 inline" />
                                    ) : (
                                        <AlertTriangle className="h-5 w-5 text-amber-500 inline" />
                                    )}
                                </h2>
                                <p className="text-sm text-muted-foreground">
                                    {isConnected ? t('payments.connected') : t('payments.notConnected')}
                                    {configData.last_tested_at && (
                                        <> · {t('payments.lastTested')}: {new Date(configData.last_tested_at).toLocaleString()}</>
                                    )}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => testMutation.mutate()}
                                disabled={testMutation.isPending}
                            >
                                {testMutation.isPending ? t('payments.testing') : t('payments.testConnection')}
                            </Button>
                            <Button 
                                variant="destructive" 
                                size="sm" 
                                onClick={handleDisconnect}
                                disabled={disconnectMutation.isPending}
                            >
                                <Trash2 className="h-4 w-4 mr-2" />
                                {t('payments.disconnect')}
                            </Button>
                        </div>
                    </div>
                    {configData.last_error && (
                        <div className="mt-3 flex gap-2 text-sm text-red-500 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                            <ShieldAlert className="h-5 w-5 shrink-0" />
                            <span>{configData.last_error}</span>
                        </div>
                    )}
                </div>
            )}

            {/* Providers Selection Grid */}
            <div className="grid gap-6 md:grid-cols-4">
                {providersData && Object.entries(providersData).map(([key, def]) => {
                    const theme = PROVIDER_THEMES[key] || { bg: 'from-muted to-muted/50', border: 'border-border', text: 'text-foreground' };
                    const isSelected = selectedProvider === key;
                    
                    return (
                        <Card 
                            key={key} 
                            onClick={() => {
                                setSelectedProvider(key);
                                setCredentials({});
                                setConfigPayload({});
                            }}
                            className={`cursor-pointer transition-all duration-300 relative overflow-hidden group ${
                                isSelected 
                                    ? `bg-gradient-to-br ${theme.bg} ${theme.border} ring-2 ring-[#635BFF]/30` 
                                    : 'hover:bg-muted/50 border-muted'
                            }`}
                        >
                            <CardHeader className="p-4">
                                <CardTitle className="text-md flex items-center justify-between">
                                    <span className={theme.text}>{def.label}</span>
                                    {isSelected && <Badge variant="secondary" className="text-[10px] bg-primary/10 text-primary">{t('payments.selected')}</Badge>}
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    {t('payments.configureGateway')}
                                </CardDescription>
                            </CardHeader>
                        </Card>
                    );
                })}
            </div>

            {/* Config Form and Webhooks Details */}
            {selectedProvider && currentProviderDef && (
                <div className="grid gap-8 lg:grid-cols-3">
                    <Card className="lg:col-span-2 border-muted bg-gradient-to-b from-background to-muted/10">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Key className="h-5 w-5 text-primary" />
                                {t('payments.credentials')} — {currentProviderDef.label}
                            </CardTitle>
                            <CardDescription>
                                {t('payments.enterKeysHelp')}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* API Endpoint for Custom Gateways */}
                            {selectedProvider === 'custom' && (
                                <div className="space-y-2">
                                    <Label htmlFor="api_endpoint">{t('payments.endpointUrl')}</Label>
                                    <Input 
                                        id="api_endpoint"
                                        placeholder={currentProviderDef.url_placeholder}
                                        value={apiEndpoint}
                                        onChange={(e) => setApiEndpoint(e.target.value)}
                                        className="bg-background"
                                    />
                                    <p className="text-xs text-muted-foreground">{currentProviderDef.url_help}</p>
                                </div>
                            )}

                            {/* Credentials */}
                            {currentProviderDef.fields.map((field) => (
                                <div key={field.key} className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <Label htmlFor={field.key}>
                                            {t(`payments.fields.${field.key}`, { defaultValue: field.label })}
                                            {field.required && <span className="text-red-500 ml-1">*</span>}
                                        </Label>
                                    </div>
                                    <div className="relative">
                                        <Input
                                            id={field.key}
                                            type={field.type === 'password' && showSecrets[field.key] ? 'text' : field.type}
                                            placeholder="••••••••••••••••"
                                            value={credentials[field.key] || ''}
                                            onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                                            className="bg-background pr-10"
                                        />
                                        {field.type === 'password' && (
                                            <button
                                                type="button"
                                                onClick={() => toggleSecret(field.key)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                            >
                                                {showSecrets[field.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* Sandbox / Environment Switch */}
                            <div className="flex items-center justify-between rounded-lg border p-4 bg-background">
                                <div className="space-y-0.5">
                                    <Label>{t('payments.sandboxMode')}</Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t('payments.sandboxModeDesc')}
                                    </p>
                                </div>
                                <Switch 
                                    checked={sandboxMode}
                                    onCheckedChange={setSandboxMode}
                                />
                            </div>

                            {/* Webhook Secret mapping optional properties */}
                            {selectedProvider !== 'custom' && (
                                <div className="space-y-2 rounded-lg border p-4 bg-background/50">
                                    <Label htmlFor="webhook_secret">{t('payments.webhookSecret')}</Label>
                                    <Input 
                                        id="webhook_secret"
                                        type="password"
                                        placeholder={t('payments.webhookSecretPlaceholder')}
                                        value={configPayload['webhook_secret'] || ''}
                                        onChange={(e) => handleConfigPayloadChange('webhook_secret', e.target.value)}
                                        className="bg-background"
                                    />
                                    <p className="text-xs text-muted-foreground">{t('payments.webhookSecretHelp')}</p>
                                </div>
                            )}
                        </CardContent>
                        <CardFooter className="flex justify-between border-t p-6 bg-muted/20 rounded-b-xl">
                            <Button 
                                onClick={handleSave} 
                                disabled={saveMutation.isPending}
                                className="bg-[#635BFF] hover:bg-[#635BFF]/95 text-white"
                            >
                                {saveMutation.isPending ? t('payments.saving') : t('payments.saveConfig')}
                            </Button>
                        </CardFooter>
                    </Card>

                    {/* Side Info Box */}
                    <div className="space-y-6">
                        <Card className="border-muted bg-gradient-to-br from-background to-muted/20">
                            <CardHeader>
                                <CardTitle className="text-md flex items-center gap-2">
                                    <Globe className="h-5 w-5 text-[#635BFF]" />
                                    {t('payments.webhooks')}
                                </CardTitle>
                                <CardDescription>
                                    {t('payments.webhooksDesc')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="p-3 bg-muted rounded-lg border border-border">
                                    <p className="text-xs font-mono break-all select-all">
                                        {`https://api.aikrofy.com/api/payment-gateways/webhook/${selectedProvider}`}
                                    </p>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {currentProviderDef.url_help || t('payments.defaultWebhookHelp')}
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            )}

            {/* Transactions Ledger Log */}
            <Card className="border-muted">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <TableIcon className="h-5 w-5 text-primary" />
                        {t('payments.ledgerTitle')}
                    </CardTitle>
                    <CardDescription>
                        {t('payments.ledgerDescription')}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{t('payments.ledgerId')}</TableHead>
                                <TableHead>{t('payments.ledgerCustomer')}</TableHead>
                                <TableHead>{t('payments.ledgerAmount')}</TableHead>
                                <TableHead>{t('payments.ledgerDescriptionCol')}</TableHead>
                                <TableHead>{t('payments.ledgerStatus')}</TableHead>
                                <TableHead>{t('payments.ledgerDate')}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {transactionsData && transactionsData.length > 0 ? (
                                transactionsData.map((tx) => (
                                    <TableRow key={tx.id}>
                                        <TableCell className="font-mono text-xs">#{tx.id}</TableCell>
                                        <TableCell>
                                            <div className="font-medium">{tx.customer_name || 'Anonymous'}</div>
                                            <div className="text-xs text-muted-foreground">{tx.customer_email || ''}</div>
                                        </TableCell>
                                        <TableCell className="font-semibold">
                                            {tx.currency} {parseFloat(tx.amount).toFixed(2)}
                                        </TableCell>
                                        <TableCell className="max-w-[200px] truncate">{tx.description || '-'}</TableCell>
                                        <TableCell>
                                            <Badge variant={tx.status === 'captured' ? 'default' : tx.status === 'failed' ? 'destructive' : 'secondary'} className="capitalize text-xs font-semibold">
                                                {tx.status}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground">
                                            {new Date(tx.created_at).toLocaleString()}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                        {t('payments.noTransactions')}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
