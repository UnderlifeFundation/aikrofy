'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from 'next-themes';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
    Building2,
    Briefcase,
    Users,
    Package,
    Cpu,
    Sparkles,
    User,
    Mail,
    Phone,
    ArrowRight,
    ArrowLeft,
    CheckCircle2,
    Clock,
    Lock,
    SmilePlus,
    Sun,
    Moon,
    Zap,
    CornerDownLeft,
    Check,
    Bot,
    ChevronRight,
    ShieldCheck,
    Sparkle,
    Rocket
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { LanguageSwitcher } from '@/components/shared/language-switcher';
import apiClient from '@/lib/api-client';

export default function BetaRegisterPage() {
    const router = useRouter();
    const { t } = useTranslation();
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [formData, setFormData] = useState(() => {
        if (typeof window !== 'undefined') {
            try {
                const saved = localStorage.getItem('aikrofy_beta_form');
                if (saved) return JSON.parse(saved);
            } catch (e) {}
        }
        return {
            company_name: '',
            industry: 'services',
            employee_count: '1-5',
            products_services: '',
            ai_experience: 'none',
            ai_results_satisfaction: 'not_applicable',
            ai_expectations: '',
            contact_name: '',
            role_in_company: '',
            email: '',
            phone: ''
        };
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isCompleted, setIsCompleted] = useState(false);
    const [touchedOption, setTouchedOption] = useState<string | null>(null);
    const [bottomOffset, setBottomOffset] = useState(0);
    const topAnchorRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setMounted(true);
    }, []);

    // Save progress to local storage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                localStorage.setItem('aikrofy_beta_form', JSON.stringify(formData));
            } catch (e) {}
        }
    }, [formData]);

    // Keyboard-aware bottom bar: moves above virtual keyboard on mobile/tablet
    useEffect(() => {
        if (typeof window === 'undefined') return;
        const vv = window.visualViewport;
        if (!vv) return;
        const update = () => {
            const keyboardH = Math.max(0, window.innerHeight - vv.height - (vv.offsetTop || 0));
            setBottomOffset(keyboardH);
        };
        vv.addEventListener('resize', update);
        vv.addEventListener('scroll', update);
        return () => {
            vv.removeEventListener('resize', update);
            vv.removeEventListener('scroll', update);
        };
    }, []);

    const QUESTIONS = useMemo(() => [
        {
            id: 'company_name',
            title: t('betaRegister.q1.title', '¿Cuál es el nombre de tu empresa u organización?'),
            subtitle: t('betaRegister.q1.subtitle', 'Queremos conocer el negocio para el que implementarás IA.'),
            type: 'text',
            field: 'company_name',
            placeholder: t('betaRegister.q1.placeholder', 'Ej. Acme Corp / Soluciones Tecnológicas'),
            icon: Building2,
            badge: t('betaRegister.q1.badge', 'Identidad Corporativa')
        },
        {
            id: 'industry',
            title: t('betaRegister.q2.title', '¿A qué sector o industria pertenece la empresa?'),
            subtitle: t('betaRegister.q2.subtitle', 'Esto nos permite personalizar las plantillas y flujos conversacionales.'),
            type: 'select',
            field: 'industry',
            options: [
                { label: t('betaRegister.q2.opt1', 'Salud y Bienestar / Estética'), value: 'health_wellness', desc: t('betaRegister.q2.opt1Desc', 'Clínicas, gimnasios, spas, consultorios'), badge: t('betaRegister.q2.badgePopular', 'Popular') },
                { label: t('betaRegister.q2.opt2', 'Comercio Electrónico / Retail'), value: 'ecommerce', desc: t('betaRegister.q2.opt2Desc', 'Tiendas online, ventas de productos'), badge: t('betaRegister.q2.badgeHighDemand', 'Alta Demanda') },
                { label: t('betaRegister.q2.opt3', 'Servicios Profesionales / B2B'), value: 'services', desc: t('betaRegister.q2.opt3Desc', 'Consultoría, agencias, software, legal') },
                { label: t('betaRegister.q2.opt4', 'Inmobiliaria y Real Estate'), value: 'real_estate', desc: t('betaRegister.q2.opt4Desc', 'Venta/alquiler de propiedades, desarrollo') },
                { label: t('betaRegister.q2.opt5', 'Educación y Formación'), value: 'education', desc: t('betaRegister.q2.opt5Desc', 'Academias, cursos, infoproductos') },
                { label: t('betaRegister.q2.opt6', 'Otro Sector'), value: 'other', desc: t('betaRegister.q2.opt6Desc', 'Otras industrias no mencionadas') }
            ],
            icon: Briefcase,
            badge: t('betaRegister.q2.badge', 'Personalización de IA')
        },
        {
            id: 'employee_count',
            title: t('betaRegister.q3.title', '¿Cuántos colaboradores o empleados integran tu equipo?'),
            subtitle: t('betaRegister.q3.subtitle', 'Nos ayuda a proyectar la capacidad operativa necesaria.'),
            type: 'select',
            field: 'employee_count',
            options: [
                { label: t('betaRegister.q3.opt1', '1 a 5 personas'), value: '1-5', desc: t('betaRegister.q3.opt1Desc', 'Emprendedores y equipos pequeños') },
                { label: t('betaRegister.q3.opt2', '6 a 20 personas'), value: '6-20', desc: t('betaRegister.q3.opt2Desc', 'Empresas en aceleración') },
                { label: t('betaRegister.q3.opt3', '21 a 50 personas'), value: '21-50', desc: t('betaRegister.q3.opt3Desc', 'Pymes consolidadas') },
                { label: t('betaRegister.q3.opt4', 'Más de 50 personas'), value: '50+', desc: t('betaRegister.q3.opt4Desc', 'Grandes corporativos / Enterprise'), badge: t('betaRegister.q3.badgeEnterprise', 'Enterprise') }
            ],
            icon: Users,
            badge: t('betaRegister.q3.badge', 'Dimensionamiento')
        },
        {
            id: 'products_services',
            title: t('betaRegister.q4.title', '¿Qué productos o servicios principales comercializan?'),
            subtitle: t('betaRegister.q4.subtitle', 'Describe brevemente la propuesta de valor principal de tu negocio.'),
            type: 'textarea',
            field: 'products_services',
            placeholder: t('betaRegister.q4.placeholder', 'Ej. Venta de membresías anuales, consultas especializadas y suplementos...'),
            icon: Package,
            badge: t('betaRegister.q4.badge', 'Catálogo & Oferta')
        },
        {
            id: 'ai_experience',
            title: t('betaRegister.q5.title', '¿Cuál es el nivel actual de adopción de IA en tu empresa?'),
            subtitle: t('betaRegister.q5.subtitle', 'Identifica la etapa tecnológica en la que se encuentran hoy.'),
            type: 'select',
            field: 'ai_experience',
            options: [
                { label: t('betaRegister.q5.opt1', 'Nivel Inicial / Primera Vez'), value: 'none', desc: t('betaRegister.q5.opt1Desc', 'Uso personal puntual (ChatGPT), sin integración empresarial') },
                { label: t('betaRegister.q5.opt2', 'Nivel Intermedio'), value: 'intermediate', desc: t('betaRegister.q5.opt2Desc', 'Herramientas no-code (Make, Zapier) o chatbots básicos') },
                { label: t('betaRegister.q5.opt3', 'Nivel Avanzado'), value: 'advanced', desc: t('betaRegister.q5.opt3Desc', 'Flujos automatizados y requerimiento de agentes autónomos IA') }
            ],
            icon: Cpu,
            badge: t('betaRegister.q5.badge', 'Madurez Digital')
        },
        {
            id: 'ai_results_satisfaction',
            title: t('betaRegister.q6.title', 'Si han utilizado IA previamente, ¿cómo ha sido su experiencia?'),
            subtitle: t('betaRegister.q6.subtitle', 'Queremos entender qué ha funcionado bien y qué desafíos han tenido.'),
            type: 'select',
            field: 'ai_results_satisfaction',
            options: [
                { label: t('betaRegister.q6.opt1', 'Altamente Positiva (Se cumplieron expectativas)'), value: 'positive', desc: t('betaRegister.q6.opt1Desc', 'Generó ahorro de tiempo y mejoró la atención') },
                { label: t('betaRegister.q6.opt2', 'Media / Parcial (Se logró algo pero falta inteligencia)'), value: 'neutral', desc: t('betaRegister.q6.opt2Desc', 'Respuestas rígidas, falta de contexto o agendamiento') },
                { label: t('betaRegister.q6.opt3', 'Frustrante / Deficiente (No funcionó)'), value: 'negative', desc: t('betaRegister.q6.opt3Desc', 'Muy complejo de mantener o respuestas incorrectas') },
                { label: t('betaRegister.q6.opt4', 'No hemos aplicado IA aún'), value: 'not_applicable', desc: t('betaRegister.q6.opt4Desc', 'Será nuestra primera experiencia empresarial') }
            ],
            icon: SmilePlus,
            badge: t('betaRegister.q6.badge', 'Feedback Histórico')
        },
        {
            id: 'ai_expectations',
            title: t('betaRegister.q7.title', '¿Qué esperan lograr principalmente con Aikrofy IA?'),
            subtitle: t('betaRegister.q7.subtitle', 'Tus metas guiarán la configuración inicial de tus agentes autónomos.'),
            type: 'textarea',
            field: 'ai_expectations',
            placeholder: t('betaRegister.q7.placeholder', 'Ej. Automatizar respuestas 24/7 en WhatsApp, agendar citas automáticamente y aumentar conversiones...'),
            icon: Sparkles,
            badge: t('betaRegister.q7.badge', 'Objetivo Clave')
        },
        {
            id: 'contact_info',
            title: t('betaRegister.q8.title', '¡Casi listos! Completa tus datos de contacto directo'),
            subtitle: t('betaRegister.q8.subtitle', 'Aquí enviaremos tu aprobación y credenciales de acceso a la Beta.'),
            type: 'contact_group',
            field: 'contact_group',
            icon: User,
            badge: t('betaRegister.q8.badge', 'Paso Final')
        }
    ], [t]);

    const step = QUESTIONS[currentStep];

    const updateField = (field: string, value: string) => {
        setFormData((prev: any) => ({ ...prev, [field]: value }));
    };

    const handleSelectOption = (field: string, value: string) => {
        setTouchedOption(value);
        updateField(field, value);
        
        // Haptic feedback simulation & auto-advance smooth transition
        setTimeout(() => {
            setTouchedOption(null);
            if (currentStep < QUESTIONS.length - 1) {
                setCurrentStep(prev => prev + 1);
            }
        }, 200);
    };

    const handleNext = () => {
        // Step Validation
        if (step.type === 'text' && !formData[step.field as keyof typeof formData]?.trim()) {
            toast.error(t('betaRegister.validationText', 'Por favor completa este campo para continuar.'));
            return;
        }
        if (step.type === 'select' && !formData[step.field as keyof typeof formData]) {
            toast.error(t('betaRegister.validationSelect', 'Por favor selecciona una opción.'));
            return;
        }
        if (step.type === 'textarea' && !formData[step.field as keyof typeof formData]?.trim()) {
            toast.error(t('betaRegister.validationText', 'Por favor comparte tu respuesta para continuar.'));
            return;
        }

        if (currentStep < QUESTIONS.length - 1) {
            setCurrentStep(prev => prev + 1);
        } else {
            handleSubmit();
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    const handleSubmit = async () => {
        // Verify company name
        if (!formData.company_name?.trim()) {
            toast.error('Por favor ingresa el nombre de tu empresa.');
            setCurrentStep(0);
            return;
        }

        if (!formData.contact_name?.trim() || !formData.email?.trim() || !formData.phone?.trim() || !formData.role_in_company?.trim()) {
            toast.error(t('betaRegister.validationContact', 'Por favor completa todos tus datos de contacto.'));
            return;
        }

        const payload = {
            ...formData,
            employee_count: formData.employee_count || '1-5',
            industry: formData.industry || 'other',
            ai_experience: formData.ai_experience || 'none',
            ai_results_satisfaction: formData.ai_results_satisfaction || 'not_applicable'
        };

        setIsSubmitting(true);
        try {
            const { data } = await apiClient.post('/beta/register', payload);
            if (data.registered_user) {
                toast.info(data.message);
                router.push('/login');
                return;
            }
            if (typeof window !== 'undefined') {
                try {
                    localStorage.removeItem('aikrofy_beta_form');
                } catch (e) {}
            }
            setIsCompleted(true);
            if (data.message) {
                toast.success(data.message);
            } else {
                toast.success(t('common.success', '¡Registro enviado con éxito!'));
            }
        } catch (err: any) {
            const errorMsg = err?.response?.data?.error || err?.response?.data?.message || t('common.error', 'Ocurrió un error al enviar el registro. Por favor intenta de nuevo.');
            toast.error(errorMsg);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Keyboard navigation (Enter to advance)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey && step.type !== 'textarea' && !isCompleted && !isSubmitting) {
                e.preventDefault();
                handleNext();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentStep, formData, isSubmitting, isCompleted]);

    // Smooth scroll focus to top anchor on step changes
    useEffect(() => {
        if (topAnchorRef.current) {
            topAnchorRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }, [currentStep]);

    const progressPercentage = Math.round(((currentStep + 1) / QUESTIONS.length) * 100);

    if (isCompleted) {
        return (
            <div className="flex min-h-[100dvh] items-center justify-center bg-gradient-to-b from-background via-background/95 to-primary/10 p-4 sm:p-6 text-foreground transition-colors duration-300 relative overflow-hidden">
                {/* Visual Ambient Blur FX */}
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[350px] sm:w-[600px] h-[350px] sm:h-[600px] rounded-full bg-primary/20 blur-[100px] pointer-events-none" />
                <div className="absolute bottom-10 right-10 w-64 h-64 rounded-full bg-indigo-500/15 blur-[90px] pointer-events-none" />

                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 280, damping: 22 }}
                    className="w-full max-w-lg rounded-3xl border border-primary/30 bg-card/95 p-6 sm:p-10 text-center shadow-2xl backdrop-blur-2xl relative overflow-hidden z-10"
                >
                    <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-500 ring-8 ring-emerald-500/10 shadow-inner">
                        <CheckCircle2 className="h-10 w-10 animate-bounce" />
                    </div>

                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-semibold mb-3 border border-emerald-500/20">
                        <Rocket className="h-3.5 w-3.5" />
                        <span>{t('betaRegister.completedBadge', '¡Solicitud Recibida!')}</span>
                    </div>

                    <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
                        {t('betaRegister.completedTitle', '¡Estás en la Lista de Espera VIP!')}
                    </h2>
                    <p className="mt-3 text-sm sm:text-base text-muted-foreground leading-relaxed">
                        {t('betaRegister.completedSubtitle', 'Hemos recibido la información de {{company}}.', { company: formData.company_name })}
                    </p>
                    <p className="mt-2 text-xs sm:text-sm text-muted-foreground/90 leading-relaxed">
                        {t('betaRegister.completedDesc', 'Nuestro equipo super admin analizará tus requerimientos y te enviará credenciales y créditos de bienvenida a {{email}}.', { email: formData.email })}
                    </p>

                    <div className="mt-6 rounded-2xl border border-amber-500/25 bg-amber-500/10 p-4 text-left shadow-sm backdrop-blur-md">
                        <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400 text-xs sm:text-sm font-medium">
                            <Clock className="h-5 w-5 shrink-0 animate-spin-slow" />
                            <span>{t('betaRegister.statusPending', 'Estado de la solicitud: Pendiente de Aprobación')}</span>
                        </div>
                    </div>

                    <div className="mt-8 flex flex-col gap-3">
                        <Link href="/">
                            <Button className="w-full bg-gradient-to-r from-primary via-indigo-600 to-purple-600 text-white font-bold py-6 rounded-2xl text-base shadow-xl shadow-primary/30 hover:opacity-95 transition-all hover:scale-[1.02] active:scale-[0.98]">
                                {t('betaRegister.goToHome', 'Volver a la Página de Inicio')}
                            </Button>
                        </Link>
                    </div>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="flex min-h-[100dvh] flex-col bg-background text-foreground transition-colors duration-300 relative selection:bg-primary/20">
            {/* Top Anchor for smooth scrolling */}
            <div ref={topAnchorRef} />

            {/* Header */}
            <header className="flex items-center justify-between border-b border-border/40 px-4 sm:px-8 py-3.5 backdrop-blur-xl bg-background/90 sticky top-0 z-50 shadow-xs">
                <div className="flex items-center gap-2.5">
                    <div className="relative flex items-center">
                        <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="h-8 w-8 sm:h-9 sm:w-9 object-contain" />
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-lg sm:text-xl font-black tracking-tight text-foreground">
                            Aikrofy
                        </span>
                        <span className="text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 shadow-2xs uppercase">
                            BETA
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm">
                    <LanguageSwitcher />

                    {mounted && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                            className="rounded-full h-9 w-9 border border-border/40 hover:bg-accent/60"
                            aria-label="Toggle Theme"
                        >
                            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-amber-500" />
                            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-indigo-400" />
                        </Button>
                    )}

                    <Link href="/login" className="flex items-center gap-1.5 text-primary hover:text-primary/80 font-bold transition-colors pl-1">
                        <Lock className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline">{t('betaRegister.alreadyHaveAccess', 'Ya tengo acceso')}</span>
                        <span className="sm:hidden">{t('betaRegister.loginMobile', 'Entrar')}</span>
                    </Link>
                </div>
            </header>

            {/* Sticky Modern Progress Bar */}
            <div className="sticky top-[57px] sm:top-[65px] z-40 bg-background/90 backdrop-blur-md border-b border-border/30 px-4 sm:px-8 py-2.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground">
                    <Sparkle className="h-3.5 w-3.5 text-primary animate-pulse" />
                    <span>{t('betaRegister.step', 'Paso {{current}} de {{total}}', { current: currentStep + 1, total: QUESTIONS.length })}</span>
                </div>

                <div className="flex items-center gap-3 w-1/2 max-w-xs">
                    <div className="flex-1 bg-accent/80 h-2.5 rounded-full overflow-hidden p-0.5 border border-border/40 shadow-inner">
                        <motion.div
                            className="h-full bg-gradient-to-r from-primary via-indigo-500 to-purple-600 rounded-full"
                            initial={{ width: '0%' }}
                            animate={{ width: `${progressPercentage}%` }}
                            transition={{ duration: 0.35, ease: "easeOut" }}
                        />
                    </div>
                    <span className="text-xs font-black text-primary w-9 text-right">{progressPercentage}%</span>
                </div>
            </div>

            {/* Main Conversational Canvas */}
            <main className="flex-1 w-full px-4 py-6 sm:px-6 sm:py-10 max-w-2xl mx-auto pb-28 sm:pb-32">
                <div className="w-full">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={step.id}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -12 }}
                            transition={{ duration: 0.2, ease: "easeOut" }}
                            className="space-y-6 sm:space-y-8"
                        >
                            {/* Question Header & Context Badge */}
                            <div className="space-y-3">
                                <div className="flex items-center">
                                    <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3.5 py-1 text-xs font-bold text-primary border border-primary/20 shadow-2xs">
                                        <step.icon className="h-3.5 w-3.5 text-primary" />
                                        <span>{step.badge}</span>
                                    </div>
                                </div>

                                <h1 className="text-xl sm:text-3xl font-black text-foreground tracking-tight leading-snug sm:leading-tight">
                                    {step.title}
                                </h1>
                                <p className="text-muted-foreground text-xs sm:text-base leading-relaxed">
                                    {step.subtitle}
                                </p>
                            </div>

                            {/* Dynamic Input Control Section */}
                            <div className="pt-1">
                                {step.type === 'text' && (
                                    <div className="space-y-3">
                                        <div className="relative">
                                            <Input
                                                autoFocus
                                                value={formData[step.field as keyof typeof formData]}
                                                onChange={e => updateField(step.field, e.target.value)}
                                                placeholder={step.placeholder}
                                                className="h-14 sm:h-16 bg-card border-border/80 text-base sm:text-xl text-foreground placeholder:text-muted-foreground/50 rounded-2xl focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary px-5 shadow-sm transition-all"
                                            />
                                        </div>
                                        <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground/70 pl-1">
                                            <CornerDownLeft className="h-3.5 w-3.5" />
                                            <span>{t('betaRegister.enterHint', 'Presiona')} <kbd className="px-1.5 py-0.5 rounded bg-muted font-sans font-medium text-[10px]">Enter ↵</kbd> {t('betaRegister.enterHintSuffix', 'para avanzar')}</span>
                                        </div>
                                    </div>
                                )}

                                {step.type === 'textarea' && (
                                    <div className="space-y-3">
                                        <Textarea
                                            autoFocus
                                            rows={4}
                                            value={formData[step.field as keyof typeof formData]}
                                            onChange={e => updateField(step.field, e.target.value)}
                                            placeholder={step.placeholder}
                                            className="bg-card border-border/80 text-base sm:text-lg text-foreground placeholder:text-muted-foreground/50 rounded-2xl focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary p-4 sm:p-5 shadow-sm transition-all resize-none min-h-[140px]"
                                        />
                                    </div>
                                )}

                                {step.type === 'select' && (
                                    <div className="grid gap-2.5 sm:grid-cols-2 sm:gap-3.5">
                                        {step.options?.map((opt, idx) => {
                                            const isSelected = formData[step.field as keyof typeof formData] === opt.value;
                                            const isTouched = touchedOption === opt.value;

                                            return (
                                                <motion.button
                                                    key={opt.value}
                                                    type="button"
                                                    whileHover={{ scale: 1.01 }}
                                                    whileTap={{ scale: 0.98 }}
                                                    onClick={() => handleSelectOption(step.field, opt.value)}
                                                    className={`w-full flex items-center justify-between rounded-2xl border p-4 sm:p-5 text-left transition-all duration-150 relative overflow-hidden ${
                                                        isSelected || isTouched
                                                            ? 'border-primary bg-primary/15 text-foreground ring-2 ring-primary/40 shadow-md'
                                                            : 'border-border/70 bg-card text-foreground hover:border-primary/50 hover:bg-accent/40 shadow-2xs'
                                                    }`}
                                                >
                                                    <div className="flex items-start gap-3.5 pr-2">
                                                        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors mt-0.5 ${
                                                            isSelected ? 'bg-primary text-primary-foreground' : 'bg-accent/80 text-muted-foreground'
                                                        }`}>
                                                            {idx + 1}
                                                        </span>
                                                        <div className="space-y-0.5">
                                                            <div className="font-bold text-sm sm:text-base text-foreground flex items-center gap-2 flex-wrap">
                                                                <span>{opt.label}</span>
                                                                {opt.badge && (
                                                                    <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                                                                        {opt.badge}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            {opt.desc && (
                                                                <p className="text-xs text-muted-foreground leading-relaxed">
                                                                    {opt.desc}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>

                                                    <div className={`h-6 w-6 rounded-full border flex items-center justify-center shrink-0 transition-all ${
                                                        isSelected ? 'border-primary bg-primary text-primary-foreground shadow-xs' : 'border-muted-foreground/30'
                                                    }`}>
                                                        {isSelected && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                                                    </div>
                                                </motion.button>
                                            );
                                        })}
                                    </div>
                                )}

                                {step.type === 'contact_group' && (
                                    <div className="grid gap-3.5 sm:grid-cols-2">
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                                                <User className="h-3.5 w-3.5 text-primary" />
                                                {t('betaRegister.q8.fullName', 'Nombre Completo')}
                                            </label>
                                            <Input
                                                value={formData.contact_name}
                                                onChange={e => updateField('contact_name', e.target.value)}
                                                placeholder={t('betaRegister.q8.fullNamePlaceholder', 'Ej. Carlos Mendoza')}
                                                className="bg-card border-border/80 text-foreground text-sm sm:text-base rounded-xl h-12 px-4 shadow-2xs focus-visible:ring-primary"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                                                <Briefcase className="h-3.5 w-3.5 text-primary" />
                                                {t('betaRegister.q8.role', 'Cargo en la Empresa')}
                                            </label>
                                            <Input
                                                value={formData.role_in_company}
                                                onChange={e => updateField('role_in_company', e.target.value)}
                                                placeholder={t('betaRegister.q8.rolePlaceholder', 'Ej. CEO / Gerente de Operaciones')}
                                                className="bg-card border-border/80 text-foreground text-sm sm:text-base rounded-xl h-12 px-4 shadow-2xs focus-visible:ring-primary"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                                                <Mail className="h-3.5 w-3.5 text-primary" />
                                                {t('betaRegister.q8.email', 'Correo Electrónico')}
                                            </label>
                                            <Input
                                                type="email"
                                                value={formData.email}
                                                onChange={e => updateField('email', e.target.value)}
                                                placeholder={t('betaRegister.q8.emailPlaceholder', 'carlos@tuempresa.com')}
                                                className="bg-card border-border/80 text-foreground text-sm sm:text-base rounded-xl h-12 px-4 shadow-2xs focus-visible:ring-primary"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                                                <Phone className="h-3.5 w-3.5 text-primary" />
                                                {t('betaRegister.q8.phone', 'Teléfono / WhatsApp')}
                                            </label>
                                            <Input
                                                type="tel"
                                                value={formData.phone}
                                                onChange={e => updateField('phone', e.target.value)}
                                                placeholder={t('betaRegister.q8.phonePlaceholder', '+593 99 123 4567')}
                                                className="bg-card border-border/80 text-foreground text-sm sm:text-base rounded-xl h-12 px-4 shadow-2xs focus-visible:ring-primary"
                                            />
                                        </div>

                                        <div className="sm:col-span-2 pt-2 flex items-center justify-center gap-2 text-xs text-muted-foreground bg-accent/30 p-2.5 rounded-xl border border-border/40">
                                            <ShieldCheck className="h-4 w-4 text-emerald-500 shrink-0" />
                                            <span>Tus datos están blindados con cifrado SSL de nivel empresarial.</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>

            {/* Unified Fixed Bottom Action Bar — all devices, keyboard-aware on mobile/tablet */}
            <div
                className="fixed left-0 right-0 z-50 bg-background/95 backdrop-blur-xl border-t border-border/50 shadow-2xl transition-[bottom] duration-150"
                style={{ bottom: `${bottomOffset}px` }}
            >
                <div className="max-w-2xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-3">
                    {currentStep > 0 ? (
                        <Button
                            type="button"
                            variant="outline"
                            onClick={handlePrev}
                            disabled={isSubmitting}
                            className="rounded-xl sm:rounded-2xl h-12 sm:h-13 px-4 sm:px-6 border-border/80 shrink-0 font-bold active:scale-95 text-sm sm:text-base"
                        >
                            <ArrowLeft className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">{t('betaRegister.previous', 'Anterior')}</span>
                        </Button>
                    ) : (
                        <div className="hidden sm:block" />
                    )}

                    <Button
                        type="button"
                        onClick={handleNext}
                        disabled={isSubmitting}
                        className="flex-1 bg-gradient-to-r from-primary via-indigo-600 to-purple-600 text-white font-bold sm:font-black h-12 sm:h-13 rounded-xl sm:rounded-2xl shadow-lg shadow-primary/25 hover:opacity-95 flex items-center justify-center gap-2 text-sm sm:text-base transition-all hover:scale-[1.02] active:scale-[0.97]"
                    >
                        {currentStep === QUESTIONS.length - 1 ? (
                            isSubmitting
                                ? t('betaRegister.submitting', 'Enviando...')
                                : <><span className="hidden sm:inline">{t('betaRegister.submit', 'Solicitar Acceso Beta VIP')}</span><span className="sm:hidden">{t('betaRegister.submit', 'Solicitar Acceso VIP')}</span></>
                        ) : (
                            <>
                                {t('betaRegister.next', 'Siguiente')}
                                <ChevronRight className="h-4 w-4 stroke-[3] sm:hidden" />
                                <ArrowRight className="h-4 w-4 ml-1 stroke-[2.5] hidden sm:block" />
                            </>
                        )}
                    </Button>
                </div>
            </div>
        </div>
    );
}
