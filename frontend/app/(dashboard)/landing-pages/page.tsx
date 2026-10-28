'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Plus, Globe, BarChart3, Settings, Eye, Smartphone, Tablet, Monitor,
    Zap, Trash2, ExternalLink, Copy, CheckCircle2, Clock, AlertCircle,
    Layers, RefreshCw, Upload
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api-client';
import { useTranslation } from 'react-i18next';
import { io } from 'socket.io-client';
import { useAuthStore } from '@/store/use-auth-store';

// ── Types ──────────────────────────────────────────────────────────────────

interface LandingPage {
    id: number;
    title: string;
    slug: string;
    status: 'draft' | 'published' | 'archived';
    version: number;
    is_primary: boolean;
    custom_domain: string | null;
    views_count: number;
    conversions_count: number;
    generation_status: 'idle' | 'generating' | 'complete' | 'error';
    generation_error: string | null;
    has_content: boolean;
    llm_model: string;
    created_at: string;
    updated_at: string;
    published_at: string | null;
}

// ── Status Badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: LandingPage['status'] }) {
    const { t } = useTranslation();
    const config = {
        draft: { label: t('landing.draft', 'Borrador'), className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
        published: { label: t('landing.published', 'Publicada'), className: 'bg-green-500/20 text-green-400 border-green-500/30' },
        archived: { label: t('landing.archived', 'Archivada'), className: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
    };
    const { label, className } = config[status] || config.draft;
    return (
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${className}`}>
            {label}
        </span>
    );
}

function GenerationStatusIndicator({ status, error }: { status: string; error: string | null }) {
    const { t } = useTranslation();
    if (status === 'generating') {
        return (
            <span className="flex items-center gap-1 text-xs text-blue-400">
                <RefreshCw className="h-3 w-3 animate-spin" /> {t('landing.generating', 'Generando...')}
            </span>
        );
    }
    if (status === 'error') {
        return (
            <span className="flex items-center gap-1 text-xs text-red-400" title={error || ''}>
                <AlertCircle className="h-3 w-3" /> {t('landing.generationError', 'Error en generación')}
            </span>
        );
    }
    if (status === 'complete') {
        return (
            <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle2 className="h-3 w-3" /> {t('landing.ready', 'Listo')}
            </span>
        );
    }
    return null;
}

// ── Create Landing Dialog ─────────────────────────────────────────────────────

interface CreateLandingDialogProps {
    open: boolean;
    onClose: () => void;
    onCreated: (page: LandingPage) => void;
}

function CreateLandingDialog({ open, onClose, onCreated }: CreateLandingDialogProps) {
    const { t } = useTranslation();
    const [title, setTitle] = useState('');
    const [prompt, setPrompt] = useState('');
    const [screenshotUrl, setScreenshotUrl] = useState('');
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [loading, setLoading] = useState(false);
    const [campaignId, setCampaignId] = useState<string>('');

    const { data: campaigns = [] } = useQuery({
        queryKey: ['strategic-campaigns'],
        queryFn: async () => {
            const { data } = await apiClient.get('/campaigns');
            return data.campaigns || [];
        },
    });

    const handleFileChange = (file: File) => {
        if (!file.type.startsWith('image/')) {
            toast.error('Por favor, selecciona un archivo de imagen válido.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const base64Data = e.target?.result as string;
            setScreenshotUrl(base64Data);
            setImagePreview(base64Data);
        };
        reader.readAsDataURL(file);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileChange(e.dataTransfer.files[0]);
        }
    };

    const handleCreate = async () => {
        if (!title.trim()) {
            toast.error('El título es requerido.');
            return;
        }
        setLoading(true);
        try {
            // 1. Create the landing page
            const payload: any = { title, prompt };
            if (campaignId) {
                payload.campaign_id = Number(campaignId);
            }
            const { data: createData } = await apiClient.post('/landing-pages/', payload);
            const page: LandingPage = createData.landing_page;

            // 2. Trigger generation if prompt or screenshot was provided
            if (prompt.trim() || screenshotUrl.trim()) {
                try {
                    await apiClient.post(`/landing-pages/${page.id}/generate`, {
                        prompt,
                        screenshot_url: screenshotUrl,
                        generation_type: 'create',
                    });
                    toast.success('Landing creada. IA generando contenido...');
                } catch (genErr: any) {
                    const errMsg = genErr?.response?.data?.error || 'Error al iniciar la generación.';
                    toast.warning(`Landing creada, pero: ${errMsg}`);
                }
            } else {
                toast.success('Landing creada como borrador.');
            }

            onCreated(page);
            onClose();
            setTitle('');
            setPrompt('');
            setScreenshotUrl('');
            setImagePreview(null);
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al crear la landing page.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-2xl bg-card border border-border text-foreground">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                        <Zap className="h-5 w-5 text-violet-400" />
                        {t('landing.newLandingDialogTitle', 'Nueva Landing Page con IA')}
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-5 py-2">
                    <div>
                        <Label className="text-sm text-foreground/80 mb-1.5 block">{t('landing.titleLabel', 'Título *')}</Label>
                        <Input
                            placeholder="Ej: Landing de Lanzamiento - Producto Pro"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="bg-muted/40 border-border text-white placeholder:text-muted-foreground/40"
                        />
                    </div>
                    <div>
                        <Label className="text-sm text-foreground/80 mb-1.5 block">
                            Vincular a Campaña Estratégica <span className="text-muted-foreground/60">(opcional)</span>
                        </Label>
                        <select
                            value={campaignId}
                            onChange={(e) => setCampaignId(e.target.value)}
                            className="w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500 transition-colors"
                        >
                            <option value="" className="bg-card text-muted-foreground">Ninguna (Sin campaña)</option>
                            {campaigns.map((camp: any) => (
                                <option key={camp.id} value={camp.id} className="bg-card text-white">
                                    {camp.name} {camp.is_active ? '🟢' : '⚪'}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <Label className="text-sm text-foreground/80 mb-1.5 block">
                            Descripción para IA <span className="text-muted-foreground/60">(opcional — genera el contenido automáticamente)</span>
                        </Label>
                        <Textarea
                            placeholder="Ej: Somos una agencia de marketing digital en México. Nuestro producto principal es el pack de automatización para PYMES. El público objetivo son dueños de negocio 35-55 años. Color principal: morado. Tono: profesional pero cercano."
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            rows={4}
                            className="bg-muted/40 border-border text-white placeholder:text-muted-foreground/40 resize-none"
                        />
                    </div>
                    <div>
                        <Label className="text-sm text-foreground/80 mb-1.5 block">
                            Diseño de Referencia o Mockup <span className="text-muted-foreground/60">(opcional — sube un diseño para que la IA se base en él)</span>
                        </Label>
                        
                        {!imagePreview ? (
                            <div
                                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                                onDragLeave={() => setIsDragOver(false)}
                                onDrop={handleDrop}
                                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-6 transition-all cursor-pointer ${
                                    isDragOver 
                                        ? 'border-violet-500 bg-violet-500/10' 
                                        : 'border-border hover:border-border/80 bg-muted/40'
                                }`}
                                onClick={() => {
                                    const input = document.createElement('input');
                                    input.type = 'file';
                                    input.accept = 'image/*';
                                    input.onchange = (e) => {
                                        const file = (e.target as HTMLInputElement).files?.[0];
                                        if (file) handleFileChange(file);
                                    };
                                    input.click();
                                }}
                            >
                                <Upload className="h-8 w-8 text-muted-foreground/40 mb-2" />
                                <span className="text-sm text-white/80 font-medium">Arrastra una imagen aquí o haz clic para cargar</span>
                                <span className="text-xs text-muted-foreground/60 mt-1">Soporta PNG, JPG, JPEG</span>
                            </div>
                        ) : (
                            <div className="relative rounded-xl border border-border overflow-hidden bg-muted/40 p-2 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <img src={imagePreview} alt="Mockup Preview" className="h-14 w-20 object-cover rounded-lg border border-border" />
                                    <div>
                                        <p className="text-xs font-medium text-white">Imagen de referencia lista</p>
                                        <p className="text-[10px] text-muted-foreground/60">Se utilizará para guiar el diseño visual</p>
                                    </div>
                                </div>
                                <Button 
                                    size="sm" 
                                    variant="ghost" 
                                    onClick={() => { setImagePreview(null); setScreenshotUrl(''); }}
                                    className="h-8 w-8 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex gap-2 justify-end pt-2">
                    <Button variant="ghost" onClick={onClose} disabled={loading} className="text-muted-foreground">
                        Cancelar
                    </Button>
                    <Button
                        onClick={handleCreate}
                        disabled={loading || !title.trim()}
                        className="bg-violet-600 hover:bg-violet-700 text-white animate-fade-in"
                    >
                        {loading ? <RefreshCw className="h-4 w-4 animate-spin mr-1" /> : <Plus className="h-4 w-4 mr-1" />}
                        {loading ? 'Creando...' : 'Crear Landing'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

// ── Landing Card ──────────────────────────────────────────────────────────────

interface LandingCardProps {
    page: LandingPage;
    onDelete: (id: number) => void;
}

function LandingCard({ page, onDelete }: LandingCardProps) {
    const router = useRouter();
    const { t } = useTranslation();
    const [copied, setCopied] = useState(false);
    const convRate = page.views_count > 0
        ? ((page.conversions_count / page.views_count) * 100).toFixed(1)
        : '0.0';

    const publicUrl = page.custom_domain
        ? `https://${page.custom_domain}`
        : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'https://aikrofy.com'}/l/${page.slug}`;

    const handleCopyUrl = () => {
        navigator.clipboard.writeText(publicUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <Card
            className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-card to-muted/30 transition-all duration-300 hover:border-violet-500/40 hover:shadow-lg hover:shadow-violet-500/10 cursor-pointer"
            onClick={() => router.push(`/landing-pages/${page.id}`)}
        >
            {/* Generation pulse indicator */}
            {page.generation_status === 'generating' && (
                <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-violet-600 via-blue-500 to-violet-600 animate-pulse" />
            )}

            <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                        <CardTitle className="text-base font-semibold text-foreground truncate">{page.title}</CardTitle>
                        <p className="text-xs text-muted-foreground/60 mt-0.5 truncate">/{page.slug}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                        <StatusBadge status={page.status} />
                    </div>
                </div>
                <GenerationStatusIndicator status={page.generation_status} error={page.generation_error} />
            </CardHeader>

            <CardContent className="pt-0">
                {/* Stats row */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                    {[
                        { label: t('landing.views', 'Visitas'), value: page.views_count.toLocaleString() },
                        { label: t('landing.conversions', 'Conversiones'), value: page.conversions_count.toLocaleString() },
                        { label: t('landing.convRate', 'Tasa Conv.'), value: `${convRate}%` },
                    ].map(({ label, value }) => (
                        <div key={label} className="text-center rounded-xl bg-muted/40 py-2">
                            <div className="text-base font-bold text-foreground">{value}</div>
                            <div className="text-[10px] text-muted-foreground/60">{label}</div>
                        </div>
                    ))}
                </div>

                {/* Custom domain badge */}
                {page.custom_domain && (
                    <div className="flex items-center gap-1.5 mb-3 text-xs text-green-400">
                        <Globe className="h-3 w-3" />
                        <span className="truncate">{page.custom_domain}</span>
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-1.5 flex-wrap" onClick={(e) => e.stopPropagation()}>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
                        onClick={handleCopyUrl}
                    >
                        {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
                        <span className="ml-1">{copied ? t('landing.copied', 'Copiado') : t('landing.copyUrl', 'URL')}</span>
                    </Button>
                    {page.status === 'published' && (
                        <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
                            onClick={() => window.open(publicUrl, '_blank')}
                        >
                            <ExternalLink className="h-3.5 w-3.5" />
                            <span className="ml-1">{t('landing.view', 'Ver')}</span>
                        </Button>
                    )}
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-red-400/60 hover:text-red-400 hover:bg-red-500/10 ml-auto"
                        onClick={(e) => { e.stopPropagation(); onDelete(page.id); }}
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function LandingPagesPage() {
    const router = useRouter();
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [showCreateDialog, setShowCreateDialog] = useState(false);

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['landing-pages'],
        queryFn: async () => {
            const { data } = await apiClient.get('/landing-pages/');
            return data.landing_pages as LandingPage[];
        },
        refetchInterval: (query) => {
            // Auto-poll if any page is generating
            const list = query.state.data as LandingPage[] | undefined;
            const generating = list?.some((p: LandingPage) => p.generation_status === 'generating');
            return generating ? 3000 : false;
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => apiClient.delete(`/landing-pages/${id}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
            toast.success(t('landing.deletedToast', 'Landing page eliminada.'));
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || t('landing.deleteErrorToast', 'Error al eliminar.'));
        },
    });

    const handleCreated = (page: LandingPage) => {
        queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
        router.push(`/landing-pages/${page.id}`);
    };

    // Socket listener: auto-refresh when Krof creates or finishes generating a landing
    useEffect(() => {
        const { user } = useAuthStore.getState();
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api';
        const socketUrl = API_URL.replace('/api', '');
        const socket = io(socketUrl, {
            path: '/socket.io',
            transports: ['websocket', 'polling'],
            reconnection: true,
        });
        socket.on('connect', () => {
            if (user?.company_id) {
                socket.emit('join_company', { company_id: user.company_id });
            }
        });
        socket.on('landing_page_created', () => {
            queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
        });
        socket.on('landing_page_ready', (data: any) => {
            queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
            queryClient.invalidateQueries({ queryKey: ['landing-page', String(data.page_id)] });
            toast.success(`✅ Landing page lista. Puedes verla en el editor.`);
        });
        return () => { socket.disconnect(); };
    }, [queryClient]);

    const pages = data || [];
    const publishedCount = pages.filter(p => p.status === 'published').length;
    const totalViews = pages.reduce((s, p) => s + (p.views_count || 0), 0);
    const totalConversions = pages.reduce((s, p) => s + (p.conversions_count || 0), 0);

    return (
        <div className="min-h-screen bg-background text-foreground p-6 space-y-8">
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent">
                        {t('landing.title', 'Landing Pages IA')}
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        {t('landing.description', 'Genera, edita y optimiza páginas de aterrizaje con inteligencia artificial.')}
                    </p>
                </div>
                <Button
                    onClick={() => setShowCreateDialog(true)}
                    className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white font-semibold shadow-lg shadow-violet-500/20"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    {t('landing.newLanding', 'Nueva Landing')}
                </Button>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                    { label: t('landing.totalLandings', 'Total Landings'), value: pages.length, icon: Layers, color: 'violet' },
                    { label: t('landing.published', 'Publicadas'), value: publishedCount, icon: Globe, color: 'green' },
                    { label: t('landing.totalViews', 'Total Visitas'), value: totalViews.toLocaleString(), icon: Eye, color: 'blue' },
                    { label: t('landing.conversions', 'Conversiones'), value: totalConversions.toLocaleString(), icon: BarChart3, color: 'orange' },
                ].map(({ label, value, icon: Icon, color }) => (
                    <div
                        key={label}
                        className={`rounded-2xl border bg-gradient-to-br p-4 ${
                            color === 'violet' ? 'border-violet-500/20 from-violet-500/10 to-violet-500/5' :
                            color === 'green' ? 'border-green-500/20 from-green-500/10 to-green-500/5' :
                            color === 'blue' ? 'border-blue-500/20 from-blue-500/10 to-blue-500/5' :
                            'border-orange-500/20 from-orange-500/10 to-orange-500/5'
                        }`}
                    >
                        <Icon className={`h-5 w-5 mb-2 ${
                            color === 'violet' ? 'text-violet-400' :
                            color === 'green' ? 'text-green-400' :
                            color === 'blue' ? 'text-blue-400' :
                            'text-orange-400'
                        }`} />
                        <div className="text-2xl font-bold text-foreground">{value}</div>
                        <div className="text-xs text-muted-foreground/60 mt-0.5">{label}</div>
                    </div>
                ))}
            </div>

            {/* Landing Pages Grid */}
            {isLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 rounded-2xl bg-muted/40 animate-pulse" />
                    ))}
                </div>
            ) : error ? (
                <div className="text-center py-16 text-red-400">
                    <AlertCircle className="h-10 w-10 mx-auto mb-3" />
                    <p>Error al cargar las landing pages.</p>
                    <Button variant="outline" onClick={() => refetch()} className="mt-3 border-red-500/30 text-red-400">
                        Reintentar
                    </Button>
                </div>
            ) : pages.length === 0 ? (
                <div className="text-center py-24 rounded-2xl border border-dashed border-border">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-violet-500/10 mb-5">
                        <Zap className="h-10 w-10 text-violet-400" />
                    </div>
                    <h2 className="text-xl font-semibold text-white mb-2">Crea tu primera Landing Page</h2>
                    <p className="text-muted-foreground/60 text-sm mb-6 max-w-md mx-auto">
                        Describe tu negocio o sube un screenshot de diseño y la IA generará una landing page completa y responsiva en segundos.
                    </p>
                    <Button
                        onClick={() => setShowCreateDialog(true)}
                        className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Crear con IA
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {pages.map((page) => (
                        <LandingCard
                            key={page.id}
                            page={page}
                            onDelete={(id) => {
                                if (confirm('¿Eliminar esta landing page? Esta acción no se puede deshacer.')) {
                                    if (confirm(t('common.confirmDelete', '¿Estás seguro?'))) deleteMutation.mutate(id);
                                }
                            }}
                        />
                    ))}
                </div>
            )}

            {/* Create Dialog */}
            <CreateLandingDialog
                open={showCreateDialog}
                onClose={() => setShowCreateDialog(false)}
                onCreated={handleCreated}
            />
        </div>
    );
}
