'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/shared/language-switcher';
import { LottieLoader } from '@/components/shared/LottieLoader';
import aiMensajesAnimation from '@/lotties/ai-mensajes.json';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowRight,
  Bot,
  Shield,
  Zap,
  MessageCircle,
  Calendar,
  BarChart3,
  FileText,
  CheckCircle2,
  Sparkles,
  Globe,
  Users,
  HeartPulse,
  Leaf,
  Sun,
  Moon,
} from 'lucide-react';
import { PlatformChatWidget } from '@/components/features/platform-chat-widget';
import { CreditPurchaseSection } from '@/components/features/billing/CreditPurchaseSection';

export default function HomePage() {
  const { t } = useTranslation();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  return (
    <>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="flex min-h-screen flex-col bg-background relative"
      >
        <PlatformChatWidget />
        {/* ═══════════════════════════════════════════════
            NAVIGATION
        ═══════════════════════════════════════════════ */}
      <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="w-8 h-8" />
            <span className="text-xl font-bold tracking-tight">
              Aikrofy
            </span>
          </div>

          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#features" className="transition-colors hover:text-foreground">
              {t('home.nav.features')}
            </a>
            <a href="#how-it-works" className="transition-colors hover:text-foreground">
              {t('home.nav.howItWorks')}
            </a>
            <Link href="/pricing" className="transition-colors hover:text-foreground">
              {t('home.nav.pricing')}
            </Link>
            <Link href="/community" className="transition-colors hover:text-foreground font-medium text-emerald-500 hover:text-emerald-400">
              Open-Core &amp; Subvenciones
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            
            {mounted ? (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              >
                <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              </Button>
            ) : (
              <div className="w-9 h-9" />
            )}

            <Link href="/login" className="hidden sm:block">
              <Button variant="ghost" size="sm">
                {t('home.hero.signIn')}
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/25 hover:shadow-lg hover:shadow-indigo-500/30 transition-all border-0">
                {t('auth.register')} <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ═══════════════════════════════════════════════
          HERO SECTION
      ═══════════════════════════════════════════════ */}
      <section className="relative overflow-hidden">
        {/* Background decoration */}
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-40 right-0 h-[500px] w-[500px] rounded-full bg-indigo-500/5 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-[400px] w-[400px] rounded-full bg-violet-500/5 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-indigo-400/3 blur-3xl" />
        </div>

        <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6 sm:py-32 lg:py-40">
          <div className="mx-auto max-w-3xl text-center">
            {/* Badge */}
            <div className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/5 px-4 py-1.5 text-sm text-indigo-600 dark:text-indigo-400 mb-8">
              <Leaf className="mr-2 h-3.5 w-3.5" />
              {t('home.hero.badge')}
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl leading-tight">
              {t('home.hero.title')}
              <br />
              <span className="bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 bg-clip-text text-transparent">
                {t('home.hero.titleAccent')}
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground leading-relaxed">
              {t('home.hero.description')}
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link href="/register">
                <Button size="lg" className="px-8 bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 hover:scale-[1.02] transition-all border-0 text-base">
                  <Sparkles className="mr-2 h-4 w-4" />
                  {t('home.hero.cta')}
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="outline" size="lg" className="px-8 text-base">
                  {t('home.hero.signIn')}
                </Button>
              </Link>
            </div>

            {/* Trust badges */}
            <div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-indigo-500" /> {t('home.hero.trustNoCard')}
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-indigo-500" /> {t('home.hero.trustSetup')}
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-indigo-500" /> {t('home.hero.trustChannels')}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          FEATURES GRID
      ═══════════════════════════════════════════════ */}
      <section id="features" className="border-t bg-muted/30 py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/5 px-3 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 mb-4">
              {t('home.features.badge')}
            </div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              {t('home.features.title')}{' '}
              <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
                {t('home.features.titleAccent')}
              </span>
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
              {t('home.features.description')}
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Feature 1 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <Bot className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.agents.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.agents.description')}
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <MessageCircle className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.channels.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.channels.description')}
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <HeartPulse className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.wellness.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.wellness.description')}
              </p>
            </div>

            {/* Feature 4 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <Users className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.crm.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.crm.description')}
              </p>
            </div>

            {/* Feature 5 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <Calendar className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.scheduling.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.scheduling.description')}
              </p>
            </div>

            {/* Feature 6 */}
            <div className="group relative rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:border-indigo-500/30">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 text-indigo-600 dark:text-indigo-400">
                <FileText className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base">{t('home.features.items.knowledge.title')}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {t('home.features.items.knowledge.description')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          HOW IT WORKS
      ═══════════════════════════════════════════════ */}
      <section id="how-it-works" className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/5 px-3 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 mb-4">
              {t('home.howItWorks.badge')}
            </div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              {t('home.howItWorks.title')}{' '}
              <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
                {t('home.howItWorks.titleAccent')}
              </span>
            </h2>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {/* Step 1 */}
            <div className="relative text-center">
              <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
                1
              </div>
              <h3 className="font-semibold text-lg mb-2">{t('home.howItWorks.steps.step1.title')}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {t('home.howItWorks.steps.step1.description')}
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative text-center">
              <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
                2
              </div>
              <h3 className="font-semibold text-lg mb-2">{t('home.howItWorks.steps.step2.title')}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {t('home.howItWorks.steps.step2.description')}
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative text-center">
              <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
                3
              </div>
              <h3 className="font-semibold text-lg mb-2">{t('home.howItWorks.steps.step3.title')}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {t('home.howItWorks.steps.step3.description')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          STATS SECTION
      ═══════════════════════════════════════════════ */}
      <section className="border-y bg-gradient-to-r from-indigo-500 to-violet-600 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-8 text-center text-white sm:grid-cols-4">
            <div>
              <div className="text-4xl font-extrabold">24/7</div>
              <div className="mt-1 text-sm text-white/70">{t('home.stats.alwaysAvailable')}</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold">+40%</div>
              <div className="mt-1 text-sm text-white/70">{t('home.stats.channels')}</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold">20h+</div>
              <div className="mt-1 text-sm text-white/70">{t('home.stats.setupTime')}</div>
            </div>
            <div>
              <div className="text-4xl font-extrabold">100%</div>
              <div className="mt-1 text-sm text-white/70">{t('home.stats.conversations')}</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          SECURITY & DATA
      ═══════════════════════════════════════════════ */}
      <section className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <div className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/5 px-3 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 mb-4">
                {t('home.security.badge')}
              </div>
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl mb-4">
                {t('home.security.title')}{' '}
                <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
                  {t('home.security.titleAccent')}
                </span>
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-8">
                {t('home.security.description')}
              </p>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    <Shield className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="font-medium text-sm">{t('home.security.encryption.title')}</div>
                    <div className="text-sm text-muted-foreground">{t('home.security.encryption.description')}</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    <Globe className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="font-medium text-sm">{t('home.security.isolation.title')}</div>
                    <div className="text-sm text-muted-foreground">{t('home.security.isolation.description')}</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    <Zap className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="font-medium text-sm">{t('home.security.i18n.title')}</div>
                    <div className="text-sm text-muted-foreground">{t('home.security.i18n.description')}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual card */}
            <div className="relative">
              <div className="rounded-2xl border bg-card p-8 shadow-xl shadow-indigo-500/5">
                <div className="space-y-4">
                  <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{t('home.security.mockup.agentName')}</div>
                      <div className="text-xs text-muted-foreground">&quot;{t('home.security.mockup.agentGreeting')}&quot;</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-indigo-500/5 p-4 border border-indigo-500/10">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      <MessageCircle className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{t('home.security.mockup.customerName')}</div>
                      <div className="text-xs text-muted-foreground">&quot;{t('home.security.mockup.customerQuery')}&quot;</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{t('home.security.mockup.agentName')}</div>
                      <div className="text-xs text-muted-foreground">&quot;{t('home.security.mockup.agentResponse')}&quot;</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400">
                      <BarChart3 className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{t('home.security.mockup.leadCaptured')}</div>
                      <div className="text-xs text-muted-foreground">{t('home.security.mockup.leadDetails')}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          INTERACTIVE FUEL / CREDIT RECHARGE TOOL
      ═══════════════════════════════════════════════ */}
      <section id="pricing" className="border-t bg-muted/20 py-12">
        <CreditPurchaseSection />
      </section>

      {/* ═══════════════════════════════════════════════
          FOOTER
      ═══════════════════════════════════════════════ */}
      <footer className="border-t py-8 bg-muted/10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="flex items-center gap-2">
                <img src="/icono-aikrofy.png" alt="Aikrofy Logo" className="w-6 h-6" />
                <span className="text-sm font-semibold">
                  Aikrofy
                </span>
              </div>
              <span className="hidden sm:inline text-xs text-muted-foreground/60">•</span>
              <p className="text-xs text-muted-foreground text-center sm:text-left">
                Un proyecto de <strong className="font-medium text-foreground">Fundación Underlife</strong> · Impulsado por <strong className="font-medium text-foreground">Weblifetech</strong>
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
              <Link href="/pricing" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                {t('legal.pricingTitle')}
              </Link>
              <Link href="/privacy" id="privacy-policy-link" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                {t('legal.privacyTitle')}
              </Link>
              <Link href="/terms" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                {t('legal.termsTitle')}
              </Link>
              <Link href="/refunds" className="text-xs text-muted-foreground hover:text-indigo-500 transition-colors">
                {t('legal.refundsTitle')}
              </Link>
              <p className="text-xs text-muted-foreground">
                © {new Date().getFullYear()} Aikrofy. {t('home.footer.legal')}
              </p>
            </div>
          </div>
        </div>
      </footer>
      </motion.div>
    </>
  );
}
