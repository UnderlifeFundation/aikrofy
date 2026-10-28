'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Bot, User, Loader2, Trash2, Sparkles, Plus, MessageSquare, Mic, Square, Volume2, VolumeX } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { useTranslation } from 'react-i18next';

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    audioUrl?: string;
}

interface ConversationSession {
    id: string;
    title: string;
    messages: ChatMessage[];
    updatedAt: Date;
}

export default function PlaygroundPage() {
    const { t } = useTranslation();
    const [sessions, setSessions] = useState<ConversationSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [input, setInput] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessingVoice, setIsProcessingVoice] = useState(false);
    const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
    const [autoPlayVoice, setAutoPlayVoice] = useState<boolean>(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('auto_play_voice') === 'true';
        }
        return false;
    });

    // Save autoPlayVoice state to localStorage
    useEffect(() => {
        localStorage.setItem('auto_play_voice', String(autoPlayVoice));
    }, [autoPlayVoice]);

    // Parse agentId from query params on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            const agentId = params.get('agentId');
            if (agentId) {
                setSelectedAgentId(agentId);
            }
        }
    }, []);

    // Fetch Agents for selector
    const { data: agents } = useQuery({
        queryKey: ['playground-agents'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ agents: any[] }>('/agents/');
            return data.agents;
        }
    });

    // Clear messages when selected agent changes to prevent mixing test contexts
    useEffect(() => {
        if (activeSessionId) {
            setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: [] } : s));
        }
    }, [selectedAgentId]);
    
    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    // Load sessions from localStorage on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const stored = localStorage.getItem('playground_sessions');
            if (stored) {
                try {
                    const parsed = JSON.parse(stored) as ConversationSession[];
                    const formatted = parsed.map(s => ({
                        ...s,
                        updatedAt: new Date(s.updatedAt),
                        messages: s.messages.map(m => ({
                            ...m,
                            timestamp: new Date(m.timestamp)
                        }))
                    }));
                    setSessions(formatted);
                    if (formatted.length > 0) {
                        setActiveSessionId(formatted[0].id);
                    } else {
                        createNewSession();
                    }
                } catch (e) {
                    console.error("Failed to parse sessions", e);
                    createNewSession();
                }
            } else {
                createNewSession();
            }
        }
    }, []);

    // Save sessions to localStorage when updated
    useEffect(() => {
        if (sessions.length > 0) {
            localStorage.setItem('playground_sessions', JSON.stringify(sessions));
        } else {
            localStorage.removeItem('playground_sessions');
        }
    }, [sessions]);

    // Active session and messages
    const activeSession = sessions.find(s => s.id === activeSessionId);
    const messages = activeSession ? activeSession.messages : [];

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const createNewSession = () => {
        const newId = `session-${Date.now()}`;
        const newSession: ConversationSession = {
            id: newId,
            title: `Nueva conversación ${sessions.length + 1}`,
            messages: [],
            updatedAt: new Date(),
        };
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newId);
        return newSession;
    };

    const deleteSession = (sessionId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        const updated = sessions.filter(s => s.id !== sessionId);
        setSessions(updated);
        
        if (activeSessionId === sessionId) {
            if (updated.length > 0) {
                setActiveSessionId(updated[0].id);
            } else {
                const newS: ConversationSession = {
                    id: `session-${Date.now()}`,
                    title: `Nueva conversación 1`,
                    messages: [],
                    updatedAt: new Date(),
                };
                setSessions([newS]);
                setActiveSessionId(newS.id);
            }
        }
        toast.success("Conversación eliminada.");
    };

    const clearAllSessions = () => {
        const newS: ConversationSession = {
            id: `session-${Date.now()}`,
            title: `Nueva conversación 1`,
            messages: [],
            updatedAt: new Date(),
        };
        setSessions([newS]);
        setActiveSessionId(newS.id);
        toast.success("Historial vaciado.");
    };

    const chatMutation = useMutation({
        mutationFn: async ({ userMessage, history }: { userMessage: string, history: ChatMessage[] }) => {
            const chatMessages = history.map((m) => ({ role: m.role, content: m.content }));

            const { data } = await apiClient.post('/agents/chat', {
                messages: chatMessages,
                user: 'playground_user',
                agent_id: selectedAgentId ? Number(selectedAgentId) : undefined
            });
            return data;
        },
        onSuccess: (data) => {
            const assistantContent =
                data?.choices?.[0]?.message?.content ||
                data?.data?.content ||
                data?.content ||
                t('playground.noResponse', { defaultValue: 'No response received.' });

            const assistantMsg: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: assistantContent,
                timestamp: new Date(),
            };

            setSessions(prev => prev.map(s => {
                if (s.id === activeSessionId) {
                    return {
                        ...s,
                        messages: [...s.messages, assistantMsg],
                        updatedAt: new Date()
                    };
                }
                return s;
            }));

            if (autoPlayVoice) {
                handlePlayTTS(assistantMsg);
            }
        },
        onError: (error: unknown) => {
            const message =
                (error as { response?: { data?: { error?: { message?: string }; error_message?: string } } })
                    ?.response?.data?.error?.message ||
                (error as { response?: { data?: { error_message?: string } } })?.response?.data?.error_message ||
                t('common.error', { defaultValue: 'Failed to get response' });
            toast.error(message);
        },
    });

    const handleSend = () => {
        const trimmed = input.trim();
        if (!trimmed || chatMutation.isPending || !activeSessionId) return;

        const userMsg: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: trimmed,
            timestamp: new Date(),
        };

        const currentSession = sessions.find(s => s.id === activeSessionId);
        if (!currentSession) return;

        const updatedMessages = [...currentSession.messages, userMsg];
        const isFirstMessage = currentSession.messages.length === 0;
        const newTitle = isFirstMessage 
            ? (trimmed.length > 30 ? trimmed.substring(0, 30) + '...' : trimmed)
            : currentSession.title;

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    title: newTitle,
                    messages: updatedMessages,
                    updatedAt: new Date()
                };
            }
            return s;
        }));

        setInput('');
        chatMutation.mutate({ userMessage: trimmed, history: updatedMessages });
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const playAudio = (url: string) => {
        const baseURL = apiClient.defaults.baseURL || 'http://localhost:5010/api';
        const hostURL = baseURL.endsWith('/api') ? baseURL.substring(0, baseURL.length - 4) : baseURL;
        const fullUrl = `${hostURL}${url}`;
        const audio = new Audio(fullUrl);
        audio.play().catch(e => {
            console.warn("Failed to autoplay audio:", e);
        });
    };

    const handlePlayTTS = async (msg: ChatMessage) => {
        if (msg.audioUrl) {
            playAudio(msg.audioUrl);
            return;
        }
        
        setPlayingMessageId(msg.id);
        try {
            const { data } = await apiClient.post('/voice/synthesize', { text: msg.content });
            if (data && data.success && data.audio_url) {
                // Update messages in the session state to save the audioUrl
                setSessions(prev => prev.map(s => {
                    return {
                        ...s,
                        messages: s.messages.map(m => m.id === msg.id ? { ...m, audioUrl: data.audio_url } : m)
                    };
                }));
                playAudio(data.audio_url);
            } else {
                toast.error("No se pudo sintetizar la voz.");
            }
        } catch (err) {
            console.error("TTS synthesis failed:", err);
            toast.error("Error al generar la voz.");
        } finally {
            setPlayingMessageId(null);
        }
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());
                await handleAudioUpload(audioBlob);
            };

            mediaRecorder.start();
            setIsRecording(true);
            toast.info("Grabando audio...");
        } catch (err) {
            console.error("Failed to start recording:", err);
            toast.error("No se pudo acceder al micrófono.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const handleAudioUpload = async (audioBlob: Blob) => {
        if (!activeSessionId) return;
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice_recording.webm');
        if (selectedAgentId) {
            formData.append('agent_id', selectedAgentId);
        }
        
        const tempUserMsgId = `user-temp-${Date.now()}`;
        const userMsg: ChatMessage = {
            id: tempUserMsgId,
            role: 'user',
            content: '🎙️ (Procesando nota de voz...)',
            timestamp: new Date(),
        };

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    messages: [...s.messages, userMsg],
                    updatedAt: new Date()
                };
            }
            return s;
        }));
        
        setIsProcessingVoice(true);

        try {
            const { data } = await apiClient.post('/voice/interact', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                }
            });
            
            if (data && data.success) {
                const updatedUserMsg: ChatMessage = {
                    id: tempUserMsgId,
                    role: 'user',
                    content: `🎙️ ${data.transcription}`,
                    timestamp: userMsg.timestamp
                };

                const assistantMsg: ChatMessage = {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: data.agent_response,
                    timestamp: new Date(),
                    audioUrl: data.audio_url
                };

                setSessions(prev => prev.map(s => {
                    if (s.id === activeSessionId) {
                        const clearedMsgs = s.messages.filter(m => m.id !== tempUserMsgId);
                        const isFirstMessage = clearedMsgs.length === 0;
                        const newTitle = isFirstMessage 
                            ? (data.transcription.length > 30 ? data.transcription.substring(0, 30) + '...' : data.transcription)
                            : s.title;
                        
                        return {
                            ...s,
                            title: newTitle,
                            messages: [...clearedMsgs, updatedUserMsg, assistantMsg],
                            updatedAt: new Date()
                        };
                    }
                    return s;
                }));

                if (data.audio_url) {
                    playAudio(data.audio_url);
                }
            } else {
                setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: s.messages.filter(m => m.id !== tempUserMsgId) } : s));
                toast.error("Error al procesar el audio.");
            }
        } catch (error: any) {
            setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: s.messages.filter(m => m.id !== tempUserMsgId) } : s));
            console.error("Audio interaction failed:", error);
            toast.error("La interacción por voz falló.");
        } finally {
            setIsProcessingVoice(false);
        }
    };

    return (
        <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
            {/* Cabecera de la Sección */}
            <div className="flex flex-col gap-1">
                <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                    <Sparkles className="h-6 w-6 text-primary animate-pulse" />
                    Zona de Pruebas de Agentes
                </h1>
                <p className="text-muted-foreground text-sm max-w-4xl">
                    Prueba y afina la inteligencia de tus agentes en tiempo real. Selecciona un agente específico para probar su comportamiento aislado o utiliza el modo de orquestación completa para experimentar el flujo de forma idéntica a como lo experimentarán tus clientes.
                </p>
            </div>

            <div className="flex flex-1 gap-4 overflow-hidden">
            {/* Sidebar History */}
            <Card className="hidden w-64 flex-col md:flex">
                <div className="p-4 border-b">
                    <Button className="w-full flex items-center justify-center gap-2" onClick={createNewSession}>
                        <Plus className="h-4 w-4" />
                        Nueva conversación
                    </Button>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {sessions.map(session => (
                        <div
                            key={session.id}
                            onClick={() => setActiveSessionId(session.id)}
                            className={cn(
                                "group flex items-center justify-between p-3 rounded-lg text-sm cursor-pointer transition-colors",
                                session.id === activeSessionId 
                                    ? "bg-primary text-primary-foreground font-semibold" 
                                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <div className="flex items-center gap-2 overflow-hidden mr-2">
                                <MessageSquare className="h-4 w-4 shrink-0" />
                                <span className="truncate">{session.title}</span>
                            </div>
                            <button
                                onClick={(e) => deleteSession(session.id, e)}
                                className={cn(
                                    "opacity-0 group-hover:opacity-100 p-1 hover:bg-background/20 rounded transition-opacity shrink-0",
                                    session.id === activeSessionId ? "text-primary-foreground" : "text-muted-foreground hover:text-destructive"
                                )}
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    ))}
                </div>
                <div className="p-4 border-t">
                    <Button variant="ghost" size="sm" className="w-full text-muted-foreground hover:text-destructive flex items-center justify-center gap-2" onClick={clearAllSessions}>
                        <Trash2 className="h-4 w-4" />
                        {t('adminChat.clearHistory', 'Vaciar historial')}
                    </Button>
                </div>
            </Card>

            {/* Chat Area */}
            <Card className="flex flex-1 flex-col overflow-hidden">
                <CardHeader className="border-b px-6 py-3">
                    <CardTitle className="flex items-center justify-between text-sm font-medium flex-wrap gap-4">
                        <div className="flex items-center gap-4 flex-wrap">
                            <div className="flex items-center gap-2">
                                <Bot className="h-4 w-4 text-primary" />
                                <span>{activeSession?.title || t('playground.liveAgentChat')}</span>
                            </div>

                            {/* Selector de Agente */}
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground font-normal">{t('playground.testing', 'Probando:')}</span>
                                <Select
                                    value={selectedAgentId || 'orchestration'}
                                    onValueChange={(val) => setSelectedAgentId(val === 'orchestration' ? null : val)}
                                >
                                    <SelectTrigger className="h-8 w-[240px] text-xs font-normal bg-background">
                                        <SelectValue placeholder={t('playground.fullOrchestration', 'Orquestación Completa (Simulación)')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="orchestration" className="text-xs font-semibold text-primary">
                                            🔗 {t('playground.fullOrchestration', 'Orquestación Completa (Simulación)')}
                                        </SelectItem>
                                        {agents?.map((agent: any) => (
                                            <SelectItem key={agent.id} value={agent.id.toString()} className="text-xs">
                                                👤 {t('playground.agentLabel', 'Agente')}: {agent.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            {/* Toggle de Auto-Lectura por Voz */}
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setAutoPlayVoice(!autoPlayVoice);
                                    toast.success(
                                        !autoPlayVoice 
                                            ? t('adminChat.toastAutoVoiceOn', 'Lectura automática activada: el agente responderá con voz automáticamente.') 
                                            : t('adminChat.toastAutoVoiceOff', 'Lectura automática desactivada.')
                                    );
                                }}
                                className={cn(
                                    "h-8 w-8 p-0 rounded-full",
                                    autoPlayVoice 
                                        ? "text-primary bg-primary/10 hover:bg-primary/20" 
                                        : "text-muted-foreground hover:bg-muted"
                                )}
                                title={autoPlayVoice ? t('adminChat.tooltipAutoVoiceOff', 'Desactivar respuesta automática de voz') : t('adminChat.tooltipAutoVoiceOn', 'Activar respuesta automática de voz')}
                            >
                                {autoPlayVoice ? (
                                    <Volume2 className="h-4 w-4" />
                                ) : (
                                    <VolumeX className="h-4 w-4" />
                                )}
                            </Button>

                            <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => {
                                    setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: [] } : s));
                                    toast.info(t('adminChat.toastConversationRestarted', 'Conversación reiniciada.'));
                                }}
                                disabled={messages.length === 0}
                                className="h-8 px-2 text-muted-foreground hover:text-destructive text-xs"
                            >
                                <Trash2 className="h-4 w-4 mr-1" />
                                {t('adminChat.clearScreen', 'Limpiar pantalla')}
                            </Button>
                        </div>
                    </CardTitle>
                </CardHeader>

                {/* Messages */}
                <CardContent ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
                    {messages.length === 0 ? (
                        <div className="flex h-full flex-col items-center justify-center text-center text-muted-foreground">
                            <Bot className="mb-4 h-16 w-16 opacity-20" />
                            <p className="text-lg font-medium">{t('common.noResults', { defaultValue: 'No messages yet' })}</p>
                            <p className="text-sm">
                                {t('playground.startTesting')}
                            </p>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={cn(
                                    'flex gap-3',
                                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                                )}
                            >
                                {msg.role === 'assistant' && (
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                                        <Bot className="h-4 w-4 text-primary" />
                                    </div>
                                )}
                                <div
                                    className={cn(
                                        'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
                                        msg.role === 'user'
                                            ? 'bg-primary text-primary-foreground font-medium'
                                            : 'bg-muted'
                                    )}
                                >
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                    <div className="flex items-center justify-between gap-4 mt-1">
                                        <p
                                            className={cn(
                                                'text-[10px]',
                                                msg.role === 'user'
                                                    ? 'text-primary-foreground/60'
                                                    : 'text-muted-foreground'
                                            )}
                                        >
                                            {msg.timestamp.toLocaleTimeString([], {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </p>
                                        {msg.role === 'assistant' && (
                                            <button
                                                onClick={() => handlePlayTTS(msg)}
                                                className={cn(
                                                    "p-1 rounded-full transition-colors text-muted-foreground hover:bg-black/10 hover:text-foreground",
                                                    playingMessageId === msg.id && "animate-pulse"
                                                )}
                                                title="Escuchar respuesta de voz"
                                                disabled={playingMessageId === msg.id}
                                            >
                                                {playingMessageId === msg.id ? (
                                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                ) : (
                                                    <Volume2 className="h-3.5 w-3.5" />
                                                )}
                                            </button>
                                        )}
                                        {msg.audioUrl && msg.role === 'user' && (
                                            <button
                                                onClick={() => playAudio(msg.audioUrl!)}
                                                className="p-1 rounded-full transition-colors text-primary-foreground/80 hover:bg-white/10 hover:text-white"
                                                title="Escuchar nota de voz de usuario"
                                            >
                                                <Volume2 className="h-3.5 w-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                                {msg.role === 'user' && (
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent">
                                        <User className="h-4 w-4" />
                                    </div>
                                )}
                            </div>
                        ))
                    )}

                    {/* Voice processing indicator */}
                    {isProcessingVoice && (
                        <div className="flex gap-3">
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                                <Bot className="h-4 w-4 text-primary" />
                            </div>
                            <div className="rounded-2xl bg-muted px-4 py-3">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                    <span>Procesando nota de voz...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Typing indicator */}
                    {chatMutation.isPending && (
                        <div className="flex gap-3">
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                                <Bot className="h-4 w-4 text-primary" />
                            </div>
                            <div className="rounded-2xl bg-muted px-4 py-3">
                                <div className="flex gap-1">
                                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/40 [animation-delay:0ms]" />
                                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/40 [animation-delay:150ms]" />
                                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/40 [animation-delay:300ms]" />
                                </div>
                            </div>
                        </div>
                    )}
                </CardContent>

                {/* Input */}
                <div className="border-t p-4">
                    <div className="flex gap-2">
                        <Input
                            ref={inputRef}
                            placeholder={t('playground.typeMessage')}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={chatMutation.isPending || isRecording || isProcessingVoice}
                            className="flex-1"
                        />
                        {isRecording ? (
                            <Button
                                onClick={stopRecording}
                                variant="destructive"
                                size="icon"
                                className="animate-pulse"
                                title="Detener grabación"
                            >
                                <Square className="h-4 w-4" />
                            </Button>
                        ) : (
                            <Button
                                onClick={startRecording}
                                variant="outline"
                                size="icon"
                                disabled={chatMutation.isPending || isProcessingVoice}
                                title="Grabar nota de voz"
                            >
                                <Mic className="h-4 w-4" />
                            </Button>
                        )}
                        <Button
                            onClick={handleSend}
                            disabled={!input.trim() || chatMutation.isPending || isRecording || isProcessingVoice}
                            size="icon"
                        >
                            {chatMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                        {t('playground.helpText')}
                    </p>
                </div>
            </Card>
        </div>
    </div>
    );
}
