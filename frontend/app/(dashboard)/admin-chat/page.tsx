'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { io, Socket } from 'socket.io-client';
import { Bot, Send, User, Loader2, MessageSquare, Plus, Trash2, Mic, Square, Volume2, VolumeX, Paperclip, FileText, PanelLeftClose, PanelLeft, Sparkles, LayoutDashboard } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import apiClient from '@/lib/api-client';
import { useTranslation } from 'react-i18next';
import { TypewriterText } from '@/components/ui/typewriter-text';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';
import { ChatChartWidget, parseChartJSON } from '@/components/chat/ChatChartWidget';
import { KrofStudioCanvas, CanvasDocument } from '@/components/chat/KrofStudioCanvas';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface ChatMessage {
    id: string | number;
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

export default function AdminChatPage() {
    const { t } = useTranslation();
    const [sessions, setSessions] = useState<ConversationSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [inputValue, setInputValue] = useState('');
    const [connected, setConnected] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessingVoice, setIsProcessingVoice] = useState(false);
    const [playingMessageId, setPlayingMessageId] = useState<string | number | null>(null);
    // TTS voice narration is currently disabled in Krof Studio per configuration (to be enabled in a future setting)
    const [autoPlayVoice, setAutoPlayVoice] = useState<boolean>(false);
    const autoPlayVoiceRef = useRef(false);
    useEffect(() => {
        autoPlayVoiceRef.current = false;
        if (typeof window !== 'undefined') {
            localStorage.setItem('auto_play_voice_chat', 'false');
        }
    }, []);
    
    const [isUploadingDoc, setIsUploadingDoc] = useState(false);
    const [isHistoryOpen, setIsHistoryOpen] = useState(true);
    const [activeDocument, setActiveDocument] = useState<CanvasDocument | null>(null);
    const [isCanvasOpen, setIsCanvasOpen] = useState(false);
    const [isCanvasExpanded, setIsCanvasExpanded] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const pageFileInputRef = useRef<HTMLInputElement>(null);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const socketRef = useRef<Socket | null>(null);
    const activeSessionIdRef = useRef<string | null>(null);
    const completeStep = useOnboardingStore((s) => s.completeStep);

    // Helper: open text in Canvas with automatic CSV-to-Markdown table transformation
    // Helper: open text in Canvas preserving full structure, tables, and chart info
    const openInCanvas = (content: string, customTitle?: string, chartConfig?: any) => {
        let processedContent = content || '';

        // Only convert raw CSV lines if there's no Markdown table structure already present
        const hasMarkdownTable = processedContent.includes('|') && processedContent.split('\n').some(l => l.includes('|-') || l.includes('| -'));
        
        if (!hasMarkdownTable) {
            const lines = processedContent.split('\n');
            const csvLineIndices: number[] = [];
            lines.forEach((l, idx) => {
                const parts = l.split(',');
                if (parts.length >= 2 && l.trim().length > 0 && !l.startsWith('#') && !l.startsWith('>')) {
                    csvLineIndices.push(idx);
                }
            });

            // If we have a contiguous cluster of 2 or more CSV lines, convert them to Markdown table
            if (csvLineIndices.length >= 2) {
                try {
                    const firstIdx = csvLineIndices[0];
                    const lastIdx = csvLineIndices[csvLineIndices.length - 1];
                    const header = lines[firstIdx].split(',').map(c => c.trim().replace(/^"|"$/g, ''));
                    const separator = header.map(() => '---');
                    const mdRows = [
                        `| ${header.join(' | ')} |`,
                        `| ${separator.join(' | ')} |`
                    ];

                    for (let i = firstIdx + 1; i <= lastIdx; i++) {
                        const cells = lines[i].split(',').map(c => c.trim().replace(/^"|"$/g, ''));
                        if (cells.length === header.length) {
                            mdRows.push(`| ${cells.join(' | ')} |`);
                        }
                    }

                    if (mdRows.length > 2) {
                        const before = lines.slice(0, firstIdx).join('\n');
                        const after = lines.slice(lastIdx + 1).join('\n');
                        processedContent = [before, mdRows.join('\n'), after].filter(Boolean).join('\n\n');
                    }
                } catch (e) {
                    console.error("Failed to convert CSV to Markdown table:", e);
                }
            }
        }

        // Detect document type
        const isTable = processedContent.includes('|') && processedContent.split('\n').some(l => l.includes('|-') || l.includes('| -'));
        const isCode = processedContent.includes('```');
        const docType = chartConfig ? 'report' : isTable ? 'table' : isCode ? 'code' : 'document';
        
        let title: string = customTitle ?? '';
        if (!title) {
            const firstHeader = processedContent.match(/^#+\s+(.+)$/m);
            if (firstHeader && firstHeader[1]) {
                title = firstHeader[1].trim();
            } else if (chartConfig && chartConfig.title) {
                title = chartConfig.title;
            } else {
                title = isTable 
                    ? t('adminChat.defaultTableTitle', 'Tabla de Datos') 
                    : isCode 
                        ? t('adminChat.defaultCodeTitle', 'Bloque de Código') 
                        : t('adminChat.defaultDocTitle', 'Documento Krof Studio');
            }
        }

        const newDoc: CanvasDocument = {
            id: `doc-${Date.now()}`,
            title,
            content: processedContent,
            type: docType,
            chartConfig: chartConfig || undefined,
            updatedAt: new Date()
        };

        setActiveDocument(newDoc);
        setIsCanvasOpen(true);
    };

    const handlePageFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !activeSessionId) return;

        setIsUploadingDoc(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            await apiClient.post('/rag/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const docName = file.name;
            toast.success(`📄 Documento "${docName}" subido y procesado correctamente.`);
            
            const systemDocMsg: ChatMessage = {
                id: `doc-${Date.now()}`,
                role: 'assistant',
                content: `✅ **Documento subido e indexado:** "${docName}"\nHa sido vectorizado en Pinecone. Puedes hacerme preguntas sobre este archivo.`,
                timestamp: new Date()
            };

            setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: [...s.messages, systemDocMsg] } : s));
        } catch (err: any) {
            console.error("Error uploading file in chat page:", err);
            toast.error(err.response?.data?.error || "Error al subir el archivo.");
        } finally {
            setIsUploadingDoc(false);
            if (pageFileInputRef.current) pageFileInputRef.current.value = '';
        }
    };

    // Keep activeSessionIdRef up to date for socket callbacks
    useEffect(() => {
        activeSessionIdRef.current = activeSessionId;
    }, [activeSessionId]);

    // Fetch initial chat history only if localStorage is empty
    const { isLoading } = useQuery({
        queryKey: ['admin-chat-history'],
        queryFn: async () => {
            const stored = localStorage.getItem('admin_chat_sessions');
            if (stored) return []; // Skip backend history if we have local sessions
            
            const { data } = await apiClient.get('/chat/history');
            if (data.messages && data.messages.length > 0) {
                const initialMsgList = data.messages.map((m: any) => ({
                    id: m.id || `msg-${Date.now()}-${Math.random()}`,
                    role: m.role,
                    content: m.content,
                    timestamp: m.created_at ? new Date(m.created_at) : new Date()
                }));
                
                const initialSession: ConversationSession = {
                    id: 'session-initial',
                    title: 'Chat Inicial',
                    messages: initialMsgList,
                    updatedAt: new Date(),
                };
                
                setSessions([initialSession]);
                setActiveSessionId('session-initial');
            }
            return data.messages || [];
        },
    });

    // Load sessions from localStorage on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const stored = localStorage.getItem('admin_chat_sessions');
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
                    }
                } catch (e) {
                    console.error("Failed to parse sessions", e);
                }
            }
        }
    }, []);

    // Save sessions to localStorage when updated
    useEffect(() => {
        if (sessions.length > 0) {
            localStorage.setItem('admin_chat_sessions', JSON.stringify(sessions));
        } else {
            localStorage.removeItem('admin_chat_sessions');
        }
    }, [sessions]);

    // Active session and messages
    const activeSession = sessions.find(s => s.id === activeSessionId);
    const messages = activeSession ? activeSession.messages : [];

    const createNewSession = () => {
        const newId = `session-${Date.now()}`;
        const newSession: ConversationSession = {
            id: newId,
            title: `${t('adminChat.newSession', 'Nueva sesión')} ${sessions.length + 1}`,
            messages: [],
            updatedAt: new Date(),
        };
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newId);
        return newSession;
    };

    // Automatically create session if empty and not loading
    useEffect(() => {
        if (sessions.length === 0 && !isLoading) {
            createNewSession();
        }
    }, [sessions, isLoading]);

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
                    title: `${t('adminChat.newSession', 'Nueva sesión')} 1`,
                    messages: [],
                    updatedAt: new Date(),
                };
                setSessions([newS]);
                setActiveSessionId(newS.id);
            }
        }
        toast.success(t('adminChat.sessionDeleted', 'Conversación eliminada.'));
    };

    const clearAllSessions = () => {
        const newS: ConversationSession = {
            id: `session-${Date.now()}`,
            title: `${t('adminChat.newSession', 'Nueva sesión')} 1`,
            messages: [],
            updatedAt: new Date(),
        };
        setSessions([newS]);
        setActiveSessionId(newS.id);
        toast.success(t('adminChat.historyCleared', 'Historial vaciado.'));
    };

    // Socket setup
    useEffect(() => {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api';
        let socketUrl = API_URL.replace(/\/api\/?$/, '');
        if (typeof window !== 'undefined' && window.location.hostname.includes('aikrofy.com')) {
            socketUrl = window.location.origin;
        }
        
        const socket = io(socketUrl, {
            path: '/socket.io',
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 15,
            reconnectionDelay: 1000,
            timeout: 10000,
        });

        socket.on('connect', () => {
            setConnected(true);
        });

        socket.on('disconnect', () => {
            setConnected(false);
        });

        socket.on('new_message', (data: any) => {
            if (data.role === 'assistant') {
                const newMsg: ChatMessage = {
                    id: Date.now(),
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date()
                };
                setSessions(prev => prev.map(s => {
                    if (s.id === activeSessionIdRef.current) {
                        return {
                            ...s,
                            messages: [...s.messages, newMsg],
                            updatedAt: new Date()
                        };
                    }
                    return s;
                }));
                
                if (autoPlayVoiceRef.current) {
                    handlePlayTTS(newMsg);
                }
            }
        });

        socket.on('call_report', (data: any) => {
            const newMsg: ChatMessage = {
                id: Date.now(),
                role: 'assistant',
                content: data.content,
                timestamp: new Date()
            };
            setSessions(prev => prev.map(s => {
                if (s.id === activeSessionIdRef.current) {
                    return {
                        ...s,
                        messages: [...s.messages, newMsg],
                        updatedAt: new Date()
                    };
                }
                return s;
            }));
            
            if (autoPlayVoiceRef.current) {
                handlePlayTTS(newMsg);
            }
        });

        socketRef.current = socket;

        return () => {
            socket.disconnect();
        };
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const sendMessageMutation = useMutation({
        mutationFn: async (content: string) => {
            const { data } = await apiClient.post('/chat/admin/message', { content });
            return data;
        },
        onSuccess: (data) => {
            if (data.assistant_message) {
                const assistantMsg: ChatMessage = {
                    id: data.assistant_message.id || Date.now(),
                    role: 'assistant',
                    content: data.assistant_message.content,
                    timestamp: new Date()
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
            }
            completeStep('chat');
        },
        onError: () => {
            const errorMsg: ChatMessage = {
                id: Date.now(),
                role: 'assistant',
                content: t('adminChat.error', { defaultValue: 'Error processing message' }),
                timestamp: new Date()
            };
            setSessions(prev => prev.map(s => {
                if (s.id === activeSessionId) {
                    return {
                        ...s,
                        messages: [...s.messages, errorMsg],
                        updatedAt: new Date()
                    };
                }
                return s;
            }));
        }
    });

    const handleSend = () => {
        const trimmed = inputValue.trim();
        if (!trimmed || sendMessageMutation.isPending || !activeSessionId) return;

        const userMsg: ChatMessage = {
            id: Date.now(),
            role: 'user',
            content: trimmed,
            timestamp: new Date()
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

        setInputValue('');
        sendMessageMutation.mutate(trimmed);
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
            toast.info(t('adminChat.voiceRecording', 'Grabando audio...'));
        } catch (err) {
            console.error("Failed to start recording:", err);
            toast.error(t('adminChat.voiceMicError', 'No se pudo acceder al micrófono.'));
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
        formData.append('channel', 'admin_chat');
        
        const tempUserMsgId = `user-temp-${Date.now()}`;
        const userMsg: ChatMessage = {
            id: tempUserMsgId,
            role: 'user',
            content: t('adminChat.processingVoice', '🎙️ (Procesando nota de voz...)'),
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

                // Auto playback disabled for now per configuration; user can play manually if button is active
                if (autoPlayVoiceRef.current && data.audio_url) {
                    playAudio(data.audio_url);
                }
            } else {
                setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: s.messages.filter(m => m.id !== tempUserMsgId) } : s));
                toast.error(t('adminChat.voiceProcessingError', 'Error al procesar el audio.'));
            }
        } catch (error: any) {
            setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: s.messages.filter(m => m.id !== tempUserMsgId) } : s));
            console.error("Audio interaction failed:", error);
            toast.error(t('adminChat.voiceInteractionError', 'La interacción por voz falló.'));
        } finally {
            setIsProcessingVoice(false);
        }
    };

    const handleAiRefineDocument = (prompt: string) => {
        if (!prompt || sendMessageMutation.isPending) return;
        sendMessageMutation.mutate(prompt);
    };

    return (
        <div className="flex h-full w-full overflow-hidden bg-background">
            {/* Sidebar History (Collapsible) */}
            {isHistoryOpen && (
                <div className="w-64 border-r bg-card flex flex-col shrink-0 transition-all duration-300">
                    <div className="p-3 border-b flex items-center justify-between gap-2 bg-muted/20">
                        <Button 
                            className="flex-1 flex items-center justify-center gap-2 h-9 text-xs font-medium shadow-sm" 
                            onClick={createNewSession}
                        >
                            <Plus className="h-4 w-4" />
                            {t('adminChat.newSession', 'Nueva sesión')}
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-9 w-9 text-muted-foreground hover:text-foreground md:flex"
                            onClick={() => setIsHistoryOpen(false)}
                            title={t('adminChat.hideHistory', 'Ocultar historial')}
                        >
                            <PanelLeftClose className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {sessions.map(session => (
                            <div
                                key={session.id}
                                onClick={() => setActiveSessionId(session.id)}
                                className={cn(
                                    "group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all",
                                    session.id === activeSessionId 
                                        ? "bg-primary text-primary-foreground font-semibold shadow-xs" 
                                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <div className="flex items-center gap-2 overflow-hidden mr-2">
                                    <MessageSquare className="h-3.5 w-3.5 shrink-0" />
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
                    <div className="p-3 border-t bg-muted/10">
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            className="w-full text-xs text-muted-foreground hover:text-destructive flex items-center justify-center gap-2 h-8" 
                            onClick={clearAllSessions}
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                            {t('adminChat.clearHistory', 'Vaciar historial')}
                        </Button>
                    </div>
                </div>
            )}

            {/* Main Chat Conversation Area */}
            <div className={cn(
                "flex flex-col min-w-0 h-full overflow-hidden transition-all duration-200",
                isCanvasOpen && isCanvasExpanded ? "hidden" : "flex-1"
            )}>
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-2.5 border-b bg-card shrink-0 gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                        {!isHistoryOpen && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0"
                                onClick={() => setIsHistoryOpen(true)}
                                title={t('adminChat.showHistory', 'Mostrar historial de sesiones')}
                            >
                                <PanelLeft className="h-4 w-4" />
                            </Button>
                        )}
                        <div className="p-1.5 rounded-lg bg-primary/10 text-primary shrink-0">
                            <Sparkles className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                            <h2 className="text-sm font-semibold truncate flex items-center gap-2">
                                {activeSession?.title || t('adminChat.workspaceTitle', 'Krof Studio Workspace')}
                            </h2>
                            <p className="text-[11px] text-muted-foreground truncate hidden sm:block">
                                {t('adminChat.workspaceSubtitle', 'Redacción inteligente, canvas interactivo y análisis RAG')}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        {/* Canvas toggle button if document exists */}
                        {activeDocument && (
                            <Button
                                variant={isCanvasOpen ? "default" : "outline"}
                                size="sm"
                                onClick={() => setIsCanvasOpen(!isCanvasOpen)}
                                className="h-8 text-xs gap-1.5 font-medium"
                            >
                                <FileText className="h-3.5 w-3.5" />
                                <span className="hidden sm:inline">{t('adminChat.canvasBtn', 'Canvas')}</span>
                            </Button>
                        )}

                        <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground px-2 py-1 bg-muted/40 rounded-full">
                            <span className="relative flex h-2 w-2">
                                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${connected ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
                                <span className={`relative inline-flex rounded-full h-2 w-2 ${connected ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                            </span>
                            <span className="text-[11px] font-medium">
                                {connected ? t('adminChat.online', 'Conectado') : t('adminChat.reconnecting', 'Reconectando')}
                            </span>
                        </div>
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={async () => {
                                try {
                                    await apiClient.post('/chat/admin/clear');
                                    setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, messages: [] } : s));
                                    toast.info(t('adminChat.toastConversationRestarted', 'Conversación reiniciada.'));
                                } catch (err) {
                                    console.error("Error resetting conversation:", err);
                                    toast.error(t('adminChat.toastRestartError', 'No se pudo reiniciar la conversación.'));
                                }
                            }}
                            disabled={messages.length === 0}
                            className="h-8 px-2 text-muted-foreground hover:text-destructive"
                        >
                            <Trash2 className="h-4 w-4 mr-1" />
                            {t('adminChat.clearScreen', 'Limpiar pantalla')}
                        </Button>
                    </div>
                </div>

                <Card className="flex flex-col flex-1 overflow-hidden border shadow-sm">
                    <div className="flex-1 p-4 overflow-y-auto space-y-6 bg-slate-50/50 dark:bg-slate-900/20">
                        {messages.length === 0 && !isLoading && (
                            <div className="flex justify-start">
                                <div className="flex max-w-[80%] items-start gap-3">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                        <Bot className="h-5 w-5" />
                                    </div>
                                    <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 shadow-sm text-sm">
                                        <p className="mb-2">{t('adminChat.welcomeMessage')}</p>
                                        <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                                            <li>{t('adminChat.welcomeItem1')}</li>
                                            <li>{t('adminChat.welcomeItem2')}</li>
                                            <li>{t('adminChat.welcomeItem3')}</li>
                                            <li>{t('adminChat.welcomeItem4')}</li>
                                            <li>{t('adminChat.welcomeItem5')}</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        {messages.map((msg, index) => {
                            const isUser = msg.role === 'user';
                            let cleanText = msg.content || '';
                            let chartConfig: any = null;
                            try {
                                const parsedChart = parseChartJSON(msg.content || '');
                                cleanText = parsedChart.cleanText;
                                chartConfig = parsedChart.chartConfig;
                            } catch (e) {
                                console.error("[ChatPage] Error parsing chart JSON:", e);
                            }
                            return (
                                <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`flex max-w-[80%] items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                                        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${isUser ? 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300' : 'bg-primary text-primary-foreground'}`}>
                                            {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                                        </div>
                                        <div className={`rounded-2xl px-4 py-3 shadow-sm text-sm ${isUser ? 'rounded-tr-sm bg-primary text-primary-foreground' : 'rounded-tl-sm bg-card border'}`}>
                                            {isUser ? (
                                                <p className="whitespace-pre-wrap">{msg.content}</p>
                                            ) : (
                                                <>
                                                    {index === messages.length - 1 && (Date.now() - new Date(msg.timestamp).getTime() < 10000) ? (
                                                        <TypewriterText 
                                                            text={cleanText} 
                                                            onComplete={scrollToBottom}
                                                        />
                                                    ) : (
                                                        <MarkdownRenderer content={cleanText} />
                                                    )}
                                                    {chartConfig && <ChatChartWidget config={chartConfig} />}
                                                </>
                                            )}
                                            <div className="flex items-center justify-between gap-4 mt-1">
                                                <span className={`text-[10px] ${isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                                {!isUser && (
                                                    <div className="flex items-center gap-1">
                                                        <button
                                                            type="button"
                                                            onClick={() => openInCanvas(cleanText, undefined, chartConfig)}
                                                            className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded transition-colors text-muted-foreground hover:bg-primary/10 hover:text-primary dark:hover:bg-primary/20"
                                                            title={t('adminChat.openCanvas', 'Abrir Canvas')}
                                                        >
                                                            <FileText className="h-3 w-3 text-primary" />
                                                            <span>{t('adminChat.openCanvas', 'Abrir Canvas')}</span>
                                                        </button>
                                                    </div>
                                                )}
                                                {msg.audioUrl && isUser && (
                                                    <button
                                                        type="button"
                                                        onClick={() => playAudio(msg.audioUrl!)}
                                                        className="p-0.5 rounded-full transition-colors text-primary-foreground/80 hover:bg-white/10 hover:text-white"
                                                        title="Audio"
                                                    >
                                                        <Volume2 className="h-3.5 w-3.5" />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {isProcessingVoice && (
                            <div className="flex justify-start">
                                <div className="flex max-w-[80%] items-start gap-3">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                        <Bot className="h-5 w-5" />
                                    </div>
                                    <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 shadow-sm text-sm flex items-center gap-2 text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                        <span>{t('adminChat.processingVoice', 'Procesando nota de voz...')}</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {sendMessageMutation.isPending && (
                            <div className="flex justify-start">
                                <div className="flex max-w-[80%] items-start gap-3">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                        <Bot className="h-5 w-5" />
                                    </div>
                                    <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 shadow-sm text-sm flex items-center gap-2 text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        {t('adminChat.thinking')}
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="p-4 border-t bg-background">
                        <input
                            type="file"
                            ref={pageFileInputRef}
                            onChange={handlePageFileUpload}
                            accept=".pdf,.docx,.txt,.csv,.xlsx"
                            className="hidden"
                        />
                        <form 
                            className="flex gap-2 items-center"
                            onSubmit={(e) => {
                                e.preventDefault();
                                handleSend();
                            }}
                        >
                            <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                onClick={() => pageFileInputRef.current?.click()}
                                disabled={isUploadingDoc || sendMessageMutation.isPending || isLoading}
                                title={t('adminChat.attachDoc', 'Adjuntar documento (PDF, DOCX, CSV, Excel, TXT)')}
                            >
                                {isUploadingDoc ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
                            </Button>
                            <Input
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        if (inputValue.trim() && !sendMessageMutation.isPending) {
                                            handleSend();
                                        }
                                    }
                                }}
                                disabled={sendMessageMutation.isPending || isLoading || isRecording || isProcessingVoice}
                                placeholder={t('adminChat.placeholder')}
                                className="flex-1"
                                autoFocus
                            />
                            {isRecording ? (
                                <Button
                                    type="button"
                                    onClick={stopRecording}
                                    variant="destructive"
                                    size="icon"
                                    className="animate-pulse"
                                    title={t('adminChat.stopRecording', 'Detener grabación')}
                                >
                                    <Square className="h-4 w-4" />
                                </Button>
                            ) : (
                                <Button
                                    type="button"
                                    onClick={startRecording}
                                    variant="outline"
                                    size="icon"
                                    disabled={sendMessageMutation.isPending || isLoading || isProcessingVoice}
                                    title={t('adminChat.recordVoice', 'Grabar nota de voz')}
                                >
                                    <Mic className="h-4 w-4" />
                                </Button>
                            )}
                            <Button 
                                type="submit" 
                                disabled={sendMessageMutation.isPending || isLoading || !inputValue.trim() || isRecording || isProcessingVoice}
                            >
                                {sendMessageMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </Button>
                        </form>
                    </div>
                </Card>
            </div>

            {/* Krof Studio Canvas Panel */}
            {isCanvasOpen && (
                <div className={cn(
                    "border-l bg-card flex flex-col shrink-0 h-full transition-all duration-300",
                    isCanvasExpanded 
                        ? "w-full flex-1 relative z-10" 
                        : "w-full md:w-[480px] lg:w-[540px] xl:w-[620px] 2xl:w-[700px] z-20 animate-in slide-in-from-right-10 duration-200 shadow-xl md:shadow-none fixed md:relative inset-0 md:inset-auto"
                )}>
                    <KrofStudioCanvas
                        document={activeDocument}
                        onClose={() => {
                            setIsCanvasOpen(false);
                            setIsCanvasExpanded(false);
                        }}
                        onUpdateContent={(newContent) => {
                            if (activeDocument) {
                                setActiveDocument({
                                    ...activeDocument,
                                    content: newContent,
                                    updatedAt: new Date()
                                });
                            }
                        }}
                        onAskAiRefinement={handleAiRefineDocument}
                        isAiRefining={sendMessageMutation.isPending}
                        isExpanded={isCanvasExpanded}
                        onToggleExpanded={() => setIsCanvasExpanded(!isCanvasExpanded)}
                    />
                </div>
            )}
        </div>
    );
}
