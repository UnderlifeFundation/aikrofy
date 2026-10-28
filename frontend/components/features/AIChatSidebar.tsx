'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  MessageCircle,
  X,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  Bot,
  User,
  Settings,
  ChevronRight,
  TrendingUp,
  FileText,
  Users,
  Compass,
  Trash2,
  LayoutTemplate,
  ExternalLink,
  RefreshCw,
  Paperclip,
  Loader2,
  Flame,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api-client';
import { ChatChartWidget, parseChartJSON } from '@/components/chat/ChatChartWidget';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { io, Socket } from 'socket.io-client';
import { toast } from 'sonner';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  isStreaming?: boolean;
  action?: string;
  actionData?: any;
  landingCard?: {
    id: number;
    title: string;
    status: 'generating' | 'complete';
    redirectUrl: string;
  };
}

const INITIAL_MESSAGE: Message = {
  id: 'init',
  sender: 'bot',
  text: '⚙️ **Consola del Asistente del Sistema**\n\nAquí puedes controlar y automatizar la plataforma utilizando comandos de voz o texto.\n\n**Acciones disponibles:**\n• **Crear o actualizar agentes/skills** (ej: *"crea un agente de ventas"* o *"agrega una skill de facturación"*).\n• **Navegar por el panel** (ej: *"llévame a ver mis agentes"* o *"ver estadísticas"*).\n• **Consultar información** sobre tus contactos, CRM, documentos RAG o facturas.\n\nEscribe o di un comando para comenzar.',
};

function parseMessageButtons(text: string) {
  if (!text) return { cleanText: '', buttons: [] };
  const lines = text.split('\n');
  const cleanTextLines: string[] = [];
  const buttons: string[] = [];

  lines.forEach(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith('👉')) {
      const label = trimmed.replace('👉', '').trim();
      if (label) {
        buttons.push(label);
      }
    } else {
      cleanTextLines.push(line);
    }
  });

  return {
    cleanText: cleanTextLines.join('\n').trim(),
    buttons
  };
}

const TypingText = React.memo(({ text, onComplete }: { text: string; onComplete?: () => void }) => {
  const [displayed, setDisplayed] = useState('');
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    let index = 0;
    setDisplayed('');
    
    const timer = setInterval(() => {
      if (index < text.length) {
        const nextChunk = text.slice(index, index + 3);
        setDisplayed(prev => prev + nextChunk);
        index += 3;
      } else {
        clearInterval(timer);
        onCompleteRef.current?.();
      }
    }, 15);
    
    return () => clearInterval(timer);
  }, [text]);

  return <span className="whitespace-pre-line">{displayed}</span>;
});

interface ChatMessageItemProps {
  msg: Message;
  isCompletedTyping: boolean;
  onTypingComplete: (msgId: string, text: string) => void;
  onButtonClick: (label: string) => void;
  onNavigate: (path: string) => void;
  getMessageActionButton: (msg: Message) => { label: string; path: string } | null;
  t: any;
}

const ChatMessageItem = React.memo(function ChatMessageItem({
  msg,
  isCompletedTyping,
  onTypingComplete,
  onButtonClick,
  onNavigate,
  getMessageActionButton,
  t,
}: ChatMessageItemProps) {
  const { cleanText, buttons, chartConfigs } = React.useMemo(() => {
    let cleanText = msg.text || '';
    let chartConfigs: any[] = [];
    let buttons: string[] = [];
    try {
      const parsedButtons = parseMessageButtons(msg.text || '');
      const textAfterButtons = parsedButtons.cleanText;
      buttons = parsedButtons.buttons || [];
      const parsedChart = parseChartJSON(textAfterButtons);
      cleanText = parsedChart.cleanText;
      chartConfigs = parsedChart.chartConfigs || [];
    } catch (e) {
      console.error("[AIChatSidebar] Error parsing message JSON/chart:", e);
    }
    return { cleanText, buttons, chartConfigs };
  }, [msg.text]);

  const handleTypingDone = useCallback(() => {
    onTypingComplete(msg.id, cleanText);
  }, [msg.id, cleanText, onTypingComplete]);

  const actBtn = msg.sender === 'bot' && !msg.isStreaming && isCompletedTyping ? getMessageActionButton(msg) : null;

  return (
    <div
      className={cn(
        "flex flex-col max-w-[88%] min-w-0 space-y-1 break-words overflow-hidden",
        msg.sender === 'user' ? "ml-auto items-end" : "items-start"
      )}
    >
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
        {msg.sender === 'user' ? <User className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
        <span>{msg.sender === 'user' ? t('copilot.senderUser', 'Administrador') : 'Krof'}</span>
      </div>
      <div
        className={cn(
          "px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed shadow-sm break-words overflow-wrap-anywhere max-w-full",
          msg.sender === 'user'
            ? "bg-primary text-primary-foreground rounded-tr-none whitespace-pre-wrap"
            : "bg-muted rounded-tl-none border border-border dark:bg-white/5 dark:border-white/10",
          msg.isStreaming && "animate-pulse"
        )}
      >
        {msg.sender === 'user' ? (
          cleanText
        ) : msg.isStreaming ? (
          <span className="whitespace-pre-wrap">{cleanText}</span>
        ) : !isCompletedTyping ? (
          <TypingText 
            text={cleanText} 
            onComplete={handleTypingDone} 
          />
        ) : (
          <MarkdownRenderer content={cleanText} className="text-xs" />
        )}
      </div>

      {/* Render chart widgets if assistant returned JSON chart configs */}
      {chartConfigs && chartConfigs.length > 0 && chartConfigs.map((cfg, idx) => (
        <ChatChartWidget key={`chart-${msg.id}-${idx}`} config={cfg} />
      ))}

      {/* Landing Page Card — shown when Krof creates or updates a landing */}
      {msg.landingCard && (
        <div className={cn(
          "mt-2 rounded-xl border p-3 flex flex-col gap-2 animate-fade-in",
          msg.landingCard.status === 'generating'
            ? "border-violet-500/30 bg-violet-900/20"
            : "border-green-500/30 bg-green-900/20"
        )}>
          <div className="flex items-center gap-2">
            <LayoutTemplate className={cn(
              "h-4 w-4 shrink-0",
              msg.landingCard.status === 'generating' ? "text-violet-400" : "text-green-400"
            )} />
            <span className="text-xs font-semibold text-foreground truncate">{msg.landingCard.title}</span>
            {msg.landingCard.status === 'generating' ? (
              <span className="ml-auto flex items-center gap-1 text-[10px] text-violet-400">
                <RefreshCw className="h-3 w-3 animate-spin" /> Generando...
              </span>
            ) : (
              <span className="ml-auto text-[10px] text-green-400">✅ Lista</span>
            )}
          </div>
          <button
            onClick={() => onNavigate(msg.landingCard!.redirectUrl)}
            className="flex items-center justify-center gap-1.5 w-full py-1.5 px-2 rounded-lg border border-violet-500/30 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 font-semibold text-[11px] transition-all hover:scale-[1.02] active:scale-95"
          >
            <ExternalLink className="h-3 w-3" />
            {msg.landingCard.status === 'generating' ? 'Ver en el editor' : 'Abrir Previsualizador'}
          </button>
        </div>
      )}

      {msg.sender === 'bot' && buttons.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1">
          {buttons.map((btn, i) => (
            <button
              key={i}
              onClick={() => onButtonClick(btn)}
              className="px-3 py-1 rounded-xl text-[11px] font-semibold border border-primary/20 bg-primary/5 hover:bg-primary/10 text-primary transition-all dark:border-violet-500/30 dark:bg-violet-600/10 dark:text-violet-400 dark:hover:bg-violet-600/20"
            >
              👉 {btn}
            </button>
          ))}
        </div>
      )}
      
      {/* Dynamic Message Action Button */}
      {actBtn && (
        <button
          onClick={() => onNavigate(actBtn.path)}
          className="mt-2.5 flex items-center justify-center gap-1.5 w-full py-2 px-3 rounded-xl border border-primary/20 bg-primary/10 hover:bg-primary/20 text-primary font-bold text-center text-[10px] transition-all hover:scale-[1.02] active:scale-95 cursor-pointer dark:border-violet-500/30 dark:bg-violet-600/20 dark:text-violet-400 dark:hover:bg-violet-600/30 animate-fade-in"
        >
          <span>{actBtn.label}</span>
          <ChevronRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
});

import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/use-auth-store';

// Persistent cache to survive SPA navigation remounts
let cachedMessages: Message[] = [];
let cachedCompletedTypingIds: Record<string, boolean> = {};
let cachedConversationId: string | null = null;
let cachedIsOpen = false;

export function AIChatSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { theme } = useTheme();
  const { hasCompletedTour } = useOnboardingStore();
  const queryClient = useQueryClient();
  const { i18n, t } = useTranslation();
  const { user } = useAuthStore();
  
  // Fetch real-time credit balance for fuel alerts
  const { data: creditData } = useQuery({
    queryKey: ['credit-balance'],
    queryFn: async () => {
      const { data } = await apiClient.get('/billing/credits');
      return data;
    },
    refetchInterval: 30000,
    enabled: !!user,
  });

  const creditBalance = creditData?.credit_balance ?? 0;
  const isCourtesy = creditData?.is_courtesy ?? false;

  const [isOpen, setIsOpen] = useState(cachedIsOpen);
  const [messages, setMessages] = useState<Message[]>(cachedMessages);
  const [completedTypingIds, setCompletedTypingIds] = useState<Record<string, boolean>>(cachedCompletedTypingIds);
  const [conversationId, setConversationId] = useState<string | null>(cachedConversationId);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [activeLandingId, setActiveLandingId] = useState<number | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Resizable sidebar drawer state (Desktop)
  const [sidebarWidth, setSidebarWidth] = useState<number>(450);
  const isResizingRef = useRef(false);

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
    if (newWidth >= 320 && newWidth <= 800) {
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
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const socketRef = useRef<Socket | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/rag/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const docName = file.name;
      toast.success(`📄 Documento "${docName}" subido y procesado correctamente.`);
      
      // Inject bot notification message
      const botMsgId = Date.now().toString();
      updateMessages(prev => [...prev, {
        id: botMsgId,
        sender: 'bot',
        text: `✅ **Documento indexado:** "${docName}"\nYa está listo en mi base de conocimiento (RAG). Puedes hacerme preguntas sobre este archivo.`,
      }]);
      updateCompletedTypingIds(prev => ({ ...prev, [botMsgId]: true }));
    } catch (err: any) {
      console.error("Error uploading file:", err);
      toast.error(err.response?.data?.error || "Error al subir el archivo.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Helper wrappers to update state and cache simultaneously
  const updateIsOpen = (val: boolean) => {
    cachedIsOpen = val;
    setIsOpen(val);
  };

  const updateMessages = (val: Message[] | ((prev: Message[]) => Message[])) => {
    if (typeof val === 'function') {
      setMessages(prev => {
        const next = val(prev);
        cachedMessages = next;
        return next;
      });
    } else {
      cachedMessages = val;
      setMessages(val);
    }
  };

  const updateCompletedTypingIds = (val: Record<string, boolean> | ((prev: Record<string, boolean>) => Record<string, boolean>)) => {
    if (typeof val === 'function') {
      setCompletedTypingIds(prev => {
        const next = val(prev);
        cachedCompletedTypingIds = next;
        return next;
      });
    } else {
      cachedCompletedTypingIds = val;
      setCompletedTypingIds(val);
    }
  };

  const updateConversationId = (val: string | null) => {
    cachedConversationId = val;
    setConversationId(val);
  };

  // Auto-open chat sidebar 3 seconds after onboarding tour is completed
  useEffect(() => {
    if (hasCompletedTour) {
      const hasAutoOpened = sessionStorage.getItem('pymai-chat-auto-opened');
      if (!hasAutoOpened) {
        const timer = setTimeout(() => {
          updateIsOpen(true);
          sessionStorage.setItem('pymai-chat-auto-opened', 'true');
        }, 3000);
        return () => clearTimeout(timer);
      }
    }
  }, [hasCompletedTour]);

  // ─── Socket.IO: listen for landing page events from backend ──────────────────
  useEffect(() => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api';
    const socketUrl = API_URL.replace('/api', '');

    const socket = io(socketUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      // Join company room to receive targeted notifications
      if (user?.company_id) {
        socket.emit('join_company', { company_id: user.company_id });
      }
    });

    // Landing page was just created and generation started
    socket.on('landing_page_created', (data: any) => {
      const pageId = data.page_id || data.landing_page_id;
      const title = data.title || 'Nueva Landing';
      setActiveLandingId(pageId);
      // Inject a bot message card inside the chat
      const cardMsgId = `landing_created_${pageId}_${Date.now()}`;
      updateMessages(prev => [...prev, {
        id: cardMsgId,
        sender: 'bot',
        text: `🚀 **Landing page creada:** "${title}"\n⏳ Generando contenido con IA... El previsualizador se abrirá automáticamente en cuanto esté lista.`,
        landingCard: {
          id: pageId,
          title,
          status: 'generating',
          redirectUrl: `/landing-pages/${pageId}`,
        },
      }]);
      updateCompletedTypingIds(prev => ({ ...prev, [cardMsgId]: true }));
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
    });

    // Landing page generation is complete
    socket.on('landing_page_ready', (data: any) => {
      const pageId = data.page_id || data.landing_page_id;
      const title = data.title || 'Landing Page';
      // Update any existing generating card to complete
      updateMessages(prev => prev.map(m => {
        if (m.landingCard && m.landingCard.id === pageId && m.landingCard.status === 'generating') {
          return {
            ...m,
            landingCard: {
              id: m.landingCard.id,
              title: m.landingCard.title,
              redirectUrl: m.landingCard.redirectUrl,
              status: 'complete' as const,
            }
          };
        }
        return m;
      }));
      // Navigate automatically to the landing page editor
      router.push(`/landing-pages/${pageId}`);
      toast.success(`✅ Landing "${title}" generada. Abriendo previsualizador...`);
      queryClient.invalidateQueries({ queryKey: ['landing-pages'] });
      queryClient.invalidateQueries({ queryKey: ['landing-page', String(pageId)] });
    });

    // Landing page is being updated/modified
    socket.on('landing_page_updating', (data: any) => {
      const pageId = data.page_id || data.landing_page_id;
      toast.info(`🎨 Aplicando cambios de diseño a la landing page...`);
      queryClient.invalidateQueries({ queryKey: ['landing-page', String(pageId)] });
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [router, queryClient, user?.company_id]);
  const inputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const stopSpeaking = useCallback(() => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.src = '';
    }
  }, []);

  const speakResponse = useCallback(async (text: string) => {
    if (!voiceEnabled) return;
    
    stopSpeaking();
    
    try {
      // Call backend Edge-TTS / synthesize endpoint
      const response = await apiClient.post('/voice/synthesize', {
        text: text.substring(0, 500)
      });
      
      const audioUrl = response.data.audio_url || response.data.data?.audio_url;
      if (audioUrl) {
        // Construct full URL pointing to FastAPI backend or local rewrites
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
  }, [voiceEnabled, stopSpeaking]);

  const handleTypingComplete = useCallback((id: string, text: string) => {
    updateCompletedTypingIds(prev => {
      if (prev[id]) return prev;
      return { ...prev, [id]: true };
    });
    speakResponse(text);
  }, [speakResponse]);

  // Navigate to different dashboard sections based on backend/agent instruction
  const handleNavigation = useCallback((path: string) => {
    router.push(path);
  }, [router]);


  const processAgentCommands = useCallback((text: string, action?: string, actionData?: any) => {
    // ONLY execute navigation if an explicit action string is passed from backend tool execution
    // NEVER perform arbitrary keyword guessing on normal chat response text to prevent route crashes!
    if (!action) return;

    let detectedAction = action;
    let detectedData = actionData || {};

    // Normalize navigation path: accept path, url, or target from any backend tool payload
    const navPath: string | undefined = detectedData?.path || detectedData?.url || detectedData?.target;

    if (detectedAction === 'navigate' && navPath) {
      handleNavigation(navPath);
      toast.success(`✅ Navegando a ${navPath}...`);
    } else if (detectedAction === 'navigate_and_select_agent' && navPath) {
      // Trigger navigation first
      handleNavigation(navPath);
      toast.success(`✅ Navegando a ${navPath}...`);
      // Dispatch a custom event to notify the Agents page to refetch and select this agent
      setTimeout(() => {
        const event = new CustomEvent('aikrofy-select-agent', {
          detail: { agentId: detectedData.agent_id }
        });
        window.dispatchEvent(event);
      }, 500);
    } else if (detectedAction === 'refresh') {
      toast.success('Actualizando datos en la pantalla actual...');
      window.location.reload();
    } else if (detectedAction === 'toast') {
      const message = detectedData?.message || 'Acción completada con éxito';
      toast.success(message);
    } else if (detectedAction === 'change_language' && detectedData?.lang) {
      i18n.changeLanguage(detectedData.lang);
      localStorage.setItem('i18nextLng', detectedData.lang);
    } else if (detectedAction === 'open_landing_preview' && detectedData?.landing_page_id) {
      handleNavigation(`/landing-pages/${detectedData.landing_page_id}`);
      toast.success(`✅ Abriendo previsualizador de landing...`);
    }
  }, [handleNavigation, i18n]);

  const sendMessage = useCallback(async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: textToSend };
    updateMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    const botMsgId = (Date.now() + 1).toString();
    updateMessages(prev => [...prev, { id: botMsgId, sender: 'bot', text: t('copilot.thinking', 'Pensando...'), isStreaming: true }]);

    try {
      const response = await apiClient.post('/chat/admin/message', {
        content: textToSend,
        interface_language: i18n.language
      });

      const assistantMsg = response.data.assistant_message || {};
      const rawResponseText = assistantMsg.content || 'Entendido, procesando tu solicitud.';
      const cleanedResponse = rawResponseText.trim();
      const action = response.data.data?.action || response.data.action || null;
      const actionData = response.data.data?.action_data || response.data.action_data || null;
      const nextConvId = assistantMsg.conversation_id;
      
      if (nextConvId) {
        updateConversationId(String(nextConvId));
      }
      
      updateMessages(prev =>
        prev.map(m =>
          m.id === botMsgId
            ? { ...m, text: cleanedResponse, isStreaming: false, action, actionData }
            : m
        )
      );

      processAgentCommands(cleanedResponse, action, actionData);
    } catch (error: any) {
      const status = error?.response?.status;
      const detail = error?.response?.data?.error || error?.response?.data?.detail;
      let errorMsg = 'No he podido conectarme con el servidor, pero puedo ayudarte a navegar localmente.';
      
      if (status === 402) {
        errorMsg = 'Tu suscripción o periodo de prueba ha expirado. Por favor, recarga combustible o activa un plan para continuar conversando.';
      } else if (status === 401) {
        errorMsg = 'Tu sesión ha expirado. Por favor, recarga la página o vuelve a iniciar sesión.';
      } else if (status === 403) {
        errorMsg = `Acceso denegado: ${detail || 'No tienes permisos o falta el contexto de empresa.'}`;
      } else if (detail) {
        errorMsg = `Aviso del servidor: ${detail}`;
      }

      updateMessages(prev =>
        prev.map(m =>
          m.id === botMsgId
            ? { ...m, text: errorMsg, isStreaming: false }
            : m
        )
      );
      if (textToSend.toLowerCase().includes('agent') || textToSend.toLowerCase().includes('agente')) {
        queryClient.invalidateQueries({ queryKey: ['agents'] });
      }
      processAgentCommands(textToSend);
    } finally {
      setLoading(false);
    }
  }, [loading, processAgentCommands, speakResponse, queryClient]);

  const handleButtonClick = useCallback((label: string) => {
    const labelLower = label.toLowerCase();
    
    // Trigger navigation if matches navigation target
    if (labelLower.includes('recargar') || labelLower.includes('credito') || labelLower.includes('combustible') || labelLower.includes('cargar $')) {
      const match = labelLower.match(/\$(\d+)/);
      if (match && match[1]) {
        handleNavigation(`/pricing?amount=${match[1]}`);
      } else {
        handleNavigation('/pricing');
      }
    } else if (labelLower.includes('agente') || labelLower.includes('agents')) {
      handleNavigation('/agents');
    } else if (labelLower.includes('analítica') || labelLower.includes('estadística') || labelLower.includes('analytics')) {
      handleNavigation('/analytics');
    } else if (labelLower.includes('canal') || labelLower.includes('whatsapp') || labelLower.includes('channel')) {
      handleNavigation('/channels');
    } else if (labelLower.includes('documento') || labelLower.includes('rag') || labelLower.includes('document')) {
      handleNavigation('/documents');
    } else if (labelLower.includes('contacto') || labelLower.includes('crm') || labelLower.includes('client')) {
      handleNavigation('/contacts');
    } else if (labelLower.includes('ajuste') || labelLower.includes('configuracion') || labelLower.includes('settings')) {
      handleNavigation('/settings');
    }
    
    // Also send the label as user message to the chat
    sendMessage(label);
  }, [handleNavigation, sendMessage]);

  const [pendingVoiceBlob, setPendingVoiceBlob] = useState<Blob | null>(null);

  const startListening = useCallback(async () => {
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
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          setPendingVoiceBlob(audioBlob);
        }
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsListening(true);
    } catch (e) {
      console.error('Microphone access denied:', e);
      alert('No se pudo acceder al micrófono.');
    }
  }, []);

  const discardPendingVoice = useCallback(() => {
    setPendingVoiceBlob(null);
    audioChunksRef.current = [];
  }, []);

  const sendPendingVoice = useCallback(async () => {
    if (!pendingVoiceBlob) return;
    const audioBlob = pendingVoiceBlob;
    setPendingVoiceBlob(null);

    // Send to `/api/voice/interact` using custom multipart/form-data
    setLoading(true);
    const botMsgId = Date.now().toString();
    updateMessages(prev => [...prev, { id: botMsgId, sender: 'bot', text: t('copilot.processingVoice', 'Procesando nota de voz...'), isStreaming: true }]);

    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'voice_command.webm');
      formData.append('channel', 'admin_chat');
      formData.append('interface_language', i18n.language);

      const response = await apiClient.post('/voice/interact', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const transcription = response.data.transcription || '(Voz enviada)';
      const agentResponse = response.data.agent_response || 'Entendido.';
      const audioUrl = response.data.audio_url;

      const action = response.data.data?.action || response.data.action || null;
      const actionData = response.data.data?.action_data || response.data.action_data || null;

      // Replace user voice note with transcription text
      updateMessages(prev => [
        ...prev.filter(m => m.id !== botMsgId),
        { id: Date.now().toString(), sender: 'user', text: transcription },
        { id: (Date.now() + 1).toString(), sender: 'bot', text: agentResponse, action, actionData }
      ]);

      processAgentCommands(agentResponse, action, actionData);

      if (voiceEnabled && audioUrl) {
        stopSpeaking();
        const fullAudioUrl = audioUrl.startsWith('http') ? audioUrl : `${window.location.origin}${audioUrl}`;
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio();
        }
        audioPlayerRef.current.src = fullAudioUrl;
        audioPlayerRef.current.play().catch(e => console.warn('Audio play block:', e));
      }
    } catch (error: any) {
      console.error('STT Voice Interaction failed:', error);
      const serverMsg = error.response?.data?.error || error.response?.data?.message || (typeof error.response?.data === 'string' ? error.response?.data : null);
      updateMessages(prev => [
        ...prev.filter(m => m.id !== botMsgId),
        { id: Date.now().toString(), sender: 'bot', text: serverMsg ? `Error al transcribir o procesar la nota de voz: ${serverMsg}` : 'Error al transcribir o procesar la nota de voz. Por favor verifica tu micrófono o conexión.' }
      ]);
    } finally {
      setLoading(false);
    }
  }, [pendingVoiceBlob, voiceEnabled, processAgentCommands, stopSpeaking, t, i18n]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
  }, []);

  const getMessageActionButton = (msg: Message): { label: string; path: string } | null => {
    // 1. If message came with an explicit navigation action from tool execution, present a dedicated button if path is provided
    if (msg.action === 'navigate_and_select_agent' && msg.actionData?.path) {
      return { label: '🤖 Ver Agente Configurado', path: msg.actionData.path };
    }
    if (msg.action === 'open_landing_preview' && msg.actionData?.landing_page_id) {
      return { label: '🚀 Ver Landing Page', path: `/landing-pages/${msg.actionData.landing_page_id}` };
    }
    if (msg.action === 'navigate' && msg.actionData?.path) {
      const p = msg.actionData.path;
      return { label: `👉 Ir a ${p}`, path: p };
    }

    const textLower = (msg.text || '').toLowerCase();
    
    // Only show recharge button if balance is actually low (<= 150) or if user explicitly requested pricing/recharge
    const isExplicitRechargeRequest = textLower.includes('quiero recargar') || textLower.includes('comprar creditos') || textLower.includes('comprar créditos') || textLower.includes('planes de pago') || textLower.includes('cuanto cuesta');
    const isLowCredits = creditBalance !== -1 && creditBalance <= 150;

    if (isExplicitRechargeRequest || (isLowCredits && (textLower.includes('recargar combustible') || textLower.includes('saldo agotado') || textLower.includes('sin créditos')))) {
      const match = textLower.match(/\$(\d+)/);
      const path = match && match[1] ? `/pricing?amount=${match[1]}` : '/pricing';
      return { label: '⚡ Recargar Combustible IA', path };
    }

    // 2. Only show explicit buttons when backed by tool execution actions or when the user explicitly asks how to navigate/recharge.
    // Do NOT generate random buttons like '📡 Ver Canales' just because text mentions a word, since Krof controls the platform directly via tools!
    return null;
  };

  return (
    <>
      {/* Backdrop overlay on mobile when chat is open */}
      {isOpen && (
        <div
          onClick={() => {
            updateIsOpen(false);
            stopSpeaking();
          }}
          className="fixed inset-0 z-[145] bg-black/60 backdrop-blur-sm transition-opacity duration-300 sm:hidden"
        />
      )}

      {/* Dynamic Chat Button (shows only when sidebar is closed and not in Krof Studio /admin-chat) */}
      {!isOpen && pathname !== '/admin-chat' && (
        <button
          onClick={() => updateIsOpen(true)}
          className={cn(
            "fixed bottom-6 right-6 z-[99] h-14 w-14 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 transform hover:scale-110 active:scale-95 border cursor-pointer",
            "bg-primary text-primary-foreground border-primary/20",
            "dark:bg-violet-600 dark:text-white dark:border-violet-500/30"
          )}
          title="Consola de Asistente IA"
        >
          <Sparkles className="h-6 w-6 animate-pulse" />
        </button>
      )}

      {/* Sidebar container (Desktop right drawer, Mobile bottom 75% sheet with curved corner) */}
      <div
        style={isOpen ? {
          width: typeof window !== 'undefined' && window.innerWidth >= 640 ? `${sidebarWidth}px` : '100%',
        } : {}}
        className={cn(
          "fixed z-[150] flex flex-col overflow-hidden transition-transform duration-300 ease-out",
          // Mobile: bottom 75% sheet, curved top-left corner, full shadow
          "bottom-0 left-0 right-0 h-[75dvh] max-h-[75dvh] rounded-tl-3xl rounded-tr-none border-t border-l border-border/80 shadow-[0_-10px_35px_rgba(0,0,0,0.4)]",
          // Desktop: full height right drawer
          "sm:bottom-auto sm:left-auto sm:top-0 sm:right-0 sm:h-[100dvh] sm:max-h-[100dvh] sm:rounded-none sm:border-t-0 sm:border-l sm:border-border",
          isOpen ? "translate-y-0 sm:translate-x-0" : "translate-y-full sm:translate-y-0 sm:translate-x-full sm:w-0 sm:border-transparent",
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
        <div className="flex items-center justify-between p-4 border-b border-border dark:border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-primary/10 text-primary dark:bg-violet-600/20 dark:text-violet-400 flex items-center justify-center overflow-hidden">
              <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="h-6 w-6 object-contain" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight">{t('copilot.title', 'Copiloto Aikrofy')}</h2>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] text-muted-foreground uppercase font-semibold">{t('copilot.statusReady', 'Listo')}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {/* Clear conversation */}
            {messages.length > 0 && (
              <button
                onClick={async () => {
                  try {
                    await apiClient.post('/chat/admin/clear');
                  } catch (e) {
                    console.error("Failed to clear chat history:", e);
                  }
                  updateMessages([]);
                  updateConversationId(null);
                  stopSpeaking();
                }}
                className="p-1.5 rounded-lg hover:bg-muted border border-transparent hover:border-border dark:hover:bg-white/10 dark:hover:border-white/10 text-muted-foreground hover:text-foreground transition-all"
                title={t('copilot.clearChat', 'Limpiar conversación')}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            {/* Toggle voice synthesis (Temporarily hidden per configuration, preserved in codebase) */}
            {false && (
              <button
                onClick={() => {
                  setVoiceEnabled(!voiceEnabled);
                  if (voiceEnabled) stopSpeaking();
                }}
                className={cn(
                  "p-1.5 rounded-lg border text-muted-foreground hover:text-foreground transition-all",
                  voiceEnabled ? "bg-primary/10 border-primary/20 text-primary dark:text-violet-400" : "border-transparent"
                )}
                title={voiceEnabled ? t('copilot.disableVoice', 'Desactivar voz') : t('copilot.enableVoice', 'Activar voz')}
              >
                {voiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              </button>
            )}
            {/* Close Sidebar */}
            <button
              onClick={() => {
                updateIsOpen(false);
                stopSpeaking();
              }}
              className="p-1.5 rounded-lg hover:bg-muted border border-transparent hover:border-border dark:hover:bg-white/10 dark:hover:border-white/10 text-muted-foreground hover:text-foreground transition-all"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Critical Fuel / Credit Alert Banner */}
        {user && user.role !== 'super_admin' && !isCourtesy && creditBalance !== -1 && creditBalance <= 100 && (
          <div className="mx-3 mt-2 p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs space-y-2 shrink-0 animate-fade-in shadow-sm">
            <div className="flex items-center justify-between font-bold text-amber-200">
              <div className="flex items-center gap-1.5">
                <Flame className="h-4 w-4 text-amber-400 animate-pulse shrink-0" />
                <span>Combustible IA Bajo: {creditBalance} créditos</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono">
                Crítico
              </span>
            </div>
            <p className="text-[11px] text-amber-300/90 leading-tight">
              Para evitar que tus agentes de atención, ventas o WhatsApp se detengan, recarga combustible antes de agotar tus créditos.
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button
                onClick={() => handleButtonClick('Recargar Combustible IA')}
                className="px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 font-bold text-[11px] hover:bg-amber-400 transition-all flex items-center gap-1 cursor-pointer"
              >
                ⚡ Recargar Ahora
              </button>
              <button
                onClick={() => handleButtonClick('Cargar $50 (5,500 Créditos)')}
                className="px-2.5 py-1 rounded-lg bg-white/10 border border-white/20 text-white font-medium text-[11px] hover:bg-white/20 transition-all cursor-pointer"
              >
                +$50 (5.5k)
              </button>
              <button
                onClick={() => handleButtonClick('Cargar $100 (11,000 Créditos)')}
                className="px-2.5 py-1 rounded-lg bg-white/10 border border-white/20 text-white font-medium text-[11px] hover:bg-white/20 transition-all cursor-pointer"
              >
                +$100 (11k)
              </button>
            </div>
          </div>
        )}
 
        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-4 animate-fade-in my-auto">
              <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary dark:bg-violet-600/20 dark:text-violet-400 flex items-center justify-center animate-bounce">
                <Bot className="h-6 w-6" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold tracking-tight">{t('copilot.consoleTitle', 'Consola de Control de Aikrofy')}</h3>
                <p className="text-[11px] text-muted-foreground max-w-[240px] leading-relaxed">
                  {t('copilot.consoleDesc', '¡Hola! Soy tu Copiloto. Escribe o di un comando para configurar agentes, navegar por las páginas o realizar acciones en tiempo real.')}
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                msg={msg}
                isCompletedTyping={!!completedTypingIds[msg.id]}
                onTypingComplete={handleTypingComplete}
                onButtonClick={handleButtonClick}
                onNavigate={handleNavigation}
                getMessageActionButton={getMessageActionButton}
                t={t}
              />
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Controls - Always pinned at bottom */}
        <div className="p-3 sm:p-4 border-t border-border dark:border-white/10 bg-background/95 dark:bg-slate-950/95 shrink-0 z-20 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.txt,.csv,.xlsx"
            className="hidden"
          />
          {/* Minimalist Pending Voice Confirmation Pill */}
          {pendingVoiceBlob && (
            <div className="mb-2 p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-between gap-2 text-xs animate-fade-in shadow-sm">
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

          <div className="flex items-center gap-1.5">
            {/* File Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || loading}
              className={cn(
                "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 border transition-all",
                isUploading
                  ? "bg-muted text-primary border-primary animate-pulse"
                  : "bg-muted border-border text-muted-foreground hover:text-foreground dark:bg-white/5 dark:border-white/10"
              )}
              title="Adjuntar documento (PDF, DOCX, CSV, Excel, TXT)"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
            </button>
            <textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
              onFocus={() => {
                setTimeout(() => {
                  chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                }, 300);
              }}
              onKeyDown={(e) => {
                // Desktop: Enter sends immediately, Shift+Enter adds newline
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && !loading) {
                    sendMessage(input);
                  }
                }
              }}
              placeholder={isListening ? t('copilot.listening', 'Escuchando voz...') : t('copilot.placeholder', 'Escribe o pide comandos...')}
              disabled={loading}
              rows={1}
              style={{ resize: 'none' }}
              className={cn(
                "flex-1 bg-muted border rounded-xl px-3 py-2 text-xs outline-none transition-all max-h-[100px] overflow-y-auto scrollbar-thin",
                "border-border focus:border-primary focus:bg-background",
                "dark:bg-white/5 dark:border-white/10 dark:focus:border-violet-500 dark:focus:bg-slate-900"
              )}
            />
            {/* Voice Command Button */}
            <button
              onClick={isListening ? stopListening : startListening}
              className={cn(
                "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 border transition-all",
                isListening
                  ? "bg-red-500 text-white border-red-500 shadow-md shadow-red-500/20 animate-pulse"
                  : "bg-muted border-border text-muted-foreground hover:text-foreground dark:bg-white/5 dark:border-white/10"
              )}
              title="Comando de voz"
            >
              {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
            {/* Send Button */}
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className={cn(
                "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 text-white shadow-md transition-all",
                "bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed",
                "dark:bg-violet-600 dark:hover:bg-violet-500"
              )}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
