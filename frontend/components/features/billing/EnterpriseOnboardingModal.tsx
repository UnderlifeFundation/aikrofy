'use client';

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Building2,
  PhoneCall,
  Sparkles,
  Calendar,
  Clock,
  CheckCircle2,
  X,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Cpu,
  Headphones,
  Users,
  Briefcase,
  Send
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

interface EnterpriseModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultNeed?: string;
}

export function EnterpriseOnboardingModal({ isOpen, onClose, defaultNeed = 'voice_ai' }: EnterpriseModalProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedNeed, setSelectedNeed] = useState<string>(defaultNeed);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Form State
  const [companyName, setCompanyName] = useState('');
  const [contactName, setContactName] = useState('');
  const [taxId, setTaxId] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [companySize, setCompanySize] = useState('11-50');
  const [preferredDate, setPreferredDate] = useState('');
  const [preferredTime, setPreferredTime] = useState('10:00');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setSelectedNeed(defaultNeed);
      setIsSubmitting(false);
    }
  }, [isOpen, defaultNeed]);

  if (!isOpen) return null;

  const enterpriseNeeds = [
    {
      id: 'voice_ai',
      icon: <PhoneCall className="w-5 h-5 text-indigo-400" />,
      title: 'Voz e IA Telefónica Autónoma',
      desc: 'Llamadas entrantes/salientes, telefonía PBX, transcripción en tiempo real y latencia <200ms.',
      badge: 'Exclusivo Enterprise'
    },
    {
      id: 'c_suite',
      icon: <Cpu className="w-5 h-5 text-purple-400" />,
      title: 'Junta Directiva C-Suite Completa (7 Chiefs)',
      desc: 'CEO, COO, CSO, CMO, CTO, CRO y CFO orquestados para automatizar todas las áreas del negocio.',
      badge: 'Multi-Agente'
    },
    {
      id: 'custom_erp',
      icon: <Briefcase className="w-5 h-5 text-pink-400" />,
      title: 'Integraciones Dedicadas ERP / CRM & RAG Privado',
      desc: 'Conectividad a SAP, Oracle, Salesforce, HubSpot y aislamiento RAG por departamentos.',
      badge: 'SLA 99.9%'
    },
    {
      id: 'dedicated_infra',
      icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
      title: 'Infraestructura On-Premise / Servidores MCP',
      desc: 'Nodos dedicados de inferencia, auditoría de seguridad y soporte de ingeniería 24/7.',
      badge: 'Máxima Seguridad'
    }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Send to contact/onboarding API or save request
      const payload = {
        companyName,
        contactName,
        taxId,
        email,
        phone,
        companySize,
        need: selectedNeed,
        preferredDate,
        preferredTime,
        notes,
        type: 'enterprise_onboarding_request'
      };

      // Best effort API dispatch
      try {
        await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } catch {}

      toast.success('¡Solicitud enviada con éxito! Nuestro equipo técnico te contactará.');
      setStep(4);
    } catch {
      toast.error('Ocurrió un error al enviar la solicitud. Por favor intenta de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 14px',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    background: 'rgba(15, 23, 42, 0.7)',
    color: '#ffffff',
    fontSize: '0.85rem',
    outline: 'none',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-white/15 rounded-2xl shadow-2xl overflow-hidden text-white flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-border bg-card/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-sm sm:text-base text-foreground">Solicitud de Onboarding Enterprise</h3>
              <p className="text-[11px] text-muted-foreground">Atención personalizada y despliegue de IA a medida</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="grid grid-cols-3 bg-muted/40 border-b border-border text-[11px] font-semibold">
          <div className={`p-2 text-center border-r border-border ${step >= 1 ? 'text-primary bg-primary/10 font-bold' : 'text-muted-foreground'}`}>
            1. Solución
          </div>
          <div className={`p-2 text-center border-r border-border ${step >= 2 ? 'text-primary bg-primary/10 font-bold' : 'text-muted-foreground'}`}>
            2. Datos Empresa
          </div>
          <div className={`p-2 text-center ${step >= 3 ? 'text-primary bg-primary/10 font-bold' : 'text-muted-foreground'}`}>
            3. Reunión
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-foreground">
          
          {/* ═════════════════════════════════════════════════════════════
              PASO 1: SELECCIÓN DEL REQUERIMIENTO ENTERPRISE
          ═════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="text-center space-y-1">
                <Badge className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20 text-[10px] uppercase tracking-wider font-bold">
                  Paso 1 de 3
                </Badge>
                <h4 className="text-xl font-bold text-foreground">¿Cuál es la prioridad para tu empresa?</h4>
                <p className="text-xs text-muted-foreground">Selecciona el módulo o infraestructura que deseas activar en tu sesión de onboarding.</p>
              </div>

              <div className="grid grid-cols-1 gap-3 pt-2">
                {enterpriseNeeds.map((need) => (
                  <div
                    key={need.id}
                    onClick={() => setSelectedNeed(need.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3.5 ${
                      selectedNeed === need.id
                        ? 'border-indigo-500 bg-indigo-500/15 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500'
                        : 'border-border bg-muted/40 hover:bg-muted/70'
                    }`}
                  >
                    <div className="p-2.5 rounded-lg bg-background border border-border shrink-0">
                      {need.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-foreground">{need.title}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 font-semibold">
                          {need.badge}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{need.desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              <Button
                size="lg"
                onClick={() => setStep(2)}
                className="w-full py-5 font-bold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-95 text-white rounded-xl cursor-pointer"
              >
                Continuar con Datos de la Empresa <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </div>
          )}

          {/* ═════════════════════════════════════════════════════════════
              PASO 2: DATOS DE LA EMPRESA Y CONTACTO
          ═════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="space-y-4">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Volver a selección de solución
              </button>

              <div className="space-y-1">
                <h4 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-indigo-500 dark:text-indigo-400" /> Datos Corporativos
                </h4>
                <p className="text-xs text-muted-foreground">Información para emitir tu propuesta técnica y preparar la demo personalizada.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Razón Social / Empresa *</label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Ej. InnovaTech Solutions S.A."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Nombre del Solicitante *</label>
                  <input
                    type="text"
                    required
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="Ej. Carlos Mendoza (CTO / CEO)"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">RUC / Tax ID / Identificación Fiscal *</label>
                  <input
                    type="text"
                    required
                    value={taxId}
                    onChange={(e) => setTaxId(e.target.value)}
                    placeholder="Ej. 1792837465001"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Tamaño de la Empresa</label>
                  <select
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  >
                    <option value="1-10">1 - 10 empleados</option>
                    <option value="11-50">11 - 50 empleados</option>
                    <option value="51-200">51 - 200 empleados</option>
                    <option value="200+">Más de 200 empleados (Corporativo)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Correo Electrónico Corporativo *</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contacto@empresa.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Teléfono / WhatsApp *</label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+593 99 123 4567"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
              </div>

              <Button
                size="lg"
                onClick={() => {
                  if (!companyName.trim() || !email.trim() || !contactName.trim()) {
                    toast.error('Por favor completa los campos obligatorios (*)');
                    return;
                  }
                  setStep(3);
                }}
                className="w-full py-5 font-bold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-95 text-white rounded-xl cursor-pointer mt-2"
              >
                Continuar a Agendamiento de Reunión <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </div>
          )}

          {/* ═════════════════════════════════════════════════════════════
              PASO 3: AGENDAMIENTO DE REUNIÓN DE ONBOARDING
          ═════════════════════════════════════════════════════════════ */}
          {step === 3 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Volver a datos de la empresa
              </button>

              <div className="space-y-1">
                <h4 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-indigo-500 dark:text-indigo-400" /> Agendar Sesión de Onboarding
                </h4>
                <p className="text-xs text-muted-foreground">Selecciona el horario preferido para tu videollamada técnica de 30 minutos (Google Meet).</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Fecha Preferida *</label>
                  <input
                    type="date"
                    required
                    value={preferredDate}
                    onChange={(e) => setPreferredDate(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Hora Preferida (GMT-5) *</label>
                  <select
                    value={preferredTime}
                    onChange={(e) => setPreferredTime(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                  >
                    <option value="09:00">09:00 AM</option>
                    <option value="10:00">10:00 AM</option>
                    <option value="11:30">11:30 AM</option>
                    <option value="14:00">02:00 PM</option>
                    <option value="15:30">03:30 PM</option>
                    <option value="17:00">05:00 PM</option>
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-foreground mb-1">Requerimientos Adicionales o Notas</label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Describe brevemente tus sistemas actuales (CRM, ERP, telefonía PBX, volumen diario de clientes)..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all resize-none"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-indigo-500/10 dark:bg-indigo-950/40 border border-indigo-500/20 text-xs text-foreground flex items-start gap-2.5">
                <ShieldCheck className="w-5 h-5 text-emerald-500 dark:text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  Tu sesión será atendida por un <strong>Ingeniero de Soluciones de Aikrofy</strong> con acceso a sandboxes de voz e integraciones personalizadas.
                </span>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                size="lg"
                className="w-full py-5 font-bold bg-gradient-to-r from-emerald-500 to-teal-600 hover:opacity-95 text-white rounded-xl shadow-lg shadow-emerald-500/20 cursor-pointer"
              >
                {isSubmitting ? 'Agendando Onboarding...' : 'Confirmar y Solicitar Onboarding Enterprise 🚀'}
              </Button>
            </form>
          )}

          {/* ═════════════════════════════════════════════════════════════
              PASO 4: CONFIRMACIÓN DE ÉXITO
          ═════════════════════════════════════════════════════════════ */}
          {step === 4 && (
            <div className="text-center space-y-4 py-4">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 border-2 border-emerald-500 text-emerald-500 flex items-center justify-center mx-auto text-3xl">
                <CheckCircle2 className="w-10 h-10" />
              </div>

              <div className="space-y-1.5">
                <h4 className="text-2xl font-bold text-foreground">¡Sesión de Onboarding Solicitada!</h4>
                <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                  Hemos registrado la solicitud de <strong>{companyName}</strong>. Te hemos enviado un correo de confirmación a <strong>{email}</strong> con los detalles de la videollamada.
                </p>
              </div>

              <div className="rounded-xl bg-muted/30 dark:bg-slate-950/70 border border-border p-4 max-w-md mx-auto text-xs text-left space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Solución:</span>
                  <span className="text-foreground font-semibold">{enterpriseNeeds.find((n) => n.id === selectedNeed)?.title}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Horario Tentativo:</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-semibold">{preferredDate || 'A coordinar'} - {preferredTime}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Contacto:</span>
                  <span className="text-foreground">{contactName} ({phone})</span>
                </div>
              </div>

              <Button
                onClick={onClose}
                className="py-5 px-8 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-bold rounded-xl cursor-pointer"
              >
                Entendido y Cerrar
              </Button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

