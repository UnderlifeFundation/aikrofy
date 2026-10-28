'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Sparkles, 
  Zap, 
  CreditCard, 
  Building2, 
  ShieldCheck, 
  CheckCircle2, 
  Flame, 
  Clock, 
  Cpu, 
  MessageSquare, 
  PhoneCall, 
  ArrowLeft,
  ArrowRight,
  Receipt,
  Coins
} from 'lucide-react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EnterpriseOnboardingModal } from './EnterpriseOnboardingModal';
import { useAuthStore } from '@/store/use-auth-store';
import { useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface PayPalButtonWrapperProps {
  amount: number;
  credits: number;
  companyName: string;
  taxId: string;
  email: string;
  phone: string;
  fundingType: 'paypal' | 'card' | 'all';
  onSuccess: (info: { invoiceId: string; amount: number; credits: number; provider: string; companyName: string }) => void;
  setProcessing: (b: boolean) => void;
  processing: boolean;
}

function PayPalButtonWrapper({
  amount,
  credits,
  companyName,
  taxId,
  email,
  phone,
  fundingType,
  onSuccess,
  setProcessing,
  processing,
}: PayPalButtonWrapperProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    let isCancelled = false;
    let buttonInstance: any = null;

    const renderButton = () => {
      if (isCancelled) return;
      const win = window as any;
      const container = containerRef.current;
      
      if (!win.paypal || !win.paypal.Buttons || !container) {
        timer = setTimeout(renderButton, 120);
        return;
      }

      setSdkReady(true);
      setRenderError(null);
      container.innerHTML = '';
      const buttonSlot = document.createElement('div');
      buttonSlot.style.width = '100%';
      buttonSlot.style.maxWidth = '460px';
      buttonSlot.style.margin = '0 auto';
      container.appendChild(buttonSlot);

      try {
        const btnConfig: any = {
          style: {
            layout: 'vertical',
            color: fundingType === 'paypal' ? 'gold' : fundingType === 'card' ? 'black' : 'gold',
            shape: 'rect',
            label: 'pay',
            tagline: false,
            height: 48,
          },
          onClick: (_data: any, actions: any) => {
            if (!email || !email.includes('@')) {
              alert(t('creditPurchase.form.emailPlaceholder', 'Por favor ingresa un correo corporativo válido para tu factura.'));
              return actions?.reject ? actions.reject() : false;
            }
            if (!companyName.trim()) {
              alert(t('creditPurchase.form.companyNamePlaceholder', 'Por favor ingresa la razón social de tu empresa.'));
              return actions?.reject ? actions.reject() : false;
            }
            return actions?.resolve ? actions.resolve() : true;
          },
          createOrder: async () => {
            setProcessing(true);
            try {
              let res = await fetch('/api/billing/credits/create-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  amount,
                  credits,
                  method: fundingType === 'paypal' ? 'paypal' : 'card',
                  email,
                  companyName,
                  taxId,
                  phone,
                }),
              });

              if (!res.ok) {
                // Fallback to Next.js API route if FastAPI route wasn't matched
                res = await fetch('/api/credits', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    amount,
                    credits,
                    method: fundingType === 'paypal' ? 'paypal' : 'card',
                    email,
                    companyName,
                    taxId,
                    phone,
                  }),
                });
              }

              const data = await res.json();
              if (data.orderId) {
                return data.orderId;
              } else if (data.paymentUrl) {
                window.location.href = data.paymentUrl;
                return '';
              } else {
                throw new Error(data.error || 'No se pudo generar la orden de recarga');
              }
            } catch (err: any) {
              setProcessing(false);
              alert(err.message || 'Error al conectar con la pasarela de pago');
              throw err;
            }
          },
          onApprove: async (data: any) => {
            try {
              let res = await fetch('/api/billing/credits/capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  orderId: data.orderID,
                  invoiceId: data.orderID,
                  companyName,
                  email,
                  credits,
                }),
              });

              if (!res.ok) {
                res = await fetch('/api/credits/capture', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    orderId: data.orderID,
                    invoiceId: data.orderID,
                    companyName,
                    email,
                    credits,
                  }),
                });
              }
              const result = await res.json();
              if (result.success) {
                // Sync with Python backend database
                try {
                  await apiClient.post('/billing/sync-credits', {
                    order_id: data.orderID,
                    invoice_id: data.orderID,
                    amount: result.amount || amount,
                    credits: result.credits || credits,
                    provider: fundingType === 'paypal' ? 'paypal' : 'card',
                  });
                } catch (syncErr) {
                  console.warn('Backend credit sync warning:', syncErr);
                }

                onSuccess({
                  invoiceId: data.orderID,
                  amount: result.amount || amount,
                  credits: result.credits || credits,
                  provider: fundingType === 'paypal' ? 'PayPal' : 'Tarjeta Débito/Crédito (PayPal)',
                  companyName,
                });
              } else {
                alert(`Error al confirmar la recarga: ${result.error || 'Intente nuevamente'}`);
              }
            } catch {
              alert('Error de conexión al confirmar la recarga de créditos.');
            } finally {
              setProcessing(false);
            }
          },
          onCancel: () => {
            setProcessing(false);
          },
          onError: (err: any) => {
            if (isCancelled) return;
            console.warn('PayPal notice:', err);
            setProcessing(false);
          },
        };

        if (fundingType === 'paypal' && win.paypal.FUNDING?.PAYPAL) {
          btnConfig.fundingSource = win.paypal.FUNDING.PAYPAL;
        } else if (fundingType === 'card' && win.paypal.FUNDING?.CARD) {
          btnConfig.fundingSource = win.paypal.FUNDING.CARD;
        }

        buttonInstance = win.paypal.Buttons(btnConfig);

        if (buttonInstance.isEligible && buttonInstance.isEligible()) {
          buttonInstance.render(buttonSlot).catch((err: any) => {
            console.warn('Button render fallback:', err);
          });
        } else {
          // Fallback if standalone funding source is constrained in user locale
          delete btnConfig.fundingSource;
          buttonInstance = win.paypal.Buttons(btnConfig);
          buttonInstance.render(buttonSlot).catch((err: any) => {
            console.warn('Button fallback render error:', err);
          });
        }
      } catch (e: any) {
        if (!isCancelled) {
          console.warn('Failed to render PayPal Button:', e);
          setRenderError(e?.message || 'Error al iniciar pasarela');
        }
      }
    };

    renderButton();

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
      if (buttonInstance && typeof buttonInstance.close === 'function') {
        try {
          buttonInstance.close();
        } catch {}
      }
    };
  }, [amount, credits, companyName, taxId, email, phone, fundingType, t]);

  return (
    <div className="w-full flex flex-col items-center justify-center relative min-h-[52px]">
      {!sdkReady && !renderError && (
        <div className="text-center py-3 text-xs sm:text-sm text-muted-foreground animate-pulse">
          Cargando pasarela de pago segura... ⏳
        </div>
      )}
      {renderError && (
        <div className="text-center py-2 text-xs text-destructive">
          {renderError}
        </div>
      )}
      {processing && (
        <div className="text-center py-2 text-xs text-primary font-semibold animate-pulse">
          Procesando recarga de combustible IA... ⏳
        </div>
      )}
      <div ref={containerRef} className="w-full flex justify-center min-h-[48px]" />
    </div>
  );
}

interface CreditPurchaseSectionProps {
  initialAmount?: number;
  showBackButton?: boolean;
}

export function CreditPurchaseSection({ initialAmount, showBackButton = true }: CreditPurchaseSectionProps = {}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const [amount, setAmount] = useState<number>(initialAmount || 100);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'paypal'>('card');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paypalLoaded, setPaypalLoaded] = useState(false);
  const [showEnterpriseModal, setShowEnterpriseModal] = useState(false);

  // Enterprise details pre-filled from authenticated user
  const [companyName, setCompanyName] = useState(user?.company_name || user?.name || '');
  const [taxId, setTaxId] = useState(user?.tax_id || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');

  // Pre-fill user details when authenticated user state changes
  useEffect(() => {
    if (user) {
      if (user.company_name && !companyName) setCompanyName(user.company_name);
      else if (user.name && !companyName) setCompanyName(user.name);
      if (user.tax_id && !taxId) setTaxId(user.tax_id);
      if (user.email && !email) setEmail(user.email);
      if (user.phone && !phone) setPhone(user.phone);
    }
  }, [user]);

  const [successInfo, setSuccessInfo] = useState<{
    invoiceId: string;
    amount: number;
    credits: number;
    provider: string;
    companyName: string;
  } | null>(null);

  const sliderRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // Load PayPal SDK dynamically if needed
  useEffect(() => {
    if (typeof window !== 'undefined' && !paypalLoaded) {
      if ((window as any).paypal) {
        setPaypalLoaded(true);
        return;
      }
      const clientId = process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID || 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in';
      const script = document.createElement('script');
      script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD&intent=capture&components=buttons,funding-eligibility&enable-funding=card&disable-funding=credit,paylater`;
      script.async = true;
      script.onload = () => {
        setPaypalLoaded(true);
      };
      document.body.appendChild(script);
    }
  }, [paypalLoaded]);

  // Check URL parameters for returns & preselected amounts
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlAmount = parseFloat(params.get('amount') || '');
      if (urlAmount && !isNaN(urlAmount) && urlAmount >= 10 && urlAmount <= 5000) {
        setAmount(urlAmount);
      }

      if (params.get('success') === 'true') {
        const amt = parseFloat(params.get('amount') || '100') || 100;
        const creds = parseInt(params.get('credits') || '0', 10) || Math.round(amt * 100);
        setSuccessInfo({
          invoiceId: params.get('orderId') || params.get('invoiceId') || `AIK-CRED-${Date.now().toString().slice(-6)}`,
          amount: amt,
          credits: creds,
          provider: params.get('provider') === 'card' ? 'Tarjeta Débito/Crédito' : 'PayPal',
          companyName: user?.company_name || user?.name || 'Cliente Empresarial',
        });
        setStep(3);
        queryClient.invalidateQueries({ queryKey: ['credit-balance'] });
      }
    }
  }, [queryClient, user]);

  // Calculate credits and bonus
  const calculateCredits = useCallback((val: number) => {
    const baseCredits = val * 100;
    let bonusRate = 0;
    if (val >= 500) {
      bonusRate = 0.25; // 25% bonus
    } else if (val >= 250) {
      bonusRate = 0.15; // 15% bonus
    } else if (val >= 100) {
      bonusRate = 0.10; // 10% bonus
    }
    const bonusCredits = Math.round(baseCredits * bonusRate);
    const totalCredits = baseCredits + bonusCredits;
    return {
      baseCredits,
      bonusPercent: bonusRate * 100,
      bonusCredits,
      totalCredits,
    };
  }, []);

  const { bonusPercent, totalCredits } = calculateCredits(amount);

  // Eased slider distribution from $10 to $5000
  const positionToAmount = useCallback((ratio: number) => {
    const min = 10;
    const max = 5000;
    const value = min + (max - min) * Math.pow(ratio, 2.2);
    const raw = Math.round(value);
    if (raw < 100) return Math.round(raw / 5) * 5;
    if (raw < 500) return Math.round(raw / 10) * 10;
    return Math.round(raw / 50) * 50;
  }, []);

  const amountToPosition = useCallback((amt: number) => {
    const min = 10;
    const max = 5000;
    return Math.pow(Math.max(0, amt - min) / (max - min), 1 / 2.2);
  }, []);

  const updateFromPosition = useCallback(
    (clientX: number) => {
      const track = sliderRef.current;
      if (!track) return;
      const rect = track.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      setAmount(positionToAmount(ratio));
    },
    [positionToAmount]
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      isDragging.current = true;
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      updateFromPosition(e.clientX);
    },
    [updateFromPosition]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDragging.current) return;
      updateFromPosition(e.clientX);
    },
    [updateFromPosition]
  );

  const handlePointerUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const ratio = amountToPosition(amount);
  const gradientPosition = `${Math.round(ratio * 100)}%`;

  const presetAmounts = [20, 50, 100, 250, 500, 1000];

  const getSliderFeedback = () => {
    if (amount < 50) return t('creditPurchase.sliderFeedback.low');
    if (amount < 300) return t('creditPurchase.sliderFeedback.mid');
    return t('creditPurchase.sliderFeedback.high');
  };

  const estimatedConversations = Math.round(totalCredits / 8);
  const estimatedVoiceMinutes = Math.round(totalCredits / 5);
  const estimatedTokens = (totalCredits * 3000).toLocaleString();

  return (
    <section id="combustible" className="w-full py-8 sm:py-12 px-4 relative overflow-hidden">
      <div className="max-w-4xl mx-auto">
        {/* Header Badge & Title */}
        <div className="text-center space-y-4 mb-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 border border-indigo-500/25 text-indigo-600 dark:text-indigo-400 text-xs font-semibold">
            <Flame className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400 animate-pulse" />
            {t('creditPurchase.badge')}
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-tight text-foreground leading-tight">
            {t('creditPurchase.headline')}{' '}
            <span className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              {t('creditPurchase.headlineAccent')}
            </span>
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            {t('creditPurchase.subheadline')}
          </p>
        </div>

        {/* Card Main Container */}
        <div className="relative rounded-2xl border border-border bg-card/90 dark:bg-slate-900/80 backdrop-blur-xl shadow-2xl overflow-hidden p-6 sm:p-10 text-card-foreground">
          
          {/* Progress Indicator */}
          <div className="flex items-center justify-between border-b border-border pb-6 mb-8 text-xs font-semibold">
            <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary font-bold' : 'text-muted-foreground'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 1 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>1</span>
              {t('creditPurchase.step1')}
            </div>
            <div className="h-[1px] flex-1 mx-4 bg-border" />
            <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary font-bold' : 'text-muted-foreground'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 2 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>2</span>
              {t('creditPurchase.step2')}
            </div>
            <div className="h-[1px] flex-1 mx-4 bg-border" />
            <div className={`flex items-center gap-2 ${step >= 3 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-muted-foreground'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 3 ? 'bg-emerald-600 text-white' : 'bg-muted text-muted-foreground'}`}>3</span>
              {t('creditPurchase.step3')}
            </div>
          </div>

          {/* ═══════════════════════════════════════════════════════════════
              STEP 1: AMOUNT & CREDITS SELECTION
          ═══════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-8">
              {/* Big Interactive Amount & Credits Display */}
              <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 via-purple-500/5 to-slate-500/5 dark:from-indigo-950/40 dark:via-purple-950/20 dark:to-slate-900/60 p-6 text-center relative overflow-hidden">
                <div className="text-xs uppercase tracking-widest font-bold text-indigo-600 dark:text-indigo-400 mb-2">
                  {t('creditPurchase.sliderTitle')}
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 my-3">
                  {/* Price */}
                  <div>
                    <span className="text-4xl sm:text-6xl font-black text-foreground tracking-tight">
                      ${amount.toLocaleString()}
                    </span>
                    <span className="text-sm font-semibold text-muted-foreground ml-1.5">USD</span>
                  </div>

                  <div className="hidden sm:block text-muted-foreground text-3xl font-light">➜</div>

                  {/* Equivalent Credits */}
                  <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-indigo-500/10 dark:bg-indigo-500/15 border border-indigo-500/30">
                    <Coins className="w-7 h-7 text-amber-500 dark:text-amber-400 animate-pulse shrink-0" />
                    <div className="text-left">
                      <div className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-amber-500 to-indigo-600 dark:from-amber-300 dark:via-yellow-200 dark:to-indigo-200 bg-clip-text text-transparent">
                        {totalCredits.toLocaleString()}
                      </div>
                      <div className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-300 uppercase tracking-wider">
                        {t('creditPurchase.creditsLabel')}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bonus Ribbon */}
                {bonusPercent > 0 && (
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-bold mt-2">
                    <Sparkles className="w-3.5 h-3.5" />
                    {t('creditPurchase.bonusApplied', { percent: bonusPercent })}
                  </div>
                )}
              </div>

              {/* Slider Component */}
              <div className="space-y-3">
                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                  <span>$10 USD (1,000 Créditos)</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">$1 USD = 100 Créditos IA</span>
                  <span>$5,000 USD (625,000+ Créditos)</span>
                </div>

                {/* Slider Track */}
                <div
                  ref={sliderRef}
                  onPointerDown={handlePointerDown}
                  onPointerMove={handlePointerMove}
                  onPointerUp={handlePointerUp}
                  className="relative h-3 rounded-full bg-muted border border-border cursor-pointer touch-none select-none my-4"
                >
                  <div
                    className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"
                    style={{
                      width: gradientPosition,
                      transition: isDragging.current ? 'none' : 'width 0.1s ease',
                    }}
                  />
                  <div
                    ref={thumbRef}
                    className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-background shadow-xl shadow-indigo-500/30 border-2 border-indigo-500 cursor-grab active:cursor-grabbing flex items-center justify-center"
                    style={{
                      left: gradientPosition,
                      transition: isDragging.current ? 'none' : 'left 0.1s ease',
                    }}
                  >
                    <div className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
                  </div>
                </div>

                {/* Preset Pills */}
                <div className="flex flex-wrap gap-2 justify-center pt-2">
                  {presetAmounts.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setAmount(preset)}
                      className={`px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
                        amount === preset
                          ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 scale-105 border border-indigo-400/40'
                          : 'bg-muted/80 text-foreground hover:bg-muted border border-border'
                      }`}
                    >
                      ${preset} USD
                    </button>
                  ))}
                </div>

                <p className="text-center text-xs text-muted-foreground pt-1 italic">
                  {getSliderFeedback()}
                </p>
              </div>

              {/* Dynamic Capacity Metrics (Ferrari Equivalence) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="rounded-xl border border-border bg-muted/40 p-3.5 text-center">
                  <MessageSquare className="w-5 h-5 text-indigo-500 dark:text-indigo-400 mx-auto mb-1.5" />
                  <div className="text-lg font-bold text-foreground">~{estimatedConversations.toLocaleString()}</div>
                  <div className="text-[11px] text-muted-foreground leading-tight">{t('creditPurchase.metrics.conversations')}</div>
                </div>

                <div className="rounded-xl border border-border bg-muted/40 p-3.5 text-center">
                  <PhoneCall className="w-5 h-5 text-purple-500 dark:text-purple-400 mx-auto mb-1.5" />
                  <div className="text-lg font-bold text-foreground">~{estimatedVoiceMinutes.toLocaleString()} min</div>
                  <div className="text-[11px] text-muted-foreground leading-tight">{t('creditPurchase.metrics.voice')}</div>
                </div>

                <div className="rounded-xl border border-border bg-muted/40 p-3.5 text-center">
                  <Cpu className="w-5 h-5 text-pink-500 dark:text-pink-400 mx-auto mb-1.5" />
                  <div className="text-lg font-bold text-foreground">~{estimatedTokens}</div>
                  <div className="text-[11px] text-muted-foreground leading-tight">{t('creditPurchase.metrics.tokens')}</div>
                </div>

                <div className="rounded-xl border border-border bg-muted/40 p-3.5 text-center">
                  <Zap className="w-5 h-5 text-amber-500 dark:text-amber-400 mx-auto mb-1.5" />
                  <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">&lt;200ms</div>
                  <div className="text-[11px] text-muted-foreground leading-tight">{t('creditPurchase.metrics.latency')}</div>
                </div>
              </div>

              {/* Enterprise Onboarding Banner */}
              <div className="p-4 rounded-xl border border-border bg-muted/30 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="text-left">
                  <div className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    🏢 ¿Buscas contrato corporativo, IA telefónica o despliegue a medida?
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Agenda una videollamada con nuestros ingenieros de soluciones para activar tu infraestructura Enterprise.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowEnterpriseModal(true)}
                  className="border-indigo-500/40 text-indigo-600 dark:text-indigo-300 hover:text-white hover:bg-indigo-600 text-xs font-bold cursor-pointer shrink-0"
                >
                  Contáctanos / Solicitar Enterprise
                </Button>
              </div>

              {/* Action Button */}
              <Button
                size="lg"
                onClick={() => setStep(2)}
                className="w-full py-6 text-base font-bold bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-600 hover:opacity-95 text-white shadow-xl shadow-indigo-500/25 cursor-pointer rounded-xl"
              >
                {t('creditPurchase.actions.next')}
              </Button>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
              STEP 2: ENTERPRISE BILLING & SECURE CHECKOUT
          ═══════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="space-y-6">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1.5 mb-2 cursor-pointer transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                {t('creditPurchase.actions.back')}
              </button>

              {/* Order Proforma Summary Bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl bg-indigo-500/10 dark:bg-indigo-950/30 border border-indigo-500/30 gap-3">
                <div className="text-left w-full sm:w-auto">
                  <div className="text-xs text-indigo-600 dark:text-indigo-300 uppercase tracking-wider font-bold">
                    {t('creditPurchase.form.orderSummary')}
                  </div>
                  <div className="text-2xl font-black text-foreground">
                    ${amount.toLocaleString()} USD
                  </div>
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <span className="px-3 py-1 rounded-lg bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border border-indigo-500/30 text-xs font-bold">
                    ⚡ {totalCredits.toLocaleString()} {t('creditPurchase.creditsLabel')}
                  </span>
                </div>
              </div>

              {/* Enterprise Billing Fields */}
              <div className="space-y-4">
                <div className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                  {t('creditPurchase.form.title')}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      {t('creditPurchase.form.companyName')} *
                    </label>
                    <input
                      type="text"
                      required
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder={t('creditPurchase.form.companyNamePlaceholder')}
                      className="w-full px-4 py-3 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      {t('creditPurchase.form.taxId')} *
                    </label>
                    <input
                      type="text"
                      required
                      value={taxId}
                      onChange={(e) => setTaxId(e.target.value)}
                      placeholder={t('creditPurchase.form.taxIdPlaceholder')}
                      className="w-full px-4 py-3 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      {t('creditPurchase.form.email')} *
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={t('creditPurchase.form.emailPlaceholder')}
                      className="w-full px-4 py-3 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      {t('creditPurchase.form.phone')}
                    </label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder={t('creditPurchase.form.phonePlaceholder')}
                      className="w-full px-4 py-3 rounded-xl border border-input bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                  </div>
                </div>
              </div>

              {/* Payment Methods Selection */}
              <div className="space-y-3 pt-2">
                <label className="block text-xs font-semibold text-foreground">
                  {t('creditPurchase.form.selectMethod')}
                </label>

                <div className="grid grid-cols-2 gap-3">
                  {/* Card */}
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('card')}
                    className={`p-4 rounded-xl border text-center transition-all flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                      paymentMethod === 'card'
                        ? 'border-indigo-500 bg-indigo-500/15 shadow-lg shadow-indigo-500/20 ring-1 ring-indigo-500'
                        : 'border-border bg-muted/40 hover:bg-muted/70 text-foreground'
                    }`}
                  >
                    <CreditCard className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                    <span className="text-sm font-bold text-foreground">{t('creditPurchase.form.card')}</span>
                    <span className="text-[11px] text-muted-foreground">{t('creditPurchase.form.cardDesc')}</span>
                  </button>

                  {/* PayPal */}
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('paypal')}
                    className={`p-4 rounded-xl border text-center transition-all flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                      paymentMethod === 'paypal'
                        ? 'border-[#0070ba] bg-[#0070ba]/15 shadow-lg shadow-[#0070ba]/20 ring-1 ring-[#0070ba]'
                        : 'border-border bg-muted/40 hover:bg-muted/70 text-foreground'
                    }`}
                  >
                    <div className="text-base font-black text-[#0070ba]">PayPal</div>
                    <span className="text-sm font-bold text-foreground">{t('creditPurchase.form.paypal')}</span>
                    <span className="text-[11px] text-muted-foreground">{t('creditPurchase.form.paypalDesc')}</span>
                  </button>
                </div>
              </div>

              {/* Native PayPal / Debit Card Smart Button Container */}
              <div className="pt-4 flex flex-col items-center justify-center w-full">
                <PayPalButtonWrapper
                  key={paymentMethod}
                  amount={amount}
                  credits={totalCredits}
                  companyName={companyName}
                  taxId={taxId}
                  email={email}
                  phone={phone}
                  fundingType={paymentMethod}
                  onSuccess={(info) => {
                    setSuccessInfo(info);
                    setStep(3);
                  }}
                  setProcessing={setIsSubmitting}
                  processing={isSubmitting}
                />
              </div>

              {/* Enterprise Onboarding Alternative in Step 2 */}
              <div className="p-4 rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-500/5 via-purple-500/5 to-slate-500/5 dark:from-indigo-950/40 dark:via-purple-950/20 dark:to-slate-900/60 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-indigo-500/10 dark:bg-indigo-600/20 border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 shrink-0">
                    <Building2 className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      ¿Prefieres Facturación Corporativa / Onboarding Dedicado?
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Agenda una sesión con nuestro equipo para activar contratos B2B e IA telefónica.
                    </div>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowEnterpriseModal(true)}
                  className="border-indigo-500/40 text-indigo-600 dark:text-indigo-300 hover:text-white hover:bg-indigo-600 text-xs font-bold shrink-0 cursor-pointer"
                >
                  Solicitar Enterprise
                </Button>
              </div>

              {/* Security Badge */}
              <div className="text-center pt-2">
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400 shrink-0" />
                  {t('creditPurchase.form.securityBadge')}
                </p>
                <div className="flex justify-center gap-3 text-[11px] text-muted-foreground font-semibold mt-2">
                  <span>VISA</span> • <span>MASTERCARD</span> • <span>AMEX</span> • <span>PAYPAL</span> • <span>DINERS</span>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
              STEP 3: SUCCESS CONFIRMATION & PROFORMA RECEIPT
          ═══════════════════════════════════════════════════════════════ */}
          {step === 3 && (
            <div className="text-center space-y-6 py-4">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 border-2 border-emerald-500 text-emerald-500 flex items-center justify-center mx-auto text-3xl">
                <CheckCircle2 className="w-10 h-10" />
              </div>

              <div className="space-y-2">
                <h3 className="text-2xl sm:text-3xl font-black text-foreground">
                  {t('creditPurchase.success.title')}
                </h3>
                <p className="text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                  {t('creditPurchase.success.subtitle')}
                </p>
              </div>

              {/* Receipt Summary Card */}
              <div className="rounded-xl border border-border bg-muted/30 dark:bg-slate-950/60 p-5 text-left max-w-lg mx-auto space-y-3 font-mono text-xs text-foreground">
                <div className="flex justify-between items-center pb-2 border-b border-border font-sans">
                  <span className="text-muted-foreground font-semibold">{t('creditPurchase.success.amountPaid')}</span>
                  <span className="text-emerald-600 dark:text-emerald-400 text-base font-black">
                    ${(successInfo?.amount || amount).toFixed(2)} USD
                  </span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-border font-sans">
                  <span className="text-muted-foreground font-semibold">{t('creditPurchase.success.creditsCredited')}</span>
                  <span className="text-amber-600 dark:text-amber-300 text-base font-black">
                    {(successInfo?.credits || totalCredits).toLocaleString()} Créditos IA
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">{t('creditPurchase.success.invoiceNumber')}</span>
                  <span className="text-foreground font-bold">{successInfo?.invoiceId || 'AIK-CRED-849201'}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">{t('creditPurchase.success.status')}</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">{t('creditPurchase.success.statusConfirmed')}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2 max-w-md mx-auto">
                <Link href="/dashboard" className="w-full">
                  <Button
                    size="lg"
                    className="w-full py-6 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/25 cursor-pointer"
                  >
                    {t('creditPurchase.success.goToDashboard')}
                  </Button>
                </Link>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => {
                    setStep(1);
                    setSuccessInfo(null);
                  }}
                  className="w-full py-6 border-border text-foreground hover:bg-muted rounded-xl cursor-pointer"
                >
                  {t('creditPurchase.success.buyMore')}
                </Button>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Enterprise Onboarding Conversational Modal */}
      <EnterpriseOnboardingModal
        isOpen={showEnterpriseModal}
        onClose={() => setShowEnterpriseModal(false)}
      />
    </section>
  );
}
