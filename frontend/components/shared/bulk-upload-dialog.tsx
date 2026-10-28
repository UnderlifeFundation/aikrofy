'use client';

import { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
    Upload,
    Download,
    FileSpreadsheet,
    CheckCircle2,
    AlertCircle,
    Loader2,
    ChevronRight,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useQueryClient } from '@tanstack/react-query';

interface EntityColumn {
    key: string;
    label: string;
    required: boolean;
    type: string;
}

interface Entity {
    key: string;
    label: string;
    description: string;
    columns: EntityColumn[];
}

interface UploadResult {
    total: number;
    imported: number;
    skipped: number;
    errors: number;
    error_details: string[];
}

interface BulkUploadDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    defaultEntity?: string;
    invalidateKeys?: string[];
}

export default function BulkUploadDialog({
    open,
    onOpenChange,
    defaultEntity,
    invalidateKeys = [],
}: BulkUploadDialogProps) {
    const queryClient = useQueryClient();

    const [step, setStep] = useState<1 | 2 | 3>(1);
    const [entities, setEntities] = useState<Entity[]>([]);
    const [loadingEntities, setLoadingEntities] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState<string>(defaultEntity || '');
    const [selectedFormat, setSelectedFormat] = useState<'csv' | 'xlsx'>('csv');
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<UploadResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const loadEntities = async () => {
        if (entities.length > 0) return;
        setLoadingEntities(true);
        try {
            const res = await apiClient.get('/ingestion/entities');
            setEntities(res.data?.data || []);
        } catch {
            setError('No se pudo cargar la lista de entidades.');
        } finally {
            setLoadingEntities(false);
        }
    };

    const handleOpen = (isOpen: boolean) => {
        if (isOpen) {
            loadEntities();
            if (defaultEntity) setSelectedEntity(defaultEntity);
        } else {
            setStep(1);
            setFile(null);
            setResult(null);
            setError(null);
        }
        onOpenChange(isOpen);
    };

    const handleDownloadTemplate = async () => {
        if (!selectedEntity) return;
        try {
            const res = await apiClient.get(
                `/ingestion/template/${selectedEntity}?format=${selectedFormat}`,
                { responseType: 'blob' }
            );
            const ext = selectedFormat === 'xlsx' ? 'xlsx' : 'csv';
            const url = URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = `template_${selectedEntity}.${ext}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            setError('Error descargando el template. Inténtalo de nuevo.');
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (f) {
            setFile(f);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file || !selectedEntity) return;

        if (file.size > 10 * 1024 * 1024) {
            setError('El archivo excede el límite de 10 MB.');
            return;
        }

        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await apiClient.post(
                `/ingestion/upload/${selectedEntity}`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
            setResult(res.data?.data || null);
            setStep(3);

            for (const key of invalidateKeys) {
                queryClient.invalidateQueries({ queryKey: [key] });
            }
        } catch (err: any) {
            const msg =
                err?.response?.data?.error ||
                err?.response?.data?.message ||
                'Error durante la importación.';
            setError(msg);
        } finally {
            setUploading(false);
        }
    };

    const entityMeta = entities.find((e) => e.key === selectedEntity);

    return (
        <Dialog open={open} onOpenChange={handleOpen}>
            <DialogContent className="w-[95vw] max-w-[560px] max-h-[90vh] overflow-y-auto p-4 sm:p-6">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-lg sm:text-xl">
                        <FileSpreadsheet className="h-5 w-5 text-primary shrink-0" />
                        Importación Masiva
                    </DialogTitle>
                    <DialogDescription>
                        Sube un archivo CSV o Excel para importar datos en bloque.
                    </DialogDescription>
                </DialogHeader>

                {/* Step indicator */}
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                    {(['Seleccionar', 'Subir archivo', 'Resultados'] as const).map((label, i) => (
                        <span key={label} className="flex items-center gap-1">
                            <span
                                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                                    step === i + 1
                                        ? 'bg-primary text-primary-foreground'
                                        : step > i + 1
                                        ? 'bg-emerald-500 text-white'
                                        : 'bg-muted text-muted-foreground'
                                }`}
                            >
                                {step > i + 1 ? '✓' : i + 1}
                            </span>
                            {label}
                            {i < 2 && <ChevronRight className="h-3 w-3" />}
                        </span>
                    ))}
                </div>

                {/* STEP 1 */}
                {step === 1 && (
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">¿Qué datos quieres importar?</label>
                            {loadingEntities ? (
                                <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Cargando entidades...
                                </div>
                            ) : (
                                <Select value={selectedEntity} onValueChange={setSelectedEntity}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Selecciona una entidad..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {entities.map((e) => (
                                            <SelectItem key={e.key} value={e.key}>
                                                {e.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        </div>

                        {entityMeta && (
                            <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
                                <p className="text-xs text-muted-foreground">{entityMeta.description}</p>
                                <div className="flex flex-wrap gap-1">
                                    {entityMeta.columns.map((col) => (
                                        <Badge
                                            key={col.key}
                                            variant={col.required ? 'default' : 'secondary'}
                                            className="text-[10px]"
                                        >
                                            {col.label}
                                            {col.required && ' *'}
                                        </Badge>
                                    ))}
                                </div>
                                <p className="text-[10px] text-muted-foreground">* Campo requerido</p>
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Formato del template</label>
                            <div className="flex gap-2">
                                {(['csv', 'xlsx'] as const).map((fmt) => (
                                    <Button
                                        key={fmt}
                                        size="sm"
                                        variant={selectedFormat === fmt ? 'default' : 'outline'}
                                        onClick={() => setSelectedFormat(fmt)}
                                        className="flex-1 uppercase text-xs"
                                    >
                                        {fmt}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={!selectedEntity}
                                onClick={handleDownloadTemplate}
                                className="gap-1.5"
                            >
                                <Download className="h-4 w-4" />
                                Descargar Template
                            </Button>
                            <Button
                                size="sm"
                                disabled={!selectedEntity}
                                onClick={() => setStep(2)}
                                className="flex-1"
                            >
                                Continuar
                                <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                        </div>
                    </div>
                )}

                {/* STEP 2 */}
                {step === 2 && (
                    <div className="space-y-4">
                        <div className="rounded-lg border-2 border-dashed border-muted-foreground/30 p-6 text-center space-y-3 hover:border-primary/50 transition-colors">
                            <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                            <div>
                                <p className="text-sm font-medium">
                                    {file ? file.name : 'Selecciona tu archivo'}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Acepta .csv, .xlsx — máximo 10 MB
                                </p>
                            </div>
                            <Input
                                type="file"
                                accept=".csv,.xlsx,.xls"
                                onChange={handleFileChange}
                                className="max-w-xs mx-auto"
                            />
                        </div>

                        {file && (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
                                <FileSpreadsheet className="h-4 w-4" />
                                <span className="font-medium">{file.name}</span>
                                <span>({(file.size / 1024).toFixed(1)} KB)</span>
                            </div>
                        )}

                        {error && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}

                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setStep(1)}
                            >
                                Volver
                            </Button>
                            <Button
                                size="sm"
                                disabled={!file || uploading}
                                onClick={handleUpload}
                                className="flex-1 gap-1.5"
                            >
                                {uploading ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Importando...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="h-4 w-4" />
                                        Importar Datos
                                    </>
                                )}
                            </Button>
                        </div>

                        {uploading && (
                            <Progress value={undefined} className="h-1.5 animate-pulse" />
                        )}
                    </div>
                )}

                {/* STEP 3 */}
                {step === 3 && result && (
                    <div className="space-y-4">
                        <div className="rounded-xl border bg-gradient-to-br from-emerald-50 to-transparent dark:from-emerald-950/30 p-4 space-y-3">
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                                <span className="font-semibold text-sm">Importación Completada</span>
                            </div>
                            <div className="grid grid-cols-4 gap-3">
                                {[
                                    { label: 'Total', value: result.total, color: 'text-foreground' },
                                    { label: 'Importados', value: result.imported, color: 'text-emerald-600' },
                                    { label: 'Omitidos', value: result.skipped, color: 'text-amber-600' },
                                    { label: 'Errores', value: result.errors, color: 'text-destructive' },
                                ].map((stat) => (
                                    <div
                                        key={stat.label}
                                        className="text-center rounded-lg bg-background/60 p-2 border"
                                    >
                                        <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
                                        <p className="text-[10px] text-muted-foreground">{stat.label}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {result.error_details.length > 0 && (
                            <div className="space-y-1">
                                <p className="text-xs font-medium text-muted-foreground">
                                    Detalles ({result.error_details.length}):
                                </p>
                                <div className="max-h-36 overflow-y-auto rounded-lg border bg-muted/20 p-2 space-y-0.5">
                                    {result.error_details.map((msg, i) => (
                                        <p key={i} className="text-[11px] text-muted-foreground">
                                            {msg}
                                        </p>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    setStep(1);
                                    setFile(null);
                                    setResult(null);
                                    setError(null);
                                }}
                            >
                                Nueva Importación
                            </Button>
                            <Button size="sm" className="flex-1" onClick={() => handleOpen(false)}>
                                Cerrar
                            </Button>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
