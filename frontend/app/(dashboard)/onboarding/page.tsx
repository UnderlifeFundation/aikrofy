'use client';
 
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/use-auth-store';
import { VoiceOnboarding } from "@/components/onboarding/VoiceOnboarding";
import { useTranslation } from "react-i18next";

export default function OnboardingPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user, hydrated, isAuthenticated } = useAuthStore();

  const canAccess = Boolean(
    user && (user.is_company_owner || user.role === 'admin' || user.role === 'super_admin' || !user.role)
  );

  useEffect(() => {
    if (hydrated && isAuthenticated && user && !canAccess) {
      router.replace('/dashboard');
    }
  }, [hydrated, isAuthenticated, user, canAccess, router]);

  if (hydrated && isAuthenticated && user && !canAccess) {
    return null;
  }

  return (
    <div className="min-h-[calc(100vh-120px)] w-full flex flex-col items-center justify-center p-4 sm:p-6 my-auto">
      <div className="w-full max-w-2xl text-center mb-6">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-clip-text text-transparent mb-2">
          {t('onboarding.welcomeFuture', 'Bienvenido al Futuro')}
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground max-w-lg mx-auto">
          {t('onboarding.welcomeDesc', 'No necesitas llenar formularios aburridos. Solo háblale a tu CTO IA sobre tu negocio, tus productos y tus reglas.')}
        </p>
      </div>
      
      <div className="w-full flex justify-center items-center">
        <VoiceOnboarding />
      </div>
    </div>
  );
}

