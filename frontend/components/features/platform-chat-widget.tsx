'use client';
 
import { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Loader2, Bot, Volume2, VolumeX, Mic, MicOff, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { CardContent, CardFooter } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api-client';
import { TypewriterText } from '@/components/ui/typewriter-text';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

interface PlatformChatWidgetProps {
    scope?: 'enterprise' | 'community';
    title?: string;
    subtitle?: string;
}

export function PlatformChatWidget({
    scope = 'enterprise',
    title,
    subtitle,
}: PlatformChatWidgetProps = {}) {
    const { t, i18n } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<{role: 'user' | 'assistant', content: string, animate?: boolean}[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [conversationId, setConversationId] = useState<number | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Resizable drawer width state (desktop)
    const [sidebarWidth, setSidebarWidth] = useState<number>(420);
    const isResizingRef = useRef(false);

    const [voiceEnabled, setVoiceEnabled] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [pendingVoiceBlob, setPendingVoiceBlob] = useState<Blob | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const startResizing = (e: React.MouseEvent) => {
        e.preventDefault();
        isResizingRef.current = true;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', stopResizing);
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'col-resize';
    };

    const handleMouseMove = (e: MouseEvent) => {
        if (!isResizingRef.current) return;
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth >= 320 && newWidth <= Math.min(800, window.innerWidth * 0.85)) {
            setSidebarWidth(newWidth);
        }
    };

    const stopResizing = () => {
        isResizingRef.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', stopResizing);
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
    };

    const stopSpeaking = () => {
        if (audioPlayerRef.current) {
            audioPlayerRef.current.pause();
            audioPlayerRef.current.src = '';
        }
    };

    const speakResponse = async (text: string) => {
        if (!voiceEnabled) return;
        stopSpeaking();
        try {
            const response = await apiClient.post('/voice/synthesize-public', {
                text: text.substring(0, 500),
                interface_language: i18n.language
            });
            const audioUrl = response.data.audio_url || response.data.data?.audio_url;
            if (audioUrl) {
                const fullAudioUrl = audioUrl.startsWith('http') ? audioUrl : `${window.location.origin}${audioUrl}`;
                if (!audioPlayerRef.current) {
                    audioPlayerRef.current = new Audio();
                }
                audioPlayerRef.current.src = fullAudioUrl;
                audioPlayerRef.current.play().catch(e => console.warn('Audio play block:', e));
            }
        } catch (e) {
            console.error('Error synthesizing voice response:', e);
        }
    };

    const startListening = async () => {
        if (typeof window === 'undefined' || !navigator.mediaDevices) return;
        try {
            setPendingVoiceBlob(null);
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                stream.getTracks().forEach(track => track.stop());
                if (audioChunksRef.current.length > 0) {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                    setPendingVoiceBlob(audioBlob);
                }
            };

            mediaRecorder.start();
            setIsListening(true);
        } catch (e) {
            console.error('Microphone access denied:', e);
            alert('No se pudo acceder al micrófono.');
        }
    };

    const stopListening = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        setIsListening(false);
    };

    const discardPendingVoice = () => {
        setPendingVoiceBlob(null);
        audioChunksRef.current = [];
    };

    const sendPendingVoice = async () => {
        if (!pendingVoiceBlob) return;
        const audioBlob = pendingVoiceBlob;
        setPendingVoiceBlob(null);
        audioChunksRef.current = [];
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'public_voice.webm');
            formData.append('interface_language', i18n.language);

            const response = await apiClient.post('/voice/transcribe-public', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            const transcription = response.data.text || '';
            if (transcription.trim()) {
                setInput(transcription);
            }
        } catch (error) {
            console.error('Public transcription failed:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleOpen = () => {
        setIsOpen(!isOpen);
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, {role: 'user', content: userMsg}]);
        setLoading(true);

        try {
            const response = await apiClient.post('/chat/platform', {
                message: userMsg,
                conversation_id: conversationId,
                channel: 'webchat',
                interface_language: i18n.language,
                scope: scope
            });

            const data = response.data.data;
            setMessages(prev => [...prev, {role: 'assistant', content: data.content, animate: true}]);
            if (data.conversation_id) setConversationId(data.conversation_id);
            speakResponse(data.content);
            
            // Check for change_language action
            if (data.action === 'change_language' && data.action_data?.lang) {
                const newLang = data.action_data.lang;
                i18n.changeLanguage(newLang);
                localStorage.setItem('i18nextLng', newLang);
            }
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant', 
                content: t('platformChat.error', 'Lo siento, tuve un problema al procesar tu mensaje. Por favor intenta de nuevo.'), 
                animate: true
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Backdrop overlay on mobile when chat is open */}
            {isOpen && (
                <div
                    onClick={() => {
                        setIsOpen(false);
                        stopSpeaking();
                    }}
                    className="fixed inset-0 z-[145] bg-black/60 backdrop-blur-sm transition-opacity duration-300 sm:hidden"
                />
            )}

            {/* Sidebar drawer container */}
            <div
                style={isOpen ? { width: typeof window !== 'undefined' && window.innerWidth >= 640 ? `${sidebarWidth}px` : '100%' } : {}}
                className={cn(
                    "fixed z-[150] flex flex-col overflow-hidden transition-transform duration-300 ease-out",
                    // Mobile: bottom 75% sheet, curved top-left corner, full shadow
                    "bottom-0 left-0 right-0 h-[75dvh] max-h-[75dvh] rounded-tl-3xl rounded-tr-none border-t border-l border-border/80 shadow-[0_-10px_35px_rgba(0,0,0,0.4)]",
                    // Desktop: full height right drawer
                    "sm:bottom-auto sm:left-auto sm:top-0 sm:right-0 sm:h-screen sm:max-h-screen sm:rounded-none sm:border-t-0 sm:border-l sm:border-border",
                    isOpen ? "translate-y-0 sm:translate-x-0" : "translate-y-full sm:translate-y-0 sm:translate-x-full",
                    "bg-background/95 backdrop-blur-xl text-foreground",
                    "dark:bg-slate-950/95 dark:border-white/10"
                )}
            >
                {/* Desktop Resizer Handle */}
                {isOpen && (
                    <div
                        onMouseDown={startResizing}
                        className="hidden sm:block absolute top-0 left-0 bottom-0 w-1.5 cursor-col-resize hover:bg-primary/50 transition-colors z-10 group"
                        title="Arrastra para ajustar el ancho del chat"
                    >
                        <div className="w-0.5 h-8 bg-border group-hover:bg-primary rounded-full absolute top-1/2 left-0.5 -translate-y-1/2" />
                    </div>
                )}

                {/* Mobile Pull Handle Pill */}
                <div className="sm:hidden w-full flex items-center justify-center pt-2 pb-1 bg-card/40 shrink-0">
                    <div className="w-10 h-1 rounded-full bg-muted-foreground/30" />
                </div>

                {/* Header */}
                <div className="p-4 border-b border-border dark:border-white/10 bg-card/50 shrink-0 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="h-8 w-8 rounded-xl bg-primary/10 text-primary dark:bg-violet-600/20 dark:text-violet-400 flex items-center justify-center overflow-hidden shrink-0 border border-primary/20">
                            <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="h-6 w-6 object-contain" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-foreground tracking-tight">
                                {title || (scope === 'community' ? 'Krof Comunitario · Underlife' : t('platformChat.title', 'Copiloto Aikrofy'))}
                            </h3>
                            <div className="flex items-center gap-1.5">
                                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                                    {subtitle || (scope === 'community' ? 'Fundación Underlife' : t('platformChat.status', 'Online'))}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {messages.length > 0 && (
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                type="button"
                                onClick={() => {
                                    setMessages([]);
                                    setConversationId(null);
                                    stopSpeaking();
                                }}
                                className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
                                title="Limpiar conversación"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        )}
                        {/* Voice Toggle Button temporarily hidden, functionality preserved */}
                        {false && (
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                type="button"
                                onClick={() => {
                                    setVoiceEnabled(!voiceEnabled);
                                    if (voiceEnabled) stopSpeaking();
                                }}
                                className={cn(
                                    "h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground",
                                    voiceEnabled && "bg-primary/10 text-primary dark:bg-violet-600/20 dark:text-violet-400"
                                )}
                                title={voiceEnabled ? "Desactivar voz" : "Activar voz"}
                            >
                                {voiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                            </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={() => { setIsOpen(false); stopSpeaking(); }} className="text-muted-foreground hover:text-foreground h-8 w-8 rounded-lg">
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
                    
                <CardContent ref={scrollRef} className="flex-1 overflow-y-auto p-4 bg-background/50 flex flex-col justify-between">
                    <div className="space-y-4">
                        {messages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center text-center p-6 space-y-4 animate-fade-in my-auto min-h-[300px]">
                                <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary dark:bg-violet-600/20 dark:text-violet-400 flex items-center justify-center animate-bounce border border-primary/20">
                                    <Bot className="h-6 w-6" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-sm font-bold text-foreground">
                                        {t('platformChat.welcomeTitle', 'Bienvenido a Aikrofy')}
                                    </h3>
                                    <p className="text-xs text-muted-foreground max-w-[260px] leading-relaxed">
                                        {t('platformChat.welcomeDesc', 'Escribe tu duda o pregunta lo que desees sobre la plataforma para comenzar.')}
                                    </p>
                                </div>
                            </div>
                        ) : (
                            messages.map((m, i) => (
                                <div key={i} className={cn(
                                    "flex flex-col max-w-[88%]",
                                    m.role === 'user' ? "ml-auto items-end" : "items-start"
                                )}>
                                    <div className={cn(
                                        "px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed shadow-sm break-words",
                                        m.role === 'user' 
                                            ? "bg-primary text-white rounded-tr-none shadow-md shadow-primary/20 dark:bg-violet-600" 
                                            : "bg-muted rounded-tl-none border border-border dark:bg-white/5 dark:border-white/10 text-foreground"
                                    )}>
                                        {m.role === 'assistant' ? (
                                            m.animate ? (
                                                <TypewriterText 
                                                    text={m.content} 
                                                    onComplete={() => {
                                                        setMessages(prev => prev.map((msg, idx) => idx === i ? { ...msg, animate: false } : msg));
                                                    }}
                                                />
                                            ) : (
                                                <MarkdownRenderer content={m.content} className="text-xs" />
                                            )
                                        ) : (
                                            m.content
                                        )}
                                    </div>
                                    {/* Voice listen button temporarily hidden, audio synthesis preserved */}
                                    {false && m.role === 'assistant' && (
                                        <button
                                            onClick={() => speakResponse(m.content)}
                                            className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted transition-all"
                                        >
                                            <Volume2 className="h-2.5 w-2.5" /> Escuchar
                                        </button>
                                    )}
                                </div>
                            ))
                        )}
                        {loading && (
                            <div className="flex items-center gap-2 text-muted-foreground italic text-xs animate-pulse pt-2">
                                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                                {t('platformChat.writing', 'Krof está escribiendo...')}
                            </div>
                        )}
                    </div>
                </CardContent>

                <CardFooter className="p-3 border-t border-border dark:border-white/10 bg-card/50 shrink-0 flex flex-col gap-2">
                    {/* Voice Confirmation Pill */}
                    {pendingVoiceBlob && (
                        <div className="w-full p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-between gap-2 text-xs animate-fade-in shadow-sm">
                            <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-medium">
                                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
                                <span>Nota de voz lista</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <button
                                    type="button"
                                    onClick={discardPendingVoice}
                                    className="px-2.5 py-1 rounded-lg text-red-500 hover:bg-red-500/10 transition-all text-xs font-semibold cursor-pointer border border-red-500/20"
                                >
                                    Eliminar
                                </button>
                                <button
                                    type="button"
                                    onClick={sendPendingVoice}
                                    disabled={loading}
                                    className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-sm cursor-pointer flex items-center gap-1"
                                >
                                    <Send className="h-3 w-3" />
                                    <span>Enviar</span>
                                </button>
                            </div>
                        </div>
                    )}
                    <form className="flex w-full items-center gap-2" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
                        <textarea
                            placeholder={isListening ? "Escuchando voz..." : t('platformChat.placeholder', 'Escribe tu duda... (Enter para enviar)')}
                            value={input}
                            onChange={(e) => {
                                setInput(e.target.value);
                                e.target.style.height = 'auto';
                                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                            }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    if (input.trim() && !loading) {
                                        handleSend();
                                    }
                                }
                            }}
                            rows={1}
                            style={{ resize: 'none' }}
                            className="flex-1 bg-muted/80 dark:bg-white/5 border border-border dark:border-white/10 rounded-xl px-3 py-2 text-base sm:text-xs focus:outline-none focus:ring-1 focus:ring-primary max-h-[120px] overflow-y-auto scrollbar-thin"
                            disabled={loading}
                        />
                        <Button 
                            variant="ghost"
                            size="icon"
                            type="button"
                            onClick={isListening ? stopListening : startListening}
                            className={cn(
                                "rounded-xl shrink-0 h-9 w-9 border transition-all",
                                isListening
                                    ? "bg-red-500 text-white border-red-500 shadow-md animate-pulse hover:bg-red-600"
                                    : "bg-muted border-border text-muted-foreground hover:text-foreground dark:bg-white/5 dark:border-white/10"
                            )}
                            title="Nota de voz"
                        >
                            {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                        </Button>
                        <Button size="icon" className="rounded-xl shrink-0 h-9 w-9 shadow-md bg-primary hover:bg-primary/90 dark:bg-violet-600 dark:hover:bg-violet-500 text-white" type="submit" disabled={!input.trim() || loading}>
                            <Send className="h-4 w-4" />
                        </Button>
                    </form>
                </CardFooter>
            </div>

            {/* Floating toggle button, hidden when sidebar drawer is open */}
            {!isOpen && (
                <div className="fixed bottom-6 right-6 z-[90]">
                    <Button 
                        onClick={handleOpen}
                        className="h-14 w-14 rounded-full shadow-2xl hover:scale-110 active:scale-95 transition-all duration-300 bg-primary hover:bg-primary/95 dark:bg-violet-600 dark:hover:bg-violet-500 text-white flex items-center justify-center p-0 border border-primary/20 shadow-primary/25"
                    >
                        <MessageCircle className="h-7 w-7" />
                    </Button>
                </div>
            )}
        </>
    );
}
