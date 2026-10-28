'use client';

import React, { useState, useEffect } from 'react';
import { 
    X, 
    Copy, 
    Check, 
    Download, 
    FileText, 
    Table, 
    Maximize2, 
    Minimize2, 
    Sparkles, 
    Edit3, 
    Eye,
    FileSpreadsheet,
    Printer,
    FileCode
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';
import { 
    DropdownMenu, 
    DropdownMenuTrigger, 
    DropdownMenuContent, 
    DropdownMenuItem,
    DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useTranslation } from 'react-i18next';

import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';
import { ChatChartWidget, ChartConfig } from '@/components/chat/ChatChartWidget';

export interface CanvasDocument {
    id: string;
    title: string;
    content: string;
    type: 'document' | 'table' | 'code' | 'report';
    chartConfig?: ChartConfig;
    updatedAt: Date;
}

interface KrofStudioCanvasProps {
    document: CanvasDocument | null;
    onClose: () => void;
    onUpdateContent: (newContent: string) => void;
    onAskAiRefinement?: (prompt: string) => void;
    isAiRefining?: boolean;
    isExpanded?: boolean;
    onToggleExpanded?: () => void;
}

// Extract table-only rows from markdown content or csv-like text
function extractTableRows(content: string): string[][] {
    const lines = content.split('\n');
    const rows: string[][] = [];

    // 1. Look for markdown table lines
    const mdTableLines = lines.filter(l => l.trim().startsWith('|') && l.trim().endsWith('|'));
    if (mdTableLines.length >= 2) {
        mdTableLines.forEach(line => {
            const cells = line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
            if (cells.length > 0 && !cells[0].includes('---')) {
                rows.push(cells);
            }
        });
        if (rows.length > 0) return rows;
    }

    // 2. Fallback: CSV detection
    const csvLines = lines.filter(l => l.includes(',') && !l.includes('|') && l.trim().length > 0);
    if (csvLines.length >= 2) {
        csvLines.forEach(line => {
            const cells = line.split(',').map(c => c.trim().replace(/^"|"$/g, ''));
            rows.push(cells);
        });
        if (rows.length > 0) return rows;
    }

    return rows;
}

export function KrofStudioCanvas({
    document,
    onClose,
    onUpdateContent,
    onAskAiRefinement,
    isAiRefining = false,
    isExpanded: propIsExpanded,
    onToggleExpanded,
}: KrofStudioCanvasProps) {
    const { t } = useTranslation();
    const [isEditing, setIsEditing] = useState(false);
    const [copied, setCopied] = useState(false);
    const [localIsFullscreen, setLocalIsFullscreen] = useState(false);

    const isFullscreen = propIsExpanded !== undefined ? propIsExpanded : localIsFullscreen;
    const toggleFullscreen = onToggleExpanded || (() => setLocalIsFullscreen(!localIsFullscreen));

    // Listen to Escape key to easily exit fullscreen/expanded mode
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isFullscreen) {
                if (onToggleExpanded) {
                    onToggleExpanded();
                } else {
                    setLocalIsFullscreen(false);
                }
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isFullscreen, onToggleExpanded]);

    if (!document) return null;

    const handleCopy = () => {
        if (!document.content) return;
        navigator.clipboard.writeText(document.content);
        setCopied(true);
        toast.success(t('canvas.copied', 'Contenido copiado al portapapeles.'));
        setTimeout(() => setCopied(false), 2000);
    };

    const handleExportMarkdown = () => {
        const blob = new Blob([document.content], { type: 'text/markdown;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.title.toLowerCase().replace(/\s+/g, '_') || 'documento'}.md`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success(t('canvas.toastMarkdown', 'Archivo Markdown (.md) descargado.'));
    };

    const getFormattedHtmlBody = () => {
        try {
            const raw = marked.parse(document.content, { gfm: true, breaks: true }) as string;
            return DOMPurify.sanitize(raw, { ADD_ATTR: ['target', 'rel'], FORCE_BODY: true });
        } catch (e) {
            return document.content.replace(/\n/g, '<br/>');
        }
    };

    const handleExportHTML = () => {
        const renderedHtml = getFormattedHtmlBody();
        const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>${document.title}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 40px; color: #0f172a; max-width: 850px; margin: auto; }
        h1, h2, h3 { color: #1e293b; margin-top: 1.5em; }
        table { border-collapse: collapse; width: 100%; margin: 24px 0; font-size: 13px; }
        th, td { border: 1px solid #cbd5e1; padding: 10px 14px; text-align: left; }
        th { background: #f1f5f9; font-weight: 600; color: #0f172a; }
        tr:nth-child(even) { background: #f8fafc; }
        pre { background: #f1f5f9; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; }
        code { font-family: monospace; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <h1>${document.title}</h1>
    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
    <div>${renderedHtml}</div>
</body>
</html>`;
        const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.title.toLowerCase().replace(/\s+/g, '_') || 'documento'}.html`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success(t('canvas.toastHTML', 'Archivo HTML descargado.'));
    };

    const handleExportWordDoc = () => {
        const renderedHtml = getFormattedHtmlBody();
        const wordHtml = `
            <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
            <head>
                <meta charset="utf-8">
                <title>${document.title}</title>
                <style>
                    body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #111; }
                    h1 { font-size: 18pt; color: #1e3a8a; }
                    h2 { font-size: 14pt; color: #1e3a8a; margin-top: 14pt; }
                    table { border-collapse: collapse; width: 100%; margin: 15pt 0; font-size: 10pt; }
                    th, td { border: 1px solid #94a3b8; padding: 6pt 8pt; text-align: left; }
                    th { background-color: #f1f5f9; font-weight: bold; }
                </style>
            </head>
            <body>
                <h1>${document.title}</h1>
                <hr/>
                <div>${renderedHtml}</div>
            </body>
            </html>
        `;
        const blob = new Blob([wordHtml], { type: 'application/msword;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.title.toLowerCase().replace(/\s+/g, '_') || 'documento'}.doc`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success(t('canvas.toastWord', 'Documento Word (.doc) descargado.'));
    };

    const handlePrintOrPDF = () => {
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            toast.error(t('canvas.toastPDFError', 'Habilita las ventanas emergentes para exportar a PDF.'));
            return;
        }

        const renderedHtml = getFormattedHtmlBody();

        printWindow.document.write(`
            <html>
                <head>
                    <title>${document.title} - Krof Studio</title>
                    <style>
                        body { font-family: system-ui, -apple-system, sans-serif; padding: 36px; color: #0f172a; max-width: 900px; margin: auto; }
                        h1, h2, h3 { color: #0f172a; margin-top: 1.4em; }
                        h1 { font-size: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
                        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }
                        th, td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }
                        th { background-color: #f1f5f9; font-weight: 600; color: #0f172a; }
                        tr:nth-child(even) { background-color: #f8fafc; }
                        pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; font-size: 11px; overflow-x: auto; }
                        code { font-family: monospace; background: #e2e8f0; padding: 2px 5px; border-radius: 4px; font-size: 11px; }
                        @media print {
                            body { padding: 15px; }
                            @page { margin: 15mm; }
                        }
                    </style>
                </head>
                <body>
                    <h1>${document.title}</h1>
                    <div>${renderedHtml}</div>
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => {
            printWindow.print();
        }, 350);
    };

    const handleExportExcel = () => {
        const tableRows = extractTableRows(document.content);
        if (tableRows.length === 0) {
            toast.error(t('canvas.toastNoTable', 'No se detectó una tabla estructurada en el documento.'));
            return;
        }

        const headerRow = tableRows[0];
        const bodyRows = tableRows.slice(1);

        const tableHtml = `
            <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
            <head>
                <meta charset="utf-8">
                <!--[if gte mso 9]>
                <xml>
                    <x:ExcelWorkbook>
                        <x:ExcelWorksheets>
                            <x:ExcelWorksheet>
                                <x:Name>${document.title.substring(0, 31)}</x:Name>
                                <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                            </x:ExcelWorksheet>
                        </x:ExcelWorksheets>
                    </x:ExcelWorkbook>
                </xml>
                <![endif]-->
                <style>
                    th { background-color: #0284c7; color: #ffffff; font-weight: bold; border: 0.5pt solid #000; padding: 6px 12px; }
                    td { border: 0.5pt solid #cbd5e1; padding: 6px 12px; }
                </style>
            </head>
            <body>
                <table>
                    <tr>
                        ${headerRow.map(h => `<th>${h}</th>`).join('')}
                    </tr>
                    ${bodyRows.map(row => `
                        <tr>
                            ${row.map(c => `<td>${c}</td>`).join('')}
                        </tr>
                    `).join('')}
                </table>
            </body>
            </html>
        `;

        const blob = new Blob([tableHtml], { type: 'application/vnd.ms-excel;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.title.toLowerCase().replace(/\s+/g, '_') || 'tabla'}.xls`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success(t('canvas.toastExcel', 'Tabla exportada a Excel (.xls).'));
    };

    const handleExportCSV = () => {
        const tableRows = extractTableRows(document.content);
        let csvContent = '';

        if (tableRows.length > 0) {
            csvContent = tableRows.map(row => row.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n');
        } else {
            csvContent = document.content
                .split('\n')
                .filter(l => l.trim().length > 0)
                .map(l => `"${l.replace(/"/g, '""')}"`)
                .join('\n');
        }

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.title.toLowerCase().replace(/\s+/g, '_') || 'tabla'}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success(t('canvas.toastCSV', 'Tabla exportada a CSV (.csv).'));
    };

    const quickRefinements = [
        { 
            label: t('canvas.summarize', '✂️ Resumir'), 
            prompt: t('canvas.summarizePrompt', `Resume de forma clara y directa el siguiente documento sin perder detalles esenciales:\n\n{content}`).replace('{content}', document.content)
        },
        { 
            label: t('canvas.executiveTone', '👔 Tono Ejecutivo'), 
            prompt: t('canvas.executiveTonePrompt', `Reescribe el siguiente texto con un tono ejecutivo, formal y persuasivo de alto nivel:\n\n{content}`).replace('{content}', document.content)
        },
        { 
            label: t('canvas.convertToTable', '📊 Convertir a Tabla'), 
            prompt: t('canvas.convertToTablePrompt', `Convierte o estructura los puntos clave de este contenido en una tabla Markdown con columnas claras:\n\n{content}`).replace('{content}', document.content)
        },
        { 
            label: t('canvas.fixStyle', '🔍 Corregir Estilo'), 
            prompt: t('canvas.fixStylePrompt', `Revisa la ortografía, claridad, fluidez y formato Markdown del siguiente texto:\n\n{content}`).replace('{content}', document.content)
        },
    ];

    return (
        <div className="flex flex-col h-full w-full bg-background transition-all duration-200 overflow-hidden relative">
            {/* Top Canvas Header */}
            <div className="p-3 px-4 border-b bg-card/90 backdrop-blur flex items-center justify-between gap-2 shrink-0 select-none">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                    <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold shrink-0">
                        {document.type === 'table' ? <Table className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0 pr-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-xs font-semibold truncate text-foreground">{document.title}</h3>
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 capitalize bg-primary/5 text-primary border-primary/20">
                                {t('canvas.badge', 'Canvas')}
                            </Badge>
                            {isFullscreen && (
                                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary hidden sm:inline-flex">
                                    {t('canvas.expandedBadge', 'Vista ampliada (Esc para restaurar)')}
                                </Badge>
                            )}
                        </div>
                        <p className="text-[10px] text-muted-foreground truncate">{t('canvas.interactiveDoc', 'Lienzo interactivo editable')}</p>
                    </div>
                </div>

                {/* Header Action Buttons */}
                <div className="flex items-center gap-1.5 shrink-0">
                    {/* View / Edit Mode Toggle */}
                    <Button
                        variant={isEditing ? "default" : "outline"}
                        size="sm"
                        onClick={() => setIsEditing(!isEditing)}
                        className="h-8 text-xs gap-1 cursor-pointer px-2.5"
                        title={isEditing ? t('canvas.viewPreview', 'Vista Previa') : t('canvas.edit', 'Editar')}
                    >
                        {isEditing ? <Eye className="h-3.5 w-3.5" /> : <Edit3 className="h-3.5 w-3.5" />}
                        <span className="hidden sm:inline">{isEditing ? t('canvas.viewPreview', 'Vista Previa') : t('canvas.edit', 'Editar')}</span>
                    </Button>

                    {/* Copy Button */}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleCopy}
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        title={t('canvas.copy', 'Copiar')}
                    >
                        {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                    </Button>

                    {/* Export Dropdown */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs gap-1.5 cursor-pointer px-2.5"
                                title={t('canvas.export', 'Exportar')}
                            >
                                <Download className="h-3.5 w-3.5 text-primary" />
                                <span className="hidden sm:inline font-medium">{t('canvas.export', 'Exportar')}</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52 text-xs p-1">
                            <DropdownMenuItem onClick={handleExportExcel} className="gap-2.5 cursor-pointer py-2 font-medium">
                                <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                                <div>
                                    <div className="text-foreground">{t('canvas.exportExcel', 'Descargar Excel (.xls)')}</div>
                                    <div className="text-[10px] text-muted-foreground font-normal">{t('canvas.exportExcelDesc', 'Compatible con Microsoft Excel')}</div>
                                </div>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleExportCSV} className="gap-2.5 cursor-pointer py-2">
                                <Table className="h-4 w-4 text-blue-500" />
                                <div>
                                    <div className="text-foreground">{t('canvas.exportCSV', 'Descargar Tabla (.csv)')}</div>
                                    <div className="text-[10px] text-muted-foreground">{t('canvas.exportCSVDesc', 'Para importar en Google Sheets')}</div>
                                </div>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={handlePrintOrPDF} className="gap-2.5 cursor-pointer py-2">
                                <Printer className="h-4 w-4 text-primary" />
                                <span>{t('canvas.exportPDF', 'Exportar / Imprimir PDF')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleExportWordDoc} className="gap-2.5 cursor-pointer py-2 font-medium">
                                <FileText className="h-4 w-4 text-blue-600" />
                                <span>{t('canvas.exportWord', 'Descargar Word (.doc)')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleExportMarkdown} className="gap-2.5 cursor-pointer py-2">
                                <FileText className="h-4 w-4 text-indigo-500" />
                                <span>{t('canvas.exportMarkdown', 'Descargar Markdown (.md)')}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleExportHTML} className="gap-2.5 cursor-pointer py-2">
                                <FileCode className="h-4 w-4 text-muted-foreground" />
                                <span>{t('canvas.exportHTML', 'Descargar como HTML (.html)')}</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Maximize / Minimize / Restore button */}
                    <Button
                        variant={isFullscreen ? "default" : "ghost"}
                        size={isFullscreen ? "sm" : "icon"}
                        onClick={toggleFullscreen}
                        className={cn(
                            "h-8 transition-colors",
                            isFullscreen 
                                ? "bg-primary text-primary-foreground hover:bg-primary/90 text-xs gap-1.5 px-2.5 font-medium shadow-sm" 
                                : "w-8 text-muted-foreground hover:text-foreground"
                        )}
                        title={isFullscreen ? t('canvas.restoreTooltip', 'Restaurar tamaño normal (Esc)') : t('canvas.fullscreen', 'Pantalla completa / Expandir')}
                    >
                        {isFullscreen ? (
                            <>
                                <Minimize2 className="h-3.5 w-3.5" />
                                <span className="hidden xs:inline sm:inline">{t('canvas.restore', 'Restaurar')}</span>
                            </>
                        ) : (
                            <Maximize2 className="h-4 w-4" />
                        )}
                    </Button>

                    {/* Close Canvas */}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        title={t('canvas.close', 'Cerrar lienzo')}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Quick Refinement Pills with AI */}
            {onAskAiRefinement && (
                <div className="px-4 py-2 border-b bg-muted/20 flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase flex items-center gap-1 shrink-0">
                        <Sparkles className="h-3 w-3 text-primary" /> {t('canvas.improveWithAI', 'Mejorar:')}
                    </span>
                    {quickRefinements.map((ref, idx) => (
                        <button
                            key={idx}
                            onClick={() => onAskAiRefinement(ref.prompt)}
                            disabled={isAiRefining}
                            className="text-[11px] px-2 py-0.5 rounded-full border bg-background hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all shrink-0 cursor-pointer disabled:opacity-50"
                        >
                            {ref.label}
                        </button>
                    ))}
                </div>
            )}

            {/* Canvas Body (Editor or Markdown Preview + Optional Chart) */}
            <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 lg:p-6 bg-card/20 space-y-4">
                {isEditing ? (
                    <Textarea
                        value={document.content}
                        onChange={(e) => onUpdateContent(e.target.value)}
                        placeholder={t('canvas.placeholder', 'Escribe o edita el documento aquí...')}
                        className="w-full h-full min-h-[420px] font-mono text-xs leading-relaxed bg-background resize-none p-4 rounded-xl border-border/80 focus-visible:ring-primary"
                    />
                ) : (
                    <>
                        {document.chartConfig && (
                            <div className="bg-card p-4 sm:p-5 rounded-2xl border shadow-xs">
                                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                    <Sparkles className="h-3.5 w-3.5 text-primary" /> {t('canvas.reportChart', 'Gráfico del Informe')}
                                </div>
                                <ChatChartWidget config={document.chartConfig} />
                            </div>
                        )}
                        <div className="bg-card p-4 sm:p-6 rounded-2xl border shadow-xs overflow-x-auto">
                            <MarkdownRenderer content={document.content} />
                        </div>
                    </>
                )}
            </div>

            {/* Bottom Status Bar */}
            <div className="p-2.5 px-4 border-t bg-muted/30 flex items-center justify-between text-[11px] text-muted-foreground shrink-0">
                <span>{t('canvas.characters', 'Caracteres:')} <strong>{document.content.length.toLocaleString()}</strong> • {t('canvas.words', 'Palabras:')} <strong>{document.content.trim().split(/\s+/).filter(Boolean).length}</strong></span>
                <span className="text-[10px] opacity-70">{t('canvas.instantUpdate', 'Los cambios se reflejan al instante')}</span>
            </div>
        </div>
    );
}
