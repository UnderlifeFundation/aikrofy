'use client';

import React, { useState } from 'react';
import QRCodeStyling, { DotType, CornerSquareType, CornerDotType } from 'qr-code-styling';
import { QRPreviewVisual, VisualConfig } from './QRPreviewVisual';
import { 
    Download, 
    Sparkles, 
    Globe, 
    MessageCircle, 
    Send, 
    FileText, 
    Code, 
    Check,
    RefreshCw
} from 'lucide-react';

export interface CampaignQRItem {
    id: string;
    company_id: number;
    campaign_id?: number | null;
    campaign_name?: string | null;
    name: string;
    slug: string;
    short_url: string;
    target_type: string;
    target_destination: string;
    fallback_destination?: string | null;
    intended_channel: string;
    visual_config: VisualConfig;
    is_dynamic: boolean;
    is_active: boolean;
    total_scans: number;
    unique_scans: number;
    last_scanned_at?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface QRFormPayload {
    name: string;
    target_type: string;
    target_destination: string;
    fallback_destination?: string;
    campaign_id?: number;
    intended_channel: string;
    visual_config: VisualConfig;
}

interface QRBuilderModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: QRFormPayload) => Promise<void>;
    initialData?: CampaignQRItem | null;
    campaigns?: Array<{ id: number; name: string }>;
}

export const QRBuilderModal: React.FC<QRBuilderModalProps> = ({
    isOpen,
    onClose,
    onSave,
    initialData,
    campaigns = [],
}) => {
    const [name, setName] = useState(initialData?.name || '');
    const [targetType, setTargetType] = useState(initialData?.target_type || 'url');
    const [targetDestination, setTargetDestination] = useState(initialData?.target_destination || '');
    const [fallbackDestination, setFallbackDestination] = useState(initialData?.fallback_destination || '');
    const [campaignId, setCampaignId] = useState<string>(initialData?.campaign_id ? String(initialData.campaign_id) : '');
    const [intendedChannel, setIntendedChannel] = useState(initialData?.intended_channel || 'omnichannel');
    const [saving, setSaving] = useState(false);
    const [copied, setCopied] = useState(false);

    // Styling State
    const [visualConfig, setVisualConfig] = useState<VisualConfig>(initialData?.visual_config || {
        dotsType: 'rounded',
        dotsColor: '#2563eb',
        cornerSquareType: 'extra-rounded',
        cornerSquareColor: '#1d4ed8',
        cornerDotType: 'dot',
        cornerDotColor: '#1d4ed8',
        backgroundColor: '#ffffff',
        logoUrl: '',
    });

    if (!isOpen) return null;

    const previewUrl = initialData?.short_url || (targetDestination ? targetDestination : 'https://aikrofy.com');

    const handleDownload = (format: 'png' | 'svg' | 'jpeg') => {
        const qrCode = new QRCodeStyling({
            width: 1024,
            height: 1024,
            data: previewUrl,
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
        });
        qrCode.download({ name: `${name || 'aikrofy-qr'}-hd`, extension: format });
    };

    const handleCopyEmbed = () => {
        const embedCode = `<div id="aikrofy-qr-${initialData?.slug || 'embed'}" data-slug="${initialData?.slug || ''}"><img src="${previewUrl}" alt="${name}" style="max-width: 250px; height: auto;" /></div>`;
        navigator.clipboard.writeText(embedCode);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            await onSave({
                name,
                target_type: targetType,
                target_destination: targetDestination,
                fallback_destination: fallbackDestination || undefined,
                campaign_id: campaignId ? Number(campaignId) : undefined,
                intended_channel: intendedChannel,
                visual_config: visualConfig,
            });
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
            <div className="relative w-full max-w-4xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-8">
                
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-blue-600/10 text-blue-600 rounded-xl">
                            <Sparkles className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                                {initialData ? 'Editar Código QR Perpetuo' : 'Generador de Código QR Perpetuo'}
                            </h2>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Totalmente dinámico: El diseño impreso jamás expira ni cambia aunque actualices el destino.
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-xl font-semibold">
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-6 p-6">
                    
                    {/* Left: Configuration Form (7 cols) */}
                    <div className="md:col-span-7 space-y-4 max-h-[70vh] overflow-y-auto pr-2">
                        
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                                Nombre de Referencia
                            </label>
                            <input 
                                type="text"
                                required
                                placeholder="Ej. Volante Verano WhatsApp, Menú Mesa 4..."
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>

                        {/* Resource Type */}
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                Tipo de Destino
                            </label>
                            <div className="grid grid-cols-3 gap-2">
                                {[
                                    { id: 'url', label: 'Sitio Web', icon: Globe },
                                    { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle },
                                    { id: 'telegram', label: 'Telegram', icon: Send },
                                    { id: 'form', label: 'Formulario', icon: FileText },
                                    { id: 'file', label: 'Descarga Archivo', icon: Download },
                                    { id: 'landing_page', label: 'Landing IA', icon: Sparkles },
                                ].map((item) => {
                                    const Icon = item.icon;
                                    return (
                                        <button
                                            key={item.id}
                                            type="button"
                                            onClick={() => setTargetType(item.id)}
                                            className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs font-medium transition-all ${
                                                targetType === item.id 
                                                ? 'border-blue-600 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 shadow-xs' 
                                                : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400'
                                            }`}
                                        >
                                            <Icon className="w-4 h-4" />
                                            {item.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Destination */}
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                                {targetType === 'whatsapp' ? 'Número o enlace directo WhatsApp (wa.me)' : 'URL o Enlace de Destino'}
                            </label>
                            <input 
                                type="text"
                                required
                                placeholder={targetType === 'whatsapp' ? 'https://wa.me/521...?text=Hola' : 'https://tusitio.com/oferta'}
                                value={targetDestination}
                                onChange={(e) => setTargetDestination(e.target.value)}
                                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono"
                            />
                        </div>

                        {/* Fallback Destination */}
                        <div>
                            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                                Destino de Contingencia (Fallback si campaña vence)
                            </label>
                            <input 
                                type="text"
                                placeholder="https://aikrofy.com"
                                value={fallbackDestination}
                                onChange={(e) => setFallbackDestination(e.target.value)}
                                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono"
                            />
                        </div>

                        {/* Campaign Association & Channel */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                                    Vincular a Campaña
                                </label>
                                <select
                                    value={campaignId}
                                    onChange={(e) => setCampaignId(e.target.value)}
                                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    <option value="">Sin campaña (Independiente)</option>
                                    {campaigns.map((c) => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                                    Canal de Distribución
                                </label>
                                <select
                                    value={intendedChannel}
                                    onChange={(e) => setIntendedChannel(e.target.value)}
                                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    <option value="omnichannel">Omnicanal (Universal)</option>
                                    <option value="print">Impresos (Cartelería / Flyers)</option>
                                    <option value="whatsapp">Mensajería WhatsApp</option>
                                    <option value="telegram">Telegram</option>
                                    <option value="email">Correo Electrónico</option>
                                    <option value="web_embed">Incrustado en Web</option>
                                </select>
                            </div>
                        </div>

                        {/* Visual Customization */}
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
                            <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                                Personalización Visual (Estilo de Marca)
                            </h3>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-[11px] font-medium text-slate-500">Color Primario (Puntos)</label>
                                    <div className="flex items-center gap-2 mt-1">
                                        <input 
                                            type="color" 
                                            value={visualConfig.dotsColor || '#2563eb'}
                                            onChange={(e) => setVisualConfig({ ...visualConfig, dotsColor: e.target.value, cornerSquareColor: e.target.value, cornerDotColor: e.target.value })}
                                            className="w-8 h-8 rounded-lg cursor-pointer border-0 p-0"
                                        />
                                        <span className="text-xs font-mono">{visualConfig.dotsColor || '#2563eb'}</span>
                                    </div>
                                </div>

                                <div>
                                    <label className="text-[11px] font-medium text-slate-500">Forma de Puntos</label>
                                    <select
                                        value={visualConfig.dotsType || 'rounded'}
                                        onChange={(e) => setVisualConfig({ ...visualConfig, dotsType: e.target.value as DotType })}
                                        className="w-full mt-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                                    >
                                        <option value="rounded">Redondeados</option>
                                        <option value="dots">Puntos Circulares</option>
                                        <option value="classy">Elegante (Classy)</option>
                                        <option value="classy-rounded">Elegante Redondeado</option>
                                        <option value="square">Cuadrado Clásico</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="text-[11px] font-medium text-slate-500">URL de Logo en el Centro (Opcional)</label>
                                <input 
                                    type="text" 
                                    placeholder="https://tudominio.com/logo.png"
                                    value={visualConfig.logoUrl || ''}
                                    onChange={(e) => setVisualConfig({ ...visualConfig, logoUrl: e.target.value })}
                                    className="w-full mt-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                                />
                            </div>
                        </div>

                    </div>

                    {/* Right: Live Preview & Export Hub (5 cols) */}
                    <div className="md:col-span-5 flex flex-col items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
                        <div className="w-full text-center space-y-3">
                            <span className="inline-block px-3 py-1 bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300 text-[11px] font-semibold rounded-full border border-green-200 dark:border-green-800">
                                ● Inmortal / Sin Expiración
                            </span>
                            
                            <QRPreviewVisual 
                                value={previewUrl}
                                visualConfig={visualConfig}
                                size={220}
                                className="mx-auto"
                            />

                            <p className="text-xs font-mono text-slate-500 truncate max-w-[240px] mx-auto">
                                {previewUrl}
                            </p>
                        </div>

                        {/* Export & Channel Actions */}
                        <div className="w-full space-y-2 mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
                            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider text-center">
                                Descargas de Alta Definición
                            </label>
                            
                            <div className="grid grid-cols-3 gap-2">
                                <button
                                    type="button"
                                    onClick={() => handleDownload('png')}
                                    className="px-2 py-1.5 text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-100 flex items-center justify-center gap-1"
                                >
                                    <Download className="w-3.5 h-3.5" /> PNG
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleDownload('svg')}
                                    className="px-2 py-1.5 text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-100 flex items-center justify-center gap-1"
                                    title="Formato vectorial para imprenta a gran escala"
                                >
                                    <Download className="w-3.5 h-3.5" /> SVG
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCopyEmbed}
                                    className="px-2 py-1.5 text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-100 flex items-center justify-center gap-1"
                                >
                                    {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Code className="w-3.5 h-3.5" />} Web
                                </button>
                            </div>

                            <button
                                type="submit"
                                disabled={saving}
                                className="w-full mt-3 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
                            >
                                {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                {initialData ? 'Guardar Cambios' : 'Crear Código QR'}
                            </button>
                        </div>
                    </div>

                </form>

            </div>
        </div>
    );
};
