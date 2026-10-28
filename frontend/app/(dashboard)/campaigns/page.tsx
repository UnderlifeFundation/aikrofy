'use client';

import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import { 
    QrCode, 
    Plus, 
    BarChart3, 
    Edit2, 
    Trash2, 
    RefreshCw, 
    Copy, 
    Check,
    Target,
    Bot,
    Globe,
    Film,
    Calendar,
    Power,
    Layers,
    ChevronRight,
    TrendingUp,
    Download,
    Share2,
    ExternalLink
} from 'lucide-react';
import QRCodeStyling, { DotType, CornerSquareType, CornerDotType } from 'qr-code-styling';
import { QRPreviewVisual, VisualConfig } from '@/components/campaigns/qr/QRPreviewVisual';
import { QRBuilderModal, CampaignQRItem, QRFormPayload } from '@/components/campaigns/qr/QRBuilderModal';
import { toast } from 'sonner';

interface QRAnalyticsData {
    qr_code_id: string;
    name: string;
    total_scans: number;
    last_scanned_at: string | null;
    devices: Record<string, number>;
    operating_systems: Record<string, number>;
    browsers: Record<string, number>;
}

interface StrategicCampaign {
    id: number;
    company_id: number;
    name: string;
    description: string;
    is_active: boolean;
    start_date: string | null;
    end_date: string | null;
    created_at: string;
    updated_at: string;
    metrics: {
        total_qrs: number;
        total_scans: number;
        total_agents: number;
        total_landings: number;
        total_landing_views: number;
        total_media: number;
    };
    linked_resources: {
        qrs: CampaignQRItem[];
        agents: Array<{ id: number; name: string; objective: string }>;
        landings: Array<{ id: number; title: string; slug: string; views_count: number }>;
        media: Array<{ id: number; filename: string; file_url: string; media_type: string }>;
    };
}

export default function CampaignsAndQRPage() {
    // Sub-navigation tab: 'campaigns' (Campañas Estratégicas) | 'qr' (Códigos QR Perpetuos)
    const [activeTab, setActiveTab] = useState<'campaigns' | 'qr'>('campaigns');

    // Strategic Campaigns state
    const [campaigns, setCampaigns] = useState<StrategicCampaign[]>([]);
    const [loadingCampaigns, setLoadingCampaigns] = useState(true);
    const [isCampaignModalOpen, setIsCampaignModalOpen] = useState(false);
    const [editingCampaign, setEditingCampaign] = useState<StrategicCampaign | null>(null);
    const [campaignName, setCampaignName] = useState('');
    const [campaignDesc, setCampaignDesc] = useState('');
    const [campaignStartDate, setCampaignStartDate] = useState('');
    const [campaignEndDate, setCampaignEndDate] = useState('');
    const [savingCampaign, setSavingCampaign] = useState(false);

    // QR Codes state
    const [qrCodes, setQrCodes] = useState<CampaignQRItem[]>([]);
    const [loadingQRs, setLoadingQRs] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedQR, setSelectedQR] = useState<CampaignQRItem | null>(null);
    const [statsModalQR, setStatsModalQR] = useState<CampaignQRItem | null>(null);
    const [statsData, setStatsData] = useState<QRAnalyticsData | null>(null);
    const [loadingStats, setLoadingStats] = useState(false);
    const [copiedSlug, setCopiedSlug] = useState<string | null>(null);

    // Fetch Strategic Campaigns
    const fetchCampaigns = useCallback(async () => {
        try {
            setLoadingCampaigns(true);
            const res = await apiClient.get('/campaigns');
            setCampaigns(res.data?.campaigns || []);
        } catch (error) {
            console.error('Error loading strategic campaigns:', error);
        } finally {
            setLoadingCampaigns(false);
        }
    }, []);

    // Fetch QR Codes
    const fetchQRCodes = useCallback(async () => {
        try {
            setLoadingQRs(true);
            const res = await apiClient.get('/campaigns/qr');
            setQrCodes(res.data?.qr_codes || []);
        } catch (error) {
            console.error('Error loading campaign QR codes:', error);
        } finally {
            setLoadingQRs(false);
        }
    }, []);

    useEffect(() => {
        void fetchCampaigns();
        void fetchQRCodes();
    }, [fetchCampaigns, fetchQRCodes]);

    // Save Campaign (Create or Update)
    const handleSaveCampaign = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!campaignName.trim() || !campaignDesc.trim()) {
            toast.error('Nombre y contexto/objetivo son requeridos');
            return;
        }

        setSavingCampaign(true);
        try {
            const payload: any = {
                name: campaignName.trim(),
                description: campaignDesc.trim(),
                start_date: campaignStartDate || null,
                end_date: campaignEndDate || null,
            };

            if (editingCampaign) {
                await apiClient.put(`/campaigns/${editingCampaign.id}`, payload);
                toast.success('Campaña estratégica actualizada');
            } else {
                await apiClient.post('/campaigns', payload);
                toast.success('Campaña estratégica creada');
            }

            setIsCampaignModalOpen(false);
            setEditingCampaign(null);
            setCampaignName('');
            setCampaignDesc('');
            setCampaignStartDate('');
            setCampaignEndDate('');
            await fetchCampaigns();
        } catch (error: any) {
            toast.error(error?.response?.data?.error || 'Error al guardar la campaña');
        } finally {
            setSavingCampaign(false);
        }
    };

    // Toggle Campaign Status
    const handleToggleCampaignStatus = async (camp: StrategicCampaign) => {
        try {
            await apiClient.put(`/campaigns/${camp.id}`, { is_active: !camp.is_active });
            toast.success(`Campaña ${!camp.is_active ? 'activada' : 'pausada'}`);
            await fetchCampaigns();
        } catch (error: any) {
            toast.error(error?.response?.data?.error || 'Error al cambiar el estado');
        }
    };

    // Delete Campaign
    const handleDeleteCampaign = async (id: number) => {
        if (!confirm('¿Estás seguro de eliminar esta campaña estratégica? Los recursos asociados (QRs, landings, etc.) serán desvinculados de forma segura.')) return;
        try {
            await apiClient.delete(`/campaigns/${id}`);
            toast.success('Campaña eliminada');
            setCampaigns((prev) => prev.filter((c) => c.id !== id));
        } catch (error: any) {
            toast.error(error?.response?.data?.error || 'Error al eliminar campaña');
        }
    };

    // Save QR
    const handleSaveQR = async (formData: QRFormPayload) => {
        try {
            if (selectedQR) {
                await apiClient.put(`/campaigns/qr/${selectedQR.id}`, formData);
                toast.success('Código QR actualizado');
            } else {
                await apiClient.post('/campaigns/qr', formData);
                toast.success('Código QR creado');
            }
            await fetchQRCodes();
            await fetchCampaigns();
        } catch (error: any) {
            toast.error(error?.response?.data?.error || 'Error al guardar el código QR');
            throw error;
        }
    };

    const handleDeleteQR = async (id: string) => {
        if (!confirm('¿Seguro que deseas eliminar este código QR?')) return;
        try {
            await apiClient.delete(`/campaigns/qr/${id}`);
            toast.success('Código QR eliminado');
            setQrCodes((prev) => prev.filter((q) => q.id !== id));
            await fetchCampaigns();
        } catch (err) {
            console.error('Error deleting QR:', err);
        }
    };

    const openAnalytics = async (qr: CampaignQRItem) => {
        setStatsModalQR(qr);
        setLoadingStats(true);
        try {
            const res = await apiClient.get(`/campaigns/qr/${qr.id}/analytics`);
            setStatsData(res.data);
        } catch (err) {
            console.error('Error fetching analytics:', err);
        } finally {
            setLoadingStats(false);
        }
    };

    const handleCopy = (text: string, slug: string) => {
        navigator.clipboard.writeText(text);
        setCopiedSlug(slug);
        toast.success('Enlace copiado al portapapeles');
        setTimeout(() => setCopiedSlug(null), 2000);
    };

    const handleDownloadQR = (qr: CampaignQRItem, format: 'png' | 'svg' = 'png') => {
        const fullRedirectUrl = qr.short_url.startsWith('http') 
            ? qr.short_url 
            : `${typeof window !== 'undefined' ? window.location.origin : ''}${qr.short_url}`;

        const visualConfig = qr.visual_config || {};
        const qrCode = new QRCodeStyling({
            width: 1024,
            height: 1024,
            data: fullRedirectUrl,
            image: visualConfig.logoUrl || undefined,
            dotsOptions: {
                color: visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.dotsType || 'rounded') as DotType,
            },
            backgroundOptions: {
                color: visualConfig.backgroundColor || '#ffffff',
            },
            cornersSquareOptions: {
                color: visualConfig.cornerSquareColor || visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.cornerSquareType || 'extra-rounded') as CornerSquareType,
            },
            cornersDotOptions: {
                color: visualConfig.cornerDotColor || visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.cornerDotType || 'dot') as CornerDotType,
            },
            imageOptions: {
                crossOrigin: 'anonymous',
                margin: visualConfig.logoMargin ?? 6,
                imageSize: visualConfig.logoSize ?? 0.35,
                hideBackgroundDots: true,
            },
        });

        qrCode.download({ name: `${qr.name || 'qr'}-hd`, extension: format });
        toast.success(`Descargando QR en alta resolución (${format.toUpperCase()})`);
    };

    const handleShareQR = async (qr: CampaignQRItem) => {
        const fullRedirectUrl = qr.short_url.startsWith('http') 
            ? qr.short_url 
            : `${typeof window !== 'undefined' ? window.location.origin : ''}${qr.short_url}`;

        if (typeof navigator !== 'undefined' && navigator.share) {
            try {
                await navigator.share({
                    title: `Código QR: ${qr.name}`,
                    text: `Escanea este código QR o abre el enlace: ${qr.name}`,
                    url: fullRedirectUrl,
                });
                toast.success('Compartido con éxito');
                return;
            } catch (err: any) {
                if (err.name !== 'AbortError') {
                    // Fallback to clipboard
                    navigator.clipboard.writeText(fullRedirectUrl);
                    toast.success('Enlace copiado para compartir');
                }
            }
        } else {
            navigator.clipboard.writeText(fullRedirectUrl);
            toast.success('Enlace copiado para compartir');
        }
    };

    // Calculate aggregated metrics for campaigns
    const totalCampaignScans = campaigns.reduce((acc, c) => acc + (c.metrics?.total_scans || 0), 0);
    const activeCampaignsCount = campaigns.filter((c) => c.is_active).length;

    return (
        <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
            
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="p-2 bg-blue-600/10 text-blue-600 rounded-xl">
                            <Target className="w-6 h-6" />
                        </span>
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Campañas Estratégicas & Códigos QR
                        </h1>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Vincula agentes IA, landings, códigos QR y recursos multimedia a campañas unificadas con analítica de conversión en tiempo real.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    {activeTab === 'campaigns' ? (
                        <button
                            onClick={() => {
                                setEditingCampaign(null);
                                setCampaignName('');
                                setCampaignDesc('');
                                setCampaignStartDate('');
                                setCampaignEndDate('');
                                setIsCampaignModalOpen(true);
                            }}
                            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow-sm transition-all"
                        >
                            <Plus className="w-4 h-4" />
                            Nueva Campaña
                        </button>
                    ) : (
                        <button
                            onClick={() => {
                                setSelectedQR(null);
                                setIsModalOpen(true);
                            }}
                            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow-sm transition-all"
                        >
                            <Plus className="w-4 h-4" />
                            Nuevo Código QR
                        </button>
                    )}
                </div>
            </div>

            {/* Sub-Navigation Tabs */}
            <div className="flex items-center gap-2 p-1.5 bg-slate-100 dark:bg-slate-800/60 rounded-2xl w-fit border border-slate-200 dark:border-slate-800">
                <button
                    onClick={() => setActiveTab('campaigns')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                        activeTab === 'campaigns'
                            ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs'
                            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                    <Target className="w-4 h-4" />
                    Campañas Estratégicas ({campaigns.length})
                </button>
                <button
                    onClick={() => setActiveTab('qr')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                        activeTab === 'qr'
                            ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs'
                            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                    <QrCode className="w-4 h-4" />
                    Códigos QR Perpetuos ({qrCodes.length})
                </button>
            </div>

            {/* TAB 1: STRATEGIC CAMPAIGNS */}
            {activeTab === 'campaigns' && (
                <div className="space-y-6">
                    {/* Metrics Bar */}
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Campañas Activas</span>
                            <p className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                                {activeCampaignsCount} <span className="text-sm font-normal text-slate-400">/ {campaigns.length}</span>
                            </p>
                        </div>
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Escaneos QR Totales</span>
                            <p className="text-3xl font-extrabold text-blue-600 mt-1">{totalCampaignScans}</p>
                        </div>
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Agentes Conectados</span>
                            <p className="text-3xl font-extrabold text-violet-600 mt-1">
                                {campaigns.reduce((acc, c) => acc + (c.metrics?.total_agents || 0), 0)}
                            </p>
                        </div>
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Landings Vinculadas</span>
                            <p className="text-3xl font-extrabold text-emerald-600 mt-1">
                                {campaigns.reduce((acc, c) => acc + (c.metrics?.total_landings || 0), 0)}
                            </p>
                        </div>
                    </div>

                    {/* Campaigns List */}
                    {loadingCampaigns ? (
                        <div className="flex items-center justify-center py-20 text-slate-400">
                            <RefreshCw className="w-6 h-6 animate-spin mr-2" /> Cargando campañas estratégicas...
                        </div>
                    ) : campaigns.length === 0 ? (
                        <div className="text-center py-16 bg-slate-50 dark:bg-slate-900/50 rounded-3xl border border-dashed border-slate-200 dark:border-slate-800 p-8">
                            <Target className="w-12 h-12 text-slate-400 mx-auto mb-3" />
                            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No hay campañas estratégicas creadas</h3>
                            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
                                Crea una campaña para coordinar tus agentes de IA, códigos QR, páginas de aterrizaje y recursos de medios bajo un mismo objetivo con trazabilidad total.
                            </p>
                            <button
                                onClick={() => {
                                    setEditingCampaign(null);
                                    setCampaignName('');
                                    setCampaignDesc('');
                                    setCampaignStartDate('');
                                    setCampaignEndDate('');
                                    setIsCampaignModalOpen(true);
                                }}
                                className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700"
                            >
                                Crear Primera Campaña
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {campaigns.map((camp) => (
                                <div
                                    key={camp.id}
                                    className="flex flex-col justify-between bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-xs hover:shadow-md transition-all"
                                >
                                    <div>
                                        {/* Header */}
                                        <div className="flex items-start justify-between gap-3 mb-3">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-bold text-slate-900 dark:text-white text-lg leading-tight">
                                                        {camp.name}
                                                    </h3>
                                                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                                                        camp.is_active
                                                            ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 border-emerald-200 dark:border-emerald-800'
                                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 border-slate-200 dark:border-slate-700'
                                                    }`}>
                                                        {camp.is_active ? 'Activa' : 'Pausada'}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                                                    {camp.description}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Metrics Strip */}
                                        <div className="grid grid-cols-4 gap-2 my-4 p-3 bg-slate-50 dark:bg-slate-800/40 rounded-2xl text-center">
                                            <div>
                                                <span className="text-[10px] font-medium text-slate-400 block">QRs</span>
                                                <span className="font-bold text-sm text-slate-800 dark:text-white">{camp.metrics?.total_qrs || 0}</span>
                                            </div>
                                            <div>
                                                <span className="text-[10px] font-medium text-slate-400 block">Escaneos</span>
                                                <span className="font-bold text-sm text-blue-600">{camp.metrics?.total_scans || 0}</span>
                                            </div>
                                            <div>
                                                <span className="text-[10px] font-medium text-slate-400 block">Agentes</span>
                                                <span className="font-bold text-sm text-violet-600">{camp.metrics?.total_agents || 0}</span>
                                            </div>
                                            <div>
                                                <span className="text-[10px] font-medium text-slate-400 block">Landings</span>
                                                <span className="font-bold text-sm text-emerald-600">{camp.metrics?.total_landings || 0}</span>
                                            </div>
                                        </div>

                                        {/* Linked Resources Badges */}
                                        <div className="space-y-2 mt-3">
                                            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 block">
                                                Recursos Vinculados:
                                            </span>
                                            <div className="flex flex-wrap gap-1.5">
                                                {camp.linked_resources?.agents?.map((a) => (
                                                    <span key={a.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-300 border border-violet-200 dark:border-violet-800">
                                                        <Bot className="w-3 h-3" />
                                                        {a.name}
                                                    </span>
                                                ))}
                                                {camp.linked_resources?.qrs?.map((q) => (
                                                    <span key={q.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                                        <QrCode className="w-3 h-3" />
                                                        {q.name}
                                                    </span>
                                                ))}
                                                {camp.linked_resources?.landings?.map((l) => (
                                                    <span key={l.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                                        <Globe className="w-3 h-3" />
                                                        {l.title}
                                                    </span>
                                                ))}
                                                {camp.linked_resources?.media?.map((m) => (
                                                    <span key={m.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                                        <Film className="w-3 h-3" />
                                                        {m.filename}
                                                    </span>
                                                ))}
                                                {(!camp.linked_resources?.agents?.length &&
                                                  !camp.linked_resources?.qrs?.length &&
                                                  !camp.linked_resources?.landings?.length &&
                                                  !camp.linked_resources?.media?.length) && (
                                                    <span className="text-[11px] text-slate-400 italic">
                                                        Ningún recurso vinculado aún. Puedes asociar agentes, QRs, landings o medios desde sus respectivas secciones.
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Card Footer */}
                                    <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-100 dark:border-slate-800 text-xs">
                                        <button
                                            onClick={() => handleToggleCampaignStatus(camp)}
                                            className={`inline-flex items-center gap-1.5 font-medium transition-colors ${
                                                camp.is_active ? 'text-amber-600 hover:text-amber-700' : 'text-emerald-600 hover:text-emerald-700'
                                            }`}
                                        >
                                            <Power className="w-3.5 h-3.5" />
                                            {camp.is_active ? 'Pausar Campaña' : 'Activar Campaña'}
                                        </button>

                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => {
                                                    setEditingCampaign(camp);
                                                    setCampaignName(camp.name);
                                                    setCampaignDesc(camp.description);
                                                    setCampaignStartDate(camp.start_date ? camp.start_date.substring(0, 10) : '');
                                                    setCampaignEndDate(camp.end_date ? camp.end_date.substring(0, 10) : '');
                                                    setIsCampaignModalOpen(true);
                                                }}
                                                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                title="Editar Campaña"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDeleteCampaign(camp.id)}
                                                className="p-1.5 text-red-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30"
                                                title="Eliminar Campaña"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* TAB 2: QR CODES PERPETUOS */}
            {activeTab === 'qr' && (
                <div className="space-y-6">
                    {/* Quick Metrics Bar */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Códigos QR</span>
                            <p className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">{qrCodes.length}</p>
                        </div>
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Escaneos Totales</span>
                            <p className="text-3xl font-extrabold text-blue-600 mt-1">
                                {qrCodes.reduce((acc, q) => acc + (q.total_scans || 0), 0)}
                            </p>
                        </div>
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Canales Activos</span>
                            <p className="text-3xl font-extrabold text-emerald-600 mt-1">Omnicanal</p>
                        </div>
                    </div>

                    {/* List / Grid of QR Codes */}
                    {loadingQRs ? (
                        <div className="flex items-center justify-center py-20 text-slate-400">
                            <RefreshCw className="w-6 h-6 animate-spin mr-2" /> Cargando herramientas de campaña...
                        </div>
                    ) : qrCodes.length === 0 ? (
                        <div className="text-center py-16 bg-slate-50 dark:bg-slate-900/50 rounded-3xl border border-dashed border-slate-200 dark:border-slate-800 p-8">
                            <QrCode className="w-12 h-12 text-slate-400 mx-auto mb-3" />
                            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No hay códigos QR creados</h3>
                            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
                                Crea tu primer código perpetuo para volantes físicos, menús, enlaces de WhatsApp, formularios o tus campañas de marketing.
                            </p>
                            <button
                                onClick={() => {
                                    setSelectedQR(null);
                                    setIsModalOpen(true);
                                }}
                                className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700"
                            >
                                Crear Primer Código QR
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {qrCodes.map((qr) => {
                                const fullRedirectUrl = qr.short_url.startsWith('http') 
                                    ? qr.short_url 
                                    : `${typeof window !== 'undefined' ? window.location.origin : ''}${qr.short_url}`;

                                return (
                                    <div 
                                        key={qr.id}
                                        className="flex flex-col justify-between bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs hover:shadow-md transition-all"
                                    >
                                        <div>
                                            <div className="flex items-start justify-between gap-2 mb-3">
                                                <div>
                                                    <h3 className="font-bold text-slate-900 dark:text-white text-base leading-tight">
                                                        {qr.name}
                                                    </h3>
                                                    <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                                                        <span className="text-[11px] font-medium text-slate-500 capitalize">
                                                            {qr.intended_channel} • {qr.target_type}
                                                        </span>
                                                        {qr.campaign_name && (
                                                            <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 dark:bg-blue-900/30 px-1.5 py-0.2 rounded">
                                                                🎯 {qr.campaign_name}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                                    {qr.total_scans || 0} escaneos
                                                </span>
                                            </div>

                                            {/* Visual preview */}
                                            <div className="my-3 flex justify-center">
                                                <QRPreviewVisual 
                                                    value={fullRedirectUrl}
                                                    visualConfig={qr.visual_config}
                                                    size={160}
                                                />
                                            </div>

                                            {/* Link and Target */}
                                            <div className="space-y-1.5 mt-2 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-2xl text-xs">
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="font-mono text-blue-600 truncate">{fullRedirectUrl}</span>
                                                    <button 
                                                        onClick={() => handleCopy(fullRedirectUrl, qr.slug)}
                                                        className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700"
                                                        title="Copiar URL del QR"
                                                    >
                                                        {copiedSlug === qr.slug ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                                                    </button>
                                                </div>
                                                <p className="text-slate-400 truncate text-[11px]">
                                                    Destino: <span className="text-slate-600 dark:text-slate-300">{qr.target_destination}</span>
                                                </p>
                                            </div>

                                            {/* Direct Quick Action Buttons (Download & Share) */}
                                            <div className="grid grid-cols-2 gap-2 mt-3">
                                                <button
                                                    onClick={() => handleDownloadQR(qr, 'png')}
                                                    className="inline-flex items-center justify-center gap-1.5 py-1.5 px-2 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-blue-600 dark:text-blue-300 rounded-xl text-xs font-semibold transition-colors border border-blue-200/60 dark:border-blue-800/60"
                                                    title="Descargar imagen QR en alta resolución"
                                                >
                                                    <Download className="w-3.5 h-3.5" />
                                                    Descargar QR
                                                </button>
                                                <button
                                                    onClick={() => handleShareQR(qr)}
                                                    className="inline-flex items-center justify-center gap-1.5 py-1.5 px-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold transition-colors border border-slate-200 dark:border-slate-700"
                                                    title="Compartir o copiar enlace"
                                                >
                                                    <Share2 className="w-3.5 h-3.5" />
                                                    Compartir
                                                </button>
                                            </div>
                                        </div>

                                        {/* Footer actions */}
                                        <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-100 dark:border-slate-800 text-xs">
                                            <button
                                                onClick={() => openAnalytics(qr)}
                                                className="inline-flex items-center gap-1.5 font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600"
                                            >
                                                <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
                                                Métricas
                                            </button>

                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => {
                                                        setSelectedQR(qr);
                                                        setIsModalOpen(true);
                                                    }}
                                                    className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    title="Ver detalles o editar configuración"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteQR(qr.id)}
                                                    className="p-1.5 text-red-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30"
                                                    title="Eliminar QR"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Modal: Crear / Editar Campaña Estratégica */}
            {isCampaignModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4">
                        <div className="flex items-center justify-between border-b pb-3">
                            <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                                <Target className="w-5 h-5 text-blue-600" />
                                {editingCampaign ? 'Editar Campaña Estratégica' : 'Nueva Campaña Estratégica'}
                            </h3>
                            <button onClick={() => setIsCampaignModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
                        </div>

                        <form onSubmit={handleSaveCampaign} className="space-y-4 text-xs">
                            <div>
                                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                    Nombre de la Campaña *
                                </label>
                                <input
                                    type="text"
                                    required
                                    placeholder="Ej: Lanzamiento Primavera 2026 / Black Friday"
                                    value={campaignName}
                                    onChange={(e) => setCampaignName(e.target.value)}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-sm focus:outline-none focus:border-blue-500"
                                />
                            </div>

                            <div>
                                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                    Objetivo Estratégico y Contexto para la IA *
                                </label>
                                <textarea
                                    required
                                    rows={3}
                                    placeholder="Explica qué busca la campaña, propuesta de valor, promociones y tono para que los agentes conectados sepan responder en base a esta estrategia..."
                                    value={campaignDesc}
                                    onChange={(e) => setCampaignDesc(e.target.value)}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                        Fecha de Inicio (Opcional)
                                    </label>
                                    <input
                                        type="date"
                                        value={campaignStartDate}
                                        onChange={(e) => setCampaignStartDate(e.target.value)}
                                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-sm focus:outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                        Fecha de Fin (Opcional)
                                    </label>
                                    <input
                                        type="date"
                                        value={campaignEndDate}
                                        onChange={(e) => setCampaignEndDate(e.target.value)}
                                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-sm focus:outline-none focus:border-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="pt-3 border-t flex justify-end gap-2">
                                <button
                                    type="button"
                                    onClick={() => setIsCampaignModalOpen(false)}
                                    className="px-4 py-2 text-slate-500 hover:text-slate-700 text-sm font-semibold"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={savingCampaign}
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold flex items-center gap-1.5"
                                >
                                    {savingCampaign && <RefreshCw className="w-4 h-4 animate-spin" />}
                                    {editingCampaign ? 'Guardar Cambios' : 'Crear Campaña'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Builder Modal QR */}
            <QRBuilderModal 
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleSaveQR}
                initialData={selectedQR}
                campaigns={campaigns.map((c) => ({ id: c.id, name: c.name }))}
            />

            {/* Analytics Modal QR */}
            {statsModalQR && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 max-w-xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4">
                        <div className="flex items-center justify-between border-b pb-3">
                            <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                                <BarChart3 className="w-5 h-5 text-blue-600" />
                                Analítica de Escaneo: {statsModalQR.name}
                            </h3>
                            <button onClick={() => setStatsModalQR(null)} className="text-slate-400 hover:text-white">✕</button>
                        </div>

                        {loadingStats ? (
                            <div className="py-10 text-center text-slate-400">
                                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" /> Cargando telemetría...
                            </div>
                        ) : statsData ? (
                            <div className="space-y-4 text-xs">
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                                        <span className="text-slate-400">Total Escaneos</span>
                                        <p className="text-2xl font-bold mt-1 text-blue-600">{statsData.total_scans}</p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                                        <span className="text-slate-400">Último Escaneo</span>
                                        <p className="text-sm font-semibold mt-2">{statsData.last_scanned_at || 'Sin escaneos'}</p>
                                    </div>
                                </div>

                                <div>
                                    <span className="font-bold text-slate-700 dark:text-slate-300 block mb-2">Dispositivos Detectados:</span>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(statsData.devices || {}).map(([dev, count]) => (
                                            <span key={dev} className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-[11px]">
                                                {dev}: <strong>{count}</strong>
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <span className="font-bold text-slate-700 dark:text-slate-300 block mb-2">Sistemas Operativos:</span>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(statsData.operating_systems || {}).map(([os, count]) => (
                                            <span key={os} className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-[11px]">
                                                {os}: <strong>{count}</strong>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}

        </div>
    );
}
