'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'next-themes';
import {
    Terminal,
    Download,
    HeartHandshake,
    Cpu,
    ShieldCheck,
    Globe,
    Users,
    ArrowRight,
    CheckCircle2,
    Sparkles,
    Key,
    Copy,
    Check,
    ExternalLink,
    Code2,
    Server,
    Loader2,
    Sun,
    Moon
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { LanguageSwitcher } from '@/components/shared/language-switcher';
import { PlatformChatWidget } from '@/components/features/platform-chat-widget';

export default function CommunityOpenCorePage() {
    const { t } = useTranslation();
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const [copiedCmd, setCopiedCmd] = useState(false);

    // Self-Hosted Activation Token Generator State
    const [tokenEmail, setTokenEmail] = useState('');
    const [tokenName, setTokenName] = useState('');
    const [tokenOrg, setTokenOrg] = useState('');
    const [tokenCountry, setTokenCountry] = useState('Ecuador');
    const [isGenerating, setIsGenerating] = useState(false);
    const [generatedToken, setGeneratedToken] = useState<string | null>(null);
    const [copiedToken, setCopiedToken] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const installCmd = `git clone https://github.com/UnderlifeFundation/aikrofy.git
cd aikrofy && cp .env.community.example .env
docker compose -f docker-compose.community.yml up -d`;

    const handleCopyCmd = () => {
        navigator.clipboard.writeText(installCmd);
        setCopiedCmd(true);
        setTimeout(() => setCopiedCmd(false), 2500);
    };

    const handleGenerateToken = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!tokenEmail || !tokenName) {
            toast.error(t('community.token_required_err', 'Nombre y correo electrónico son requeridos para emitir tu token.'));
            return;
        }
        setIsGenerating(true);
        try {
            const res = await apiClient.post('/community/generate-token', {
                email: tokenEmail,
                name: tokenName,
                organization: tokenOrg || tokenName,
                country: tokenCountry,
            });
            if (res.data?.token) {
                setGeneratedToken(res.data.token);
                toast.success(t('community.token_success_toast', '¡Token de Activación Oficial emitido exitosamente!'));
            }
        } catch (err: any) {
            toast.error(err?.response?.data?.error || t('community.token_err_toast', 'Error generando token de activación'));
        } finally {
            setIsGenerating(false);
        }
    };

    const handleCopyToken = () => {
        if (!generatedToken) return;
        navigator.clipboard.writeText(generatedToken);
        setCopiedToken(true);
        toast.info(t('community.token_copied_toast', 'Token copiado al portapapeles'));
        setTimeout(() => setCopiedToken(false), 2500);
    };

    return (
        <div className="min-h-screen bg-background text-foreground transition-colors duration-300 selection:bg-emerald-500/30">
            <PlatformChatWidget 
                scope="community" 
                title="Krof Comunitario" 
                subtitle="Fundación Underlife · Soporte & Subvenciones" 
            />
            {/* Top Institutional Banner */}
            <div className="border-b border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-950/40 px-3 sm:px-4 py-2 sm:py-2.5 text-center text-xs sm:text-sm text-emerald-700 dark:text-emerald-300 font-medium">
                <span className="font-semibold">🏛️ FUNDACIÓN UNDERLIFE</span>
                <span className="hidden sm:inline"> — {t('community.top_banner', 'Programa de Inclusión Productiva Digital & Soberanía Tecnológica en Ecuador y Perú (2026–2027)')}</span>
                <span className="inline sm:hidden"> — {t('community.top_banner_mobile', 'Inclusión Digital & Soberanía Tecnológica (2026–2027)')}</span>
            </div>

            {/* Navbar */}
            <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-3 sm:px-6 lg:px-8 py-3">
                    <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                        <Link href="/" className="flex items-center gap-2 sm:gap-3 min-w-0">
                            <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="h-8 w-8 sm:h-9 sm:w-9 object-contain shrink-0" />
                            <div className="min-w-0">
                                <div className="flex items-center gap-1.5 sm:gap-2">
                                    <span className="text-base sm:text-lg font-bold tracking-tight text-foreground">Aikrofy</span>
                                    <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] sm:text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                                        Community
                                    </span>
                                </div>
                                <p className="hidden md:block text-[11px] text-muted-foreground truncate">{t('community.sub_tag', 'Impulsado por Fundación Underlife · Ingeniería WEBLIFETECH')}</p>
                            </div>
                        </Link>
                    </div>

                    <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
                        <LanguageSwitcher />

                        {mounted ? (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl hover:bg-accent shrink-0"
                                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                                title="Cambiar tema"
                            >
                                <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-amber-500" />
                                <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-sky-400" />
                            </Button>
                        ) : (
                            <div className="w-8 h-8 sm:w-9 sm:h-9" />
                        )}

                        <a
                            href="https://github.com/UnderlifeFundation/aikrofy"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hidden lg:inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2 text-xs font-medium text-foreground hover:bg-accent transition"
                        >
                            <Code2 className="h-4 w-4 text-emerald-500" />
                            {t('community.github_btn', 'GitHub Open-Core')}
                            <ExternalLink className="h-3 w-3 opacity-60" />
                        </a>
                        <Link href="/register?category=emprendimiento" className="shrink-0">
                            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5 cursor-pointer shadow-sm text-xs sm:text-sm px-2.5 sm:px-3 h-8 sm:h-9">
                                <Sparkles className="h-3.5 w-3.5 shrink-0" />
                                <span className="hidden sm:inline">{t('community.request_subsidized_btn', 'Solicitar Cuenta Subvencionada')}</span>
                                <span className="inline sm:hidden">{t('community.request_subsidized_btn_short', 'Solicitar Beca')}</span>
                            </Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="relative overflow-hidden py-14 sm:py-20">
                <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                    <div className="mx-auto max-w-3xl text-center space-y-6">
                        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                            <HeartHandshake className="h-4 w-4" />
                            {t('community.hero_pill', 'Democratización de Fuerza Laboral Autónoma para Emprendedores y Comunidades Vulnerables')}
                        </div>
                        <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
                            {t('community.hero_title_prefix', 'Inteligencia Artificial Soberana para la')}{' '}
                            <span className="bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 bg-clip-text text-transparent">
                                {t('community.hero_title_highlight', 'Economía Popular')}
                            </span>
                        </h1>
                        <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
                            {t('community.hero_desc', 'Aikrofy permite a microempresas, artesanos, cooperativas, comercios locales y ONGs en Ecuador, Perú y el mundo automatizar su atención, POS nativo, agendamiento, catálogo y ventas 24/7 por WhatsApp y Webchat. Elige entre descargar la versión auto-hospedada (Self-Hosted) con tu Token Oficial de Activación gratuita, o activar una cuenta en la nube subvencionada con créditos gratuitos otorgados por Fundación Underlife.')}
                        </p>

                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                            <Link href="/register?category=emprendimiento" className="w-full sm:w-auto">
                                <Button size="lg" className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-2 h-12 px-6 cursor-pointer shadow-md shadow-emerald-500/20">
                                    <Sparkles className="h-4 w-4" />
                                    {t('community.create_subsidized_btn', 'Crear Cuenta con Beca de Créditos Gratis')}
                                    <ArrowRight className="h-4 w-4" />
                                </Button>
                            </Link>
                            <a
                                href="#self-hosted-activation"
                                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-md border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 px-6 h-12 text-sm font-semibold text-cyan-700 dark:text-cyan-300 transition"
                            >
                                <Key className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
                                {t('community.get_token_btn', 'Obtener Token de Activación Self-Hosted')}
                            </a>
                        </div>
                    </div>

                    {/* Dual Path Cards: Self-Hosted Open-Core vs Subsidized Cloud */}
                    <div className="mt-14 grid gap-8 lg:grid-cols-2">
                        {/* Card 1: Self-Hosted Open-Core */}
                        <Card className="border-border bg-card text-card-foreground shadow-xl">
                            <CardHeader className="space-y-2 border-b border-border/80 pb-6">
                                <div className="flex items-center justify-between">
                                    <span className="inline-flex items-center gap-1.5 rounded-md bg-cyan-500/10 px-2.5 py-1 text-xs font-semibold text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                                        <Server className="h-3.5 w-3.5" />
                                        {t('community.opt1_badge', 'Opción 1 · Auto-Hospedado (Self-Hosted)')}
                                    </span>
                                    <span className="text-xs font-mono text-muted-foreground">PolyForm Noncommercial 1.0</span>
                                </div>
                                <CardTitle className="text-2xl font-bold text-foreground">
                                    {t('community.opt1_title', 'Aikrofy Community Edition (Open-Core)')}
                                </CardTitle>
                                <CardDescription className="text-muted-foreground">
                                    {t('community.opt1_desc', 'Instala Aikrofy en tu propio servidor VPS o máquina local. Conecta directamente tus propias claves API de IA (BYOK) sin intermediarios.')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-6">
                                <ul className="space-y-3 text-sm text-foreground/90">
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt1_f1', '100% BYOK (Bring Your Own Key): Conecta tu propia API Key de OpenAI, Groq, Google Gemini, Anthropic, DeepSeek u OpenRouter con uso ilimitado local.')}</span>
                                    </li>
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt1_f2', 'POS Nativo & Códigos de Barras EAN-13 / QR: Administra productos, inventario y ventas físicas y por WhatsApp de forma 100% soberana.')}</span>
                                    </li>
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt1_f3', 'Puente WhatsApp Single-Account: Impulsado por @agenticnucleus/whatsapp-multitenant pre-configurado para 1 cuenta por servidor.')}</span>
                                    </li>
                                </ul>

                                {/* Terminal Snippet */}
                                <div className="rounded-xl border border-border bg-muted/60 dark:bg-slate-950 p-4 font-mono text-xs">
                                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/80 text-muted-foreground">
                                        <span className="flex items-center gap-1.5">
                                            <Terminal className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
                                            {t('community.quick_docker', 'Instalación rápida con Docker Compose')}
                                        </span>
                                        <button
                                            type="button"
                                            onClick={handleCopyCmd}
                                            className="inline-flex items-center gap-1 text-[11px] text-cyan-600 dark:text-cyan-400 hover:opacity-80 cursor-pointer"
                                        >
                                            {copiedCmd ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                            {copiedCmd ? t('community.copied', 'Copiado') : t('community.copy', 'Copiar')}
                                        </button>
                                    </div>
                                    <pre className="overflow-x-auto text-foreground font-mono leading-relaxed">{installCmd}</pre>
                                </div>

                                <div className="flex flex-wrap gap-3 pt-2">
                                    <a
                                        href="https://github.com/UnderlifeFundation/aikrofy"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-2.5 px-4 text-sm transition shadow-sm"
                                    >
                                        <Download className="h-4 w-4" />
                                        {t('community.github_repo', 'Repositorio Oficial en GitHub')}
                                    </a>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Card 2: Subsidized Cloud Account */}
                        <Card className="border-emerald-500/40 bg-card text-card-foreground shadow-xl">
                            <CardHeader className="space-y-2 border-b border-emerald-500/20 pb-6">
                                <div className="flex items-center justify-between">
                                    <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-300 border border-emerald-500/20">
                                        <Sparkles className="h-3.5 w-3.5" />
                                        {t('community.opt2_badge', 'Opción 2 · Nube Subvencionada (Cero Servidores)')}
                                    </span>
                                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">{t('community.opt2_tag', 'Beca de Bienvenida Activa')}</span>
                                </div>
                                <CardTitle className="text-2xl font-bold text-foreground">
                                    {t('community.opt2_title', 'Acceso Cloud Subvencionado para PyMEs y Emprendedores')}
                                </CardTitle>
                                <CardDescription className="text-muted-foreground">
                                    {t('community.opt2_desc', 'Ideal para negocios populares, microempresas y emprendimientos que no disponen de servidor propio. Regístrate y recibe créditos gratuitos al instante.')}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-6">
                                <div className="grid grid-cols-3 gap-3 text-center">
                                    <div className="rounded-xl border border-emerald-500/20 bg-muted/40 p-3">
                                        <div className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">{t('community.opt2_stat1_num', '5,000')}</div>
                                        <div className="text-[11px] text-muted-foreground">{t('community.opt2_stat1_label', 'Créditos Gratis Emprendimiento')}</div>
                                    </div>
                                    <div className="rounded-xl border border-emerald-500/20 bg-muted/40 p-3">
                                        <div className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">{t('community.opt2_stat2_num', '10,000')}</div>
                                        <div className="text-[11px] text-muted-foreground">{t('community.opt2_stat2_label', 'Créditos Gratis PyME Social')}</div>
                                    </div>
                                    <div className="rounded-xl border border-emerald-500/20 bg-muted/40 p-3">
                                        <div className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">BYOK</div>
                                        <div className="text-[11px] text-muted-foreground">{t('community.opt2_stat3_label', 'O conecta tu propia API Key')}</div>
                                    </div>
                                </div>

                                <ul className="space-y-3 text-sm text-foreground/90">
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt2_f1', 'Activación Inmediata sin Tarjeta: Empieza a atender clientes en WhatsApp escaneando un código QR en menos de 2 minutos.')}</span>
                                    </li>
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt2_f2', 'Sostenibilidad Continua: Al terminar tu beca inicial de créditos, puedes conectar tus propias API Keys (OpenAI/Groq/Gemini) o realizar micro-recargas accesibles desde $5 USD.')}</span>
                                    </li>
                                    <li className="flex items-start gap-2.5">
                                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                                        <span>{t('community.opt2_f3', 'Acompañamiento Comunitario: Diseñado para reducir la brecha digital en zonas urbanas periféricas y rurales de Ecuador y Perú.')}</span>
                                    </li>
                                </ul>

                                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                                    <Link href="/register?category=emprendimiento" className="flex-1">
                                        <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 h-auto text-sm gap-2 cursor-pointer shadow-sm">
                                            {t('community.register_subsidized_now', 'Registrar Cuenta Subvencionada Ahora')}
                                            <ArrowRight className="h-4 w-4" />
                                        </Button>
                                    </Link>
                                    <Link href="/beta-register">
                                        <Button variant="outline" className="w-full sm:w-auto border-emerald-500/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/10 py-2.5 h-auto text-xs cursor-pointer">
                                            {t('community.apply_ngo', 'Postular Organización / ONG')}
                                        </Button>
                                    </Link>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </section>

            {/* SECTION: Self-Hosted Official Activation Token Generator */}
            <section id="self-hosted-activation" className="border-t border-border bg-muted/20 py-14 scroll-mt-20">
                <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 space-y-8">
                    <div className="text-center space-y-3">
                        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-1 text-xs font-semibold text-cyan-700 dark:text-cyan-300">
                            <ShieldCheck className="h-4 w-4" />
                            {t('community.token_badge', 'Activación Criptográfica de Instancia Auto-Hospedada')}
                        </div>
                        <h2 className="text-3xl font-extrabold text-foreground">
                            {t('community.token_title', 'Obtén tu Token de Activación Oficial para tu Servidor')}
                        </h2>
                        <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
                            {t('community.token_desc', 'Para garantizar la soberanía operativa y la integridad del software, las instancias auto-hospedadas de Aikrofy requieren un Token de Activación Oficial gratuito emitido por Fundación Underlife para la comunidad open-core.')}
                        </p>
                    </div>

                    <Card className="border-cyan-500/30 bg-card text-card-foreground shadow-lg">
                        <CardHeader className="border-b border-border">
                            <CardTitle className="text-lg flex items-center gap-2 text-cyan-700 dark:text-cyan-400">
                                <Key className="h-5 w-5" />
                                {t('community.token_card_title', 'Registro y Emisión Inmediata de Token de Activación')}
                            </CardTitle>
                            <CardDescription className="text-xs text-muted-foreground">
                                {t('community.token_card_desc', 'Ingresa tus datos para registrar tu nodo en el observatorio comunitario y recibir tu token criptográfico listo para pegar en tu servidor.')}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="p-6 space-y-6">
                            {!generatedToken ? (
                                <form onSubmit={handleGenerateToken} className="space-y-4">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-1.5">
                                            <Label className="text-xs text-foreground/80">{t('community.token_input_name', 'Nombre Completo / Representante')} *</Label>
                                            <Input
                                                value={tokenName}
                                                onChange={(e) => setTokenName(e.target.value)}
                                                placeholder="Ej. María Quispe / Carlos Mendoza"
                                                className="bg-background border-border"
                                                required
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs text-foreground/80">{t('community.token_input_email', 'Correo Institucional o del Responsable')} *</Label>
                                            <Input
                                                type="email"
                                                value={tokenEmail}
                                                onChange={(e) => setTokenEmail(e.target.value)}
                                                placeholder="tu-correo@organizacion.org"
                                                className="bg-background border-border"
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-1.5">
                                            <Label className="text-xs text-foreground/80">{t('community.token_input_org', 'Nombre de la Organización, Taller o Negocio')}</Label>
                                            <Input
                                                value={tokenOrg}
                                                onChange={(e) => setTokenOrg(e.target.value)}
                                                placeholder="Ej. Asociación de Caficultores / Mi PyME"
                                                className="bg-background border-border"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs text-foreground/80">{t('community.token_input_country', 'País de Despliegue')}</Label>
                                            <select
                                                value={tokenCountry}
                                                onChange={(e) => setTokenCountry(e.target.value)}
                                                className="flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground"
                                            >
                                                <option value="Ecuador">Ecuador</option>
                                                <option value="Peru">Perú</option>
                                                <option value="Colombia">Colombia</option>
                                                <option value="Mexico">México</option>
                                                <option value="Chile">Chile</option>
                                                <option value="Argentina">Argentina</option>
                                                <option value="Espana">España</option>
                                                <option value="Estados Unidos">Estados Unidos</option>
                                                <option value="Republica Checa">República Checa</option>
                                                <option value="Global">Otro (Global)</option>
                                            </select>
                                        </div>
                                    </div>

                                    <Button
                                        type="submit"
                                        disabled={isGenerating}
                                        className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold h-11 text-sm gap-2 cursor-pointer mt-2 shadow-sm"
                                    >
                                        {isGenerating ? (
                                            <>
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                Generando Token Criptográfico...
                                            </>
                                        ) : (
                                            <>
                                                <Key className="h-4 w-4" />
                                                {t('community.token_btn_generate', 'Generar Token de Activación Gratuito')}
                                            </>
                                        )}
                                    </Button>
                                </form>
                            ) : (
                                <div className="space-y-4">
                                    <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 space-y-3">
                                        <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
                                            <CheckCircle2 className="h-5 w-5" />
                                            {t('community.token_generated_title', 'Tu Token Oficial de Activación Comunitaria:')} ({tokenOrg || tokenName})
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            {t('community.token_generated_help', 'Guarda este token. Lo necesitarás en el paso de instalación web (/activate) o en tu archivo .env (COMMUNITY_LICENSE_TOKEN).')}
                                        </p>
                                        <div className="relative">
                                            <pre className="p-3 rounded-lg bg-muted border border-border text-[11px] font-mono text-cyan-700 dark:text-cyan-300 break-all select-all overflow-x-auto">
                                                {generatedToken}
                                            </pre>
                                            <Button
                                                size="sm"
                                                onClick={handleCopyToken}
                                                className="absolute top-2 right-2 h-7 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold gap-1.5"
                                            >
                                                {copiedToken ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                                                {copiedToken ? t('community.copied', 'Copiado') : t('community.copy', 'Copiar')}
                                            </Button>
                                        </div>
                                    </div>

                                    <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setGeneratedToken(null)}
                                            className="text-xs text-muted-foreground hover:text-foreground"
                                        >
                                            Emitir otro token para otro servidor
                                        </Button>
                                        <Link href="/register?category=emprendimiento">
                                            <Button size="sm" variant="outline" className="border-emerald-500/40 text-emerald-700 dark:text-emerald-300 text-xs">
                                                ¿Prefieres usar la nube sin configurar servidores? Regístrate aquí
                                            </Button>
                                        </Link>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </section>

            {/* Impact & Development Cooperation Section (Ecuador & Peru 2027) */}
            <section className="border-t border-border bg-background py-16">
                <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
                    <div className="max-w-3xl space-y-3">
                        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                            <Globe className="h-4 w-4" />
                            Impacto Medible y Sostenibilidad (Programa 2027 · Ecuador & Perú)
                        </div>
                        <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
                            Tecnología Productiva para la Inclusión Económica Sostenible
                        </h2>
                        <p className="text-sm sm:text-base text-muted-foreground">
                            Más allá de la formación teórica, Fundación Underlife entrega infraestructura productiva real: cada beneficiario recibe su propio agente operativo configurado, catálogo digitalizado y canal de ventas automatizado con métricas auditables en tiempo real.
                        </p>
                    </div>

                    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                        <div className="rounded-2xl border border-border bg-card p-6 space-y-2 shadow-sm">
                            <Users className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                            <div className="text-2xl font-bold text-foreground">Emprendedores y Microempresas</div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                Focalizado en mujeres jefas de hogar, jóvenes emprendedores, asociaciones de artesanos y pequeños comercios vulnerables en Ecuador y Perú.
                            </p>
                        </div>

                        <div className="rounded-2xl border border-border bg-card p-6 space-y-2 shadow-sm">
                            <Key className="h-6 w-6 text-cyan-600 dark:text-cyan-400" />
                            <div className="text-2xl font-bold text-foreground">Autonomía BYOK Sin Lock-In</div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                Cero dependencia forzada: cada cuenta puede conectar sus propias API keys de modelos abiertos o comerciales (Groq, Gemini, OpenAI, DeepSeek).
                            </p>
                        </div>

                        <div className="rounded-2xl border border-border bg-card p-6 space-y-2 shadow-sm">
                            <Cpu className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                            <div className="text-2xl font-bold text-foreground">Atención y Ventas 24/7</div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                Incremento directo de ingresos mediante respuesta inmediata en WhatsApp, agendamiento automático y reducción de pérdida de clientes.
                            </p>
                        </div>

                        <div className="rounded-2xl border border-border bg-card p-6 space-y-2 shadow-sm">
                            <ShieldCheck className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                            <div className="text-2xl font-bold text-foreground">Transparencia y Código Abierto</div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                Repositorio público auditable en GitHub bajo Fundación Underlife y trazabilidad completa de beneficiarios directos e indirectos.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-border bg-muted/40 py-10 text-xs text-muted-foreground">
                <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                        <p className="font-semibold text-foreground">{t('community.footer_title', 'FUNDACIÓN UNDERLIFE & WEBLIFETECH')}</p>
                        <p>{t('community.footer_subtitle', 'Plataforma Aikrofy Open-Core · Soberanía Operativa e Inclusión Productiva Digital.')}</p>
                    </div>
                    <div className="flex items-center gap-6">
                        <a href="https://github.com/UnderlifeFundation/aikrofy" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">
                            GitHub Repository
                        </a>
                        <Link href="/register" className="hover:text-foreground transition">
                            Registro Subvencionado
                        </Link>
                        <Link href="/login" className="hover:text-foreground transition">
                            Iniciar Sesión
                        </Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}
