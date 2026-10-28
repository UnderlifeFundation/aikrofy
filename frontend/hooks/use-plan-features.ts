'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';

interface PlanFeatures {
  max_agents: number;
  max_documents: number;
  max_leads: number;
  monthly_credits: number;
  channels: string[];
  integrations: string[];
  rag_enabled: boolean;
  analytics_enabled: boolean;
  voice_enabled: boolean;
  scheduling_enabled: boolean;
  payments_enabled: boolean;
}

interface SubscriptionData {
  status: string;
  is_active: boolean;
  features?: Partial<PlanFeatures>;
  plan_name?: string;
}

const DEFAULT_FEATURES: PlanFeatures = {
  max_agents: 1,
  max_documents: 5,
  max_leads: 50,
  monthly_credits: 0,
  channels: ['whatsapp'],
  integrations: [],
  rag_enabled: false,
  analytics_enabled: false,
  voice_enabled: false,
  scheduling_enabled: false,
  payments_enabled: false,
};

const UNLIMITED_FEATURES: PlanFeatures = {
  max_agents: 999,
  max_documents: 999,
  max_leads: 999999,
  monthly_credits: 999999,
  channels: ['whatsapp', 'telegram', 'email', 'google', 'webchat'],
  integrations: ['paypal', 'twilio'],
  rag_enabled: true,
  analytics_enabled: true,
  voice_enabled: true,
  scheduling_enabled: true,
  payments_enabled: true,
};

export function usePlanFeatures() {
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.role === 'super_admin';

  const { data: subscription, isLoading } = useQuery<SubscriptionData>({
    queryKey: ['my-subscription'],
    queryFn: async () => {
      const { data } = await apiClient.get('/billing/my-subscription');
      return data;
    },
    staleTime: 60_000,
  });

  const isCourtesy = subscription?.status === 'courtesy';
  const isActive = subscription?.is_active ?? false;

  // Super admin and courtesy accounts get unlimited access
  if (isSuperAdmin || isCourtesy) {
    return {
      ...UNLIMITED_FEATURES,
      isCourtesy,
      isActive: true,
      isSuperAdmin,
      isLoading,
      planName: subscription?.plan_name ?? '',
      // Helper methods
      canUseChannel: (_channel: string) => true,
      canUseIntegration: (_integration: string) => true,
      hasReachedAgentLimit: (_currentCount: number) => false,
      hasReachedDocumentLimit: (_currentCount: number) => false,
      hasReachedLeadLimit: (_currentCount: number) => false,
    };
  }

  const features = subscription?.features ?? {};

  const resolved: PlanFeatures = {
    max_agents: features.max_agents ?? DEFAULT_FEATURES.max_agents,
    max_documents: features.max_documents ?? DEFAULT_FEATURES.max_documents,
    max_leads: features.max_leads ?? DEFAULT_FEATURES.max_leads,
    monthly_credits: features.monthly_credits ?? DEFAULT_FEATURES.monthly_credits,
    channels: features.channels ?? DEFAULT_FEATURES.channels,
    integrations: features.integrations ?? DEFAULT_FEATURES.integrations,
    rag_enabled: features.rag_enabled ?? DEFAULT_FEATURES.rag_enabled,
    analytics_enabled: features.analytics_enabled ?? DEFAULT_FEATURES.analytics_enabled,
    voice_enabled: features.voice_enabled ?? DEFAULT_FEATURES.voice_enabled,
    scheduling_enabled: features.scheduling_enabled ?? DEFAULT_FEATURES.scheduling_enabled,
    payments_enabled: features.payments_enabled ?? DEFAULT_FEATURES.payments_enabled,
  };

  return {
    ...resolved,
    isCourtesy,
    isActive,
    isSuperAdmin,
    isLoading,
    planName: subscription?.plan_name ?? '',
    canUseChannel: (channel: string) => resolved.channels.includes(channel),
    canUseIntegration: (integration: string) => resolved.integrations.includes(integration),
    hasReachedAgentLimit: (currentCount: number) => currentCount >= resolved.max_agents,
    hasReachedDocumentLimit: (currentCount: number) => currentCount >= resolved.max_documents,
    hasReachedLeadLimit: (currentCount: number) => currentCount >= resolved.max_leads,
  };
}
