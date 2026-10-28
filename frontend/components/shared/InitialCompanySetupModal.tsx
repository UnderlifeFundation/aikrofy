'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  Building2,
  Users,
  Package,
  ArrowRight,
  ArrowLeft,
  Bot,
  Rocket
} from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useAuthStore } from '@/store/use-auth-store';
import { useOnboardingStore } from '@/store/use-onboarding-store';
import apiClient from '@/lib/api-client';
import { toast } from 'sonner';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Company } from '@/types';

interface InitialSetupData {
  company_name: string;
  industry: string;
  departments: string[];
  products_services: string;
  business_goals: string;
}

export function InitialCompanySetupModal() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, updateUser } = useAuthStore();

  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: meData } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await apiClient.get('/auth/me');
      return data.data;
    },
    staleTime: 60_000,
  });

  const effectiveCompany = meData?.company || user?.company;
  const rawCompanyName = effectiveCompany?.name || user?.company_name || '';
  const isPlaceholder = !rawCompanyName || ['mi empresa', 'my company', 'nueva empresa', 'company'].includes(rawCompanyName.toLowerCase().trim());
  const isSetupDoneBackend = Boolean(effectiveCompany?.initial_setup_completed);

  const [formData, setFormData] = useState<InitialSetupData>({
    company_name: isPlaceholder ? '' : rawCompanyName,
    industry: effectiveCompany?.industry || 'services',
    departments: ['sales', 'support'],
    products_services: '',
    business_goals: '',
  });

  const STORAGE_KEY = `aikrofy_initial_setup_done_${user?.id || 'guest'}`;

  // Check if first-time user needs initial setup (Only for company owners who haven't completed setup)
  useEffect(() => {
    if (!user) return;
    if (!user.is_company_owner) return;
    
    // If backend confirms setup is done, or company has a real name, never show
    if (isSetupDoneBackend) {
      if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, 'true');
      setIsOpen(false);
      return;
    }

    const localIsDone = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (localIsDone || !isPlaceholder) {
      setIsOpen(false);
      return;
    }
    
    const timer = setTimeout(() => {
      setIsOpen(true);
    }, 1500);
    return () => clearTimeout(timer);
  }, [user, isSetupDoneBackend, isPlaceholder, STORAGE_KEY]);

  if (!user?.is_company_owner) return null;
  if (isSetupDoneBackend) return null;

  const updateField = (field: keyof InitialSetupData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const toggleDepartment = (dept: string) => {
    setFormData((prev) => {
      const exists = prev.departments.includes(dept);
      const next = exists ? prev.departments.filter((d) => d !== dept) : [...prev.departments, dept];
      return { ...prev, departments: next.length > 0 ? next : ['sales'] };
    });
  };

  const handleNext = () => {
    if (currentStep === 0 && !formData.company_name.trim()) {
      toast.error(t('setup.errorCompany', 'Por favor ingresa el nombre de tu empresa'));
      return;
    }
    if (currentStep < 3) {
      setCurrentStep((prev) => prev + 1);
    } else {
      handleCompleteSetup();
    }
  };

  const handleCompleteSetup = async () => {
    setIsSubmitting(true);
    try {
      // 1. Save company basic details to API
      await apiClient.put('/companies/me', {
        name: formData.company_name,
        industry: formData.industry,
        products_services: formData.products_services,
        departments: formData.departments,
        business_goals: formData.business_goals,
        initial_setup_completed: true
      });

      // Update local auth store and react-query cache
      if (user) {
        updateUser({
          company_name: formData.company_name,
          company: {
            ...(user.company || ({} as any)),
            name: formData.company_name,
            initial_setup_completed: true
          }
        });
      }

      await queryClient.invalidateQueries({ queryKey: ['me'] });

      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, 'true');
      }
      setIsOpen(false);

      toast.success(t('setup.welcomeSuccess', '¡Primera capa configurada con éxito!'));

      // Redirect immediately to Magic Voice Onboarding
      router.push('/onboarding');
    } catch (e: any) {
      console.error('Setup error:', e);
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, 'true');
      }
      setIsOpen(false);
      router.push('/onboarding');
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    {
      title: '¿Cómo se llama tu empresa o negocio?',
      subtitle: 'Configura la identidad principal de tu organización para tus agentes de IA.',
      icon: <Building2 className="w-6 h-6 text-primary" />,
      component: (
        <div className="space-y-4 pt-2">
          <Input
            autoFocus
            type="text"
            value={formData.company_name}
            onChange={(e) => updateField('company_name', e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNext()}
            placeholder="Ej. InnovaTech S.A. / Consultora Nexus"
            className="text-base py-6 px-4 rounded-xl border-primary/30 focus:border-primary bg-background shadow-inner"
          />
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sector o Industria Principal</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {[
                { id: 'services', label: '💼 Servicios / B2B' },
                { id: 'ecommerce', label: '🛍️ E-Commerce / Retail' },
                { id: 'health', label: '🏥 Salud / Estética' },
                { id: 'realestate', label: '🏢 Inmobiliaria' },
                { id: 'education', label: '🎓 Educación' },
                { id: 'tech', label: '🚀 Software / Tech' },
              ].map((ind) => (
                <button
                  key={ind.id}
                  type="button"
                  onClick={() => updateField('industry', ind.id)}
                  className={`p-3 rounded-xl text-xs font-semibold border text-left transition-all cursor-pointer ${
                    formData.industry === ind.id
                      ? 'border-primary bg-primary/10 text-primary shadow-sm font-bold ring-1 ring-primary'
                      : 'border-border bg-muted/40 hover:bg-muted/70 text-foreground'
                  }`}
                >
                  {ind.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '¿Qué departamentos deseas activar con IA?',
      subtitle: 'Tus agentes autónomos orquestarán la operación de estas áreas de forma coordinada.',
      icon: <Users className="w-6 h-6 text-purple-500" />,
      component: (
        <div className="space-y-3 pt-2">
          {[
            { id: 'sales', title: 'Ventas & Cierre Comercial (CSO)', desc: 'Captura leads, cotiza y genera enlaces de cobro 24/7' },
            { id: 'support', title: 'Soporte & Atención al Cliente (COO)', desc: 'Resuelve dudas frecuentes, estados de órdenes y seguimiento' },
            { id: 'marketing', title: 'Marketing & Adquisición (CMO)', desc: 'Califica prospectos y gestiona campañas omnicanal' },
            { id: 'operations', title: 'Operaciones & RAG Interno (CTO)', desc: 'Consulta bases de conocimiento, políticas y datos ERP' },
          ].map((dept) => {
            const selected = formData.departments.includes(dept.id);
            return (
              <div
                key={dept.id}
                onClick={() => toggleDepartment(dept.id)}
                className={`p-3.5 rounded-xl border flex items-start gap-3 transition-all cursor-pointer ${
                  selected
                    ? 'border-primary bg-primary/10 text-foreground shadow-sm ring-1 ring-primary'
                    : 'border-border bg-muted/40 hover:bg-muted/70 text-muted-foreground'
                }`}
              >
                <div className={`w-5 h-5 rounded-md mt-0.5 flex items-center justify-center border text-xs ${
                  selected ? 'bg-primary text-primary-foreground border-primary' : 'border-border bg-background'
                }`}>
                  {selected && '✓'}
                </div>
                <div>
                  <div className="text-xs font-bold text-foreground">{dept.title}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{dept.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      ),
    },
    {
      title: '¿Qué productos o servicios ofrece tu negocio?',
      subtitle: 'Tus agentes aprenderán esta información básica para orientar a tus clientes de inmediato.',
      icon: <Package className="w-6 h-6 text-pink-500" />,
      component: (
        <div className="space-y-3 pt-2">
          <Textarea
            rows={4}
            value={formData.products_services}
            onChange={(e) => updateField('products_services', e.target.value)}
            placeholder="Ej. Vendemos planes de consultoría empresarial, diseño de páginas web y asesoría financiera personalizada..."
            className="w-full text-xs sm:text-sm p-3.5 rounded-xl border-border bg-background focus:border-primary resize-none"
          />
          <p className="text-[11px] text-muted-foreground">
            💡 En el siguiente paso podrás detallar aún más mediante una nota de voz con tu CTO IA.
          </p>
        </div>
      ),
    },
    {
      title: '¡Listo para activar tu Ecosistema de Agentes!',
      subtitle: 'Hemos creado la primera capa de tu empresa. A continuación pasarás al Onboarding Mágico con tu CTO IA.',
      icon: <Rocket className="w-6 h-6 text-emerald-500" />,
      component: (
        <div className="space-y-4 pt-2 text-center">
          <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-left space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Empresa:</span>
              <span className="font-bold text-foreground">{formData.company_name}</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Departamentos:</span>
              <span className="font-semibold text-primary">{formData.departments.join(', ').toUpperCase()}</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Siguiente Fase:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">Onboarding Mágico por Voz 🎙️</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Solo tendrás que pulsar el micrófono y contarle a tu CTO IA sobre tus productos y reglas. La IA armará tus agentes al instante.
          </p>
        </div>
      ),
    },
  ];

  const current = steps[currentStep];

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent showCloseButton={false} className="sm:max-w-[540px] p-0 overflow-hidden border-none bg-card shadow-2xl rounded-2xl">
        {/* Header Ribbon */}
        <div className="p-6 text-white bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 flex items-center justify-between relative overflow-hidden">
          <div className="relative z-10 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-white/20 border border-white/20 backdrop-blur-md">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-indigo-200">Bienvenido a Aikrofy</div>
              <h3 className="text-lg font-black text-white leading-tight">Configuración Inicial de tu Empresa</h3>
            </div>
          </div>
          <div className="text-xs font-bold px-2.5 py-1 rounded-full bg-white/20 border border-white/20 text-white">
            Paso {currentStep + 1} de {steps.length}
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 text-primary">{current.icon}</div>
              <h4 className="text-base font-bold text-foreground">{current.title}</h4>
            </div>
            <p className="text-xs text-muted-foreground">{current.subtitle}</p>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {current.component}
            </motion.div>
          </AnimatePresence>

          {/* Navigation Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-border gap-3">
            {currentStep > 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep((prev) => prev - 1)}
                className="text-xs font-semibold rounded-xl"
              >
                <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Anterior
              </Button>
            ) : <div />}

            <Button
              size="lg"
              disabled={isSubmitting}
              onClick={handleNext}
              className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold rounded-xl px-6 cursor-pointer shadow-md shadow-indigo-500/20"
            >
              {currentStep === steps.length - 1 ? (
                isSubmitting ? 'Iniciando Onboarding Mágico...' : 'Comenzar Onboarding Mágico 🚀'
              ) : (
                <>
                  Siguiente <ArrowRight className="w-4 h-4 ml-1.5" />
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
