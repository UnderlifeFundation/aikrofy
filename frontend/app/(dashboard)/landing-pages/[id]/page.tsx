'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Monitor, Tablet, Smartphone, Eye, Settings, BarChart3,
    Globe, Save, Zap, ArrowLeft, RefreshCw, CheckCircle2,
    AlertCircle, ExternalLink, Copy, Upload, Edit3, ChevronDown,
    X, Plus, Trash2, PenLine, TrendingUp, Users, MousePointer,
    Clock, Filter, Calendar, Map, Cpu, Key, Link, MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery as useRQuery, useMutation as useRMutation } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import apiClient from '@/lib/api-client';
import { io } from 'socket.io-client';
import { useAuthStore } from '@/store/use-auth-store';
 
// ── Types ──────────────────────────────────────────────────────────────────
 
interface LandingPage {
    id: number;
    title: string;
    slug: string;
    status: 'draft' | 'published' | 'archived';
    version: number;
    custom_domain: string | null;
    custom_domain_verified: boolean;
    views_count: number;
    conversions_count: number;
    generation_status: 'idle' | 'generating' | 'complete' | 'error';
    generation_error: string | null;
    has_content: boolean;
    html_content?: string;
    llm_model: string;
    llm_config: Record<string, any>;
    generation_prompt?: string;
    meta_title?: string;
    meta_description?: string;
    chatweb_enabled?: boolean;
}

interface Analytics {
    page: { id: number; title: string; views_count: number; conversions_count: number; status: string };
    analytics: {
        total_visits: number; leads_identified: number; conversions: number;
        conversion_rate: number; avg_scroll_depth: number; avg_time_on_page: number;
        cta_clicks_total: number; ctr: number;
    };
    segments: {
        by_device: Record<string, number>;
        by_utm_source: Record<string, number>;
        by_country: Record<string, number>;
    };
    daily_trend: Array<{ date: string; visits: number }>;
}

interface CustomDomain {
    id: number;
    company_id: number;
    domain: string;
    landing_page_id: number | null;
    is_active: boolean;
    verified_at: string | null;
    dns_token: string;
    ssl_status: string;
    created_at: string;
}

type TabKey = 'preview' | 'editor' | 'analytics' | 'config';
type Viewport = 'desktop' | 'tablet' | 'mobile';

const VIEWPORT_SIZES: Record<Viewport, { width: string; label: string; icon: React.ElementType }> = {
    desktop: { width: '100%', label: 'Desktop', icon: Monitor },
    tablet: { width: '768px', label: 'Tablet', icon: Tablet },
    mobile: { width: '375px', label: 'Móvil', icon: Smartphone },
};

const LLM_MODELS = [
    { value: 'gpt-5-nano', label: 'gpt-5-nano (Default Plataforma)', default: true },
    { value: 'gpt-4.1-mini-2025-04-14', label: 'GPT-4.1 Mini', enterprise: false },
    { value: 'gpt-4.1-2025-04-14', label: 'GPT-4.1', enterprise: true },
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (Enterprise)', enterprise: true },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4 (Enterprise)', enterprise: true },
    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash (Enterprise)', enterprise: true },
    { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro Preview (Enterprise)', enterprise: true },
];

// ── Preview Tab ───────────────────────────────────────────────────────────────

function PreviewTab({ page, onGenerate, isEnterprise }: {
    page: LandingPage;
    onGenerate: (params: { prompt: string; screenshot_url?: string; generation_type: string }) => void;
    isEnterprise: boolean;
}) {
    const { t } = useTranslation();
    const [viewport, setViewport] = useState<Viewport>('desktop');
    const [prompt, setPrompt] = useState(page.generation_prompt || '');
    const [screenshotUrl, setScreenshotUrl] = useState('');
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [showGeneratePanel, setShowGeneratePanel] = useState(!page.has_content);
    const iframeRef = useRef<HTMLIFrameElement>(null);

    // Update iframe when generation completes
    useEffect(() => {
        if (page.generation_status === 'complete' && page.html_content && iframeRef.current) {
            const iframe = iframeRef.current;
            const doc = iframe.contentDocument || iframe.contentWindow?.document;
            if (doc) {
                doc.open();
                doc.write(page.html_content);
                doc.close();
            }
        }
    }, [page.generation_status, page.html_content]);

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

    const handleGenerate = () => {
        if (!prompt.trim() && !screenshotUrl.trim()) {
            toast.error('Escribe una descripción o carga una imagen para generar.');
            return;
        }
        onGenerate({
            prompt,
            screenshot_url: screenshotUrl || undefined,
            generation_type: page.has_content ? 'update' : 'create',
        });
        setShowGeneratePanel(false);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
                <div className="flex items-center gap-1.5">
                    {(Object.entries(VIEWPORT_SIZES) as [Viewport, typeof VIEWPORT_SIZES[Viewport]][]).map(([key, { label, icon: Icon }]) => (
                        <button
                            key={key}
                            onClick={() => setViewport(key)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                viewport === key
                                    ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                            }`}
                        >
                            <Icon className="h-3.5 w-3.5" />
                            {t('landingEditor.' + key, label)}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-2">
                    {page.status === 'published' && (
                        <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                            onClick={() => {
                                const url = page.custom_domain
                                    ? `https://${page.custom_domain}`
                                    : `${window.location.origin}/l/${page.slug}`;
                                window.open(url, '_blank');
                            }}
                        >
                            <ExternalLink className="h-3.5 w-3.5 mr-1" />
                            {t('landingEditor.open', 'Abrir')}
                        </Button>
                    )}
                    <Button
                        size="sm"
                        onClick={() => setShowGeneratePanel(!showGeneratePanel)}
                        className="h-7 px-3 text-xs bg-violet-600/80 hover:bg-violet-600 text-white"
                    >
                        <Zap className="h-3.5 w-3.5 mr-1" />
                        {page.has_content ? t('landingEditor.updateWithAI', 'Actualizar con IA') : t('landingEditor.generate', 'Generar')}
                    </Button>
                </div>
            </div>

            {/* Generate Panel */}
            {showGeneratePanel && (
                <div className="px-4 py-3 bg-violet-900/20 border-b border-violet-500/20 shrink-0">
                    <div className="flex gap-3 items-end">
                        <div className="flex-1">
                            <Label className="text-xs text-violet-300 mb-1 block">
                                {page.has_content ? t('landingEditor.changeInstruction', 'Instrucción de cambio') : t('landingEditor.landingDesc', 'Descripción de la landing')}
                            </Label>
                            <Input
                                placeholder={page.has_content
                                    ? t('landingEditor.placeholderChange', 'Ej: Cambia el botón CTA a verde y haz el título más llamativo...')
                                    : t('landingEditor.placeholderDesc', 'Ej: Agencia de marketing en México, colores morado y negro...')
                                }
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                className="bg-muted/40 border-violet-500/30 text-white placeholder:text-muted-foreground/40 text-sm h-9"
                                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                            />
                        </div>
                        <div className="w-56 flex items-center gap-2">
                            {!imagePreview ? (
                                <Button
                                    type="button"
                                    variant="outline"
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
                                    className="h-9 w-full bg-muted/40 border-violet-500/30 text-foreground/80 hover:text-foreground text-xs"
                                >
                                    <Upload className="h-3.5 w-3.5 mr-1" />
                                    Subir Mockup
                                </Button>
                            ) : (
                                <div className="h-9 rounded-lg border border-violet-500/30 bg-muted/40 p-1 flex items-center justify-between w-full">
                                    <div className="flex items-center gap-1.5">
                                        <img src={imagePreview} className="h-7 w-10 object-cover rounded border border-border" />
                                        <span className="text-[10px] text-muted-foreground truncate max-w-[80px]">Imagen lista</span>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => { setImagePreview(null); setScreenshotUrl(''); }}
                                        className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
                                    >
                                        <X className="h-3 w-3" />
                                    </Button>
                                </div>
                            )}
                        </div>
                        <Button
                            onClick={handleGenerate}
                            disabled={page.generation_status === 'generating'}
                            className="h-9 bg-violet-600 hover:bg-violet-700 text-white shrink-0"
                        >
                            {page.generation_status === 'generating'
                                ? <RefreshCw className="h-4 w-4 animate-spin" />
                                : <Zap className="h-4 w-4" />
                            }
                        </Button>
                    </div>
                </div>
            )}

            {/* Preview Area */}
            <div className="flex-1 overflow-hidden flex items-start justify-center bg-background p-4">
                {page.generation_status === 'generating' ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                        <div className="relative">
                            <div className="w-20 h-20 rounded-full border-4 border-violet-600/20 border-t-violet-600 animate-spin" />
                            <Zap className="absolute inset-0 m-auto h-8 w-8 text-violet-400" />
                        </div>
                        <div>
                            <p className="text-white font-semibold">IA generando tu landing page...</p>
                            <p className="text-muted-foreground/60 text-sm mt-1">Esto puede tomar 15-60 segundos</p>
                        </div>
                    </div>
                ) : !page.has_content ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                        <Eye className="h-16 w-16 text-white/10" />
                        <div>
                            <p className="text-muted-foreground">Aún no hay contenido generado.</p>
                            <p className="text-muted-foreground/40 text-sm">Usa el panel de arriba para generar con IA.</p>
                        </div>
                    </div>
                ) : (
                    <div
                        className="h-full rounded-2xl overflow-hidden border border-border transition-all duration-300 shadow-2xl"
                        style={{ width: VIEWPORT_SIZES[viewport].width, maxWidth: '100%' }}
                    >
                        <iframe
                            ref={iframeRef}
                            srcDoc={page.html_content || ''}
                            className="w-full h-full"
                            title="Landing Page Preview"
                            sandbox="allow-scripts allow-same-origin"
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

// ── No-Code Editor Tab ────────────────────────────────────────────────────────

function EditorTab({ page, onSave }: { page: LandingPage; onSave: (data: Partial<LandingPage>) => void }) {
    const [htmlContent, setHtmlContent] = useState(page.html_content || '');
    const [metaTitle, setMetaTitle] = useState(page.meta_title || '');
    const [metaDescription, setMetaDescription] = useState(page.meta_description || '');
    const [hasChanges, setHasChanges] = useState(false);
    const [activeMode, setActiveMode] = useState<'visual' | 'code'>('visual');

    useEffect(() => {
        setHtmlContent(page.html_content || '');
    }, [page.html_content]);

    const handleSave = () => {
        onSave({ html_content: htmlContent, meta_title: metaTitle, meta_description: metaDescription });
        setHasChanges(false);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Editor Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
                <div className="flex items-center gap-1.5">
                    <button
                        onClick={() => setActiveMode('visual')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            activeMode === 'visual' ? 'bg-muted text-white' : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                        <Eye className="h-3.5 w-3.5 inline mr-1" />
                        No-Code
                    </button>
                    <button
                        onClick={() => setActiveMode('code')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            activeMode === 'code' ? 'bg-muted text-white' : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                        <PenLine className="h-3.5 w-3.5 inline mr-1" />
                        Editor HTML
                    </button>
                </div>
                {hasChanges && (
                    <Button size="sm" onClick={handleSave} className="h-7 px-3 text-xs bg-green-600 hover:bg-green-700 text-white">
                        <Save className="h-3.5 w-3.5 mr-1" />
                        Guardar cambios
                    </Button>
                )}
            </div>

            {/* Meta fields */}
            <div className="px-4 py-3 border-b border-border bg-card shrink-0">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <Label className="text-xs text-muted-foreground mb-1 block">Meta Título (SEO)</Label>
                        <Input
                            value={metaTitle}
                            onChange={(e) => { setMetaTitle(e.target.value); setHasChanges(true); }}
                            placeholder="Título para SEO y redes sociales"
                            className="bg-muted/40 border-border text-white placeholder:text-muted-foreground/40 text-sm h-8"
                        />
                    </div>
                    <div>
                        <Label className="text-xs text-muted-foreground mb-1 block">Meta Descripción (SEO)</Label>
                        <Input
                            value={metaDescription}
                            onChange={(e) => { setMetaDescription(e.target.value); setHasChanges(true); }}
                            placeholder="Descripción para buscadores (155 chars)"
                            className="bg-muted/40 border-border text-white placeholder:text-muted-foreground/40 text-sm h-8"
                        />
                    </div>
                </div>
            </div>

            {/* Main Editor */}
            <div className="flex-1 overflow-hidden">
                {activeMode === 'code' ? (
                    <Textarea
                        value={htmlContent}
                        onChange={(e) => { setHtmlContent(e.target.value); setHasChanges(true); }}
                        className="w-full h-full resize-none bg-[#0a0c12] border-0 text-green-300 font-mono text-xs focus:ring-0 rounded-none p-4"
                        placeholder="<!-- HTML de la landing page -->"
                        spellCheck={false}
                    />
                ) : (
                    <div className="h-full overflow-y-auto p-4">
                        {!page.has_content ? (
                            <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                                <Edit3 className="h-12 w-12 text-white/10" />
                                <p className="text-muted-foreground/60 text-sm">Genera contenido primero para editar los elementos.</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <div className="rounded-xl border border-border bg-muted/40 p-4">
                                    <p className="text-xs text-muted-foreground/60 mb-1">Modo visual</p>
                                    <p className="text-sm text-foreground/80">
                                        El editor no-code visual extrae automáticamente los elementos de tu landing page generada.
                                        Puedes editar textos, colores y botones directamente en el panel de código HTML o usar las instrucciones de IA.
                                    </p>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setActiveMode('code')}
                                        className="mt-3 border-border/80 text-foreground/80 hover:text-foreground text-xs h-7"
                                    >
                                        Abrir Editor HTML
                                    </Button>
                                </div>
                                {/* Quick editable fields parsed from HTML */}
                                <QuickEditFields html={htmlContent} onChange={(newHtml) => { setHtmlContent(newHtml); setHasChanges(true); }} />
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function QuickEditFields({ html, onChange }: { html: string; onChange: (html: string) => void }) {
    // Extract <title>, h1, first h2, first p content from HTML
    const extractTag = (tag: string, src: string) => {
        const match = src.match(new RegExp(`<${tag}[^>]*>(.*?)<\/${tag}>`, 'is'));
        return match ? match[1].replace(/<[^>]+>/g, '').trim() : '';
    };

    const [h1, setH1] = useState(extractTag('h1', html));
    const [firstP, setFirstP] = useState(extractTag('p', html));

    const updateH1 = (val: string) => {
        setH1(val);
        const updated = html.replace(/(<h1[^>]*>)[\s\S]*?(<\/h1>)/i, `$1${val}$2`);
        onChange(updated);
    };

    return (
        <div className="space-y-3">
            <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Título Principal (H1)</Label>
                <Input
                    value={h1}
                    onChange={(e) => updateH1(e.target.value)}
                    className="bg-muted/40 border-border text-white text-sm"
                />
            </div>
            {firstP && (
                <div>
                    <Label className="text-xs text-muted-foreground mb-1 block">Primer párrafo</Label>
                    <Textarea
                        value={firstP}
                        onChange={(e) => {
                            setFirstP(e.target.value);
                            const updated = html.replace(/(<p[^>]*>)[\s\S]*?(<\/p>)/i, `$1${e.target.value}$2`);
                            onChange(updated);
                        }}
                        rows={3}
                        className="bg-muted/40 border-border text-white text-sm resize-none"
                    />
                </div>
            )}
        </div>
    );
}

// ── Analytics Tab ─────────────────────────────────────────────────────────────

function AnalyticsTab({ pageId }: { pageId: number }) {
    const [filters, setFilters] = useState({
        device: '', utm_source: '', country: '', has_lead: '', date_from: '', date_to: ''
    });

    const { data: analytics, isLoading } = useRQuery({
        queryKey: ['landing-analytics', pageId, filters],
        queryFn: async () => {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
            const { data } = await apiClient.get(`/landing-pages/${pageId}/analytics?${params.toString()}`);
            return data as Analytics;
        },
        refetchInterval: 30000,
    });

    const stats = analytics?.analytics;
    const segments = analytics?.segments;

    const StatCard = ({ icon: Icon, label, value, subtext, color = 'violet' }: any) => (
        <div className={`rounded-2xl border p-4 bg-gradient-to-br ${
            color === 'violet' ? 'border-violet-500/20 from-violet-500/10 to-transparent' :
            color === 'green' ? 'border-green-500/20 from-green-500/10 to-transparent' :
            color === 'blue' ? 'border-blue-500/20 from-blue-500/10 to-transparent' :
            'border-orange-500/20 from-orange-500/10 to-transparent'
        }`}>
            <Icon className={`h-5 w-5 mb-2 ${
                color === 'violet' ? 'text-violet-400' : color === 'green' ? 'text-green-400' :
                color === 'blue' ? 'text-blue-400' : 'text-orange-400'
            }`} />
            <div className="text-2xl font-bold text-foreground">{value}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
            {subtext && <div className="text-[10px] text-muted-foreground/40 mt-1">{subtext}</div>}
        </div>
    );

    return (
        <div className="flex flex-col h-full overflow-y-auto">
            {/* Filters */}
            <div className="px-4 py-3 border-b border-border bg-card shrink-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <Filter className="h-4 w-4 text-muted-foreground/60 shrink-0" />
                    {[
                        { key: 'device', placeholder: 'Dispositivo', options: ['desktop', 'tablet', 'mobile'] },
                        { key: 'has_lead', placeholder: 'Leads', options: ['true', 'false'] },
                    ].map(({ key, placeholder, options }) => (
                        <select
                            key={key}
                            value={filters[key as keyof typeof filters]}
                            onChange={(e) => setFilters(prev => ({ ...prev, [key]: e.target.value }))}
                            className="bg-muted/40 border border-border text-white text-xs rounded-lg px-2 py-1.5 h-8"
                        >
                            <option value="">{placeholder}: Todos</option>
                            {options.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                    ))}
                    <Input
                        placeholder="UTM Source"
                        value={filters.utm_source}
                        onChange={(e) => setFilters(prev => ({ ...prev, utm_source: e.target.value }))}
                        className="bg-muted/40 border-border text-white text-xs h-8 w-28 placeholder:text-muted-foreground/40"
                    />
                    <Input
                        placeholder="País"
                        value={filters.country}
                        onChange={(e) => setFilters(prev => ({ ...prev, country: e.target.value }))}
                        className="bg-muted/40 border-border text-white text-xs h-8 w-20 placeholder:text-muted-foreground/40"
                    />
                    <Input
                        type="date"
                        value={filters.date_from}
                        onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                        className="bg-muted/40 border-border text-white text-xs h-8 w-36"
                    />
                    {Object.values(filters).some(Boolean) && (
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setFilters({ device: '', utm_source: '', country: '', has_lead: '', date_from: '', date_to: '' })}
                            className="h-8 text-xs text-muted-foreground hover:text-foreground"
                        >
                            <X className="h-3.5 w-3.5" />
                        </Button>
                    )}
                </div>
            </div>

            <div className="flex-1 p-4 space-y-6">
                {isLoading ? (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        {[1, 2, 3, 4].map(i => <div key={i} className="h-28 rounded-2xl bg-muted/40 animate-pulse" />)}
                    </div>
                ) : (
                    <>
                        {/* Key Metrics */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <StatCard icon={Users} label="Visitas Totales" value={stats?.total_visits || 0} color="violet" />
                            <StatCard icon={TrendingUp} label="Leads Identificados" value={stats?.leads_identified || 0} color="blue" />
                            <StatCard icon={CheckCircle2} label="Conversiones" value={stats?.conversions || 0} subtext={`${stats?.conversion_rate || 0}% tasa`} color="green" />
                            <StatCard icon={MousePointer} label="Clics en CTA" value={stats?.cta_clicks_total || 0} subtext={`${stats?.ctr || 0}% CTR`} color="orange" />
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                            <div className="rounded-2xl border border-border bg-white/3 p-4">
                                <div className="text-xs text-muted-foreground/60 mb-1">Scroll promedio</div>
                                <div className="text-2xl font-bold text-foreground">{stats?.avg_scroll_depth || 0}%</div>
                                <div className="w-full bg-muted rounded-full h-1.5 mt-2">
                                    <div className="bg-violet-500 h-1.5 rounded-full" style={{ width: `${stats?.avg_scroll_depth || 0}%` }} />
                                </div>
                            </div>
                            <div className="rounded-2xl border border-border bg-white/3 p-4">
                                <Clock className="h-4 w-4 text-muted-foreground/60 mb-1" />
                                <div className="text-2xl font-bold text-foreground">{Math.round((stats?.avg_time_on_page || 0) / 60)}m {(stats?.avg_time_on_page || 0) % 60}s</div>
                                <div className="text-xs text-muted-foreground/60 mt-0.5">Tiempo promedio en página</div>
                            </div>
                        </div>

                        {/* Segments */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            {[
                                { title: 'Por Dispositivo', data: segments?.by_device },
                                { title: 'Por UTM Source', data: segments?.by_utm_source },
                                { title: 'Por País', data: segments?.by_country },
                            ].map(({ title, data }) => (
                                <div key={title} className="rounded-2xl border border-border bg-white/3 p-4">
                                    <h3 className="text-sm font-semibold text-foreground/80 mb-3">{title}</h3>
                                    <div className="space-y-2">
                                        {data && Object.entries(data).sort(([, a], [, b]) => (b as number) - (a as number)).slice(0, 5).map(([key, count]) => {
                                            const total = Object.values(data).reduce((s, v) => s + (v as number), 0);
                                            const pct = total > 0 ? Math.round(((count as number) / total) * 100) : 0;
                                            return (
                                                <div key={key}>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span className="text-foreground/80 capitalize">{key}</span>
                                                        <span className="text-muted-foreground">{count as number} ({pct}%)</span>
                                                    </div>
                                                    <div className="w-full bg-muted rounded-full h-1">
                                                        <div className="bg-violet-500 h-1 rounded-full" style={{ width: `${pct}%` }} />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        {(!data || Object.keys(data).length === 0) && (
                                            <p className="text-xs text-muted-foreground/40">Sin datos aún</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Daily Trend */}
                        <div className="rounded-2xl border border-border bg-white/3 p-4">
                            <h3 className="text-sm font-semibold text-foreground/80 mb-3">Tendencia de Visitas (30 días)</h3>
                            <div className="flex items-end gap-0.5 h-20">
                                {analytics?.daily_trend?.slice(-30).map(({ date, visits }) => {
                                    const maxV = Math.max(...(analytics?.daily_trend?.map(d => d.visits) || [1]));
                                    const height = maxV > 0 ? Math.max(4, (visits / maxV) * 100) : 4;
                                    return (
                                        <div key={date} className="flex-1 flex flex-col items-center gap-0.5" title={`${date}: ${visits} visitas`}>
                                            <div
                                                className="w-full rounded-sm bg-violet-500/60 hover:bg-violet-400 transition-colors"
                                                style={{ height: `${height}%` }}
                                            />
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

// ── Config Tab ────────────────────────────────────────────────────────────────

function ConfigTab({ page, onSave, isEnterprise }: {
    page: LandingPage;
    onSave: (data: Partial<LandingPage>) => void;
    isEnterprise: boolean;
}) {
    const { t } = useTranslation();
    const [slug, setSlug] = useState(page.slug);
    const [llmModel, setLlmModel] = useState(page.llm_model || 'gpt-5-nano');
    const [enterpriseApiKey, setEnterpriseApiKey] = useState(page.llm_config?.api_key || '');
    const [enterpriseProvider, setEnterpriseProvider] = useState(page.llm_config?.provider || 'openai');
    const [enterpriseBaseUrl, setEnterpriseBaseUrl] = useState(page.llm_config?.base_url || '');
    const [chatwebEnabled, setChatwebEnabled] = useState(page.chatweb_enabled || false);

    // Custom Domain section
    const [newDomain, setNewDomain] = useState('');
    const [isPublished, setIsPublished] = useState(page.status === 'published');
    const queryClient = useRQuery;

    const { data: domainsData, refetch: refetchDomains } = useRQuery({
        queryKey: ['custom-domains'],
        queryFn: async () => {
            const { data } = await apiClient.get('/landing-pages/domains');
            return data.domains as CustomDomain[];
        },
    });

    const handleSaveConfig = () => {
        onSave({
            slug,
            llm_model: llmModel,
            llm_config: isEnterprise ? {
                api_key: enterpriseApiKey,
                provider: enterpriseProvider,
                base_url: enterpriseBaseUrl,
            } : {},
            chatweb_enabled: chatwebEnabled,
        });
    };

    const handleRegisterDomain = async () => {
        if (!newDomain.trim()) return;
        try {
            const { data } = await apiClient.post('/landing-pages/domains', {
                domain: newDomain.trim(),
                landing_page_id: page.id,
            });
            toast.success('Dominio registrado. Sigue las instrucciones DNS para verificarlo.');
            refetchDomains();
            setNewDomain('');
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al registrar dominio.');
        }
    };

    const handleVerifyDomain = async (domainId: number) => {
        try {
            const { data } = await apiClient.post(`/landing-pages/domains/${domainId}/verify`);
            toast.success(data.message);
            refetchDomains();
        } catch (err: any) {
            toast.warning(err?.response?.data?.message || 'DNS aún no propagado.');
        }
    };

    const handleDeleteDomain = async (domainId: number) => {
        if (!confirm('¿Eliminar este dominio?')) return;
        try {
            await apiClient.delete(`/landing-pages/domains/${domainId}`);
            toast.success('Dominio eliminado.');
            refetchDomains();
        } catch {
            toast.error('Error al eliminar dominio.');
        }
    };

    const handlePublishToggle = async () => {
        try {
            await apiClient.post(`/landing-pages/${page.id}/publish`, {
                action: isPublished ? 'unpublish' : 'publish',
            });
            setIsPublished(!isPublished);
            toast.success(isPublished ? 'Landing despublicada.' : '¡Landing publicada con éxito!');
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al publicar.');
        }
    };

    const domains = domainsData || [];
    const thisPageDomains = domains.filter(d => d.landing_page_id === page.id || !d.landing_page_id);

    return (
        <div className="flex flex-col h-full overflow-y-auto p-4 space-y-6">
            {/* Publish */}
            <div className="rounded-2xl border border-border bg-white/3 p-4">
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Globe className="h-4 w-4 text-green-400" />
                    {t('landingEditor.configTab.publishStatus', 'Estado de Publicación')}
                </h3>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm text-foreground/80">
                            {isPublished 
                                ? t('landingEditor.configTab.publishedDesc', '✅ La landing está publicada y accesible públicamente.') 
                                : t('landingEditor.configTab.draftDesc', '⚠️ La landing está en modo borrador.')
                            }
                        </p>
                        <p className="text-xs text-muted-foreground/60 mt-0.5">
                            URL: <code className="bg-muted rounded px-1">
                                {page.custom_domain ? `https://${page.custom_domain}` : `/l/${page.slug}`}
                            </code>
                        </p>
                    </div>
                    <Button
                        onClick={handlePublishToggle}
                        disabled={!page.has_content}
                        className={isPublished
                            ? 'bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }
                    >
                        {isPublished ? t('landingEditor.configTab.unpublish', 'Despublicar') : t('landingEditor.configTab.publish', 'Publicar Ahora')}
                    </Button>
                </div>
            </div>

            {/* URL Slug */}
            <div className="rounded-2xl border border-border bg-white/3 p-4">
                <h3 className="text-sm font-semibold text-foreground mb-3">{t('landingEditor.configTab.urlSlug', 'URL Slug')}</h3>
                <div className="flex gap-2">
                    <div className="flex items-center bg-muted/40 border border-border rounded-lg px-3 text-muted-foreground/60 text-sm shrink-0">
                        /l/
                    </div>
                    <Input
                        value={slug}
                        onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                        className="bg-muted/40 border-border text-white text-sm"
                    />
                    <Button onClick={handleSaveConfig} size="sm" className="bg-violet-600 hover:bg-violet-700 text-white">
                        <Save className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Custom Domain */}
            <div className="rounded-2xl border border-border bg-white/3 p-4">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                        <Link className="h-4 w-4 text-blue-400" />
                        {t('landingEditor.configTab.customDomain', 'Dominio Personalizado')}
                        <span className="text-xs text-green-400 font-normal">{t('landingEditor.configTab.betaDesc', '(Disponible para todos en Beta)')}</span>
                    </h3>
                </div>

                {/* Register new domain */}
                <div className="flex gap-2 mb-4">
                    <Input
                        placeholder={t('landingEditor.configTab.placeholderDomain', 'mi-empresa.com o promo.mi-empresa.com')}
                        value={newDomain}
                        onChange={(e) => setNewDomain(e.target.value)}
                        className="bg-muted/40 border-border text-white text-sm placeholder:text-muted-foreground/40"
                    />
                    <Button onClick={handleRegisterDomain} className="bg-blue-600 hover:bg-blue-700 text-white shrink-0">
                        {t('landingEditor.configTab.register', 'Registrar')}
                    </Button>
                </div>

                {/* Domain list */}
                <div className="space-y-2">
                    {thisPageDomains.length === 0 ? (
                        <p className="text-xs text-muted-foreground/40">{t('landingEditor.configTab.noDomains', 'No hay dominios registrados. Agrega uno arriba.')}</p>
                    ) : thisPageDomains.map(domain => (
                        <div key={domain.id} className="rounded-xl border border-border bg-muted/40 p-3">
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-mono text-white">{domain.domain}</span>
                                        {domain.is_active ? (
                                            <span className="text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 rounded-full px-1.5 py-0.5">{t('landingEditor.configTab.active', 'Activo')}</span>
                                        ) : (
                                            <span className="text-[10px] bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded-full px-1.5 py-0.5">{t('landingEditor.configTab.pending', 'Pendiente')}</span>
                                        )}
                                        <span className="text-[10px] text-muted-foreground/40">SSL: {domain.ssl_status}</span>
                                    </div>
                                    {!domain.is_active && (
                                        <div className="mt-2 rounded-lg bg-blue-900/20 border border-blue-500/20 p-2 text-xs text-blue-300">
                                            <strong>{t('landingEditor.configTab.dnsInstruction', 'Instrucción DNS:')}</strong> {t('landingEditor.configTab.addCname', 'Agrega un registro CNAME:')}<br />
                                            <code className="text-blue-200 bg-muted/40 rounded px-1">aikrofy-verify.{domain.domain}</code> →{' '}
                                            <code className="text-blue-200 bg-muted/40 rounded px-1">{domain.dns_token}.domains.aikrofy.com</code>
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                    {!domain.is_active && (
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => handleVerifyDomain(domain.id)}
                                            className="h-7 px-2 text-xs text-blue-400 hover:bg-blue-500/10"
                                        >
                                            {t('landingEditor.configTab.verify', 'Verificar')}
                                        </Button>
                                    )}
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => handleDeleteDomain(domain.id)}
                                        className="h-7 px-2 text-xs text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Chatbot Widget setting */}
            <div className="rounded-2xl border border-border bg-white/3 p-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                            <MessageSquare className="h-4 w-4 text-violet-400" />
                            {t('landingEditor.configTab.activateChat', 'Activar Chat Widget')}
                        </h3>
                        <p className="text-xs text-muted-foreground/60 mt-1">
                            {t('landingEditor.configTab.chatDesc', 'Habilita el widget de chat IA flotante en esta landing page.')}
                        </p>
                    </div>
                    <Switch
                        checked={chatwebEnabled}
                        onCheckedChange={setChatwebEnabled}
                    />
                </div>
            </div>

            {/* LLM Configuration */}
            <div className="rounded-2xl border border-border bg-white/3 p-4">
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-violet-400" />
                    {t('landingEditor.configTab.aiModel', 'Modelo de IA')}
                </h3>
                <div className="space-y-3">
                    <div>
                        <Label className="text-xs text-muted-foreground mb-1 block">{t('landingEditor.configTab.modelForGeneration', 'Modelo para Generación')}</Label>
                        <select
                            value={llmModel}
                            onChange={(e) => setLlmModel(e.target.value)}
                            className="w-full bg-muted/40 border border-border text-white text-sm rounded-lg px-3 py-2"
                            disabled={!isEnterprise && llmModel !== 'gpt-5-nano'}
                        >
                            {LLM_MODELS.filter(m => !m.enterprise || isEnterprise).map(m => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                            ))}
                        </select>
                        {!isEnterprise && (
                            <p className="text-xs text-muted-foreground/40 mt-1">
                                {t('landingEditor.configTab.enterpriseNotice', '✨ Modelos avanzados disponibles en plan Enterprise. Actualiza para acceder a Claude, GPT-4.1, Gemini 3.')}
                            </p>
                        )}
                    </div>

                    {/* Enterprise: BYO API Key */}
                    {isEnterprise && (
                        <>
                            <div>
                                <Label className="text-xs text-muted-foreground mb-1 block flex items-center gap-1">
                                    <Key className="h-3 w-3" />
                                    {t('landingEditor.configTab.byoKey', 'API Key Propia (Enterprise BYO)')}
                                </Label>
                                <Input
                                    type="password"
                                    placeholder={t('landingEditor.configTab.byoPlaceholder', 'sk-... (opcional: usa tu propia cuenta)')}
                                    value={enterpriseApiKey}
                                    onChange={(e) => setEnterpriseApiKey(e.target.value)}
                                    className="bg-muted/40 border-border text-white text-sm placeholder:text-muted-foreground/40"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Label className="text-xs text-muted-foreground mb-1 block">{t('landingEditor.configTab.provider', 'Proveedor')}</Label>
                                    <select
                                        value={enterpriseProvider}
                                        onChange={(e) => setEnterpriseProvider(e.target.value)}
                                        className="w-full bg-muted/40 border border-border text-white text-sm rounded-lg px-3 py-2"
                                    >
                                        <option value="openai">OpenAI</option>
                                        <option value="anthropic">Anthropic</option>
                                        <option value="gemini">Google Gemini</option>
                                        <option value="openrouter">OpenRouter</option>
                                    </select>
                                </div>
                                <div>
                                    <Label className="text-xs text-muted-foreground mb-1 block">{t('landingEditor.configTab.baseUrl', 'Base URL (opcional)')}</Label>
                                    <Input
                                        placeholder="https://api.openai.com/v1"
                                        value={enterpriseBaseUrl}
                                        onChange={(e) => setEnterpriseBaseUrl(e.target.value)}
                                        className="bg-muted/40 border-border text-white text-sm placeholder:text-muted-foreground/40"
                                    />
                                </div>
                            </div>
                        </>
                    )}

                    <Button onClick={handleSaveConfig} size="sm" className="bg-violet-600 hover:bg-violet-700 text-white">
                        <Save className="h-4 w-4 mr-1" />
                        {t('landingEditor.configTab.saveConfig', 'Guardar Configuración')}
                    </Button>
                </div>
            </div>
        </div>
    );
}

// ── Main Detail Page ──────────────────────────────────────────────────────────

export default function LandingPageDetailPage() {
    const { t } = useTranslation();
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<TabKey>('preview');

    const { data: pageData, isLoading, refetch } = useQuery({
        queryKey: ['landing-page', id],
        queryFn: async () => {
            const { data } = await apiClient.get(`/landing-pages/${id}`);
            return data.landing_page as LandingPage;
        },
        refetchInterval: (query) => {
            const d = query.state.data as LandingPage | undefined;
            return d?.generation_status === 'generating' ? 2500 : false;
        },
    });

    // Fetch company info to determine enterprise status
    const { data: meData } = useQuery({
        queryKey: ['me'],
        queryFn: async () => {
            const { data } = await apiClient.get('/auth/me');
            return data.data;
        },
    });

    const isEnterprise = ['enterprise', 'executiv', 'corporate'].includes(
        (meData?.company?.plan_type || '').toLowerCase()
    );

    const saveMutation = useMutation({
        mutationFn: async (updates: Partial<LandingPage>) => {
            const { data } = await apiClient.put(`/landing-pages/${id}`, updates);
            return data.landing_page as LandingPage;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
            toast.success('Cambios guardados.');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al guardar.');
        },
    });

    const generateMutation = useMutation({
        mutationFn: async (params: { prompt: string; screenshot_url?: string; generation_type: string }) => {
            const { data } = await apiClient.post(`/landing-pages/${id}/generate`, params);
            return data;
        },
        onSuccess: (data) => {
            toast.success(data.message || 'Generación iniciada.');
            refetch();
        },
        onError: (err: any) => {
            if (err?.response?.status === 402) {
                toast.error('Tokens insuficientes. Recarga tu saldo para continuar.', {
                    action: { label: 'Recargar', onClick: () => router.push('/pricing') },
                });
            } else {
                toast.error(err?.response?.data?.error || 'Error al iniciar generación.');
            }
        },
    });

    const page = pageData;

    const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
        { key: 'preview', label: t('landingEditor.preview', 'Vista Previa'), icon: Eye },
        { key: 'editor', label: t('landingEditor.editor', 'Editor'), icon: Edit3 },
        { key: 'analytics', label: t('landingEditor.analytics', 'Analítica'), icon: BarChart3 },
        { key: 'config', label: t('landingEditor.config', 'Configuración'), icon: Settings },
    ];

    // Real-time socket listener: refresh preview when Krof modifies this page
    useEffect(() => {
        if (!id) return;
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
        // When Krof finishes generating or modifying this landing, refresh the data + preview
        socket.on('landing_page_ready', (data: any) => {
            if (String(data.page_id) === String(id)) {
                queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
                refetch();
                // Auto-switch to preview tab to show result
                setActiveTab('preview');
                toast.success('✅ Landing page actualizada. Previsualizando...');
            }
        });
        socket.on('landing_page_updating', (data: any) => {
            if (String(data.page_id) === String(id)) {
                queryClient.invalidateQueries({ queryKey: ['landing-page', id] });
                refetch();
            }
        });
        return () => { socket.disconnect(); };
    }, [id, queryClient, refetch]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-background">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-10 w-10 rounded-full border-4 border-violet-600/20 border-t-violet-600 animate-spin" />
                    <p className="text-muted-foreground/60 text-sm">{t('landingEditor.loading', 'Cargando landing page...')}</p>
                </div>
            </div>
        );
    }

    if (!page) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-background gap-4">
                <AlertCircle className="h-12 w-12 text-red-400" />
                <p className="text-muted-foreground">{t('landingEditor.notFound', 'Landing page no encontrada.')}</p>
                <Button onClick={() => router.push('/landing-pages')} variant="outline" className="border-border/80 text-white">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    {t('landingEditor.back', 'Volver')}
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
            {/* Top Bar */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card shrink-0">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push('/landing-pages')}
                    className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                >
                    <ArrowLeft className="h-4 w-4" />
                </Button>

                <div className="flex-1 min-w-0">
                    <h1 className="text-sm font-semibold text-foreground truncate">{page.title}</h1>
                    <p className="text-xs text-muted-foreground/60 truncate">/{page.slug}</p>
                </div>

                {/* Status indicators */}
                <div className="flex items-center gap-2 shrink-0">
                    {page.generation_status === 'generating' && (
                        <span className="flex items-center gap-1 text-xs text-blue-400">
                            <RefreshCw className="h-3 w-3 animate-spin" />
                            Generando...
                        </span>
                    )}
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
                        page.status === 'published'
                            ? 'bg-green-500/20 text-green-400 border-green-500/30'
                            : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                    }`}>
                        {page.status === 'published' ? 'Publicada' : 'Borrador'}
                    </span>
                    <span className="text-xs text-muted-foreground/40">v{page.version}</span>
                </div>
            </div>

            {/* Tab Bar */}
            <div className="flex items-center px-4 border-b border-border bg-card shrink-0">
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        onClick={() => setActiveTab(key)}
                        className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                            activeTab === key
                                ? 'border-violet-500 text-violet-400'
                                : 'border-transparent text-muted-foreground hover:text-foreground/80'
                        }`}
                    >
                        <Icon className="h-4 w-4" />
                        <span className="hidden sm:block">{label}</span>
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-hidden">
                {activeTab === 'preview' && (
                    <PreviewTab
                        page={page}
                        onGenerate={(params) => generateMutation.mutate(params)}
                        isEnterprise={isEnterprise}
                    />
                )}
                {activeTab === 'editor' && (
                    <EditorTab
                        page={page}
                        onSave={(updates) => saveMutation.mutate(updates)}
                    />
                )}
                {activeTab === 'analytics' && (
                    <AnalyticsTab pageId={page.id} />
                )}
                {activeTab === 'config' && (
                    <ConfigTab
                        page={page}
                        onSave={(updates) => saveMutation.mutate(updates)}
                        isEnterprise={isEnterprise}
                    />
                )}
            </div>
        </div>
    );
}
