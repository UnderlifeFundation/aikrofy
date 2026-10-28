'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FileText,
    UploadCloud,
    Trash2,
    CheckCircle2,
    Loader2,
    AlertCircle,
    Mic,
    Square,
    Play,
    Pause,
    Volume2,
    FileCode,
    FileSpreadsheet,
    Sparkles,
    Radio,
    Globe,
    RefreshCw,
    ExternalLink,
    Layers,
    Clock,
    Atom,
    Bot,
    Building2,
    Image as ImageIcon
} from 'lucide-react';
import dynamic from 'next/dynamic';

// Lazy-load D3 galaxy (no SSR)
const KnowledgeGalaxy = dynamic(
    () => import('@/components/features/brain/KnowledgeGalaxy').then((m) => ({ default: m.KnowledgeGalaxy })),
    { ssr: false, loading: () => <Skeleton className="h-[560px] w-full rounded-2xl" /> }
);

const AgentSynapseMonitor = dynamic(
    () => import('@/components/features/brain/AgentSynapseMonitor').then((m) => ({ default: m.AgentSynapseMonitor })),
    { ssr: false }
);
import { toast } from 'sonner';
import { format } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import apiClient from '@/lib/api-client';
import type { Document } from '@/types';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/use-auth-store';

const ALLOWED_MIME_OR_EXT = ".pdf,.docx,.doc,.txt,.md,.markdown,.csv,.json,.xlsx,.xls,.mp3,.wav,.m4a,.ogg,.opus,.aac,.webm,.oga,.flac";

export default function DocumentsPage() {
    const { t } = useTranslation();
    const { user } = useAuthStore();
    const queryClient = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isUploading, setIsUploading] = useState(false);

    // Website Crawler State
    const [websiteUrl, setWebsiteUrl] = useState('');
    const [websiteTitle, setWebsiteTitle] = useState('');
    const [maxPages, setMaxPages] = useState<number>(25);
    const [deepCrawl, setDeepCrawl] = useState<boolean>(true);
    const [autoSync, setAutoSync] = useState<boolean>(true);
    const [syncingDocId, setSyncingDocId] = useState<number | null>(null);

    // Voice Recording State
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
    const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
    const [voiceNoteTitle, setVoiceNoteTitle] = useState('');
    const [isPlayingPreview, setIsPlayingPreview] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const previewAudioRef = useRef<HTMLAudioElement | null>(null);

    // Page View Mode: 'list' (cargar/gestionar) vs 'galaxy' (visualización del conocimiento)
    const [pageMode, setPageMode] = useState<'list' | 'galaxy'>('list');
    const [galaxyData, setGalaxyData] = useState<any | null>(null);
    const [loadingGalaxy, setLoadingGalaxy] = useState(false);
    const [refreshingGalaxy, setRefreshingGalaxy] = useState(false);
    const [synapseMonitorOpen, setSynapseMonitorOpen] = useState(false);

    const fetchGalaxy = async (silent = false) => {
        if (!silent) setLoadingGalaxy(true);
        else setRefreshingGalaxy(true);
        try {
            const res = await apiClient.get('/rag/knowledge-graph');
            setGalaxyData(res.data);
        } catch (err: any) {
            toast.error('Error al cargar el grafo: ' + (err.response?.data?.error || err.message));
        } finally {
            setLoadingGalaxy(false);
            setRefreshingGalaxy(false);
        }
    };

    useEffect(() => {
        if (pageMode === 'galaxy' && !galaxyData) {
            fetchGalaxy();
        }
    }, [pageMode]);

    // Fetch Documents
    const { data: documents, isLoading } = useQuery({
        queryKey: ['documents'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: Document[] }>('/rag');
            return data.data;
        },
        refetchInterval: (query) => {
            const docs = query.state.data;
            const hasProcessing = docs?.some(d => d.status === 'processing' || d.status === 'pending');
            return hasProcessing ? 3000 : false;
        }
    });

    // Upload Mutation
    const uploadMutation = useMutation({
        mutationFn: async (params: { file: File | Blob; filename?: string; title?: string; isVoice?: boolean }) => {
            const formData = new FormData();
            const filename = params.filename || (params.file instanceof File ? params.file.name : 'voice_note.webm');
            formData.append('file', params.file, filename);
            if (params.title) {
                formData.append('title', params.title);
            }
            if (params.isVoice) {
                formData.append('is_voice_note', 'true');
            }
            return apiClient.post('/rag/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast.success(t('common.success', { defaultValue: 'Documento subido y procesándose' }));
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
            resetVoiceRecording();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error', { defaultValue: 'Error al subir archivo' }));
            setIsUploading(false);
        },
    });

    // Website Crawl Mutation
    const crawlWebsiteMutation = useMutation({
        mutationFn: async (payload: { url: string; title?: string; max_pages: number; deep_crawl: boolean; auto_sync: boolean }) => {
            return apiClient.post('/rag/crawl-website', payload);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast.success('Rastreo del sitio web iniciado. Las páginas se indexarán en Pinecone en segundo plano.');
            setWebsiteUrl('');
            setWebsiteTitle('');
            setIsUploading(false);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || 'Error al iniciar rastreo del sitio web');
            setIsUploading(false);
        }
    });

    // Website Sync Mutation
    const syncWebsiteMutation = useMutation({
        mutationFn: async (documentId: number) => {
            setSyncingDocId(documentId);
            return apiClient.post(`/rag/sync-website/${documentId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast.success('Sincronización del sitio web iniciada. Comprobando cambios en segundo plano...');
            setSyncingDocId(null);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || 'Error al sincronizar sitio web');
            setSyncingDocId(null);
        }
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            return apiClient.delete(`/rag/documents/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast.success(t('common.success', { defaultValue: 'Documento eliminado' }));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error', { defaultValue: 'Error al eliminar' }));
        }
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setIsUploading(true);
            uploadMutation.mutate({ file });
        }
    };

    const handleCrawlSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!websiteUrl.trim()) {
            toast.error('Por favor ingresa una URL válida');
            return;
        }
        setIsUploading(true);
        crawlWebsiteMutation.mutate({
            url: websiteUrl.trim(),
            title: websiteTitle.trim() || undefined,
            max_pages: maxPages,
            deep_crawl: deepCrawl,
            auto_sync: autoSync
        });
    };

    // Voice Recorder Handlers
    const startRecording = async () => {
        try {
            audioChunksRef.current = [];
            setRecordedBlob(null);
            setRecordedAudioUrl(null);
            setIsPlayingPreview(false);

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Choose supported mimeType
            let mimeType = 'audio/webm';
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                mimeType = 'audio/mp4';
            } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
                mimeType = 'audio/ogg';
            }

            const mediaRecorder = new MediaRecorder(stream, { mimeType });
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
                setRecordedBlob(audioBlob);
                const url = URL.createObjectURL(audioBlob);
                setRecordedAudioUrl(url);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start(250);
            setIsRecording(true);
            setRecordingTime(0);

            timerIntervalRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        } catch (err) {
            console.error('Error accessing microphone:', err);
            toast.error(t('common.error', { defaultValue: 'No se pudo acceder al micrófono' }));
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
                timerIntervalRef.current = null;
            }
        }
    };

    const resetVoiceRecording = () => {
        if (timerIntervalRef.current) {
            clearInterval(timerIntervalRef.current);
            timerIntervalRef.current = null;
        }
        if (recordedAudioUrl) {
            URL.revokeObjectURL(recordedAudioUrl);
        }
        setIsRecording(false);
        setRecordingTime(0);
        setRecordedBlob(null);
        setRecordedAudioUrl(null);
        setVoiceNoteTitle('');
        setIsPlayingPreview(false);
    };

    const handleSaveVoiceNote = () => {
        if (!recordedBlob) return;
        setIsUploading(true);
        const timestamp = format(new Date(), 'yyyy-MM-dd_HHmm');
        const defaultTitle = `Nota de voz - ${format(new Date(), 'PPpp')}`;
        const title = voiceNoteTitle.trim() || defaultTitle;
        const filename = `voice_note_${timestamp}.webm`;

        uploadMutation.mutate({
            file: recordedBlob,
            filename,
            title,
            isVoice: true
        });
    };

    const togglePlayPreview = () => {
        if (!previewAudioRef.current) return;
        if (isPlayingPreview) {
            previewAudioRef.current.pause();
            setIsPlayingPreview(false);
        } else {
            previewAudioRef.current.play();
            setIsPlayingPreview(true);
        }
    };

    useEffect(() => {
        return () => {
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
            if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
        };
    }, [recordedAudioUrl]);

    const formatTimer = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getDocumentIcon = (doc: Document) => {
        if (doc.file_type === 'url' || doc.original_filename?.startsWith('http')) {
            return <Globe className="h-4 w-4 text-cyan-500" />;
        }
        const ext = doc.original_filename?.split('.').pop()?.toLowerCase() || '';
        const isVoice = doc.doc_metadata?.is_voice || ['mp3', 'wav', 'ogg', 'm4a', 'opus', 'webm', 'flac'].includes(ext);
        
        if (isVoice) {
            return <Mic className="h-4 w-4 text-violet-500" />;
        }
        if (['md', 'markdown', 'json'].includes(ext)) {
            return <FileCode className="h-4 w-4 text-emerald-500" />;
        }
        if (['xlsx', 'xls', 'csv'].includes(ext)) {
            return <FileSpreadsheet className="h-4 w-4 text-teal-500" />;
        }
        return <FileText className="h-4 w-4 text-blue-500" />;
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{t('documents.title')}</h2>
                    <p className="text-muted-foreground">
                        Base de conocimiento RAG: Archivos, Grabaciones de Voz, Sitios Web y Visualización de Grafo de Conocimiento.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Tabs value={pageMode} onValueChange={(val) => setPageMode(val as 'list' | 'galaxy')}>
                        <TabsList className="grid grid-cols-2 w-[280px]">
                            <TabsTrigger value="list" className="flex items-center gap-1.5 text-xs">
                                <FileText className="h-3.5 w-3.5" />
                                Gestión RAG
                            </TabsTrigger>
                            <TabsTrigger value="galaxy" className="flex items-center gap-1.5 text-xs">
                                <Atom className="h-3.5 w-3.5 text-indigo-500" />
                                Galaxia Visual
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSynapseMonitorOpen(true)}
                        className="bg-violet-950/40 hover:bg-violet-900/50 border-violet-700/50 text-violet-300 text-xs font-semibold gap-1.5"
                    >
                        <Atom className="w-3.5 h-3.5 text-violet-400" />
                        Monitor Sináptico
                    </Button>
                </div>
            </div>

            {pageMode === 'galaxy' ? (
                <div className="space-y-6">
                    {/* Header bar */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md">
                                    <Atom className="h-4 w-4 text-white" />
                                </div>
                                <h3 className="text-base font-semibold">Galaxia del Conocimiento RAG</h3>
                                <Badge variant="outline">Interactivo</Badge>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Grafo visual que conecta documentos, skills, media, agentes y departamentos de tu empresa.
                            </p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => fetchGalaxy(true)}
                            disabled={refreshingGalaxy}
                            className="self-start sm:self-center"
                        >
                            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refreshingGalaxy ? 'animate-spin' : ''}`} />
                            Actualizar Grafo
                        </Button>
                    </div>

                    {/* Stats row */}
                    {galaxyData && (
                        <div className="flex flex-wrap gap-2">
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-indigo-600 bg-card shadow-xs">
                                <FileText className="h-3.5 w-3.5" />
                                <strong>{galaxyData.stats.documents}</strong>
                                <span className="text-muted-foreground text-xs">Documentos</span>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-emerald-600 bg-card shadow-xs">
                                <Sparkles className="h-3.5 w-3.5" />
                                <strong>{galaxyData.stats.skills}</strong>
                                <span className="text-muted-foreground text-xs">Skills</span>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-amber-600 bg-card shadow-xs">
                                <ImageIcon className="h-3.5 w-3.5" />
                                <strong>{galaxyData.stats.media}</strong>
                                <span className="text-muted-foreground text-xs">Media</span>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-violet-600 bg-card shadow-xs">
                                <Bot className="h-3.5 w-3.5" />
                                <strong>{galaxyData.stats.agents}</strong>
                                <span className="text-muted-foreground text-xs">Agentes</span>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-blue-600 bg-card shadow-xs">
                                <Building2 className="h-3.5 w-3.5" />
                                <strong>{galaxyData.stats.departments}</strong>
                                <span className="text-muted-foreground text-xs">Departamentos</span>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm text-muted-foreground bg-muted/40 shadow-xs">
                                <span className="font-medium text-foreground">{galaxyData.stats.total_nodes}</span> nodos ·
                                <span className="font-medium text-foreground">{galaxyData.stats.total_edges}</span> relaciones
                            </div>
                        </div>
                    )}

                    {/* Graph Card */}
                    <Card className="rounded-2xl shadow-xs overflow-hidden">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-semibold">Visualización de Red Semántica</CardTitle>
                            <p className="text-xs text-muted-foreground">
                                Arrastra los nodos, haz zoom con la rueda del ratón y busca términos clave para iluminar la red.
                            </p>
                        </CardHeader>
                        <CardContent className="p-3">
                            {loadingGalaxy ? (
                                <Skeleton className="h-[580px] w-full rounded-xl" />
                            ) : galaxyData ? (
                                <KnowledgeGalaxy
                                    nodes={galaxyData.nodes}
                                    edges={galaxyData.edges}
                                    width={900}
                                    height={580}
                                />
                            ) : (
                                <div className="flex h-48 flex-col items-center justify-center gap-3 text-muted-foreground">
                                    <Atom className="h-10 w-10 opacity-30" />
                                    <p className="text-sm">No se pudo cargar el grafo de conocimiento</p>
                                    <Button variant="outline" size="sm" onClick={() => fetchGalaxy()}>
                                        Reintentar
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-3">
                {/* Upload, Voice & Website Card */}
                <Card className="col-span-1 border bg-card">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-primary" />
                            {t('documents.uploadTitle')}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Tabs defaultValue="file" className="w-full">
                            <TabsList className="grid w-full grid-cols-3 p-1 bg-muted/60 rounded-lg h-auto mb-4 border border-border/40">
                                <TabsTrigger 
                                    value="file" 
                                    className="flex items-center justify-center gap-1.5 py-2 px-2 text-xs font-medium rounded-md transition-all data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
                                >
                                    <UploadCloud className="h-3.5 w-3.5 shrink-0 text-primary" />
                                    <span className="truncate font-semibold">{t('documents.tabsFiles')}</span>
                                </TabsTrigger>
                                <TabsTrigger 
                                    value="voice" 
                                    className="flex items-center justify-center gap-1.5 py-2 px-2 text-xs font-medium rounded-md transition-all data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
                                >
                                    <Mic className="h-3.5 w-3.5 shrink-0 text-violet-500" />
                                    <span className="truncate font-semibold">{t('documents.tabsVoice')}</span>
                                </TabsTrigger>
                                <TabsTrigger 
                                    value="website" 
                                    className="flex items-center justify-center gap-1.5 py-2 px-2 text-xs font-medium rounded-md transition-all data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
                                >
                                    <Globe className="h-3.5 w-3.5 shrink-0 text-cyan-500" />
                                    <span className="truncate font-semibold">Sitio Web</span>
                                </TabsTrigger>
                            </TabsList>

                            {/* Tab 1: File Upload */}
                            <TabsContent value="file" className="space-y-4">
                                <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl bg-muted/20 text-center">
                                    <div className="rounded-full bg-primary/10 p-3.5 shadow-sm text-primary mb-3">
                                        <UploadCloud className="h-7 w-7" />
                                    </div>
                                    <p className="text-xs text-muted-foreground mb-4">
                                        {t('documents.uploadDesc')}
                                    </p>
                                    <Button
                                        disabled={isUploading}
                                        onClick={() => fileInputRef.current?.click()}
                                        className="w-full"
                                    >
                                        {isUploading ? (
                                             <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.saving')}
                                            </>
                                        ) : (
                                            t('documents.selectFile')
                                        )}
                                    </Button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        className="hidden"
                                        accept={ALLOWED_MIME_OR_EXT}
                                        onChange={handleFileChange}
                                    />
                                </div>
                            </TabsContent>

                            {/* Tab 2: Voice Note Recording */}
                            <TabsContent value="voice" className="space-y-4">
                                {!recordedBlob ? (
                                    <div className="flex flex-col items-center justify-center p-6 border rounded-xl bg-muted/20 text-center space-y-4">
                                        <div className={`rounded-full p-4 transition-all duration-300 ${isRecording ? 'bg-red-500/20 text-red-600 animate-pulse ring-4 ring-red-500/30' : 'bg-primary/10 text-primary'}`}>
                                            <Mic className="h-8 w-8" />
                                        </div>

                                        {isRecording ? (
                                            <div className="space-y-2">
                                                <div className="flex items-center justify-center gap-2">
                                                    <span className="h-2.5 w-2.5 rounded-full bg-red-600 animate-ping" />
                                                    <span className="font-mono text-xl font-bold text-red-600">{formatTimer(recordingTime)}</span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">{t('documents.recordingVoice')}</p>
                                                <Button
                                                    variant="destructive"
                                                    size="sm"
                                                    onClick={stopRecording}
                                                    className="w-full mt-2"
                                                >
                                                    <Square className="h-4 w-4 mr-2" />
                                                    {t('documents.stopRecording')}
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="space-y-2 w-full">
                                                <p className="text-xs text-muted-foreground">
                                                    {t('documents.recordVoiceDesc')}
                                                </p>
                                                <Button
                                                    onClick={startRecording}
                                                    className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white shadow-sm"
                                                >
                                                    <Mic className="h-4 w-4 mr-2" />
                                                    {t('documents.recordVoice')}
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="space-y-3 p-4 border rounded-xl bg-muted/10">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                                                <Volume2 className="h-3.5 w-3.5 text-primary" />
                                                {t('documents.recordedAudio')} ({formatTimer(recordingTime)})
                                            </span>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-7 text-xs text-destructive hover:bg-destructive/10"
                                                onClick={resetVoiceRecording}
                                            >
                                                {t('documents.cancelRecording')}
                                            </Button>
                                        </div>

                                        {recordedAudioUrl && (
                                            <div className="flex items-center gap-2 bg-background p-2 rounded-lg border">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="h-8 w-8 p-0 shrink-0"
                                                    onClick={togglePlayPreview}
                                                >
                                                    {isPlayingPreview ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                                                </Button>
                                                <audio
                                                    ref={previewAudioRef}
                                                    src={recordedAudioUrl}
                                                    onEnded={() => setIsPlayingPreview(false)}
                                                    className="hidden"
                                                />
                                                <span className="text-xs text-muted-foreground truncate font-mono">
                                                    {isPlayingPreview ? t('documents.playing') : t('documents.readyToProcess')}
                                                </span>
                                            </div>
                                        )}

                                        <div className="space-y-1">
                                            <Label className="text-xs">{t('documents.voiceNoteTitle')}</Label>
                                            <Input
                                                placeholder={t('documents.voiceNotePlaceholder')}
                                                value={voiceNoteTitle}
                                                onChange={(e) => setVoiceNoteTitle(e.target.value)}
                                                className="h-8 text-xs"
                                            />
                                        </div>

                                        <Button
                                            disabled={isUploading}
                                            onClick={handleSaveVoiceNote}
                                            className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white"
                                        >
                                            {isUploading ? (
                                                <>
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('documents.transcribing')}
                                                </>
                                            ) : (
                                                <>
                                                    <Radio className="mr-2 h-4 w-4" /> {t('documents.saveVoiceNote')}
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                )}
                            </TabsContent>

                            {/* Tab 3: Website Crawler & Auto-Sync */}
                            <TabsContent value="website" className="space-y-4">
                                <form onSubmit={handleCrawlSubmit} className="p-4 border rounded-xl bg-muted/10 space-y-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                                            <Globe className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <h4 className="text-xs font-bold text-foreground">Rastreador Web Inteligente</h4>
                                            <p className="text-[11px] text-muted-foreground">Indexa todo el sitio y sincroniza cambios automáticamente.</p>
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <Label className="text-xs font-medium">URL del Sitio Web *</Label>
                                        <Input
                                            type="url"
                                            placeholder="https://ejemplo.com"
                                            value={websiteUrl}
                                            onChange={(e) => setWebsiteUrl(e.target.value)}
                                            required
                                            className="h-8 text-xs"
                                        />
                                    </div>

                                    <div className="space-y-1">
                                        <Label className="text-xs font-medium">Título o Nombre (Opcional)</Label>
                                        <Input
                                            placeholder="Ej. Portal Corporativo"
                                            value={websiteTitle}
                                            onChange={(e) => setWebsiteTitle(e.target.value)}
                                            className="h-8 text-xs"
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 pt-1">
                                        <div className="space-y-1">
                                            <Label className="text-[11px] text-muted-foreground">Límite de Páginas</Label>
                                            <select
                                                value={maxPages}
                                                onChange={(e) => setMaxPages(Number(e.target.value))}
                                                className="w-full h-8 text-xs rounded-md border border-input bg-background px-2"
                                            >
                                                <option value={10}>Hasta 10 páginas</option>
                                                <option value={25}>Hasta 25 páginas (Recomendado)</option>
                                                <option value={50}>Hasta 50 páginas</option>
                                                <option value={100}>Hasta 100 páginas</option>
                                            </select>
                                        </div>
                                        <div className="flex flex-col justify-end space-y-1">
                                            <label className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer pt-1">
                                                <input
                                                    type="checkbox"
                                                    checked={deepCrawl}
                                                    onChange={(e) => setDeepCrawl(e.target.checked)}
                                                    className="rounded border-input text-cyan-600 focus:ring-cyan-500 h-3.5 w-3.5"
                                                />
                                                <span>Subpáginas & Sitemap</span>
                                            </label>
                                            <label className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={autoSync}
                                                    onChange={(e) => setAutoSync(e.target.checked)}
                                                    className="rounded border-input text-cyan-600 focus:ring-cyan-500 h-3.5 w-3.5"
                                                />
                                                <span className="text-cyan-600 dark:text-cyan-400 font-semibold">Auto-Sync Activo</span>
                                            </label>
                                        </div>
                                    </div>

                                    <Button
                                        type="submit"
                                        disabled={isUploading || crawlWebsiteMutation.isPending}
                                        className="w-full mt-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 text-white shadow-sm h-8 text-xs font-semibold"
                                    >
                                        {crawlWebsiteMutation.isPending ? (
                                            <>
                                                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Rastreado en curso...
                                            </>
                                        ) : (
                                            <>
                                                <Globe className="mr-2 h-3.5 w-3.5" /> Rastrear e Indexar Sitio
                                            </>
                                        )}
                                    </Button>
                                </form>
                            </TabsContent>
                        </Tabs>
                    </CardContent>
                </Card>

                {/* Documents List */}
                <Card className="col-span-2">
                    <CardHeader>
                        <CardTitle>{t('documents.myDocuments')}</CardTitle>
                        <CardDescription>
                            {t('documents.documentsCount', { count: documents?.length || 0 })}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="space-y-2">
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-full" />
                            </div>
                        ) : !documents || documents.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground space-y-2">
                                <FileText className="h-10 w-10 opacity-20" />
                                <p className="text-sm">{t('documents.noDocuments')}</p>
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>{t('common.name')}</TableHead>
                                        <TableHead>{t('common.size')}</TableHead>
                                        <TableHead>{t('common.status')}</TableHead>
                                        <TableHead>{t('common.date')}</TableHead>
                                        <TableHead className="text-right">{t('common.actions')}</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {documents.map((doc) => {
                                        const ext = doc.original_filename?.split('.').pop()?.toLowerCase() || '';
                                        const isVoice = doc.doc_metadata?.is_voice || ['mp3', 'wav', 'ogg', 'm4a', 'opus', 'webm', 'flac'].includes(ext);
                                        const isWebsite = doc.file_type === 'url' || doc.original_filename?.startsWith('http');
                                        const pagesCount = doc.doc_metadata?.pages_indexed || (doc.doc_metadata?.pages ? Object.keys(doc.doc_metadata.pages).length : 1);
                                        const isSyncing = syncingDocId === doc.id;

                                        return (
                                            <TableRow key={doc.id}>
                                                <TableCell className="font-medium max-w-[280px]">
                                                    <div className="flex items-center gap-2">
                                                        {getDocumentIcon(doc)}
                                                        <div className="truncate">
                                                            <div className="truncate text-sm font-medium flex items-center gap-1.5">
                                                                {doc.title || doc.original_filename}
                                                                {isWebsite && (
                                                                    <a 
                                                                        href={doc.original_filename} 
                                                                        target="_blank" 
                                                                        rel="noopener noreferrer" 
                                                                        className="text-muted-foreground hover:text-cyan-500"
                                                                        title="Abrir sitio web"
                                                                    >
                                                                        <ExternalLink className="h-3 w-3" />
                                                                    </a>
                                                                )}
                                                            </div>
                                                            {isVoice && (
                                                                <div className="text-[11px] text-violet-600 dark:text-violet-400 flex items-center gap-1 font-normal">
                                                                    <Mic className="h-3 w-3" /> {t('documents.audioVoiceBadge')}
                                                                </div>
                                                            )}
                                                            {isWebsite && (
                                                                <div className="text-[11px] text-cyan-600 dark:text-cyan-400 flex items-center gap-1 font-normal">
                                                                    <Layers className="h-3 w-3" /> {pagesCount} {pagesCount === 1 ? 'página' : 'páginas'} indexadas
                                                                    {doc.doc_metadata?.auto_sync && (
                                                                        <span className="text-[10px] bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 px-1.5 py-0.2 rounded-full border border-cyan-500/20 ml-1">
                                                                            Auto-Sync
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-xs text-muted-foreground">
                                                    {isWebsite ? `${doc.chunk_count || 0} fragmentos` : formatFileSize(doc.file_size || 0)}
                                                </TableCell>
                                                <TableCell>
                                                    {doc.status === 'indexed' ? (
                                                        <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                                                            <CheckCircle2 className="mr-1 h-3 w-3" /> {t('common.ready')}
                                                        </Badge>
                                                    ) : doc.status === 'error' ? (
                                                        <Badge variant="destructive" className="text-xs" title={doc.error_message || ''}>
                                                            <AlertCircle className="mr-1 h-3 w-3" /> Error
                                                        </Badge>
                                                    ) : (
                                                        <Badge variant="secondary" className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                                                            <Loader2 className="mr-1 h-3 w-3 animate-spin" /> {t('common.processing')}
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-xs text-muted-foreground">
                                                    <div>{doc.uploaded_at ? format(new Date(doc.uploaded_at), 'MMM d, yyyy') : '-'}</div>
                                                    {isWebsite && doc.doc_metadata?.last_synced_at && (
                                                        <div className="text-[10px] text-muted-foreground/80 flex items-center gap-0.5 mt-0.5">
                                                            <Clock className="h-2.5 w-2.5" /> {format(new Date(doc.doc_metadata.last_synced_at), 'HH:mm')}
                                                        </div>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        {isWebsite && (
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                disabled={isSyncing || doc.status === 'processing'}
                                                                className="h-8 px-2 text-xs border-cyan-500/30 text-cyan-700 dark:text-cyan-400 hover:bg-cyan-500/10"
                                                                onClick={() => syncWebsiteMutation.mutate(doc.id)}
                                                                title="Comprobar cambios y actualizar vectores ahora"
                                                            >
                                                                <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
                                                                <span>Sincronizar</span>
                                                            </Button>
                                                        )}
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                                                            onClick={() => {
                                                                if (confirm(t('common.confirmDelete', { defaultValue: '¿Eliminar este documento?' }))) {
                                                                    deleteMutation.mutate(doc.id);
                                                                }
                                                            }}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
            )}

            {/* Monitor Sináptico Modal */}
            {synapseMonitorOpen && (
                <AgentSynapseMonitor
                    isOpen={synapseMonitorOpen}
                    onClose={() => setSynapseMonitorOpen(false)}
                    companyId={user?.company_id}
                />
            )}
        </div>
    );
}

