'use client';

import { AlertTriangle, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface Props {
  /** Layer 1 (operational) balance. `-1` = unlimited. */
  creditBalance?: number | null;
  /** Layer 2 (observability / LEM telemetry) balance. `-1` = unlimited. */
  observabilityCredits?: number | null;
  /** Beta trial, demo, courtesy or active subscription accounts keep LEM protection. */
  isBetaOrTrial?: boolean;
  /** Super admins and master accounts are never shown the CTA. */
  isPrivileged?: boolean;
  /** Company data not loaded yet — render nothing instead of flashing a false alarm. */
  isLoading?: boolean;
  className?: string;
}

/**
 * Mirrors the backend `is_protected` rule in routes/observatory.py so the UI and
 * the API never disagree about whether LEM protection is active.
 */
export function hasLemProtection({
  creditBalance,
  observabilityCredits,
  isBetaOrTrial,
  isPrivileged,
}: Pick<Props, 'creditBalance' | 'observabilityCredits' | 'isBetaOrTrial' | 'isPrivileged'>) {
  return (
    !!isPrivileged ||
    !!isBetaOrTrial ||
    (creditBalance ?? 0) > 0 ||
    creditBalance === -1 ||
    (observabilityCredits ?? 0) > 0 ||
    observabilityCredits === -1
  );
}

export function SecurityCreditBanner({
  creditBalance,
  observabilityCredits,
  isBetaOrTrial,
  isPrivileged,
  isLoading,
  className,
}: Props) {
  if (isLoading) return null;
  if (hasLemProtection({ creditBalance, observabilityCredits, isBetaOrTrial, isPrivileged })) {
    return null;
  }

  return (
    <div className={`bg-amber-500/15 border-b border-amber-500/30 px-4 py-2 flex items-center justify-between text-xs text-amber-200 select-none z-20 ${className || ''}`}>
      <div className="flex items-center gap-2">
        <span className="p-1 rounded-md bg-amber-500/20 text-amber-400">
          <AlertTriangle className="h-4 w-4 animate-bounce" />
        </span>
        <span>
          <strong className="text-amber-300 font-semibold">Blindaje Determinista Desactivado:</strong> Tu cuenta no dispone de <strong>Tokens de Protección</strong>. El sistema opera en modo probabilístico vulnerable a alucinaciones y desvíos de datos.
        </span>
      </div>
      <Link
        href="/pricing"
        className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-500 hover:bg-amber-600 text-neutral-950 font-bold transition shadow-sm"
      >
        <span>Recargar Protección</span>
        <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
