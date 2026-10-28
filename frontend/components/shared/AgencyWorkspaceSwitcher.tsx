'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import { Building2, ChevronDown, Check, Plus, ExternalLink, ShieldCheck } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export function AgencyWorkspaceSwitcher() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeCompanyId, setActiveCompanyId] = useState<number | null>(null);

  // Load active company from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('aikrofy_active_company_id');
      if (saved) setActiveCompanyId(Number(saved));
    }
  }, []);

  // Fetch all companies under this agency account
  const { data, isLoading } = useQuery({
    queryKey: ['agency-companies'],
    queryFn: async () => {
      const res = await apiClient.get('/agency/companies');
      return res.data;
    },
    enabled: !!user && (user.role === 'agency' || user.role === 'super_admin'),
    staleTime: 60000,
  });

  const switchMutation = useMutation({
    mutationFn: async (companyId: number) => {
      const res = await apiClient.post(`/agency/companies/${companyId}/switch`);
      return res.data;
    },
    onSuccess: (data, companyId) => {
      localStorage.setItem('aikrofy_active_company_id', String(companyId));
      setActiveCompanyId(companyId);
      toast.success(data.message || 'Espacio de trabajo cambiado');
      // Invalidate all app data to reflect active company context
      queryClient.invalidateQueries();
    },
    onError: () => {
      toast.error('No se pudo cambiar al espacio de trabajo seleccionado');
    }
  });

  // Only render for agency or super_admin users
  if (!user || (user.role !== 'agency' && user.role !== 'super_admin')) {
    return null;
  }

  const companies: any[] = data?.companies || [];
  const currentCompany = companies.find(c => (c.company_id || c.id) === activeCompanyId) || companies[0];

  return (
    <div className="flex items-center">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-2 border-violet-500/30 bg-violet-500/10 hover:bg-violet-500/20 text-xs font-semibold text-violet-300 transition-all shadow-sm"
          >
            <Building2 className="h-3.5 w-3.5 text-violet-400" />
            <span className="max-w-[120px] sm:max-w-[160px] truncate">
              {currentCompany?.company_name || currentCompany?.name || 'Mi Espacio'}
            </span>
            <ChevronDown className="h-3 w-3 opacity-60" />
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
            <span>Cuentas de Clientes</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-mono">
              Agencia
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />

          <div className="max-h-56 overflow-y-auto space-y-0.5">
            {companies.map((c) => {
              const compId = c.company_id || c.id;
              const isSelected = activeCompanyId ? activeCompanyId === compId : compId === currentCompany?.company_id;
              return (
                <DropdownMenuItem
                  key={compId}
                  onClick={() => switchMutation.mutate(compId)}
                  className={`flex items-center justify-between cursor-pointer text-xs ${
                    isSelected ? 'bg-violet-500/15 font-semibold text-violet-300' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <Building2 className="h-3.5 w-3.5 opacity-70 shrink-0" />
                    <span className="truncate">{c.company_name || c.name}</span>
                  </div>
                  {isSelected && <Check className="h-3.5 w-3.5 text-violet-400 shrink-0" />}
                </DropdownMenuItem>
              );
            })}
          </div>

          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => router.push('/agency')}
            className="text-xs text-violet-400 font-medium cursor-pointer flex items-center gap-2"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Gestionar Licencias y Clientes</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
