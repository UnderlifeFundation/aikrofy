'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Cpu,
    Server,
    Check,
    Loader2,
    Plus,
    Trash2,
    Play,
    AlertCircle,
    Info,
    ExternalLink,
    RefreshCw,
    ToggleLeft,
    ToggleRight,
    Search,
    Braces,
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
import { useAuthStore } from '@/store/use-auth-store';

interface MCPServer {
    id: number;
    company_id: number;
    name: string;
    label: string;
    description: string | null;
    url: string;
    headers: Record<string, string>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

interface TestResultTool {
    name: string;
    description: string | null;
    arguments: Record<string, any>;
}

interface TestConnectionResponse {
    status: 'success' | 'warning' | 'error';
    message: string;
    tools: TestResultTool[];
}

export default function MCPSettingsPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const user = useAuthStore((s) => s.user);
    const companyId = user?.company_id;

    // UI States
    const [isAdding, setIsAdding] = useState(false);
    const [testingServerId, setTestingServerId] = useState<number | null>(null);
    const [testResults, setTestResults] = useState<Record<number, TestConnectionResponse>>({});
    const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>({});

    const DEFAULT_HEADERS_TEMPLATE = `{\n  "Authorization": "Bearer TU_TOKEN_DE_SEGURIDAD"\n}`;

    // Form States
    const [name, setName] = useState('');
    const [label, setLabel] = useState('');
    const [description, setDescription] = useState('');
    const [url, setUrl] = useState('');
    const [headersJson, setHeadersJson] = useState(DEFAULT_HEADERS_TEMPLATE);

    // Fetch registered MCP servers
    const { data: serversData, isLoading } = useQuery({
        queryKey: ['mcp-servers', companyId],
        queryFn: async () => {
            if (!companyId) return [];
            const { data } = await apiClient.get<{ servers: MCPServer[] }>(`/companies/${companyId}/mcp`);
            return data.servers;
        },
        enabled: !!companyId,
    });

    // Create server mutation
    const createMutation = useMutation({
        mutationFn: async () => {
            let parsedHeaders = {};
            const trimmed = headersJson.trim();
            if (trimmed) {
                try {
                    parsedHeaders = JSON.parse(trimmed);
                } catch (e) {
                    throw new Error('Invalid JSON format for Auth Headers. Please verify syntax.');
                }
            }

            const { data } = await apiClient.post(`/companies/${companyId}/mcp`, {
                name,
                label,
                description: description || null,
                url,
                headers: parsedHeaders,
                is_active: true,
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['mcp-servers', companyId] });
            toast.success('MCP Server registered successfully!');
            setIsAdding(false);
            // Reset form
            setName('');
            setLabel('');
            setDescription('');
            setUrl('');
            setHeadersJson(DEFAULT_HEADERS_TEMPLATE);
        },
        onError: (err: any) => {
            toast.error(err.message || err?.response?.data?.detail || 'Failed to register server.');
        },
    });

    // Toggle active status mutation
    const toggleMutation = useMutation({
        mutationFn: async (serverId: number) => {
            const { data } = await apiClient.post(`/companies/${companyId}/mcp/${serverId}/toggle`);
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['mcp-servers', companyId] });
            toast.success(data.message || 'Status updated.');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || 'Failed to toggle status.');
        },
    });

    // Delete server mutation
    const deleteMutation = useMutation({
        mutationFn: async (serverId: number) => {
            const { data } = await apiClient.delete(`/companies/${companyId}/mcp/${serverId}`);
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['mcp-servers', companyId] });
            toast.success(data.message || 'Server deleted.');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || 'Failed to delete server.');
        },
    });

    // Test connection mutation
    const testMutation = useMutation({
        mutationFn: async (serverId: number) => {
            setTestingServerId(serverId);
            const { data } = await apiClient.post<TestConnectionResponse>(`/companies/${companyId}/mcp/${serverId}/test`);
            return { serverId, data };
        },
        onSuccess: ({ serverId, data }) => {
            setTestResults((prev) => ({ ...prev, [serverId]: data }));
            if (data.status === 'success') {
                toast.success(data.message);
            } else if (data.status === 'warning') {
                toast.warning(data.message);
            } else {
                toast.error(data.message);
            }
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || 'Connection test failed.');
        },
        onSettled: () => {
            setTestingServerId(null);
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!name || !label || !url) {
            toast.error('Name, Label, and URL are required.');
            return;
        }
        createMutation.mutate();
    };

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-10 w-48" />
                    <Skeleton className="h-10 w-32" />
                </div>
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-5xl space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{t('mcp.title', 'Model Context Protocol (MCP)')}</h2>
                    <p className="text-muted-foreground">
                        {t('mcp.description', 'Integrate remote external services dynamically via HTTP/SSE. Register servers to expose custom APIs to your agent as executable tools.')}
                    </p>
                </div>
                {!isAdding && (
                    <Button onClick={() => setIsAdding(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        {t('mcp.addServer', 'Add MCP Server')}
                    </Button>
                )}
            </div>

            {/* Addition Form Card */}
            {isAdding && (
                <Card className="border-primary/20 bg-card/50 backdrop-blur-sm">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Cpu className="h-5 w-5 text-primary" />
                            Register New MCP Server
                        </CardTitle>
                        <CardDescription>
                            Configure connection details for an external SSE/HTTP-based MCP service.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid gap-6 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="name">System Name (Slug)</Label>
                                    <Input
                                        id="name"
                                        placeholder="e.g. crm-interno"
                                        value={name}
                                        onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ''))}
                                        required
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        URL-friendly unique slug. Used to prefix tool names.
                                    </p>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="label">Display Name</Label>
                                    <Input
                                        id="label"
                                        placeholder="e.g. CRM Interno"
                                        value={label}
                                        onChange={(e) => setLabel(e.target.value)}
                                        required
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Name visible in UI cards and lists.
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="url">Server SSE Endpoint URL</Label>
                                <Input
                                    id="url"
                                    placeholder="https://mcp.company.com/sse"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    required
                                />
                                <p className="text-xs text-muted-foreground">
                                    The Server-Sent Events handshake endpoint. Must be accessible over HTTPS/HTTP.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="description">Description</Label>
                                <Input
                                    id="description"
                                    placeholder="e.g. Provides tools to fetch customer balances and invoice history."
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="headers">Custom Auth Headers (JSON Format)</Label>
                                <textarea
                                    id="headers"
                                    rows={3}
                                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                    placeholder='{ "Authorization": "Bearer key-xxxx" }'
                                    value={headersJson}
                                    onChange={(e) => setHeadersJson(e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Define auth tokens or cookies required to handshake with the remote endpoint.
                                </p>
                            </div>

                            <div className="flex justify-end gap-3">
                                <Button type="button" variant="outline" onClick={() => setIsAdding(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={createMutation.isPending}>
                                    {createMutation.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Saving...
                                        </>
                                    ) : (
                                        'Register Server'
                                    )}
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            )}

            {/* List Registered Servers */}
            <div className="space-y-4">
                {(!serversData || serversData.length === 0) ? (
                    <Card className="border-dashed border-muted bg-transparent p-12 text-center">
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                            <Server className="h-6 w-6 text-primary" />
                        </div>
                        <h3 className="mt-4 text-lg font-semibold">{t('mcp.noServers', 'No MCP servers registered')}</h3>
                        <p className="mt-2 text-sm text-muted-foreground">
                            {t('mcp.help', 'Add custom external business functions so the agent can interact with your existing platforms in real-time.')}
                        </p>
                    </Card>
                ) : (
                    serversData.map((server) => {
                        const testResult = testResults[server.id];
                        const isTesting = testingServerId === server.id;
                        const showTools = expandedTools[server.id];

                        return (
                            <Card key={server.id} className="transition-all hover:shadow-md">
                                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <CardTitle className="text-xl font-bold">{server.label}</CardTitle>
                                            <Badge variant={server.is_active ? 'default' : 'secondary'} className={server.is_active ? 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20' : ''}>
                                                {server.is_active ? 'Active' : 'Inactive'}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-muted-foreground font-mono">{server.name} ({server.url})</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => toggleMutation.mutate(server.id)}
                                            title={server.is_active ? 'Deactivate' : 'Activate'}
                                        >
                                            {server.is_active ? (
                                                <ToggleRight className="h-6 w-6 text-emerald-500" />
                                            ) : (
                                                <ToggleLeft className="h-6 w-6 text-muted-foreground" />
                                            )}
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => {
                                                if (confirm(`Are you sure you want to delete "${server.label}"? This will remove all associated dynamic tools.`)) {
                                                    deleteMutation.mutate(server.id);
                                                }
                                            }}
                                            className="text-destructive hover:bg-destructive/10"
                                            title="Delete Connection"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {server.description && (
                                        <p className="text-sm text-muted-foreground">{server.description}</p>
                                    )}

                                    <div className="flex items-center gap-3">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            disabled={isTesting}
                                            onClick={() => testMutation.mutate(server.id)}
                                        >
                                            {isTesting ? (
                                                <>
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    Testing Connection...
                                                </>
                                            ) : (
                                                <>
                                                    <Play className="mr-2 h-3.5 w-3.5" />
                                                    Test Connection & Fetch Tools
                                                </>
                                            )}
                                        </Button>

                                        {testResult && testResult.tools.length > 0 && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => setExpandedTools((prev) => ({ ...prev, [server.id]: !prev[server.id] }))}
                                            >
                                                {showTools ? 'Hide Discovered Tools' : `Show Discovered Tools (${testResult.tools.length})`}
                                            </Button>
                                        )}
                                    </div>

                                    {/* Test Result status box */}
                                    {testResult && (
                                        <div className={`rounded-lg border p-4 text-sm flex gap-3 items-start ${
                                            testResult.status === 'success'
                                                ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                                                : testResult.status === 'warning'
                                                ? 'bg-amber-500/5 border-amber-500/20 text-amber-700 dark:text-amber-300'
                                                : 'bg-destructive/5 border-destructive/20 text-destructive'
                                        }`}>
                                            <Info className="h-5 w-5 shrink-0 mt-0.5" />
                                            <div>
                                                <p className="font-semibold capitalize">Connection {testResult.status}</p>
                                                <p className="mt-1 text-xs opacity-90">{testResult.message}</p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Discovered Tools Accordion */}
                                    {showTools && testResult && testResult.tools.length > 0 && (
                                        <div className="space-y-3 rounded-lg bg-muted/40 p-4 border">
                                            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                                                <Braces className="h-4 w-4 text-primary" />
                                                Imported Tools
                                            </div>
                                            <div className="grid gap-3">
                                                {testResult.tools.map((tool) => (
                                                    <div key={tool.name} className="bg-background border rounded-lg p-3 hover:border-primary/20 transition-all">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-sm font-mono font-bold text-primary">
                                                                mcp_{server.name}_{tool.name}
                                                            </span>
                                                            <Badge variant="outline" className="text-[10px]">
                                                                Type: JSON Schema
                                                            </Badge>
                                                        </div>
                                                        {tool.description && (
                                                            <p className="text-xs text-muted-foreground mt-1.5">{tool.description}</p>
                                                        )}
                                                        {tool.arguments && Object.keys(tool.arguments).length > 0 && (
                                                            <div className="mt-2.5">
                                                                <div className="text-[10px] font-semibold text-muted-foreground mb-1">Expected Arguments:</div>
                                                                <div className="flex flex-wrap gap-1.5">
                                                                    {Object.entries(tool.arguments).map(([argName, argVal]: [string, any]) => (
                                                                        <span key={argName} className="text-[10px] font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground" title={argVal.description}>
                                                                            {argName}: <span className="text-primary">{argVal.type}</span>
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })
                )}
            </div>
        </div>
    );
}
