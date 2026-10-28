'use client';

import React from 'react';
import { User, Phone, Mail, Award, TrendingUp, Calendar, ExternalLink, ShieldCheck, Sparkles, Tag, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChannelBadge } from './ChannelBadge';
import { Conversation } from '@/types';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

interface ContactProfileSidebarProps {
    conversation: Conversation | null;
    onOpenCrmDrawer?: (customerId: number) => void;
}

export function ContactProfileSidebar({ conversation, onOpenCrmDrawer }: ContactProfileSidebarProps) {
    const { t } = useTranslation();

    if (!conversation) {
        return (
            <div className="hidden lg:flex flex-col items-center justify-center h-full border-l p-6 text-center text-muted-foreground bg-card/40">
                <p className="text-xs">
                    {t('omnichannelChat.selectConversationDesc', 'Selecciona una conversación para ver los detalles del contacto.')}
                </p>
            </div>
        );
    }

    const contactName = conversation.contact_name || t('common.unknown', 'Sin nombre registrado');
    const isAiPaused = conversation.conv_metadata?.is_ai_active === false;

    let startedDate = 'N/A';
    if (conversation.started_at) {
        try {
            const d = new Date(conversation.started_at);
            if (!isNaN(d.getTime())) {
                startedDate = format(d, "dd MMM yyyy, HH:mm", { locale: es });
            } else {
                startedDate = conversation.started_at;
            }
        } catch {
            startedDate = conversation.started_at;
        }
    }

    return (
        <div className="hidden lg:flex flex-col h-full min-h-0 border-l bg-card/40 w-80 shrink-0 overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between shrink-0">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t('omnichannelChat.contactDetails', 'Ficha del Contacto (360°)')}
                </h3>
                {conversation.customer_id && onOpenCrmDrawer && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onOpenCrmDrawer(conversation.customer_id!)}
                        className="h-7 text-xs gap-1 text-primary hover:text-primary cursor-pointer"
                    >
                        <span>{t('omnichannelChat.openCrm', 'Ver en CRM')}</span>
                        <ExternalLink className="h-3 w-3" />
                    </Button>
                )}
            </div>

            <div className="flex-1 min-h-0 overflow-hidden">
                <ScrollArea className="h-full w-full p-4 space-y-4">
                {/* Main Avatar & Identity */}
                <div className="flex flex-col items-center text-center space-y-2 py-2">
                    <div className="h-16 w-16 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xl border-2 border-primary/20">
                        {contactName.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h4 className="font-semibold text-sm text-foreground">{contactName}</h4>
                        <div className="flex items-center justify-center gap-1.5 mt-1">
                            <Badge variant="outline" className="text-[11px] capitalize">
                                {conversation.type || 'Cliente'}
                            </Badge>
                            <ChannelBadge channel={conversation.channel} size="sm" />
                        </div>
                    </div>
                </div>

                <Separator />

                {/* Direct Contact Info */}
                <div className="space-y-2.5">
                    <h5 className="text-[11px] font-semibold text-muted-foreground uppercase">
                        {t('omnichannelChat.contactDetails', 'Información de Contacto')}
                    </h5>

                    {conversation.contact_phone && (
                        <div className="flex items-center gap-2 text-xs">
                            <Phone className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                            <span className="truncate">{conversation.contact_phone}</span>
                        </div>
                    )}

                    {conversation.contact_email && (
                        <div className="flex items-center gap-2 text-xs">
                            <Mail className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                            <span className="truncate">{conversation.contact_email}</span>
                        </div>
                    )}

                    <div className="flex items-center gap-2 text-xs">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="text-muted-foreground">
                            {t('omnichannelChat.lastActivity', 'Iniciado')}: {startedDate}
                        </span>
                    </div>
                </div>

                <Separator />

                {/* Scores & Status */}
                <div className="space-y-2.5">
                    <h5 className="text-[11px] font-semibold text-muted-foreground uppercase">
                        {t('sidebar.analytics', 'Métricas')} & {t('common.status', 'Estado')}
                    </h5>

                    <div className="grid grid-cols-2 gap-2">
                        <div className="p-2.5 rounded-lg border bg-background/50 text-center">
                            <span className="text-[10px] text-muted-foreground block">
                                {t('omnichannelChat.leadScore', 'Lead Score')}
                            </span>
                            <span className="text-base font-bold text-foreground">
                                {conversation.lead_score ?? 'N/A'}
                            </span>
                        </div>

                        <div className="p-2.5 rounded-lg border bg-background/50 text-center">
                            <span className="text-[10px] text-muted-foreground block">
                                {t('omnichannelChat.sentiment', 'Sentimiento')}
                            </span>
                            <span className="text-base font-bold text-foreground">
                                {conversation.sentiment_score !== null && conversation.sentiment_score !== undefined
                                    ? conversation.sentiment_score > 0.2
                                        ? `😊 ${t('omnichannelChat.positive', 'Positivo')}`
                                        : conversation.sentiment_score < -0.2
                                        ? `😟 ${t('omnichannelChat.negative', 'Negativo')}`
                                        : `😐 ${t('omnichannelChat.neutral', 'Neutro')}`
                                    : t('omnichannelChat.neutral', 'Neutro')}
                            </span>
                        </div>
                    </div>

                    <div className="p-2.5 rounded-lg border bg-background/50 space-y-1">
                        <span className="text-[10px] text-muted-foreground block">
                            {t('sidebar.agentSetup', 'Control de IA')}
                        </span>
                        <div className="flex items-center gap-1.5 text-xs font-medium">
                            <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
                            <span>
                                {isAiPaused 
                                    ? t('omnichannelChat.aiPaused', 'Pausada (Intervención Agente)') 
                                    : t('omnichannelChat.aiActive', 'Activa (Auto-respuesta)')}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Tags if any */}
                {conversation.tags && conversation.tags.length > 0 && (
                    <>
                        <Separator />
                        <div className="space-y-2">
                            <h5 className="text-[11px] font-semibold text-muted-foreground uppercase flex items-center gap-1">
                                <Tag className="h-3 w-3" /> {t('common.tags', 'Etiquetas')}
                            </h5>
                            <div className="flex flex-wrap gap-1">
                                {conversation.tags.map((tag, idx) => (
                                    <Badge key={idx} variant="secondary" className="text-[10px] px-2 py-0.5">
                                        {tag}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    </>
                )}
                </ScrollArea>
            </div>
        </div>
    );
}
