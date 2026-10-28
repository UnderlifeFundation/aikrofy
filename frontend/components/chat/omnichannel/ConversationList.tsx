'use client';

import React from 'react';
import { Search, RotateCw, CheckCircle2, AlertCircle, Clock, User, Phone, Mail, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChannelBadge } from './ChannelBadge';
import { Conversation } from '@/types';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

interface ConversationListProps {
    conversations: Conversation[];
    selectedId: number | null;
    onSelect: (conv: Conversation) => void;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    activeTab: string;
    onTabChange: (tab: string) => void;
    selectedChannel: string;
    onChannelChange: (channel: string) => void;
    isLoading: boolean;
    onRefresh: () => void;
}

export function ConversationList({
    conversations,
    selectedId,
    onSelect,
    searchTerm,
    onSearchChange,
    activeTab,
    onTabChange,
    selectedChannel,
    onChannelChange,
    isLoading,
    onRefresh,
}: ConversationListProps) {
    const { t } = useTranslation();

    const channels = [
        { key: 'all', label: t('omnichannelChat.channels.all', 'Todos') },
        { key: 'whatsapp', label: t('omnichannelChat.channels.whatsapp', 'WhatsApp') },
        { key: 'telegram', label: t('omnichannelChat.channels.telegram', 'Telegram') },
        { key: 'webchat', label: t('omnichannelChat.channels.webchat', 'Webchat') },
    ];

    return (
        <div className="flex flex-col h-full min-h-0 border-r bg-card/60 overflow-hidden">
            {/* Header & Tabs - Fixed */}
            <div className="p-3 border-b space-y-3 shrink-0">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-sm font-semibold tracking-tight">
                            {t('omnichannelChat.inbox', 'Bandeja de Entrada')}
                        </h2>
                        <p className="text-xs text-muted-foreground">
                            {conversations.length} {conversations.length === 1 ? t('omnichannelChat.conversationCount', 'conversación') : t('omnichannelChat.conversationsCount', 'conversaciones')}
                        </p>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={onRefresh}
                        disabled={isLoading}
                        title={t('omnichannelChat.refresh', 'Actualizar')}
                    >
                        <RotateCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
                    </Button>
                </div>

                {/* Primary Category Tabs */}
                <div className="flex rounded-lg bg-muted/60 p-1 text-xs font-medium overflow-x-auto scrollbar-none">
                    <button
                        onClick={() => onTabChange('all')}
                        className={cn(
                            'flex-1 py-1 px-2 rounded-md transition-all text-center whitespace-nowrap',
                            activeTab === 'all'
                                ? 'bg-background text-foreground shadow-xs font-semibold'
                                : 'text-muted-foreground hover:text-foreground'
                        )}
                    >
                        {t('omnichannelChat.all', 'Todos')}
                    </button>
                    <button
                        onClick={() => onTabChange('handover')}
                        className={cn(
                            'flex-1 py-1 px-2 rounded-md transition-all text-center whitespace-nowrap flex items-center justify-center gap-1',
                            activeTab === 'handover'
                                ? 'bg-amber-500 text-white shadow-xs font-semibold'
                                : 'text-amber-600 dark:text-amber-400 hover:text-foreground'
                        )}
                    >
                        <AlertCircle className="h-3 w-3" />
                        {t('omnichannelChat.handoverTab', 'Por Atender')}
                    </button>
                    <button
                        onClick={() => onTabChange('customer')}
                        className={cn(
                            'flex-1 py-1 px-2 rounded-md transition-all text-center whitespace-nowrap',
                            activeTab === 'customer'
                                ? 'bg-background text-foreground shadow-xs font-semibold'
                                : 'text-muted-foreground hover:text-foreground'
                        )}
                    >
                        {t('omnichannelChat.customers', 'Clientes')}
                    </button>
                    <button
                        onClick={() => onTabChange('resolved')}
                        className={cn(
                            'flex-1 py-1 px-2 rounded-md transition-all text-center whitespace-nowrap',
                            activeTab === 'resolved'
                                ? 'bg-background text-foreground shadow-xs font-semibold'
                                : 'text-muted-foreground hover:text-foreground'
                        )}
                    >
                        {t('omnichannelChat.resolved', 'Resueltos')}
                    </button>
                </div>

                {/* Search Bar */}
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                        type="text"
                        placeholder={t('omnichannelChat.searchPlaceholder', 'Buscar por contacto o teléfono...')}
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="pl-8 h-8 text-xs bg-background/80"
                    />
                </div>

                {/* Channel Filter Chips */}
                <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                    {channels.map((ch) => (
                        <button
                            key={ch.key}
                            onClick={() => onChannelChange(ch.key)}
                            className={cn(
                                'text-[11px] px-2 py-0.5 rounded-full border transition-all shrink-0 cursor-pointer',
                                selectedChannel === ch.key
                                    ? 'bg-primary text-primary-foreground border-primary font-medium shadow-xs'
                                    : 'bg-background text-muted-foreground border-border/80 hover:bg-muted'
                            )}
                        >
                            {ch.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Conversation List - Scrollable */}
            <div className="flex-1 min-h-0 overflow-hidden">
                <ScrollArea className="h-full w-full">
                {conversations.length === 0 ? (
                    <div className="p-8 text-center space-y-2">
                        <AlertCircle className="h-8 w-8 text-muted-foreground/40 mx-auto" />
                        <p className="text-xs font-medium text-muted-foreground">
                            {t('omnichannelChat.noConversations', 'No hay conversaciones')}
                        </p>
                        <p className="text-[11px] text-muted-foreground/70">
                            {t('omnichannelChat.noConversationsDesc', 'Los mensajes de clientes o empleados aparecerán aquí automáticamente.')}
                        </p>
                    </div>
                ) : (
                    <div className="divide-y divide-border/40">
                        {conversations.map((conv) => {
                            const isSelected = selectedId === conv.id;
                            const contactDisplay =
                                conv.contact_name ||
                                conv.contact_phone ||
                                conv.contact_email ||
                                `Conversación #${conv.id}`;

                            let relativeTime = '';
                            if (conv.last_message_at) {
                                try {
                                    const d = new Date(conv.last_message_at);
                                    if (!isNaN(d.getTime())) {
                                        relativeTime = formatDistanceToNow(d, {
                                            addSuffix: false,
                                            locale: es,
                                        });
                                    }
                                } catch {
                                    relativeTime = '';
                                }
                            }

                            const isAiPaused = conv.conv_metadata?.is_ai_active === false;

                            return (
                                <div
                                    key={conv.id}
                                    onClick={() => onSelect(conv)}
                                    className={cn(
                                        'p-3 transition-colors cursor-pointer text-left relative flex flex-col gap-1.5 hover:bg-muted/40',
                                        isSelected && 'bg-muted/80 border-l-2 border-l-primary font-normal'
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <div className="h-7 w-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-semibold shrink-0">
                                                {contactDisplay.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="min-w-0">
                                                <p className="text-xs font-semibold truncate text-foreground">
                                                    {contactDisplay}
                                                </p>
                                                {conv.contact_phone && conv.contact_name && (
                                                    <p className="text-[10px] text-muted-foreground truncate">
                                                        {conv.contact_phone}
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex flex-col items-end shrink-0 gap-1">
                                            <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                                                {relativeTime}
                                            </span>
                                            <ChannelBadge channel={conv.channel} size="sm" showLabel={false} />
                                        </div>
                                    </div>

                                    {/* Sub-row: Badges & Status */}
                                    <div className="flex items-center justify-between gap-1 pt-0.5">
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            {conv.is_resolved ? (
                                                <Badge
                                                    variant="outline"
                                                    className="text-[10px] px-1.5 py-0 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5"
                                                >
                                                    <CheckCircle2 className="h-2.5 w-2.5 mr-1" />
                                                    {t('omnichannelChat.resolved', 'Resuelto')}
                                                </Badge>
                                            ) : (conv.handover_status === 'human_taken' || isAiPaused) ? (
                                                <Badge
                                                    variant="outline"
                                                    className="text-[10px] px-1.5 py-0 border-amber-500/40 text-amber-600 dark:text-amber-400 bg-amber-500/10 font-medium"
                                                >
                                                    <AlertCircle className="h-2.5 w-2.5 mr-1" />
                                                    {t('omnichannelChat.humanAgent', 'Operador Humano')}
                                                </Badge>
                                            ) : (
                                                <Badge
                                                    variant="outline"
                                                    className="text-[10px] px-1.5 py-0 border-indigo-500/30 text-indigo-600 dark:text-indigo-400 bg-indigo-500/5"
                                                >
                                                    {t('omnichannelChat.aiActive', 'IA Activa')}
                                                </Badge>
                                            )}

                                            {conv.type && conv.type !== 'customer' && (
                                                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                                    {conv.type}
                                                </Badge>
                                            )}
                                        </div>

                                        {conv.message_count !== undefined && conv.message_count > 0 && (
                                            <span className="text-[10px] text-muted-foreground">
                                                {conv.message_count} msgs
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
                </ScrollArea>
            </div>
        </div>
    );
}
