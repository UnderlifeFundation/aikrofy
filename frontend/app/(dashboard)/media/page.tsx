'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Image as ImageIcon,
    Video,
    UploadCloud,
    Trash2,
    Folder,
    FolderPlus,
    Tag,
    ExternalLink,
    Loader2,
    Search,
    AlertCircle,
    Info,
    Plus,
    Film,
    FileText,
    FileSpreadsheet,
    FileCode,
    Music,
    File,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/lib/api-client';

interface MediaAsset {
    id: number;
    company_id: number;
    folder: string;
    filename: string;
    token?: string;
    file_url: string;
    media_type: 'image' | 'video' | 'audio' | 'document' | string;
    size_bytes: number;
    mime_type: string;
    title: string;
    description: string;
    keywords: string[];
    created_at: string;
}

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export default function MediaPage() {
    const queryClient = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Filters & views
    const [selectedFolder, setSelectedFolder] = useState<string>('all');
    const [selectedType, setSelectedType] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState<string>('');

    // Upload modal
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadFolder, setUploadFolder] = useState('general');
    const [newFolderInput, setNewFolderInput] = useState('');
    const [uploadTitle, setUploadTitle] = useState('');
    const [uploadDescription, setUploadDescription] = useState('');
    const [uploadKeywords, setUploadKeywords] = useState('');
    const [uploadCampaignId, setUploadCampaignId] = useState('');
    const [uploadError, setUploadError] = useState<string | null>(null);

    // Preview modal
    const [previewAsset, setPreviewAsset] = useState<MediaAsset | null>(null);
    const [editCampaignId, setEditCampaignId] = useState<string>('');

    // ── Queries ─────────────────────────────────────────────────────────────
    const { data: campaigns = [] } = useQuery({
        queryKey: ['strategic-campaigns'],
        queryFn: async () => {
            const res = await apiClient.get('/campaigns');
            return res.data?.campaigns || [];
        },
    });

    const { data: foldersData } = useQuery({
        queryKey: ['media-folders'],
        queryFn: async () => {
            const res = await apiClient.get('/media/folders');
            return (res.data?.data as string[]) || ['general'];
        },
    });

    const folders = foldersData || ['general'];

    const { data: mediaData, isLoading } = useQuery({
        queryKey: ['media-list', selectedFolder, selectedType, searchQuery],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (selectedFolder !== 'all') params.append('folder', selectedFolder);
            if (selectedType !== 'all') params.append('media_type', selectedType);
            if (searchQuery.trim()) params.append('q', searchQuery.trim());

            const res = await apiClient.get(`/media?${params.toString()}`);
            return res.data?.data as MediaAsset[];
        },
    });

    const assets = mediaData || [];

    // ── Mutations ───────────────────────────────────────────────────────────
    const uploadMutation = useMutation({
        mutationFn: async () => {
            if (!uploadFile) throw new Error('Selecciona un archivo');
            if (uploadFile.size > MAX_SIZE_BYTES) {
                throw new Error('El archivo excede el límite máximo de 10 MB');
            }

            const targetFolder =
                uploadFolder === '__new__' && newFolderInput.trim()
                    ? newFolderInput.trim()
                    : uploadFolder;

            const formData = new FormData();
            formData.append('file', uploadFile);
            formData.append('folder', targetFolder);
            formData.append('title', uploadTitle.trim());
            formData.append('description', uploadDescription.trim());
            formData.append('keywords', uploadKeywords.trim());
            if (uploadCampaignId) {
                formData.append('campaign_id', uploadCampaignId);
            }

            const res = await apiClient.post('/media/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['media-list'] });
            queryClient.invalidateQueries({ queryKey: ['media-folders'] });
            toast.success('Archivo subido exitosamente a la biblioteca');
            setIsUploadOpen(false);
            resetUploadForm();
        },
        onError: (err: any) => {
            const msg =
                err?.response?.data?.error || err?.message || 'Error al subir el archivo';
            setUploadError(msg);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await apiClient.delete(`/media/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['media-list'] });
            queryClient.invalidateQueries({ queryKey: ['media-folders'] });
            toast.success('Archivo eliminado de la biblioteca');
            setPreviewAsset(null);
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al eliminar');
        },
    });

    const updateCampaignMutation = useMutation({
        mutationFn: async ({ assetId, campaignId }: { assetId: number; campaignId: string }) => {
            await apiClient.patch(`/media/${assetId}`, {
                campaign_id: campaignId ? Number(campaignId) : null,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['media-list'] });
            toast.success('Campaña vinculada exitosamente al recurso');
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.error || 'Error al vincular campaña');
        },
    });

    const resetUploadForm = () => {
        setUploadFile(null);
        setUploadFolder('general');
        setNewFolderInput('');
        setUploadTitle('');
        setUploadDescription('');
        setUploadKeywords('');
        setUploadCampaignId('');
        setUploadError(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (file.size > MAX_SIZE_BYTES) {
            setUploadError('El archivo excede el límite de 10 MB.');
            setUploadFile(null);
            return;
        }

        setUploadFile(file);
        setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
        setUploadError(null);
    };

    const formatBytes = (bytes: number) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const dm = 1;
        const sizes = ['B', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    };

    const getMediaUrl = (asset: MediaAsset) => {
        // Preferred: Direct streaming endpoint by unguessable token or ID
        const token = asset.token || (asset.filename?.includes('_') ? asset.filename.split('_')[0] : null);
        if (token && token.length === 32) {
            return `/api/media/file/${token}`;
        }
        if (asset.id) {
            return `/api/media/file/${asset.id}`;
        }
        if (asset.file_url?.startsWith('http')) {
            return asset.file_url;
        }
        if (asset.file_url?.startsWith('/api/')) {
            return asset.file_url;
        }
        // Legacy /uploads path -> route through /api/uploads
        if (asset.file_url?.startsWith('/uploads/')) {
            return `/api${asset.file_url}`;
        }
        return asset.file_url || '';
    };

    return (
        <div className="space-y-6 w-full max-w-[1920px] mx-auto pb-12">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
                        <ImageIcon className="h-7 w-7 sm:h-8 sm:w-8 text-primary shrink-0" />
                        Biblioteca de Medios
                    </h2>
                    <p className="text-sm text-muted-foreground mt-0.5 sm:mt-1 max-w-3xl">
                        Sube imágenes y videos cortos (&lt; 10MB) clasificados en carpetas. El agente de IA los consultará y enviará automáticamente cuando los clientes soliciten demos o catálogo.
                    </p>
                </div>

                <Button
                    onClick={() => {
                        resetUploadForm();
                        setIsUploadOpen(true);
                    }}
                    className="gap-2 bg-primary hover:bg-primary/90 w-full sm:w-auto shrink-0 h-9 sm:h-10"
                >
                    <UploadCloud className="h-4 w-4" />
                    Subir Medio
                </Button>
            </div>

            {/* Filter and search bar */}
            <div className="flex flex-col sm:flex-row gap-3 p-3 bg-muted/20 rounded-xl border">
                <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Buscar por nombre, descripción o palabras clave..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 bg-background"
                    />
                </div>

                <Select value={selectedFolder} onValueChange={setSelectedFolder}>
                    <SelectTrigger className="w-[180px] bg-background">
                        <Folder className="h-4 w-4 mr-2 text-muted-foreground" />
                        <SelectValue placeholder="Carpeta" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todas las carpetas</SelectItem>
                        {folders.map((f) => (
                            <SelectItem key={f} value={f}>
                                {f}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select value={selectedType} onValueChange={setSelectedType}>
                    <SelectTrigger className="w-[150px] bg-background">
                        <SelectValue placeholder="Tipo" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos los tipos</SelectItem>
                        <SelectItem value="image">Imágenes</SelectItem>
                        <SelectItem value="video">Videos</SelectItem>
                        <SelectItem value="document">Documentos</SelectItem>
                        <SelectItem value="audio">Audios</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Content grid */}
            {isLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <Skeleton key={i} className="h-48 rounded-xl" />
                    ))}
                </div>
            ) : assets.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <Film className="h-12 w-12 text-muted-foreground/30 mb-3" />
                        <h3 className="font-semibold text-lg">No hay medios cargados</h3>
                        <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-4">
                            Sube demos, imágenes de catálogo o videos tutoriales para que tus agentes de IA puedan compartirlos en conversaciones de soporte o ventas.
                        </p>
                        <Button
                            variant="outline"
                            onClick={() => {
                                resetUploadForm();
                                setIsUploadOpen(true);
                            }}
                            className="gap-2"
                        >
                            <Plus className="h-4 w-4" />
                            Subir primer archivo
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
                    {assets.map((asset) => (
                        <Card
                            key={asset.id}
                            className="group relative overflow-hidden rounded-xl border hover:shadow-md transition-all cursor-pointer bg-card"
                            onClick={() => setPreviewAsset(asset)}
                        >
                            {/* Media thumbnail */}
                            <div className="aspect-video w-full bg-muted/60 relative overflow-hidden flex items-center justify-center">
                                {asset.media_type === 'image' ? (
                                    <img
                                        src={getMediaUrl(asset)}
                                        alt={asset.title}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                        loading="lazy"
                                    />
                                ) : asset.media_type === 'video' ? (
                                    <div className="flex flex-col items-center justify-center text-muted-foreground">
                                        <Video className="h-10 w-10 mb-1 text-primary" />
                                        <span className="text-[10px] font-semibold uppercase tracking-wider">Video</span>
                                    </div>
                                ) : asset.media_type === 'audio' ? (
                                    <div className="flex flex-col items-center justify-center text-muted-foreground">
                                        <Music className="h-10 w-10 mb-1 text-amber-500" />
                                        <span className="text-[10px] font-semibold uppercase tracking-wider">Audio</span>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center text-muted-foreground">
                                        {asset.filename.endsWith('.pdf') ? (
                                            <FileText className="h-10 w-10 mb-1 text-red-500" />
                                        ) : asset.filename.endsWith('.xlsx') || asset.filename.endsWith('.xls') || asset.filename.endsWith('.csv') ? (
                                            <FileSpreadsheet className="h-10 w-10 mb-1 text-emerald-500" />
                                        ) : asset.filename.endsWith('.json') || asset.filename.endsWith('.md') ? (
                                            <FileCode className="h-10 w-10 mb-1 text-blue-500" />
                                        ) : (
                                            <FileText className="h-10 w-10 mb-1 text-primary" />
                                        )}
                                        <span className="text-[10px] font-semibold uppercase tracking-wider">
                                            {asset.filename.split('.').pop() || 'DOC'}
                                        </span>
                                    </div>
                                )}
                                <Badge
                                    variant="secondary"
                                    className="absolute top-2 left-2 text-[10px] px-1.5 py-0.5 bg-background/80 backdrop-blur-xs font-mono"
                                >
                                    {asset.media_type === 'video'
                                        ? 'VIDEO'
                                        : asset.media_type === 'audio'
                                        ? 'AUDIO'
                                        : asset.media_type === 'document'
                                        ? (asset.filename.split('.').pop()?.toUpperCase() || 'DOC')
                                        : 'IMG'}
                                </Badge>
                                <span className="absolute bottom-2 right-2 text-[10px] text-white/90 bg-black/60 px-1.5 py-0.5 rounded font-mono">
                                    {formatBytes(asset.size_bytes)}
                                </span>
                            </div>

                            {/* Details */}
                            <CardContent className="p-3">
                                <p className="font-semibold text-sm truncate" title={asset.title}>
                                    {asset.title}
                                </p>
                                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                    <Folder className="h-3 w-3 shrink-0" />
                                    <span className="truncate">{asset.folder}</span>
                                </div>

                                {asset.keywords && asset.keywords.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {asset.keywords.slice(0, 3).map((kw, i) => (
                                            <Badge
                                                key={i}
                                                variant="outline"
                                                className="text-[9px] px-1 py-0 h-4 border-muted-foreground/30"
                                            >
                                                {kw}
                                            </Badge>
                                        ))}
                                        {asset.keywords.length > 3 && (
                                            <span className="text-[9px] text-muted-foreground">
                                                +{asset.keywords.length - 3}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* ── Upload Modal ────────────────────────────────────────────── */}
            <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <UploadCloud className="h-5 w-5 text-primary" />
                            Subir Recurso Multimedia
                        </DialogTitle>
                        <DialogDescription>
                            Sube imágenes, videos, documentos (PDF, Excel, Word, etc.) o audios. Tamaño máximo: <strong>10 MB</strong>.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-2">
                        {/* File drop area */}
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className="border-2 border-dashed border-muted-foreground/30 hover:border-primary/60 rounded-xl p-6 text-center cursor-pointer transition-colors"
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.ppt,.pptx,.txt,.md,.markdown,.json,image/*,video/*,audio/*"
                                onChange={handleFileSelect}
                                className="hidden"
                            />
                            {uploadFile ? (
                                <div className="space-y-1">
                                    <p className="font-medium text-sm text-foreground">{uploadFile.name}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {formatBytes(uploadFile.size)} · Tipo: {uploadFile.type || 'Archivo'}
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    <UploadCloud className="h-8 w-8 mx-auto text-muted-foreground" />
                                    <p className="text-sm font-medium">Haz clic para seleccionar un archivo</p>
                                    <p className="text-xs text-muted-foreground">
                                        PDF, DOCX, XLSX, CSV, JSON, MD, TXT, Imágenes, Videos, Audios (máx. 10 MB)
                                    </p>
                                </div>
                            )}
                        </div>

                        {uploadError && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{uploadError}</AlertDescription>
                            </Alert>
                        )}

                        {/* Folder selection */}
                        <div className="space-y-1.5">
                            <Label className="text-xs font-semibold">Carpeta de destino</Label>
                            <Select value={uploadFolder} onValueChange={setUploadFolder}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {folders.map((f) => (
                                        <SelectItem key={f} value={f}>
                                            📁 {f}
                                        </SelectItem>
                                    ))}
                                    <SelectItem value="__new__">➕ Crear nueva carpeta...</SelectItem>
                                </SelectContent>
                            </Select>

                            {uploadFolder === '__new__' && (
                                <Input
                                    placeholder="Nombre de la nueva carpeta (ej: demos, catalogo-2026)"
                                    value={newFolderInput}
                                    onChange={(e) => setNewFolderInput(e.target.value)}
                                    className="mt-2"
                                />
                            )}
                        </div>

                        {/* Title */}
                        <div className="space-y-1.5">
                            <Label className="text-xs font-semibold">Título del recurso</Label>
                            <Input
                                placeholder="Ej: Video Demo Plataforma Aikrofy"
                                value={uploadTitle}
                                onChange={(e) => setUploadTitle(e.target.value)}
                            />
                        </div>

                        {/* Keywords for AI */}
                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <Label className="text-xs font-semibold flex items-center gap-1">
                                    <Tag className="h-3 w-3 text-primary" />
                                    Palabras clave para la IA (separadas por coma)
                                </Label>
                            </div>
                            <Input
                                placeholder="ej: demo, presentacion, precios, tutorial, crm"
                                value={uploadKeywords}
                                onChange={(e) => setUploadKeywords(e.target.value)}
                            />
                            <p className="text-[11px] text-muted-foreground">
                                Permite al agente encontrar este archivo cuando el cliente pregunte por estos términos.
                            </p>
                        </div>

                        {/* Strategic Campaign */}
                        <div className="space-y-1.5">
                            <Label className="text-xs font-semibold">Vincular a Campaña Estratégica (opcional)</Label>
                            <Select value={uploadCampaignId} onValueChange={setUploadCampaignId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Ninguna (Sin campaña)" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="">Ninguna (Sin campaña)</SelectItem>
                                    {campaigns.map((camp: any) => (
                                        <SelectItem key={camp.id} value={String(camp.id)}>
                                            🎯 {camp.name} {camp.is_active ? '🟢' : '⚪'}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Description */}
                        <div className="space-y-1.5">
                            <Label className="text-xs font-semibold">Descripción (opcional)</Label>
                            <Textarea
                                placeholder="Breve contexto de cuándo compartir este archivo..."
                                value={uploadDescription}
                                onChange={(e) => setUploadDescription(e.target.value)}
                                rows={2}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setIsUploadOpen(false)}
                            disabled={uploadMutation.isPending}
                        >
                            Cancelar
                        </Button>
                        <Button
                            onClick={() => uploadMutation.mutate()}
                            disabled={!uploadFile || uploadMutation.isPending}
                            className="gap-1.5"
                        >
                            {uploadMutation.isPending && (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            )}
                            Subir Archivo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Preview / Detail Modal ──────────────────────────────────── */}
            {previewAsset && (
                <Dialog open={!!previewAsset} onOpenChange={() => setPreviewAsset(null)}>
                    <DialogContent className="sm:max-w-[650px]">
                        <DialogHeader>
                            <DialogTitle className="flex items-center justify-between pr-4">
                                <span className="truncate">{previewAsset.title}</span>
                                <Badge variant="secondary" className="font-mono text-xs uppercase">
                                    {previewAsset.media_type}
                                </Badge>
                            </DialogTitle>
                            <DialogDescription>
                                Carpeta: <code>{previewAsset.folder}</code> · Tamaño:{' '}
                                {formatBytes(previewAsset.size_bytes)}
                            </DialogDescription>
                        </DialogHeader>

                        {/* Media Display */}
                        <div className="w-full bg-black/95 rounded-lg overflow-hidden flex items-center justify-center min-h-[220px] max-h-[420px] p-4">
                            {previewAsset.media_type === 'image' ? (
                                <img
                                    src={getMediaUrl(previewAsset)}
                                    alt={previewAsset.title}
                                    className="max-h-[400px] w-auto object-contain"
                                />
                            ) : previewAsset.media_type === 'video' ? (
                                <video
                                    src={getMediaUrl(previewAsset)}
                                    controls
                                    playsInline
                                    preload="metadata"
                                    className="max-h-[400px] w-full rounded"
                                >
                                    Tu navegador no soporta la reproducción de video HTML5.
                                </video>
                            ) : previewAsset.media_type === 'audio' ? (
                                <div className="flex flex-col items-center justify-center gap-4 py-8 text-white w-full max-w-md">
                                    <Music className="h-16 w-16 text-amber-400" />
                                    <span className="text-sm font-medium">{previewAsset.filename}</span>
                                    <audio
                                        src={getMediaUrl(previewAsset)}
                                        controls
                                        className="w-full"
                                    >
                                        Tu navegador no soporta la reproducción de audio.
                                    </audio>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center gap-3 py-6 text-white text-center">
                                    {previewAsset.filename.endsWith('.pdf') ? (
                                        <FileText className="h-16 w-16 text-red-400" />
                                    ) : previewAsset.filename.endsWith('.xlsx') || previewAsset.filename.endsWith('.xls') || previewAsset.filename.endsWith('.csv') ? (
                                        <FileSpreadsheet className="h-16 w-16 text-emerald-400" />
                                    ) : previewAsset.filename.endsWith('.json') || previewAsset.filename.endsWith('.md') ? (
                                        <FileCode className="h-16 w-16 text-blue-400" />
                                    ) : (
                                        <File className="h-16 w-16 text-slate-300" />
                                    )}
                                    <p className="text-sm font-semibold text-slate-200">{previewAsset.filename}</p>
                                    <p className="text-xs text-slate-400">
                                        Formato: {previewAsset.mime_type || 'Documento'} · {formatBytes(previewAsset.size_bytes)}
                                    </p>
                                    <Button
                                        asChild
                                        variant="secondary"
                                        size="sm"
                                        className="mt-2 gap-2"
                                    >
                                        <a href={getMediaUrl(previewAsset)} target="_blank" rel="noreferrer" download>
                                            <ExternalLink className="h-4 w-4" />
                                            Ver / Descargar Documento
                                        </a>
                                    </Button>
                                </div>
                            )}
                        </div>

                        {/* Info details */}
                        <div className="space-y-2 text-xs">
                            {previewAsset.description && (
                                <div>
                                    <span className="font-semibold text-muted-foreground">Descripción:</span>
                                    <p className="text-foreground mt-0.5">{previewAsset.description}</p>
                                </div>
                            )}

                            {previewAsset.keywords && previewAsset.keywords.length > 0 && (
                                <div>
                                    <span className="font-semibold text-muted-foreground">Palabras clave IA:</span>
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {previewAsset.keywords.map((kw, i) => (
                                            <Badge key={i} variant="outline" className="text-xs">
                                                {kw}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Strategic Campaign link */}
                            <div className="pt-2 border-t flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                <div>
                                    <span className="font-semibold text-muted-foreground block mb-0.5">Campaña Estratégica:</span>
                                    <p className="text-[11px] text-muted-foreground">
                                        {(() => {
                                            const match = (previewAsset.description || '').match(/\[CAMPAIGN_ID:(\d+)\]/);
                                            if (match) {
                                                const c = campaigns.find((x: any) => x.id === Number(match[1]));
                                                return c ? `🎯 ${c.name} (ID: ${c.id})` : `🎯 Campaña #${match[1]}`;
                                            }
                                            return 'Ninguna campaña vinculada';
                                        })()}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <select
                                        defaultValue={(() => {
                                            const match = (previewAsset.description || '').match(/\[CAMPAIGN_ID:(\d+)\]/);
                                            return match ? match[1] : '';
                                        })()}
                                        onChange={(e) => {
                                            updateCampaignMutation.mutate({
                                                assetId: previewAsset.id,
                                                campaignId: e.target.value,
                                            });
                                        }}
                                        className="text-xs bg-muted border border-border rounded px-2 py-1 text-foreground"
                                    >
                                        <option value="">Sin campaña</option>
                                        {campaigns.map((camp: any) => (
                                            <option key={camp.id} value={String(camp.id)}>
                                                {camp.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="pt-2 border-t flex items-center justify-between text-muted-foreground">
                                <span className="font-mono text-[11px] truncate max-w-[350px]">
                                    {getMediaUrl(previewAsset)}
                                </span>
                                <a
                                    href={getMediaUrl(previewAsset)}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="flex items-center gap-1 text-primary hover:underline"
                                >
                                    Abrir original <ExternalLink className="h-3 w-3" />
                                </a>
                            </div>
                        </div>

                        <DialogFooter className="flex justify-between sm:justify-between">
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => deleteMutation.mutate(previewAsset.id)}
                                disabled={deleteMutation.isPending}
                                className="gap-1.5"
                            >
                                <Trash2 className="h-4 w-4" />
                                Eliminar
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => setPreviewAsset(null)}>
                                Cerrar
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            )}
        </div>
    );
}
