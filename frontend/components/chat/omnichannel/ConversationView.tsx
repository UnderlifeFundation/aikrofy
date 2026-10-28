'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Send, Bot, User, Check, CheckCheck, Loader2, CheckCircle2, RotateCcw, AlertCircle, Phone, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChannelBadge } from './ChannelBadge';
import { Conversation, Message } from '@/types';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

interface ConversationViewProps {
    conversation: Conversation | null;
    messages: Message[];
    isLoadingMessages: boolean;
    onSendMessage: (content: string, pauseAi: boolean) => Promise<void>;
    isSending: boolean;
    onToggleResolved: () => void;
    isUpdatingStatus: boolean;
    onToggleAi: () => void;
    onBack?: () => void;
}

export function ConversationView({
    conversation,
    messages,
    isLoadingMessages,
    onSendMessage,
    isSending,
    onToggleResolved,
    isUpdatingStatus,
    onToggleAi,
    onBack,
}: ConversationViewProps) {
    const { t } = useTranslation();
    const [replyText, setReplyText] = useState('');
    const [pauseAi, setPauseAi] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto scroll to bottom when new messages arrive
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoadingMessages]);

    if (!conversation) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-background/50">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
                    <Bot className="h-6 w-6 text-muted-foreground" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">
                    {t('omnichannelChat.selectConversation', 'Ninguna conversación seleccionada')}
                </h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                    {t('omnichannelChat.selectConversationDesc', 'Selecciona una conversación de la lista para ver el historial y responder directamente al canal del contacto.')}
                </p>
            </div>
        );
    }

    const contactTitle =
        conversation.contact_name ||
        conversation.contact_phone ||
        conversation.contact_email ||
        `Conversación #${conversation.id}`;

    const isAiPaused = conversation.conv_metadata?.is_ai_active === false;

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyText.trim() || isSending) return;
        const text = replyText;
        setReplyText('');
        try {
            await onSendMessage(text, pauseAi);
        } catch {
            setReplyText(text);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend(e);
        }
    };

    return (
        <div className="flex flex-col h-full min-h-0 bg-background overflow-hidden">
            {/* Conversation Header - Fixed */}
            <div className="px-4 py-3 border-b flex items-center justify-between gap-3 bg-card/40 shrink-0">
                <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                    {onBack && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={onBack}
                            className="h-8 w-8 shrink-0 md:hidden text-muted-foreground hover:text-foreground"
                            title="Volver a la lista de conversaciones"
                        >
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                    )}
                    <div className="h-9 w-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm shrink-0">
                        {contactTitle.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                        <div className="flex items-center gap-2">
                            <h2 className="text-sm font-semibold truncate text-foreground">{contactTitle}</h2>
                            <ChannelBadge channel={conversation.channel} size="sm" />
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            {conversation.contact_phone && <span>{conversation.contact_phone}</span>}
                            {conversation.contact_email && <span>• {conversation.contact_email}</span>}
                        </div>
                    </div>
                </div>

                {/* Header Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                    <Button
                        variant={isAiPaused ? 'outline' : 'secondary'}
                        size="sm"
                        onClick={onToggleAi}
                        disabled={isUpdatingStatus}
                        className={cn(
                            'text-xs h-8 gap-1.5',
                            isAiPaused
                                ? 'border-amber-500/40 text-amber-600 dark:text-amber-400 bg-amber-500/10'
                                : 'text-indigo-600 dark:text-indigo-400 bg-indigo-500/10'
                        )}
                        title={isAiPaused ? t('omnichannelChat.aiPaused', 'IA Pausada') : t('omnichannelChat.aiActive', 'IA Activa')}
                    >
                        <Sparkles className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline">
                            {isAiPaused ? t('omnichannelChat.aiPaused', 'IA Pausada') : t('omnichannelChat.aiActive', 'IA Activa')}
                        </span>
                        <span className="sm:hidden">{isAiPaused ? 'IA Off' : 'IA On'}</span>
                    </Button>

                    <Button
                        variant={conversation.is_resolved ? 'outline' : 'default'}
                        size="sm"
                        onClick={onToggleResolved}
                        disabled={isUpdatingStatus}
                        className="text-xs h-8 gap-1.5"
                    >
                        {conversation.is_resolved ? (
                            <>
                                <RotateCcw className="h-3.5 w-3.5" />
                                <span className="hidden sm:inline">{t('omnichannelChat.markOpen', 'Reabrir')}</span>
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="h-3.5 w-3.5" />
                                <span className="hidden sm:inline">{t('omnichannelChat.markResolved', 'Resolver')}</span>
                            </>
                        )}
                    </Button>
                </div>
            </div>

            {/* Handover Alert Banner (Enterprise 10X) */}
            {(conversation.handover_status === 'human_taken' || isAiPaused) && (
                <div className="px-4 py-2.5 bg-amber-500/10 border-b border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shrink-0">
                    <div className="flex items-start gap-2 min-w-0">
                        <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                        <div className="text-xs">
                            <p className="font-semibold text-amber-700 dark:text-amber-300">
                                {t('omnichannelChat.handoverActiveTitle', 'Conversación en Control Humano (IA en Pausa Preventiva)')}
                            </p>
                            {conversation.handover_summary ? (
                                <p className="text-amber-600/90 dark:text-amber-400/90 whitespace-pre-line mt-0.5 font-mono text-[11px]">
                                    {conversation.handover_summary}
                                </p>
                            ) : (
                                <p className="text-amber-600/80 dark:text-amber-400/80 mt-0.5">
                                    {t('omnichannelChat.handoverActiveDesc', 'Tus respuestas se enviarán directamente al cliente. La IA no responderá automáticamente.')}
                                </p>
                            )}
                        </div>
                    </div>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={onToggleAi}
                        className="h-7 text-xs border-amber-500/40 text-amber-700 dark:text-amber-300 bg-background/80 hover:bg-amber-500/20 shrink-0"
                    >
                        <Sparkles className="h-3 w-3 mr-1" />
                        {t('omnichannelChat.returnToAi', 'Devolver a IA')}
                    </Button>
                </div>
            )}
            <div className="flex-1 min-h-0 overflow-hidden relative">
                <ScrollArea className="h-full w-full">
                {isLoadingMessages ? (
                    <div className="flex flex-col items-center justify-center h-48 space-y-2">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">{t('omnichannelChat.loadingMessages', 'Cargando mensajes...')}</p>
                    </div>
                ) : messages.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground space-y-1">
                        <p className="text-xs font-medium">{t('omnichannelChat.noMessages', 'No hay mensajes registrados')}</p>
                        <p className="text-[11px]">{t('omnichannelChat.typeBelowToStart', 'Escribe abajo para iniciar o responder.')}</p>
                    </div>
                ) : (
                    <div className="space-y-3 max-w-3xl mx-auto p-4 sm:p-5 pr-5 sm:pr-6">
                        {messages.map((msg, idx) => {
                            const isUser = msg.role === 'user';
                            const isAssistant = msg.role === 'assistant';
                            const isSystem = msg.role === 'system';

                            let timeStr = '';
                            if (msg.created_at) {
                                try {
                                    const d = new Date(msg.created_at);
                                    if (!isNaN(d.getTime())) {
                                        timeStr = format(d, 'HH:mm', { locale: es });
                                    }
                                } catch {
                                    timeStr = '';
                                }
                            }

                            if (isSystem) {
                                return (
                                    <div key={msg.id || idx} className="text-center my-2">
                                        <span className="text-[11px] bg-muted/60 text-muted-foreground px-2.5 py-1 rounded-full border">
                                            {msg.content}
                                        </span>
                                    </div>
                                );
                            }

                            return (
                                <div
                                    key={msg.id || idx}
                                    className={cn('w-full flex', isUser ? 'justify-start' : 'justify-end')}
                                >
                                    <div className={cn(
                                        'flex items-end gap-2 max-w-[85%] sm:max-w-[75%]',
                                        isUser ? 'flex-row' : 'flex-row-reverse'
                                    )}>
                                        {isUser ? (
                                            <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center text-[10px] font-semibold text-muted-foreground shrink-0 mb-1">
                                                <User className="h-3 w-3" />
                                            </div>
                                        ) : (
                                            <div className="h-6 w-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-semibold shrink-0 mb-1">
                                                <Bot className="h-3 w-3" />
                                            </div>
                                        )}

                                        <div
                                            className={cn(
                                                'rounded-2xl px-3.5 py-2 text-xs leading-relaxed shadow-xs relative min-w-0 break-words',
                                                isUser
                                                    ? 'bg-muted text-foreground rounded-bl-xs'
                                                    : 'bg-primary text-primary-foreground rounded-br-xs'
                                            )}
                                        >
                                            <div className="whitespace-pre-wrap break-words">{msg.content}</div>

                                            {/* Media / Attachment if present */}
                                            {msg.media_url && (
                                                <div className="mt-2 pt-2 border-t border-current/10">
                                                    <a
                                                        href={msg.media_url}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                        className="underline text-[11px] font-medium"
                                                    >
                                                        {t('omnichannelChat.viewAttachment', 'Ver archivo adjunto')}
                                                    </a>
                                                </div>
                                            )}

                                            <div
                                                className={cn(
                                                    'flex items-center justify-end gap-1 text-[9px] mt-1 opacity-70',
                                                    isUser ? 'text-muted-foreground' : 'text-primary-foreground'
                                                )}
                                            >
                                                <span>{timeStr}</span>
                                                {!isUser && <CheckCheck className="h-2.5 w-2.5" />}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                        <div ref={messagesEndRef} />
                    </div>
                )}
                </ScrollArea>
            </div>

            {/* Composer Footer - Fixed at bottom */}
            <div className="p-3 border-t bg-card/60 space-y-2 shrink-0">
                <div className="flex items-center justify-between text-xs px-1">
                    <div className="flex items-center gap-2">
                        <Switch
                            id="pause-ai"
                            checked={pauseAi}
                            onCheckedChange={setPauseAi}
                            className="scale-75"
                        />
                        <Label htmlFor="pause-ai" className="text-[11px] cursor-pointer text-muted-foreground">
                            {t('omnichannelChat.pauseAi', 'Pausar IA al responder (control manual del agente)')}
                        </Label>
                    </div>

                    <span className="text-[11px] text-muted-foreground">
                        {t('omnichannelChat.channel', 'Canal')}: <strong className="capitalize">{conversation.channel}</strong>
                    </span>
                </div>

                <form onSubmit={handleSend} className="flex gap-2 items-end">
                    <Textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={t('omnichannelChat.replyPrompt', {
                            name: contactTitle,
                            channel: conversation.channel,
                            defaultValue: `Responder a ${contactTitle} por ${conversation.channel}... (Enter para enviar)`
                        })}
                        className="min-h-[44px] max-h-32 text-xs resize-none bg-background flex-1"
                        disabled={isSending}
                    />

                    <Button
                        type="submit"
                        size="default"
                        disabled={isSending || !replyText.trim()}
                        className="h-[44px] px-4 shrink-0 gap-1.5"
                    >
                        {isSending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <>
                                <Send className="h-4 w-4" />
                                <span className="hidden sm:inline text-xs">{t('omnichannelChat.sendBtn', 'Enviar')}</span>
                            </>
                        )}
                    </Button>
                </form>
            </div>
        </div>
    );
}
