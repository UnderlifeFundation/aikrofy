/**
 * ============================================================
 * AIKROFY AI — Enterprise Conversational Navigator & Webchat Widget
 * Copyright 2026 AIKROFY AI. All rights reserved.
 * ============================================================
 * Capacidades y Diseño:
 * 1. Sidebar Drawer moderno idéntico al Copiloto y Home de Aikrofy (Dark & Light support, Glassmorphism, Resizable/Ajustable)
 * 2. Ancho ajustable en desktop (arrastrar borde izquierdo) y 100% responsivo en móviles.
 * 3. Reconocimiento flexible del widget_id (?id=... o data-widget-id="...").
 * 4. Envío de mensajes y RAG en /api/webhooks/webchat/message.
 * 5. Motor de Voz Completo:
 *    - STT (Speech-to-Text): Transcripción de notas de voz vía /api/voice/transcribe-public con fallback a Web Speech API.
 *    - TTS (Text-to-Speech): Edge-TTS Neural de alta calidad vía /api/voice/synthesize-public con fallback a SpeechSynthesis nativo.
 *    - Toggle On/Off de síntesis de voz en tiempo real con reproductor y control de volumen.
 * 6. Botón flotante FAB moderno con branding de Aikrofy, indicador de estado online pulsante y tooltip/pill interactivo.
 * 7. Renderizador de Markdown enriquecido (negritas, cursivas, listas, código, enlaces automáticos).
 * 8. Historial de sesión limpio y persistente durante la navegación por sesión.
 * ============================================================
 */

(function () {
    if (window.AikrofyWidgetInjected) return;
    window.AikrofyWidgetInjected = true;

    // 1. Detectar configuración desde el tag del script
    let script = document.currentScript;
    if (!script) {
        const scripts = document.getElementsByTagName('script');
        for (let i = scripts.length - 1; i >= 0; i--) {
            if (scripts[i].src && (scripts[i].src.includes('widget.js') || scripts[i].hasAttribute('data-widget-id'))) {
                script = scripts[i];
                break;
            }
        }
    }

    let widgetId = script ? script.getAttribute('data-widget-id') : null;
    let customApiHost = script ? (script.getAttribute('data-api-host') || script.getAttribute('data-host')) : null;
    let API_HOST = "https://aikrofy.com";

    // Intentar extraer de query params si se cargó como /widget.js?id=...
    if (script && script.src) {
        try {
            const urlObj = new URL(script.src, window.location.href);
            if (!widgetId) {
                widgetId = urlObj.searchParams.get('id');
            }
            if (urlObj.hostname && (urlObj.hostname.includes('aikrofy.com') || urlObj.hostname.includes('aikrofy.app'))) {
                API_HOST = urlObj.origin;
            }
        } catch (e) {}
    }

    if (customApiHost) {
        API_HOST = customApiHost;
    }

    if (!widgetId) {
        // Fallback por defecto o atributo global
        widgetId = window.AIKROFY_WIDGET_ID || 'f97f9776-e3e5-4891-ad7f-5e54f91462c1';
    }

    const CONFIG = {
        widgetId: widgetId,
        apiHost: API_HOST,
        brandPrimary: script?.getAttribute('data-brand-color') || '#7C3AED', // Violet/Indigo Aikrofy
        brandSecondary: script?.getAttribute('data-brand-secondary') || '#6366F1',
        theme: script?.getAttribute('data-theme') || 'auto', // 'auto' | 'dark' | 'light'
        lang: (
            script?.getAttribute('data-lang') || 
            (typeof document !== 'undefined' && document.documentElement.lang ? document.documentElement.lang.slice(0, 2) : '') || 
            (typeof navigator !== 'undefined' && navigator.language ? navigator.language.slice(0, 2) : '') || 
            'es'
        ).toLowerCase(),
        companyName: script?.getAttribute('data-company-name') || 'Asistente',
        agentName: script?.getAttribute('data-agent-name') || ''
    };

    if (!['es', 'en', 'pt', 'fr', 'de', 'it'].includes(CONFIG.lang)) {
        CONFIG.lang = 'es';
    }

    const STORAGE_KEY_SESSION = "aikrofy_webchat_session_" + CONFIG.widgetId;
    const STORAGE_KEY_OPEN = "aikrofy_webchat_open_" + CONFIG.widgetId;
    const STORAGE_KEY_HISTORY = "aikrofy_webchat_history_" + CONFIG.widgetId;
    const STORAGE_KEY_VOICE = "aikrofy_webchat_voice_" + CONFIG.widgetId;
    const STORAGE_KEY_WIDTH = "aikrofy_webchat_width_" + CONFIG.widgetId;

    // Identificador de usuario y conversación persistente por sesión/dominio
    let userId = sessionStorage.getItem(STORAGE_KEY_SESSION) || localStorage.getItem(STORAGE_KEY_SESSION);
    if (!userId) {
        userId = "guest_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
        try {
            sessionStorage.setItem(STORAGE_KEY_SESSION, userId);
            localStorage.setItem(STORAGE_KEY_SESSION, userId);
        } catch (e) {}
    }

    // Detector dinámico del tema del sitio anfitrión y navegador
    function detectHostTheme() {
        if (CONFIG.theme === 'light') return 'light';
        if (CONFIG.theme === 'dark') return 'dark';

        try {
            const htmlEl = document.documentElement;
            const bodyEl = document.body;

            // 1. Clases en <html> o <body> (e.g. Tailwind, Next.js dark mode)
            if (htmlEl.classList.contains('dark') || (bodyEl && bodyEl.classList.contains('dark'))) return 'dark';
            if (htmlEl.classList.contains('light') || (bodyEl && bodyEl.classList.contains('light'))) return 'light';

            // 2. Data attributes (e.g. data-theme="dark", data-bs-theme="dark")
            const attrs = ['data-theme', 'data-bs-theme', 'data-mode', 'data-color-mode', 'data-theme-mode'];
            for (let attr of attrs) {
                const val = htmlEl.getAttribute(attr) || (bodyEl && bodyEl.getAttribute(attr));
                if (val) {
                    if (val.toLowerCase().includes('dark')) return 'dark';
                    if (val.toLowerCase().includes('light')) return 'light';
                }
            }

            // 3. LocalStorage de temas comunes
            const stored = localStorage.getItem('theme') || localStorage.getItem('color-theme') || 
                           localStorage.getItem('mode') || localStorage.getItem('chakra-ui-color-mode') || 
                           localStorage.getItem('next-theme');
            if (stored) {
                if (stored.toLowerCase().includes('dark')) return 'dark';
                if (stored.toLowerCase().includes('light')) return 'light';
            }

            // 4. Preferencia del navegador / Sistema Operativo
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return 'dark';
            }
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
                return 'light';
            }
        } catch (e) {}

        return 'dark'; // Default seguro
    }

    const STATE = {
        open: false,
        voiceEnabled: sessionStorage.getItem(STORAGE_KEY_VOICE) === '1',
        isListening: false,
        loading: false,
        lang: CONFIG.lang,
        currentTheme: detectHostTheme(),
        sidebarWidth: parseInt(sessionStorage.getItem(STORAGE_KEY_WIDTH) || '420', 10), // Ancho persistente
        companyName: CONFIG.companyName,
        agentName: CONFIG.agentName || 'Asistente',
        messages: []
    };

    function applyTheme(forcedTheme) {
        const theme = forcedTheme || detectHostTheme();
        STATE.currentTheme = theme;
        const root = document.getElementById('aikrofy-widget-root');
        if (root) {
            root.classList.remove('aik-theme-dark', 'aik-theme-light');
            root.classList.add('aik-theme-' + theme);
            root.setAttribute('data-aik-theme', theme);
        }
    }

    // Textos i18n
    const I18N = {
        es: {
            title: "Asistente Virtual",
            statusReady: "EN LÍNEA",
            welcomeTitle: "Consola de Asistente IA",
            welcomeDesc: "¡Hola! Soy tu asistente inteligente. Puedes escribir tu duda o hablar por voz para consultar información, navegar o realizar consultas en tiempo real.",
            inputPlaceholder: "Escribe un mensaje... (Enter para enviar)",
            listening: "Escuchando voz... Haz clic para enviar",
            processingVoice: "Procesando nota de voz...",
            thinking: "Pensando...",
            clearChat: "Limpiar conversación",
            enableVoice: "Activar lectura por voz (TTS)",
            disableVoice: "Desactivar lectura por voz (TTS)",
            voiceBtn: "Hablar por voz",
            sendBtn: "Enviar mensaje",
            closeBtn: "Cerrar chat",
            resizeTooltip: "Arrastra para ajustar el ancho",
            listenAudio: "🔊 Escuchar",
            errorConnection: "No se pudo conectar con el servidor. Intenta de nuevo más tarde."
        },
        en: {
            title: "Virtual Assistant",
            statusReady: "ONLINE",
            welcomeTitle: "AI Assistant Console",
            welcomeDesc: "Hello! I am your AI assistant. You can type or use voice commands to ask questions, explore services or get support in real time.",
            inputPlaceholder: "Type a message... (Press Enter to send)",
            listening: "Listening to voice... Click to send",
            processingVoice: "Processing voice note...",
            thinking: "Thinking...",
            clearChat: "Clear conversation",
            enableVoice: "Enable voice reading (TTS)",
            disableVoice: "Disable voice reading (TTS)",
            voiceBtn: "Voice command",
            sendBtn: "Send message",
            closeBtn: "Close chat",
            resizeTooltip: "Drag to resize sidebar width",
            listenAudio: "🔊 Listen",
            errorConnection: "Could not connect to the server. Please try again later."
        },
        pt: {
            title: "Assistente Virtual",
            statusReady: "ONLINE",
            welcomeTitle: "Console do Assistente IA",
            welcomeDesc: "Olá! Sou seu assistente inteligente. Escreva ou use sua voz para tirar dúvidas em tempo real.",
            inputPlaceholder: "Digite uma mensagem... (Enter para enviar)",
            listening: "Ouvindo voz...",
            processingVoice: "Processando voz...",
            thinking: "Pensando...",
            clearChat: "Limpar conversa",
            enableVoice: "Ativar voz",
            disableVoice: "Desativar voz",
            voiceBtn: "Comando de voz",
            sendBtn: "Enviar",
            closeBtn: "Fechar",
            resizeTooltip: "Arraste para redimensionar",
            listenAudio: "🔊 Ouvir",
            errorConnection: "Erro ao conectar. Tente novamente."
        }
    };

    function t(key) {
        const langPack = I18N[STATE.lang] || I18N['es'];
        return langPack[key] || I18N['es'][key] || key;
    }

    // Inyectar Estilos Completos del Sidebar con Variables CSS Dinámicas Dark / Light
    const styleEl = document.createElement('style');
    styleEl.id = "aikrofy-widget-styles";
    styleEl.innerHTML = `
        /* Root container with Dynamic Theme Variables */
        #aikrofy-widget-root {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-size: 14px;
            
            /* Dark Theme Defaults */
            --aik-bg: rgba(2, 6, 23, 0.96);
            --aik-header-bg: rgba(15, 23, 42, 0.75);
            --aik-footer-bg: rgba(15, 23, 42, 0.85);
            --aik-border: rgba(255, 255, 255, 0.1);
            --aik-border-subtle: rgba(255, 255, 255, 0.08);
            --aik-text-primary: #F8FAFC;
            --aik-text-secondary: #94A3B8;
            --aik-text-muted: #64748B;
            --aik-bot-bubble-bg: rgba(30, 41, 59, 0.75);
            --aik-bot-bubble-border: rgba(255, 255, 255, 0.08);
            --aik-bot-bubble-text: #F8FAFC;
            --aik-input-bg: rgba(255, 255, 255, 0.05);
            --aik-input-border: rgba(255, 255, 255, 0.12);
            --aik-input-text: #FFFFFF;
            --aik-input-placeholder: #64748B;
            --aik-card-bg: rgba(124, 58, 237, 0.15);
            --aik-card-border: rgba(124, 58, 237, 0.3);
            --aik-card-text: #DDD6FE;
            --aik-chip-bg: rgba(124, 58, 237, 0.18);
            --aik-chip-border: rgba(124, 58, 237, 0.4);
            --aik-chip-text: #DDD6FE;
            --aik-btn-hover-bg: rgba(255, 255, 255, 0.08);
            --aik-shadow: -15px 0 50px rgba(0, 0, 0, 0.7);
            --aik-scrollbar-thumb: rgba(255, 255, 255, 0.15);
            --aik-code-bg: rgba(0, 0, 0, 0.4);
            color: var(--aik-text-primary);
        }

        #aikrofy-widget-root.aik-theme-light {
            /* Light Theme Overrides */
            --aik-bg: rgba(255, 255, 255, 0.98);
            --aik-header-bg: rgba(248, 250, 252, 0.95);
            --aik-footer-bg: rgba(248, 250, 252, 0.95);
            --aik-border: rgba(0, 0, 0, 0.1);
            --aik-border-subtle: rgba(0, 0, 0, 0.06);
            --aik-text-primary: #0F172A;
            --aik-text-secondary: #475569;
            --aik-text-muted: #94A3B8;
            --aik-bot-bubble-bg: rgba(241, 245, 249, 0.95);
            --aik-bot-bubble-border: rgba(226, 232, 240, 0.8);
            --aik-bot-bubble-text: #0F172A;
            --aik-input-bg: #FFFFFF;
            --aik-input-border: rgba(203, 213, 225, 0.85);
            --aik-input-text: #0F172A;
            --aik-input-placeholder: #94A3B8;
            --aik-card-bg: rgba(243, 232, 255, 0.75);
            --aik-card-border: rgba(196, 181, 253, 0.5);
            --aik-card-text: #5B21B6;
            --aik-chip-bg: rgba(237, 233, 254, 0.9);
            --aik-chip-border: rgba(196, 181, 253, 0.6);
            --aik-chip-text: #6D28D9;
            --aik-btn-hover-bg: rgba(0, 0, 0, 0.06);
            --aik-shadow: -15px 0 45px rgba(0, 0, 0, 0.12);
            --aik-scrollbar-thumb: rgba(0, 0, 0, 0.18);
            --aik-code-bg: rgba(241, 245, 249, 0.95);
            color: var(--aik-text-primary);
        }

        /* FAB Trigger Button */
        #aikrofy-fab-root {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 2147483640;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            user-select: none;
        }
        #aikrofy-fab-root:hover {
            transform: scale(1.08);
        }
        #aikrofy-fab-root:active {
            transform: scale(0.95);
        }
        #aikrofy-fab-btn {
            width: 58px;
            height: 58px;
            border-radius: 50%;
            background: linear-gradient(135deg, #7C3AED 0%, #6366F1 100%);
            border: 1px solid rgba(255, 255, 255, 0.25);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            box-shadow: 0 10px 30px -5px rgba(124, 58, 237, 0.6), 0 0 20px rgba(124, 58, 237, 0.3);
            position: relative;
            transition: all 0.25s ease;
        }
        #aikrofy-fab-dot {
            position: absolute;
            top: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #10B981;
            border: 2px solid #0F172A;
            box-shadow: 0 0 8px #10B981;
            animation: aik-pulse-dot 2s infinite ease-in-out;
        }
        @keyframes aik-pulse-dot {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.35); opacity: 0.7; }
        }

        /* Sidebar Drawer (Full Height Right Sidebar) */
        #aikrofy-sidebar-container {
            position: fixed;
            top: 0;
            right: 0;
            bottom: 0;
            height: 100vh;
            height: 100dvh;
            z-index: 2147483645;
            background: var(--aik-bg);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-left: 1px solid var(--aik-border);
            display: flex;
            flex-direction: column;
            box-shadow: var(--aik-shadow);
            transform: translateX(100%);
            pointer-events: none;
            visibility: hidden;
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.3s ease, width 0.05s ease, background 0.3s ease, border-color 0.3s ease;
            box-sizing: border-box;
            overflow: hidden;
        }
        #aikrofy-sidebar-container.open {
            transform: translateX(0);
            pointer-events: auto;
            visibility: visible;
        }

        /* Resize Handle for Desktop */
        #aikrofy-resizer {
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            width: 8px;
            cursor: col-resize;
            z-index: 10;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent;
            transition: background 0.2s;
        }
        #aikrofy-resizer:hover, #aikrofy-resizer.resizing {
            background: rgba(124, 58, 237, 0.3);
        }
        #aikrofy-resizer-line {
            width: 2px;
            height: 36px;
            border-radius: 9999px;
            background: var(--aik-border);
            transition: background 0.2s;
        }
        #aikrofy-resizer:hover #aikrofy-resizer-line, #aikrofy-resizer.resizing #aikrofy-resizer-line {
            background: #A78BFA;
        }

        /* Header Bar */
        #aikrofy-header {
            padding: 14px 18px;
            border-bottom: 1px solid var(--aik-border-subtle);
            background: var(--aik-header-bg);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            box-sizing: border-box;
            transition: background 0.3s ease, border-color 0.3s ease;
        }
        .aik-header-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .aik-header-avatar {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.3), rgba(99, 102, 241, 0.2));
            border: 1px solid rgba(124, 58, 237, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            flex-shrink: 0;
        }
        .aik-header-avatar img {
            width: 22px;
            height: 22px;
            object-fit: contain;
        }
        .aik-header-info {
            display: flex;
            flex-direction: column;
        }
        .aik-header-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--aik-text-primary);
            letter-spacing: -0.01em;
            line-height: 1.2;
            transition: color 0.3s ease;
        }
        .aik-header-status {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 2px;
        }
        .aik-status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 8px #10B981;
        }
        .aik-status-text {
            font-size: 9px;
            font-weight: 700;
            color: var(--aik-text-secondary);
            letter-spacing: 0.05em;
            text-transform: uppercase;
            transition: color 0.3s ease;
        }
        .aik-header-actions {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .aik-icon-btn {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: 1px solid transparent;
            background: transparent;
            color: var(--aik-text-secondary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
            padding: 0;
        }
        .aik-icon-btn:hover {
            background: var(--aik-btn-hover-bg);
            color: var(--aik-text-primary);
            border-color: var(--aik-border);
        }
        .aik-icon-btn.active {
            background: rgba(124, 58, 237, 0.2);
            color: #C4B5FD;
            border-color: rgba(124, 58, 237, 0.4);
        }

        /* Message List / Feed */
        #aikrofy-feed {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            box-sizing: border-box;
            scroll-behavior: smooth;
        }
        #aikrofy-feed::-webkit-scrollbar {
            width: 5px;
        }
        #aikrofy-feed::-webkit-scrollbar-thumb {
            background: var(--aik-scrollbar-thumb);
            border-radius: 9999px;
        }

        /* Welcome Empty State */
        .aik-welcome-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 24px 16px;
            margin: auto 0;
            gap: 12px;
        }
        .aik-welcome-icon {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: var(--aik-card-bg);
            border: 1px solid var(--aik-card-border);
            color: #A78BFA;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.3s ease, border-color 0.3s ease;
        }
        .aik-welcome-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--aik-text-primary);
            transition: color 0.3s ease;
        }
        .aik-welcome-desc {
            font-size: 12px;
            color: var(--aik-text-secondary);
            line-height: 1.5;
            max-width: 280px;
            transition: color 0.3s ease;
        }

        /* Chat Bubbles */
        .aik-msg-row {
            display: flex;
            flex-direction: column;
            max-width: 88%;
            gap: 4px;
            animation: aik-msg-fade 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes aik-msg-fade {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .aik-msg-user {
            align-self: flex-end;
            align-items: flex-end;
        }
        .aik-msg-bot {
            align-self: flex-start;
            align-items: flex-start;
        }
        .aik-msg-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            margin-bottom: 4px;
            padding: 0 4px;
        }
        .aik-msg-user .aik-msg-header {
            justify-content: flex-end;
        }
        .aik-msg-sender {
            font-size: 11px;
            font-weight: 600;
            color: var(--aik-text-secondary);
            letter-spacing: 0.2px;
            transition: color 0.3s ease;
        }
        .aik-msg-tts-btn {
            background: transparent;
            border: none;
            color: var(--aik-text-muted);
            cursor: pointer;
            padding: 2px 5px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            opacity: 0.7;
        }
        .aik-msg-tts-btn:hover {
            color: #C4B5FD;
            background: rgba(124, 58, 237, 0.2);
            opacity: 1;
            transform: scale(1.12);
        }
        .aik-msg-bubble {
            padding: 10px 14px;
            font-size: 13px;
            line-height: 1.55;
            border-radius: 16px;
            word-break: break-word;
            box-sizing: border-box;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .aik-msg-user .aik-msg-bubble {
            background: linear-gradient(135deg, #7C3AED 0%, #6366F1 100%);
            color: #FFFFFF;
            border-top-right-radius: 4px;
            font-weight: 450;
        }
        .aik-msg-bot .aik-msg-bubble {
            background: var(--aik-bot-bubble-bg);
            border: 1px solid var(--aik-bot-bubble-border);
            color: var(--aik-bot-bubble-text);
            border-top-left-radius: 4px;
            transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;
        }
        .aik-msg-bubble p {
            margin: 0 0 8px 0;
        }
        .aik-msg-bubble p:last-child {
            margin-bottom: 0;
        }
        .aik-msg-bubble ul, .aik-msg-bubble ol {
            margin: 4px 0 8px 18px;
            padding: 0;
        }
        .aik-msg-bubble li {
            margin-bottom: 3px;
        }
        .aik-msg-bubble strong {
            color: var(--aik-text-primary);
            font-weight: 700;
            transition: color 0.3s ease;
        }
        .aik-msg-bubble code {
            font-family: monospace;
            background: var(--aik-code-bg);
            color: var(--aik-text-primary);
            padding: 2px 5px;
            border-radius: 4px;
            font-size: 11px;
            transition: background 0.3s ease, color 0.3s ease;
        }
        .aik-msg-bubble a {
            color: #7C3AED;
            text-decoration: underline;
            text-underline-offset: 2px;
        }
        .aik-site-link {
            color: #8B5CF6 !important;
            font-weight: 600;
            cursor: pointer;
        }
        .aik-nav-chips-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        .aik-nav-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            background: var(--aik-chip-bg);
            border: 1px solid var(--aik-chip-border);
            color: var(--aik-chip-text);
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            margin-top: 6px;
            margin-right: 4px;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }
        .aik-nav-chip:hover {
            background: linear-gradient(135deg, #7C3AED 0%, #6366F1 100%);
            border-color: #8B5CF6;
            color: #FFFFFF;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
        }
        .aik-nav-chip svg {
            flex-shrink: 0;
        }
        .aik-thinking {
            display: flex;
            align-items: center;
            gap: 6px;
            font-style: italic;
            font-size: 12px;
            color: var(--aik-text-secondary);
            transition: color 0.3s ease;
        }
        .aik-spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(124, 58, 237, 0.3);
            border-top-color: #A78BFA;
            border-radius: 50%;
            animation: aik-spin 0.8s linear infinite;
        }
        @keyframes aik-spin {
            to { transform: rotate(360deg); }
        }
        /* Footer & Input Controls */
        #aikrofy-footer {
            padding: 12px 14px;
            border-top: 1px solid var(--aik-border-subtle);
            background: var(--aik-footer-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
            box-sizing: border-box;
            transition: background 0.3s ease, border-color 0.3s ease;
        }
        #aikrofy-input-row {
            display: flex;
            align-items: flex-end;
            gap: 8px;
            position: relative;
            width: 100%;
            box-sizing: border-box;
        }
        #aikrofy-textarea {
            flex: 1;
            background: var(--aik-input-bg);
            border: 1px solid var(--aik-input-border);
            border-radius: 12px;
            padding: 9px 12px;
            font-size: 13px;
            color: var(--aik-input-text);
            outline: none;
            resize: none;
            min-height: 40px;
            max-height: 120px;
            box-sizing: border-box;
            font-family: inherit;
            line-height: 1.4;
            transition: all 0.2s ease;
        }
        #aikrofy-textarea:focus {
            border-color: #7C3AED;
            box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.25);
        }
        #aikrofy-textarea::placeholder {
            color: var(--aik-input-placeholder);
        }
        .aik-ctrl-btn {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            border: 1px solid transparent;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s ease;
            padding: 0;
            box-sizing: border-box;
        }
        #aikrofy-mic-btn {
            background: var(--aik-btn-hover-bg);
            border-color: var(--aik-border);
            color: var(--aik-text-secondary);
        }
        #aikrofy-mic-btn:hover {
            background: var(--aik-card-bg);
            color: var(--aik-text-primary);
        }
        #aikrofy-mic-btn.recording {
            background: #EF4444 !important;
            border-color: #DC2626 !important;
            color: #FFFFFF !important;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.5);
            animation: aik-pulse-rec 1s infinite ease-in-out;
        }
        @keyframes aik-pulse-rec {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.08); }
        }
        #aikrofy-send-btn {
            background: linear-gradient(135deg, #7C3AED 0%, #6366F1 100%);
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
        }
        #aikrofy-send-btn:hover {
            box-shadow: 0 6px 18px rgba(124, 58, 237, 0.5);
            transform: translateY(-1px);
        }
        #aikrofy-send-btn:active {
            transform: translateY(0);
        }
        #aikrofy-send-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .aik-branding-bar {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            font-size: 10px;
            color: var(--aik-text-muted);
            font-weight: 500;
        }
        .aik-branding-bar a {
            color: #8B5CF6;
            text-decoration: none;
            font-weight: 600;
        }
        .aik-branding-bar a:hover {
            text-decoration: underline;
        }

        /* Mobile 75% Bottom Sheet with Curved Corner and Shadow */
        #aikrofy-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 2147483640;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }
        #aikrofy-backdrop.open {
            opacity: 1;
            pointer-events: auto;
        }

        @media (max-width: 640px) {
            #aikrofy-sidebar-container {
                width: 100vw !important;
                right: 0 !important;
                left: 0 !important;
                top: auto !important;
                bottom: 0 !important;
                height: 75vh !important;
                height: 75dvh !important;
                max-height: 75dvh !important;
                border-top-left-radius: 28px !important;
                border-top-right-radius: 0 !important;
                border-left: 1px solid var(--aik-border) !important;
                border-top: 1px solid var(--aik-border) !important;
                box-shadow: 0 -12px 40px rgba(0, 0, 0, 0.45) !important;
                transform: translateY(100%) !important;
                transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.35s ease !important;
            }
            #aikrofy-sidebar-container.open {
                transform: translateY(0) !important;
            }
            #aikrofy-resizer {
                display: none !important;
            }
            #aikrofy-textarea {
                font-size: 16px !important; /* Previene el zoom automático de Safari iOS / Chrome Mobile al hacer focus */
            }
        }
    `;

    // 2. Elementos del DOM
    const widgetRoot = document.createElement("div");
    widgetRoot.id = "aikrofy-widget-root";

    // FAB Root (Botón Flotante Limpio sin etiqueta de texto)
    const fabRoot = document.createElement("div");
    fabRoot.id = "aikrofy-fab-root";
    fabRoot.title = t('title');
    fabRoot.innerHTML = `
        <button id="aikrofy-fab-btn" aria-label="${t('title')}">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10a9.96 9.96 0 0 1-4.708-1.175L2 22l1.175-5.292A9.96 9.96 0 0 1 2 12C2 6.477 6.477 2 12 2z"/>
                <path d="M8 12h.01M12 12h.01M16 12h.01"/>
            </svg>
            <span id="aikrofy-fab-dot"></span>
        </button>
    `;

    // Sidebar Container (Drawer Lateral Derecho)
    const sidebar = document.createElement("div");
    sidebar.id = "aikrofy-sidebar-container";
    sidebar.style.width = `${STATE.sidebarWidth}px`;
    sidebar.innerHTML = `
        <!-- Resizer Handle -->
        <div id="aikrofy-resizer" title="${t('resizeTooltip')}">
            <div id="aikrofy-resizer-line"></div>
        </div>

        <!-- Header -->
        <div id="aikrofy-header">
            <div class="aik-header-brand">
                <div class="aik-header-avatar">
                    <img id="aikrofy-brand-logo" src="${CONFIG.apiHost}/icono-aikrofy.png" onerror="this.onerror=null; this.src='https://aikrofy.com/icono-aikrofy.png'; if(!this.src) this.parentNode.innerHTML='⚡';" alt="Logo" />
                </div>
                <div class="aik-header-info">
                    <span class="aik-header-title" id="aikrofy-brand-name">${STATE.companyName}</span>
                    <div class="aik-header-status">
                        <span class="aik-status-dot"></span>
                        <span class="aik-status-text">${t('statusReady')}</span>
                    </div>
                </div>
            </div>
            <div class="aik-header-actions">
                <!-- Clear Chat -->
                <button id="aikrofy-clear-btn" class="aik-icon-btn" title="${t('clearChat')}">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
                <!-- Voice Toggle (Temporarily hidden, functionality preserved) -->
                <button id="aikrofy-voice-toggle" class="aik-icon-btn" style="display:none;" title="${t('enableVoice')}">
                    <svg id="aikrofy-vol-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                        <line x1="23" y1="9" x2="17" y2="15"/>
                        <line x1="17" y1="9" x2="23" y2="15"/>
                    </svg>
                </button>
                <!-- Close Button -->
                <button id="aikrofy-close-btn" class="aik-icon-btn" title="${t('closeBtn')}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        </div>

        <!-- Chat Messages Feed -->
        <div id="aikrofy-feed">
            <div class="aik-welcome-box">
                <div class="aik-welcome-icon" id="aikrofy-welcome-icon-box">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="11" width="18" height="10" rx="2"/>
                        <circle cx="12" cy="5" r="2"/>
                        <path d="M12 7v4M8 15h.01M16 15h.01"/>
                    </svg>
                </div>
                <div class="aik-welcome-title">${t('welcomeTitle')}</div>
                <div class="aik-welcome-desc">${t('welcomeDesc')}</div>
            </div>
        </div>

        <!-- Input Area -->
        <div id="aikrofy-footer">
            <div id="aikrofy-input-row">
                <textarea id="aikrofy-textarea" rows="1" placeholder="${t('inputPlaceholder')}"></textarea>
                <button id="aikrofy-mic-btn" class="aik-ctrl-btn" title="${t('voiceBtn')}">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                        <line x1="12" x2="12" y1="19" y2="22"/>
                    </svg>
                </button>
                <button id="aikrofy-send-btn" class="aik-ctrl-btn" title="${t('sendBtn')}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                </button>
            </div>
            <div class="aik-branding-bar">
                <span>Powered by</span>
                <a href="https://aikrofy.com" target="_blank" rel="noopener">Aikrofy</a>
            </div>
        </div>
    `;

    // Backdrop Root (Mobile overlay)
    const backdropEl = document.createElement("div");
    backdropEl.id = "aikrofy-backdrop";
    backdropEl.onclick = () => toggleSidebar(false);

    function mountWidgetDOM() {
        if (document.getElementById('aikrofy-widget-root')) return;
        if (!document.body) {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', mountWidgetDOM);
            } else {
                window.addEventListener('load', mountWidgetDOM);
                setTimeout(mountWidgetDOM, 100);
            }
            return;
        }
        if (!document.getElementById('aikrofy-widget-styles')) {
            const targetHead = document.head || document.getElementsByTagName('head')[0] || document.documentElement;
            if (targetHead) {
                targetHead.appendChild(styleEl);
            } else {
                document.body.appendChild(styleEl);
            }
        }
        if (!widgetRoot.parentNode) {
            widgetRoot.appendChild(backdropEl);
            widgetRoot.appendChild(sidebar);
            widgetRoot.appendChild(fabRoot);
            document.body.appendChild(widgetRoot);
        }
    }
    mountWidgetDOM();

    // Helpers de Navegación y Estructura del Sitio del Cliente (Co-Browsing)
    function extractSiteStructure() {
        try {
            const links = [];
            const seen = new Set();

            // 1. Extraer enlaces de navegación del menú y cabeceras
            document.querySelectorAll('nav a[href], header a[href], [role="navigation"] a[href], footer a[href]').forEach(el => {
                const href = el.getAttribute('href');
                const text = (el.innerText || el.getAttribute('title') || el.getAttribute('aria-label') || '').trim();
                if (href && text && !seen.has(href) && !href.startsWith('javascript:') && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
                    seen.add(href);
                    links.push({ title: text.slice(0, 50), url: href, type: href.startsWith('#') ? 'section' : 'page' });
                }
            });

            // 2. Extraer secciones con ID en la página actual (Landing pages / SPAs)
            document.querySelectorAll('section[id], div[id], main [id]').forEach(el => {
                const id = el.getAttribute('id');
                if (id && !id.startsWith('aikrofy-') && !id.startsWith('__') && !seen.has('#' + id)) {
                    // Obtener título o encabezado de la sección si existe
                    const header = el.querySelector('h1, h2, h3, h4, [class*="title"], [class*="heading"]');
                    const title = (header ? header.innerText : id).trim().slice(0, 50);
                    if (title && id.length > 2) {
                        seen.add('#' + id);
                        links.push({ title: title, url: '#' + id, type: 'section' });
                    }
                }
            });

            return links.slice(0, 25);
        } catch (e) {
            return [];
        }
    }

    // Extraer el contenido textual visible de la página actual (On-Screen Awareness)
    function extractCurrentPageContent() {
        try {
            const mainEl = document.querySelector('main') || document.querySelector('[role="main"]') || document.querySelector('article') || document.body;
            if (!mainEl) return '';

            const clone = mainEl.cloneNode(true);
            const widgetEl = clone.querySelector('#aikrofy-widget-root');
            if (widgetEl) widgetEl.remove();
            clone.querySelectorAll('script, style, noscript, svg, iframe, nav, footer, #aikrofy-widget-root').forEach(el => el.remove());

            const text = (clone.innerText || clone.textContent || '').replace(/\s+/g, ' ').trim();
            return text.slice(0, 4500);
        } catch (e) {
            return '';
        }
    }

    // Detección profunda y automática de capacidades del sitio web anfitrión (Co-browsing Awareness)
    function detectSiteCapabilities() {
        try {
            const caps = {
                languages: [],
                current_language: (document.documentElement.lang || navigator.language || 'es').slice(0, 2).toLowerCase(),
                has_theme_toggle: false,
                current_theme: 'light',
                theme_attribute: 'class',
                framework: 'standard'
            };

            const foundLangs = new Set();
            if (caps.current_language) foundLangs.add(caps.current_language);

            // 0. Detectar idioma actual desde localStorage, DOM y cookies
            try {
                const storedLang = localStorage.getItem('wlt_lang') || localStorage.getItem('i18nextLng') || localStorage.getItem('locale') || localStorage.getItem('lang') || localStorage.getItem('NEXT_LOCALE');
                if (storedLang && storedLang.length >= 2) {
                    caps.current_language = storedLang.slice(0, 2).toLowerCase();
                    foundLangs.add(caps.current_language);
                }
            } catch (e) {}

            // 1. Detectar enlaces de idiomas (<link rel="alternate" hreflang="...">)
            document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(el => {
                const hl = el.getAttribute('hreflang');
                if (hl && hl.length >= 2 && !hl.includes('x-default')) {
                    foundLangs.add(hl.slice(0, 2).toLowerCase());
                }
            });

            // 2. Detectar switchers y enlaces de idioma en el DOM (incluyendo botones con aria-label)
            const langSelectors = 'a[href*="/es/"], a[href*="/en/"], a[href*="/pt/"], a[href*="/fr/"], a[href*="/de/"], a[href*="?lang="], a[href*="?locale="], [data-lang], [data-language], .lang-switcher a, .language-switcher a, .wpml-ls-link, .gtranslate a, button[aria-label*="language" i], button[aria-label*="idioma" i]';
            document.querySelectorAll(langSelectors).forEach(el => {
                const dataLang = el.getAttribute('data-lang') || el.getAttribute('data-language');
                const aria = el.getAttribute('aria-label') || el.getAttribute('title') || '';
                if (dataLang && dataLang.length >= 2) {
                    foundLangs.add(dataLang.slice(0, 2).toLowerCase());
                } else if (/change language to (en|es|pt|fr|de|it)/i.test(aria)) {
                    const match = aria.match(/change language to (en|es|pt|fr|de|it)/i);
                    if (match && match[1]) {
                        const targetLang = match[1].toLowerCase();
                        foundLangs.add(targetLang);
                        foundLangs.add(targetLang === 'es' ? 'en' : 'es');
                        if (!caps.current_language) {
                            caps.current_language = targetLang === 'es' ? 'en' : 'es';
                        }
                    }
                } else {
                    const href = el.getAttribute('href') || '';
                    const match = href.match(/(?:\/|\?lang=|\?locale=)(es|en|pt|fr|de|it)(?:\/|\?|&|$)/i);
                    if (match && match[1]) {
                        foundLangs.add(match[1].toLowerCase());
                    }
                }
            });

            // 3. Detectar selects de idioma
            document.querySelectorAll('select[name*="lang"], select[name*="locale"], select.language-picker, select#language-select').forEach(sel => {
                sel.querySelectorAll('option').forEach(opt => {
                    const val = (opt.value || opt.innerText || '').trim().slice(0, 2).toLowerCase();
                    if (['es', 'en', 'pt', 'fr', 'de', 'it'].includes(val)) {
                        foundLangs.add(val);
                    }
                });
            });

            // 4. Detectar bibliotecas i18n globales en window
            if (window.i18next && window.i18next.languages) {
                window.i18next.languages.forEach(l => foundLangs.add(l.slice(0, 2).toLowerCase()));
            }
            if (window.__NEXT_DATA__ && window.__NEXT_DATA__.locales) {
                window.__NEXT_DATA__.locales.forEach(l => foundLangs.add(l.slice(0, 2).toLowerCase()));
                if (window.__NEXT_DATA__.locale) caps.current_language = window.__NEXT_DATA__.locale.slice(0, 2).toLowerCase();
            }

            caps.languages = Array.from(foundLangs);
            if (caps.languages.length === 0) {
                caps.languages = ['es', 'en'];
            }

            // 5. Detectar tema activo y soporte de modo oscuro
            const isDark = document.documentElement.classList.contains('dark') || 
                           document.body.classList.contains('dark') ||
                           document.documentElement.classList.contains('theme-dark') ||
                           document.documentElement.getAttribute('data-theme') === 'dark' ||
                           document.documentElement.getAttribute('data-bs-theme') === 'dark' ||
                           document.documentElement.getAttribute('data-mode') === 'dark';

            caps.current_theme = isDark ? 'dark' : 'light';

            const themeElements = document.querySelectorAll('[data-theme-toggle], .theme-toggle, #theme-toggle, .dark-mode-toggle, [aria-label*="theme"], [aria-label*="dark"], [aria-label*="modo"], button[class*="theme"], button[class*="dark"]');
            caps.has_theme_toggle = themeElements.length > 0 || !!document.querySelector('[data-theme]') || document.documentElement.classList.contains('dark') || document.documentElement.classList.contains('light');

            return caps;
        } catch (e) {
            return {
                languages: ['es', 'en'],
                current_language: 'es',
                has_theme_toggle: true,
                current_theme: 'light'
            };
        }
    }

    function navigateToUrl(url) {
        if (!url) return;
        try {
            let cleanUrl = url.trim();
            // Si no tiene prefijo pero coincide con un ID en el DOM, anteponer '#'
            if (!cleanUrl.startsWith('#') && !cleanUrl.startsWith('/') && !cleanUrl.startsWith('http') && document.getElementById(cleanUrl)) {
                cleanUrl = '#' + cleanUrl;
            }

            // Handle Hash / On-page section (Smooth Scroll con Spotlight)
            if (cleanUrl.startsWith('#')) {
                const targetId = cleanUrl.replace(/^#/, '');
                const targetEl = document.getElementById(targetId) || 
                                 document.querySelector(`[name="${targetId}"]`) || 
                                 document.querySelector(`[id*="${targetId}"]`) ||
                                 document.querySelector(`.${targetId}`) ||
                                 document.querySelector(cleanUrl);
                if (targetEl) {
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    
                    // Efecto visual interactivo (Spotlight / Resplandor de foco)
                    const origTransition = targetEl.style.transition;
                    const origBoxShadow = targetEl.style.boxShadow;
                    const origOutline = targetEl.style.outline;
                    
                    targetEl.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
                    targetEl.style.outline = '2px solid rgba(124, 58, 237, 0.85)';
                    targetEl.style.boxShadow = '0 0 25px rgba(124, 58, 237, 0.45)';
                    
                    setTimeout(() => {
                        targetEl.style.outline = origOutline;
                        targetEl.style.boxShadow = origBoxShadow;
                        targetEl.style.transition = origTransition;
                    }, 2800);
                } else {
                    // Smart Fallback: Si el ancla no existe en la página actual, buscar si corresponde a una ruta de página independiente
                    const links = extractSiteStructure();
                    const cleanKeyword = targetId.toLowerCase();
                    const matchedLink = links.find(l => 
                        !l.url.startsWith('#') && 
                        (l.url.toLowerCase().includes(cleanKeyword) || 
                         l.title.toLowerCase().includes(cleanKeyword) ||
                         (cleanKeyword.includes('precio') && (l.url.includes('servicio') || l.title.toLowerCase().includes('tarifa') || l.title.toLowerCase().includes('precio'))) ||
                         (cleanKeyword.includes('servicio') && l.url.includes('servicio')) ||
                         (cleanKeyword.includes('contacto') && l.url.includes('contacto')))
                    );
                    if (matchedLink && matchedLink.url) {
                        window.location.href = matchedLink.url;
                        return;
                    }
                    window.location.hash = cleanUrl;
                }
                return;
            }

            // Handle relative route or same domain
            if (cleanUrl.startsWith('/') || cleanUrl.startsWith('./')) {
                window.location.href = cleanUrl;
                return;
            }

            // Handle full URLs
            if (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')) {
                if (cleanUrl.startsWith(window.location.origin)) {
                    window.location.href = cleanUrl;
                } else {
                    window.open(cleanUrl, '_blank', 'noopener');
                }
            }
        } catch (e) {
            console.warn("[Aikrofy] Navigation error:", url, e);
        }
    }

    function triggerFullDomClick(el) {
        if (!el) return false;
        try {
            if (typeof el.focus === 'function') el.focus();
            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                const mouseEvt = new MouseEvent(evt, {
                    bubbles: true,
                    cancelable: true,
                    composed: true,
                    view: window
                });
                el.dispatchEvent(mouseEvt);
            });
            if (typeof el.click === 'function') {
                el.click();
            }
            return true;
        } catch (e) {
            console.debug("[Aikrofy] triggerFullDomClick error:", e);
            return false;
        }
    }

    function sendClientTelemetry(eventType, action, details) {
        try {
            console.info(`%c[Aikrofy Live Audit] ${eventType} -> ${action}:`, 'color: #06b6d4; font-weight: bold;', details);
            if (CONFIG.apiHost && CONFIG.widgetId) {
                fetch(CONFIG.apiHost + '/api/channels/webchat/telemetry', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        widget_id: CONFIG.widgetId,
                        event_type: eventType,
                        action: action,
                        details: details,
                        timestamp: Date.now(),
                        url: window.location.href,
                        current_lang: localStorage.getItem('wlt_lang') || document.documentElement.lang
                    })
                }).catch(() => {});
            }
        } catch (e) {}
    }

    function executeLanguageChange(lang) {
        if (!lang) return;
        try {
            const cleanLang = lang.trim().toLowerCase().slice(0, 2);
            const initialLang = localStorage.getItem('wlt_lang') || document.documentElement.lang || 'es';
            
            // 1. Actualizar idioma interno del widget
            STATE.lang = cleanLang;
            try { sessionStorage.setItem(STORAGE_KEY_LANG, cleanLang); } catch (e) {}
            applyTranslations();

            // 2. Persistir en todas las claves estándar de localStorage para SPAs / React / Next.js
            try {
                localStorage.setItem('wlt_lang', cleanLang);
                localStorage.setItem('i18nextLng', cleanLang);
                localStorage.setItem('lang', cleanLang);
                localStorage.setItem('locale', cleanLang);
                localStorage.setItem('language', cleanLang);
                localStorage.setItem('NEXT_LOCALE', cleanLang);
            } catch (e) {}

            // 3. Disparar eventos CustomEvent globales en window y document para el host (Weblifetech, i18next, custom SPAs)
            const detail = { language: cleanLang, lang: cleanLang, timestamp: Date.now() };
            window.dispatchEvent(new CustomEvent('wlt:lang-changed', { detail }));
            document.dispatchEvent(new CustomEvent('wlt:lang-changed', { detail }));
            window.dispatchEvent(new CustomEvent('aikrofy:change_language', { detail }));
            window.dispatchEvent(new CustomEvent('aikrofy:set_language', { detail }));
            window.dispatchEvent(new CustomEvent('languagechange', { detail }));
            try {
                window.dispatchEvent(new StorageEvent('storage', { key: 'wlt_lang', newValue: cleanLang, url: window.location.href }));
            } catch (e) {}

            // 4. Activar botones o enlaces de idioma en el DOM
            let clickedCount = 0;
            
            // 4a. Buscar botones con aria-label o title específicos
            const ariaButtons = document.querySelectorAll('button[aria-label*="language" i], button[aria-label*="idioma" i], a[aria-label*="language" i], a[aria-label*="idioma" i], button[title*="language" i], button[title*="idioma" i], button[title*="english" i], button[title*="español" i], button[title*="switch" i]');
            for (const btn of ariaButtons) {
                if (btn.closest('#aikrofy-widget-root')) continue;
                const aria = (btn.getAttribute('aria-label') || btn.getAttribute('title') || '').toLowerCase();
                if (aria.includes(`to ${cleanLang}`) || aria.includes(`a ${cleanLang}`) || (cleanLang === 'es' && (aria.includes('español') || aria.includes('spanish') || aria.includes('to es'))) || (cleanLang === 'en' && (aria.includes('english') || aria.includes('ingles') || aria.includes('inglés') || aria.includes('to en')))) {
                    if (triggerFullDomClick(btn)) clickedCount++;
                }
            }

            // 4b. Selectores directos por atributos de datos o IDs
            const directSelectors = [
                `[data-lang="${cleanLang}"]`,
                `[data-language="${cleanLang}"]`,
                `a[hreflang="${cleanLang}"]`,
                `button[data-lang="${cleanLang}"]`,
                `#lang-${cleanLang}`,
                `.lang-${cleanLang}`,
                `a[href*="/${cleanLang}/"]`,
                `a[href*="?lang=${cleanLang}"]`,
                `a[href*="?locale=${cleanLang}"]`
            ];
            for (const sel of directSelectors) {
                const el = document.querySelector(sel);
                if (el && !el.closest('#aikrofy-widget-root')) {
                    if (triggerFullDomClick(el)) clickedCount++;
                }
            }

            // 4c. Si hay un botón de switch de idioma de dos estados y no fue clickeado (porque el idioma destino no coincidía con el título previo)
            if (clickedCount === 0 && ariaButtons.length > 0 && initialLang !== cleanLang) {
                for (const b of ariaButtons) {
                    if (b.closest('#aikrofy-widget-root')) continue;
                    if (triggerFullDomClick(b)) {
                        clickedCount++;
                        break;
                    }
                }
            }

            // 5. Activar selects de idioma
            const selectEls = document.querySelectorAll('select[name*="lang"], select[name*="locale"], select.language-picker, select#language-select');
            selectEls.forEach(sel => {
                for (let i = 0; i < sel.options.length; i++) {
                    const optVal = (sel.options[i].value || sel.options[i].text || '').toLowerCase();
                    if (optVal.startsWith(cleanLang) || optVal.includes(cleanLang)) {
                        sel.selectedIndex = i;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        clickedCount++;
                        break;
                    }
                }
            });

            // 6. Soporte para rutas i18n estructuradas (ej: /en/services -> /es/servicios o /es/services)
            if (clickedCount === 0 && (window.location.pathname.startsWith('/en/') || window.location.pathname.startsWith('/es/') || window.location.pathname.startsWith('/pt/'))) {
                const currentPath = window.location.pathname;
                const newPath = currentPath.replace(/^\/(?:es|en|pt|fr|de|it)/i, '/' + cleanLang);
                if (newPath !== currentPath) {
                    sendClientTelemetry('ACTION_EXECUTION', 'change_language_redirect', { from: currentPath, to: newPath });
                    window.location.href = newPath + window.location.search + window.location.hash;
                    return;
                }
            }

            // 7. Actualizar atributo lang en HTML
            document.documentElement.lang = cleanLang;
            document.documentElement.setAttribute('lang', cleanLang);

            // 8. Enviar telemetría de auditoría en vivo al backend
            sendClientTelemetry('ACTION_EXECUTION', 'change_language', {
                requested: cleanLang,
                initialLang: initialLang,
                buttonsClicked: clickedCount,
                domLang: document.documentElement.lang,
                storedWltLang: localStorage.getItem('wlt_lang')
            });

        } catch (e) {
            console.warn("[Aikrofy] Error executing language change:", e);
            sendClientTelemetry('ACTION_ERROR', 'change_language', { error: String(e) });
        }
    }

    function executeThemeChange(theme) {
        try {
            let finalTheme = theme;
            const isCurrentDark = document.documentElement.classList.contains('dark') || 
                                 document.body.classList.contains('dark') ||
                                 document.documentElement.getAttribute('data-theme') === 'dark';

            if (theme === 'toggle') {
                finalTheme = isCurrentDark ? 'light' : 'dark';
            } else if (['dark', 'oscuro', 'noche'].includes(theme)) {
                finalTheme = 'dark';
            } else {
                finalTheme = 'light';
            }

            // 1. Disparar eventos CustomEvent globales
            const detail = { theme: finalTheme, timestamp: Date.now() };
            window.dispatchEvent(new CustomEvent('aikrofy:change_theme', { detail }));
            window.dispatchEvent(new CustomEvent('aikrofy:set_theme', { detail }));

            // 2. Modificar clases en <html> y <body>
            if (finalTheme === 'dark') {
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
                document.body.classList.add('dark');
                document.body.classList.remove('light');
                document.documentElement.setAttribute('data-theme', 'dark');
                document.documentElement.setAttribute('data-bs-theme', 'dark');
            } else {
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                document.body.classList.remove('dark');
                document.body.classList.add('light');
                document.documentElement.setAttribute('data-theme', 'light');
                document.documentElement.setAttribute('data-bs-theme', 'light');
            }

            // 3. Persistir en localStorage
            try {
                localStorage.setItem('theme', finalTheme);
                localStorage.setItem('color-theme', finalTheme);
            } catch (e) {}

            // 4. Intentar accionar switch de tema en el DOM si existe
            const themeBtn = document.querySelector('[data-theme-toggle], #theme-toggle, .dark-mode-toggle, button[aria-label*="dark" i], button[aria-label*="theme" i]');
            if (themeBtn && !themeBtn.closest('#aikrofy-widget-root')) {
                try {
                    themeBtn.click();
                    themeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                } catch (e) {}
            }
        } catch (e) {
            console.warn("[Aikrofy] Error executing theme change:", e);
        }
    }

    function highlightElement(selector) {
        if (!selector) return;
        try {
            let cleanSel = String(selector).trim();
            if (!cleanSel.startsWith('#') && !cleanSel.startsWith('.') && !cleanSel.startsWith('[') && document.getElementById(cleanSel)) {
                cleanSel = '#' + cleanSel;
            }
            const targetEl = document.querySelector(cleanSel) || document.getElementById(cleanSel.replace(/^#/, ''));
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const origTransition = targetEl.style.transition;
                const origBoxShadow = targetEl.style.boxShadow;
                const origOutline = targetEl.style.outline;

                targetEl.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
                targetEl.style.outline = '3px solid rgba(124, 58, 237, 0.9)';
                targetEl.style.boxShadow = '0 0 30px rgba(124, 58, 237, 0.6)';

                setTimeout(() => {
                    targetEl.style.outline = origOutline;
                    targetEl.style.boxShadow = origBoxShadow;
                    targetEl.style.transition = origTransition;
                }, 3200);
            }
        } catch (e) {
            console.debug("[Aikrofy] Highlight error:", e);
        }
    }

    function executeScroll(direction, target) {
        try {
            const rawDir = (direction || target || 'down').toString().trim().toLowerCase();
            
            // 1. Scroll al fondo / pie de página
            if (['bottom', 'fondo', 'final', 'pie', 'footer', 'abajo_del_todo'].includes(rawDir)) {
                window.scrollTo({
                    top: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
                    behavior: 'smooth'
                });
                return;
            }
            
            // 2. Scroll al inicio / arriba del todo
            if (['top', 'arriba', 'inicio', 'header', 'arriba_del_todo'].includes(rawDir)) {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
                return;
            }
            
            // 3. Scroll hacia abajo (1 viewport)
            if (['down', 'abajo', 'bajar', 'siguiente'].includes(rawDir)) {
                window.scrollBy({
                    top: window.innerHeight * 0.75,
                    behavior: 'smooth'
                });
                return;
            }
            
            // 4. Scroll hacia arriba (1 viewport)
            if (['up', 'subir', 'anterior'].includes(rawDir)) {
                window.scrollBy({
                    top: -window.innerHeight * 0.75,
                    behavior: 'smooth'
                });
                return;
            }
            
            // 5. Scroll al medio
            if (['middle', 'centro', 'medio'].includes(rawDir)) {
                const totalH = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                window.scrollTo({
                    top: totalH / 2,
                    behavior: 'smooth'
                });
                return;
            }
            
            // 6. Si es un selector CSS o texto de sección
            const targetEl = document.querySelector(rawDir) || document.getElementById(rawDir.replace(/^#/, ''));
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                // Fallback: desplazamiento hacia abajo
                window.scrollBy({
                    top: window.innerHeight * 0.75,
                    behavior: 'smooth'
                });
            }
        } catch (e) {
            console.warn("[Aikrofy] Scroll execution error:", e);
        }
    }

    function handleWidgetAction(action, actionData, responseText) {
        try {
            // 1. Acciones de Desplazamiento y Scroll en la Página
            if (action === 'scroll_page' || action === 'scroll_website' || action === 'scroll') {
                const dir = typeof actionData === 'string' ? actionData : (actionData?.direction || actionData?.target || 'down');
                executeScroll(dir, actionData?.target);
                return;
            }

            // 2. Acciones de Navegación
            if (action === 'navigate' || action === 'redirect') {
                const targetUrl = typeof actionData === 'string' ? actionData : (actionData?.target || actionData?.url || actionData?.path || actionData?.section);
                if (targetUrl) {
                    navigateToUrl(targetUrl);
                    return;
                }
            }
            if (actionData && (actionData.target || actionData.url || actionData.path || actionData.section) && (action === 'navigate' || !action)) {
                navigateToUrl(actionData.target || actionData.url || actionData.path || actionData.section);
                return;
            }

            // 3. Acciones de Cambio de Idioma
            if (action === 'change_language' || action === 'set_language' || action === 'switch_language') {
                const targetLang = typeof actionData === 'string' ? actionData : (actionData?.lang || actionData?.language || actionData?.target || '');
                if (targetLang) {
                    executeLanguageChange(targetLang);
                    return;
                }
            }

            // 4. Acciones de Cambio de Tema
            if (action === 'change_theme' || action === 'set_theme' || action === 'switch_theme') {
                const targetTheme = typeof actionData === 'string' ? actionData : (actionData?.theme || actionData?.target || 'toggle');
                executeThemeChange(targetTheme);
                return;
            }

            // 5. Destacar elemento
            if (action === 'highlight_element' || (actionData && actionData.selector)) {
                const selector = actionData?.selector || actionData?.target || actionData;
                highlightElement(selector);
                return;
            }

            // 6. Selector scroll directo
            if (actionData && actionData.selector) {
                const el = document.querySelector(actionData.selector);
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }

            // Fallback: Directiva [NAVIGATE:...] en texto
            if (responseText) {
                const match = responseText.match(/\[NAVIGATE:([^|\]]+)(?:\|[^\]]+)?\]/i);
                if (match && match[1]) {
                    navigateToUrl(match[1].trim());
                }
            }
        } catch (e) {
            console.debug("[Aikrofy] Widget action error:", e);
        }
    }

    const handleNavigationAction = handleWidgetAction;

    // 3. Conexión y Ping Inicial con el Backend
    if (widgetId) {
        const siteLinks = extractSiteStructure();
        const capabilities = detectSiteCapabilities();
        fetch(CONFIG.apiHost + '/api/channels/webchat/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                widget_id: widgetId,
                url: window.location.href,
                current_url: window.location.href,
                host_domain: window.location.origin,
                current_page: window.location.pathname,
                page_title: document.title,
                page_content: extractCurrentPageContent(),
                site_structure: siteLinks,
                site_capabilities: capabilities
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data) {
                if (data.company_name) {
                    STATE.companyName = data.company_name;
                    const nameEl = document.getElementById("aikrofy-brand-name");
                    if (nameEl) nameEl.innerText = data.company_name;
                }
                if (data.agent_name) {
                    STATE.agentName = data.agent_name;
                }
                if (data.logo_url) {
                    STATE.logoUrl = data.logo_url;
                    const logoImg = document.getElementById("aikrofy-brand-logo");
                    if (logoImg) {
                        const fullLogo = data.logo_url.startsWith('http') ? data.logo_url : `${CONFIG.apiHost}${data.logo_url}`;
                        logoImg.src = fullLogo;
                    }
                    const welcomeIcon = document.getElementById("aikrofy-welcome-icon-box");
                    if (welcomeIcon) {
                        const fullLogo = data.logo_url.startsWith('http') ? data.logo_url : `${CONFIG.apiHost}${data.logo_url}`;
                        welcomeIcon.innerHTML = `<img src="${fullLogo}" style="width:100%;height:100%;object-fit:contain;border-radius:12px;" alt="${data.company_name || 'Logo'}" />`;
                    }
                }
                if (data.agent_gender) {
                    STATE.agentGender = data.agent_gender;
                }
                if (data.voice_model) {
                    STATE.voiceModel = data.voice_model;
                }
            }
        })
        .catch(err => console.debug("[Aikrofy] Ping status:", err));
    }

    // 4. Parser de Markdown Sencillo y Seguro con Chips de Navegación
    function parseMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Convert [NAVIGATE:url|Label] or [NAVIGATE:url] into clickable quick-action buttons
        escaped = escaped.replace(/\[NAVIGATE:([^|\]]+)(?:\|([^\]]+))?\]/gi, (match, url, label) => {
            const btnText = (label || 'Ir a la sección').trim();
            const cleanUrl = url.trim();
            return `<button class="aik-nav-chip" data-nav="${encodeURIComponent(cleanUrl)}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg><span>${btnText}</span></button>`;
        });

        // Negritas **texto**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Cursivas *texto*
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Código inline `code`
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Links [label](url) -> converted into custom clickable navigation link if hash/site
        escaped = escaped.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label, href) => {
            if (href.startsWith('#') || href.startsWith('/')) {
                return `<a href="${href}" class="aik-site-link" data-nav="${encodeURIComponent(href)}">${label}</a>`;
            }
            return `<a href="${href}" target="_blank" rel="noopener">${label}</a>`;
        });
        // Links planos https://...
        escaped = escaped.replace(/(?<!href=")(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        // Saltos de línea
        escaped = escaped.replace(/\n/g, '<br>');
        return escaped;
    }

    // 5. Motor de Audio / TTS (Edge-TTS público y Web Speech API)
    let activeAudio = null;

    function stopSpeaking() {
        if (activeAudio) {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            activeAudio = null;
        }
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }

    async function speakText(text) {
        if (!text || !text.trim()) return;
        stopSpeaking();

        const clean = text.replace(/<[^>]*>?/gm, '').trim();

        // 1. Intentar Backend Edge-TTS Neural de alta fidelidad con selección inteligente de voz y género
        try {
            const resp = await fetch(CONFIG.apiHost + '/api/voice/synthesize-public', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: clean.substring(0, 450),
                    interface_language: STATE.lang,
                    widget_id: CONFIG.widgetId,
                    gender: STATE.agentGender || 'neutral',
                    voice: STATE.voiceModel || 'smart'
                })
            });
            const data = await resp.json();
            if (data && data.audio_url) {
                const fullAudioUrl = data.audio_url.startsWith('http') ? data.audio_url : `${CONFIG.apiHost}${data.audio_url}`;
                activeAudio = new Audio(fullAudioUrl);
                activeAudio.play().catch(e => console.debug("Audio autoplay prevented:", e));
                return;
            }
        } catch (err) {
            console.debug("Backend TTS fallback:", err);
        }

        // 2. Fallback nativo Web Speech API
        if ('speechSynthesis' in window) {
            const u = new SpeechSynthesisUtterance(clean);
            u.lang = STATE.lang === 'es' ? 'es-ES' : (STATE.lang === 'pt' ? 'pt-BR' : 'en-US');
            u.rate = 1.05;
            window.speechSynthesis.speak(u);
        }
    }

    // 6. Motor de Voz STT (Speech-to-Text) con MediaRecorder y SpeechRecognition
    let mediaRecorder = null;
    let audioChunks = [];
    let mediaStream = null;

    async function toggleVoiceRecording() {
        const micBtn = document.getElementById('aikrofy-mic-btn');
        const textarea = document.getElementById('aikrofy-textarea');

        if (STATE.isListening) {
            // Detener grabación y pasar a confirmación
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
                mediaStream = null;
            }
            STATE.isListening = false;
            if (micBtn) micBtn.classList.remove('recording');
            if (textarea) textarea.placeholder = t('inputPlaceholder');
            return;
        }

        // Si hay una nota de voz pendiente de confirmación previa, descartarla
        discardPendingVoice();

        // Iniciar grabación con MediaRecorder para Whisper en Backend
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaStream = stream;
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) audioChunks.push(e.data);
                };

                mediaRecorder.onstop = () => {
                    if (mediaStream) {
                        mediaStream.getTracks().forEach(track => track.stop());
                        mediaStream = null;
                    }
                    if (audioChunks.length === 0) return;

                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    // Mostrar barra de confirmación/eliminación antes de enviar (idéntico a Krof Copiloto)
                    STATE.pendingVoiceBlob = audioBlob;
                    renderVoiceConfirmationBar(audioBlob);
                };

                mediaRecorder.start();
                STATE.isListening = true;
                if (micBtn) micBtn.classList.add('recording');
                if (textarea) textarea.placeholder = t('listening');
                return;
            } catch (err) {
                console.warn("Microphone access denied or error:", err);
            }
        }

        // Fallback a Web Speech Recognition
        if (('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window)) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            const rec = new SpeechRec();
            rec.lang = STATE.lang === 'es' ? 'es-ES' : (STATE.lang === 'pt' ? 'pt-BR' : 'en-US');
            rec.interimResults = false;

            if (micBtn) micBtn.classList.add('recording');
            rec.onresult = (e) => {
                const text = e.results[0][0].transcript;
                if (micBtn) micBtn.classList.remove('recording');
                if (text) sendUserMessage(text);
            };
            rec.onerror = () => { if (micBtn) micBtn.classList.remove('recording'); };
            rec.onend = () => { if (micBtn) micBtn.classList.remove('recording'); };
            rec.start();
        } else {
            alert("No se pudo acceder al micrófono.");
        }
    }

    function discardPendingVoice() {
        STATE.pendingVoiceBlob = null;
        audioChunks = [];
        const existingBar = document.getElementById("aikrofy-voice-confirm-bar");
        if (existingBar) existingBar.remove();
        const textarea = document.getElementById('aikrofy-textarea');
        if (textarea) textarea.placeholder = t('inputPlaceholder');
    }

    function renderVoiceConfirmationBar(audioBlob) {
        const inputRow = document.getElementById("aikrofy-input-row");
        const footer = document.getElementById("aikrofy-footer");
        if (!inputRow || !footer) return;

        let existingBar = document.getElementById("aikrofy-voice-confirm-bar");
        if (existingBar) existingBar.remove();

        const bar = document.createElement("div");
        bar.id = "aikrofy-voice-confirm-bar";
        bar.style.cssText = "display: flex; align-items: center; justify-content: space-between; gap: 8px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 7px 12px; width: 100%; box-sizing: border-box; font-size: 12px; animation: aik-msg-fade 0.2s ease;";

        bar.innerHTML = `
            <div style="display: flex; align-items: center; gap: 6px; color: #818cf8; font-weight: 600; min-width: 0;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; flex-shrink: 0; box-shadow: 0 0 6px #10b981;"></span>
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Nota de voz lista</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <button type="button" id="aikrofy-discard-voice-btn" style="background: none; border: 1px solid rgba(239, 68, 68, 0.4); color: #ef4444; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.2s ease;">Eliminar</button>
                <button type="button" id="aikrofy-send-voice-btn" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; border: none; padding: 4px 12px; border-radius: 8px; font-size: 11px; font-weight: bold; cursor: pointer; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35); transition: all 0.2s ease; display: inline-flex; align-items: center; gap: 4px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                    <span>Enviar</span>
                </button>
            </div>
        `;

        inputRow.parentNode.insertBefore(bar, inputRow);

        const discardBtn = document.getElementById("aikrofy-discard-voice-btn");
        if (discardBtn) {
            discardBtn.onclick = (e) => {
                e.preventDefault();
                discardPendingVoice();
            };
        }

        const sendBtnEl = document.getElementById("aikrofy-send-voice-btn");
        if (sendBtnEl) {
            sendBtnEl.onclick = async (e) => {
                e.preventDefault();
                if (!STATE.pendingVoiceBlob) return;
                const blobToSend = STATE.pendingVoiceBlob;
                discardPendingVoice();

                const formData = new FormData();
                formData.append('file', blobToSend, 'public_voice.webm');
                formData.append('interface_language', STATE.lang);

                const thinkingId = appendMessage(t('processingVoice'), 'bot', true);

                try {
                    const resp = await fetch(CONFIG.apiHost + '/api/voice/transcribe-public', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    removeMessage(thinkingId);

                    if (data && data.text && data.text.trim()) {
                        sendUserMessage(data.text.trim());
                    }
                } catch (err) {
                    removeMessage(thinkingId);
                    console.error("STT Error:", err);
                }
            };
        }
    }

    // 7. Gestión de Mensajes en la UI
    function appendMessage(text, role, isThinking = false, saveHistory = true) {
        const feed = document.getElementById("aikrofy-feed");
        if (!feed) return null;

        // Limpiar estado de bienvenida si existe
        const welcome = feed.querySelector('.aik-welcome-box');
        if (welcome) {
            welcome.style.display = 'none';
        }

        const msgId = 'aik-msg-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6);
        const row = document.createElement("div");
        row.id = msgId;
        row.className = `aik-msg-row aik-msg-${role}`;

        const senderName = role === 'user' ? 'Tú' : (STATE.agentName || STATE.companyName || 'Asistente');
        
        let contentHtml = '';
        if (isThinking) {
            contentHtml = `
                <div class="aik-msg-header">
                    <span class="aik-msg-sender">${senderName}</span>
                </div>
                <div class="aik-msg-bubble">
                    <div class="aik-thinking">
                        <div class="aik-spinner"></div>
                        <span>${text}</span>
                    </div>
                </div>
            `;
        } else {
            const parsed = role === 'bot' ? parseMarkdown(text) : text.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
            contentHtml = `
                <div class="aik-msg-header">
                    <span class="aik-msg-sender">${senderName}</span>
                    ${false && role === 'bot' ? `
                        <button class="aik-msg-tts-btn" title="Escuchar respuesta" data-text="${encodeURIComponent(text)}">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
                <div class="aik-msg-bubble">
                    <div>${parsed}</div>
                </div>
            `;

            // Persistir mensaje en el almacenamiento de la sesión para navegación continua
            if (saveHistory) {
                STATE.messages.push({ text, role, time: Date.now() });
                if (STATE.messages.length > 50) STATE.messages.shift();
                try {
                    sessionStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(STATE.messages));
                } catch (e) {}
            }
        }

        row.innerHTML = contentHtml;
        feed.appendChild(row);
        feed.scrollTop = feed.scrollHeight;

        // Listener para botones de navegación interactiva (.aik-nav-chip y .aik-site-link)
        row.querySelectorAll('.aik-nav-chip, .aik-site-link').forEach(btn => {
            btn.onclick = (e) => {
                e.preventDefault();
                const target = decodeURIComponent(btn.getAttribute('data-nav') || btn.getAttribute('href') || '');
                if (target) navigateToUrl(target);
            };
        });

        // Listener para botón TTS minimalista
        const ttsBtn = row.querySelector('.aik-msg-tts-btn');
        if (ttsBtn) {
            ttsBtn.onclick = () => {
                const raw = decodeURIComponent(ttsBtn.getAttribute('data-text') || '');
                speakText(raw);
            };
        }

        return msgId;
    }

    function restoreChatHistory() {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY_HISTORY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    STATE.messages = [];
                    parsed.forEach(m => {
                        appendMessage(m.text, m.role, false, true);
                    });
                }
            }
        } catch (e) {
            console.debug("[Aikrofy] History restore error:", e);
        }
    }

    function removeMessage(id) {
        if (!id) return;
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // 8. Envío de Mensajes al Webhook de Aikrofy
    async function sendUserMessage(text) {
        if (!text || !text.trim() || STATE.loading) return;

        const cleanText = text.trim();
        const textarea = document.getElementById("aikrofy-textarea");
        if (textarea) {
            textarea.value = "";
            textarea.style.height = "auto";
        }

        appendMessage(cleanText, 'user');
        STATE.loading = true;

        const sendBtn = document.getElementById("aikrofy-send-btn");
        if (sendBtn) sendBtn.disabled = true;

        const thinkingId = appendMessage(t('thinking'), 'bot', true);

        try {
            const siteLinks = extractSiteStructure();
            const capabilities = detectSiteCapabilities();
            const resp = await fetch(CONFIG.apiHost + '/api/webhooks/webchat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    widget_id: CONFIG.widgetId,
                    message: cleanText,
                    user_id: userId,
                    current_page: window.location.pathname,
                    current_url: window.location.href,
                    host_domain: window.location.origin,
                    page_title: document.title,
                    page_content: extractCurrentPageContent(),
                    site_structure: siteLinks,
                    site_capabilities: capabilities,
                    language: STATE.lang
                })
            });

            const data = await resp.json();
            removeMessage(thinkingId);

            if (data && data.company_name) {
                STATE.companyName = data.company_name;
                const nameEl = document.getElementById("aikrofy-brand-name");
                if (nameEl) nameEl.innerText = data.company_name;
            }
            if (data && data.agent_name) {
                STATE.agentName = data.agent_name;
                const pillText = document.getElementById("aikrofy-fab-text");
                if (pillText) pillText.innerText = data.agent_name;
            }

            let replyText = "";
            if (data.response) {
                replyText = data.response;
            } else if (data.data && data.data.content) {
                replyText = data.data.content;
            } else if (data.error) {
                replyText = "Error: " + data.error;
            } else {
                replyText = "Entendido. ¿En qué más puedo ayudarte?";
            }

            appendMessage(replyText, 'bot');

            // Ejecutar acciones de navegación del sitio del cliente si fueron provistas por el agente
            handleNavigationAction(data.action, data.action_data, replyText);

            if (STATE.voiceEnabled) {
                speakText(replyText);
            }
        } catch (err) {
            removeMessage(thinkingId);
            console.error("[Aikrofy] Webhook error:", err);
            appendMessage(t('errorConnection'), 'bot');
        } finally {
            STATE.loading = false;
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    // 9. Control del Sidebar y Redimensionamiento
    function toggleSidebar(openState) {
        STATE.open = typeof openState === 'boolean' ? openState : !STATE.open;
        try {
            sessionStorage.setItem(STORAGE_KEY_OPEN, STATE.open ? "1" : "0");
        } catch (e) {}

        if (STATE.open) {
            sidebar.classList.add('open');
            if (backdropEl) backdropEl.classList.add('open');
            fabRoot.style.display = 'none';
            setTimeout(() => {
                const txt = document.getElementById('aikrofy-textarea');
                if (txt) txt.focus();
            }, 250);
        } else {
            sidebar.classList.remove('open');
            if (backdropEl) backdropEl.classList.remove('open');
            fabRoot.style.display = 'flex';
            stopSpeaking();
        }
    }

    // Resizer Drag Logic
    const resizer = document.getElementById('aikrofy-resizer');
    let isResizing = false;

    if (resizer) {
        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            isResizing = true;
            resizer.classList.add('resizing');
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';

            const onMouseMove = (moveEvent) => {
                if (!isResizing) return;
                const newWidth = window.innerWidth - moveEvent.clientX;
                if (newWidth >= 320 && newWidth <= Math.min(800, window.innerWidth * 0.85)) {
                    STATE.sidebarWidth = newWidth;
                    sidebar.style.width = `${newWidth}px`;
                    try {
                        sessionStorage.setItem(STORAGE_KEY_WIDTH, String(newWidth));
                    } catch (e) {}
                }
            };

            const onMouseUp = () => {
                isResizing = false;
                resizer.classList.remove('resizing');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);
            };

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        });
    }

    // 10. Event Listeners y Bindings
    fabRoot.onclick = () => toggleSidebar(true);
    document.getElementById('aikrofy-close-btn').onclick = () => toggleSidebar(false);

    // Limpiar Chat
    document.getElementById('aikrofy-clear-btn').onclick = () => {
        STATE.messages = [];
        try {
            sessionStorage.removeItem(STORAGE_KEY_HISTORY);
        } catch (e) {}

        const feed = document.getElementById("aikrofy-feed");
        if (feed) {
            feed.innerHTML = `
                <div class="aik-welcome-box">
                    <div class="aik-welcome-icon" id="aikrofy-welcome-icon-box">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="11" width="18" height="10" rx="2"/>
                            <circle cx="12" cy="5" r="2"/>
                            <path d="M12 7v4M8 15h.01M16 15h.01"/>
                        </svg>
                    </div>
                    <div class="aik-welcome-title">${t('welcomeTitle')}</div>
                    <div class="aik-welcome-desc">${t('welcomeDesc')}</div>
                </div>
            `;
        }
        stopSpeaking();
    };

    // Toggle Lectura por Voz (TTS)
    const voiceToggleBtn = document.getElementById('aikrofy-voice-toggle');
    voiceToggleBtn.onclick = () => {
        STATE.voiceEnabled = !STATE.voiceEnabled;
        try {
            sessionStorage.setItem(STORAGE_KEY_VOICE, STATE.voiceEnabled ? "1" : "0");
        } catch (e) {}

        voiceToggleBtn.classList.toggle('active', STATE.voiceEnabled);
        voiceToggleBtn.title = STATE.voiceEnabled ? t('disableVoice') : t('enableVoice');

        const volIcon = document.getElementById('aikrofy-vol-icon');
        if (STATE.voiceEnabled) {
            volIcon.innerHTML = `
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
            `;
        } else {
            stopSpeaking();
            volIcon.innerHTML = `
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <line x1="23" y1="9" x2="17" y2="15"/>
                <line x1="17" y1="9" x2="23" y2="15"/>
            `;
        }
    };

    // Micrófono STT
    document.getElementById('aikrofy-mic-btn').onclick = toggleVoiceRecording;

    // Enviar Mensaje
    const sendBtn = document.getElementById('aikrofy-send-btn');
    const textarea = document.getElementById('aikrofy-textarea');

    sendBtn.onclick = () => {
        if (textarea) sendUserMessage(textarea.value);
    };

    textarea.onkeydown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendUserMessage(textarea.value);
        }
    };

    textarea.oninput = () => {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    };

    // 11. Restaurar historial previo y estado persistente entre navegación de páginas
    restoreChatHistory();

    const savedWidth = sessionStorage.getItem(STORAGE_KEY_WIDTH);
    if (savedWidth) {
        const parsedW = parseInt(savedWidth, 10);
        if (parsedW >= 320 && parsedW <= Math.min(800, window.innerWidth * 0.85)) {
            STATE.sidebarWidth = parsedW;
            sidebar.style.width = `${parsedW}px`;
        }
    }

    // Mantener sidebar abierto automáticamente si el usuario lo tenía abierto al navegar
    if (sessionStorage.getItem(STORAGE_KEY_OPEN) === "1") {
        toggleSidebar(true);
    }

    // 12. Sincronización en tiempo real del tema con el sitio web anfitrión y el navegador
    applyTheme();

    if (window.matchMedia) {
        try {
            const darkMedia = window.matchMedia('(prefers-color-scheme: dark)');
            const onMediaChange = (e) => {
                if (CONFIG.theme === 'auto') {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            };
            if (darkMedia.addEventListener) {
                darkMedia.addEventListener('change', onMediaChange);
            } else if (darkMedia.addListener) {
                darkMedia.addListener(onMediaChange);
            }
        } catch (e) {}
    }

    // Observar en vivo si el sitio web cliente cambia su clase 'dark' / 'light' o data-theme
    if (typeof MutationObserver !== 'undefined') {
        const themeObserver = new MutationObserver(() => {
            if (CONFIG.theme === 'auto') {
                applyTheme();
            }
        });
        if (document.documentElement) {
            themeObserver.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['class', 'data-theme', 'data-bs-theme', 'data-mode', 'data-color-mode', 'data-theme-mode']
            });
        }
        if (document.body) {
            themeObserver.observe(document.body, {
                attributes: true,
                attributeFilter: ['class', 'data-theme', 'data-bs-theme', 'data-mode', 'data-color-mode', 'data-theme-mode']
            });
        }
    }

    // Observar cambios en localStorage de temas
    window.addEventListener('storage', (e) => {
        if (['theme', 'color-theme', 'mode', 'chakra-ui-color-mode', 'next-theme'].includes(e.key)) {
            if (CONFIG.theme === 'auto') {
                applyTheme();
            }
        }
    });

    // Escuchar mensajes postMessage si el widget o iframe recibe una instrucción de cambio de tema
    window.addEventListener('message', (e) => {
        if (e.data && (e.data.type === 'AIKROFY_SET_THEME' || e.data.type === 'SET_THEME')) {
            const requested = e.data.theme;
            if (['dark', 'light', 'auto'].includes(requested)) {
                CONFIG.theme = requested;
                applyTheme(requested === 'auto' ? undefined : requested);
            }
        }
    });

    // Exponer API pública del widget para desarrolladores del sitio web anfitrión
    const aikrofyPublicApi = {
        version: "2.5.0",
        open: () => toggleSidebar(true),
        close: () => toggleSidebar(false),
        toggle: () => toggleSidebar(),
        sendMessage: (msg) => sendUserMessage(msg),
        setLanguage: (lang) => executeLanguageChange(lang),
        changeLanguage: (lang) => executeLanguageChange(lang),
        setTheme: (theme) => executeThemeChange(theme),
        changeTheme: (theme) => executeThemeChange(theme),
        getTheme: () => STATE.currentTheme,
        getLanguage: () => STATE.lang,
        navigate: (target) => navigateToUrl(target),
        highlight: (selector) => highlightElement(selector),
        getCapabilities: () => detectSiteCapabilities(),
        on: (eventName, callback) => {
            if (typeof callback !== 'function') return;
            const fullEventName = eventName.startsWith('aikrofy:') ? eventName : `aikrofy:${eventName}`;
            window.addEventListener(fullEventName, (e) => callback(e.detail || {}));
        }
    };

    window.AikrofyWidget = aikrofyPublicApi;
    window.Aikrofy = aikrofyPublicApi;

})();
