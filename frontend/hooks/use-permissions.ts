/**
 * usePermissions — Aikrofy Company Hierarchy Hook
 * ================================================
 * Provides role-aware boolean flags for conditional UI rendering.
 *
 * Usage:
 *   const { isOwner, canGrantWebAccess, canManageAdmins } = usePermissions();
 *
 * The hook reads data returned by GET /api/auth/me (permissions_context),
 * falling back to simple role inference if the context is not yet loaded.
 *
 * Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
 */
'use client';

import { useAuthStore } from '@/store/use-auth-store';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { PermissionsContext } from '@/types';

interface UsePermissionsResult {
  /** True if the logged-in user is the founding account of the company (root). */
  isOwner: boolean;
  /** True for platform super-admins (Aikrofy staff). */
  isSuperAdmin: boolean;
  /** True for any admin (owner or delegated) and super-admins. */
  isAdmin: boolean;
  /** True if the user can toggle has_web_access on employee records. Only owner + super-admin. */
  canGrantWebAccess: boolean;
  /** True if the user can create or delete ADMIN-level user accounts. Only owner + super-admin. */
  canManageAdmins: boolean;
  /** True if the user can create/edit/delete employees (manager-level and below). */
  canManageEmployees: boolean;
  /** The raw permissions_context from the backend, if available. */
  permissionsContext: PermissionsContext | null;
  /** True while the permissions context is still loading. */
  isLoading: boolean;
}

export function usePermissions(): UsePermissionsResult {
  const { user, isAuthenticated } = useAuthStore();

  // Fetch fresh context from /api/auth/me
  const { data: meData, isLoading } = useQuery({
    queryKey: ['me-permissions'],
    queryFn: async () => {
      const { data } = await apiClient.get('/auth/me');
      return data.data as {
        user: typeof user;
        permissions_context?: PermissionsContext;
      };
    },
    enabled: isAuthenticated,
    staleTime: 60_000, // 1 min cache
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 401) return false;
      return failureCount < 2;
    },
  });

  const ctx = meData?.permissions_context ?? null;

  // Derive fallback values from the locally stored user
  const localRole = user?.role ?? 'employee';
  const localIsOwner = user?.is_company_owner ?? false;
  const localIsSuperAdmin = localRole === 'super_admin';
  const localIsAdmin = localRole === 'admin' || localIsSuperAdmin;

  // Prefer server-side context over local inference
  const isOwner = ctx?.is_company_owner ?? localIsOwner;
  const isSuperAdmin = localIsSuperAdmin;
  const isAdmin = ctx?.is_admin_or_above ?? localIsAdmin;
  const canGrantWebAccess = ctx?.can_grant_web_access ?? (isOwner || isSuperAdmin);
  const canManageAdmins = ctx?.can_manage_admins ?? (isOwner || isSuperAdmin);
  const canManageEmployees = isAdmin; // delegated admins can also manage employees

  return {
    isOwner,
    isSuperAdmin,
    isAdmin,
    canGrantWebAccess,
    canManageAdmins,
    canManageEmployees,
    permissionsContext: ctx,
    isLoading,
  };
}
