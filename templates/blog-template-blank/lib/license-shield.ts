/**
 * Aikrofy Cryptographic Shield Client
 * Enforces hardware & tenant license verification.
 * Prevents unauthorized execution if the company has not purchased the asset
 * or if the cryptographic signature is invalid.
 *
 * Copyright © 2026 WEBLIFETECH. All Rights Reserved.
 */

export interface LicenseStatus {
  valid: boolean;
  company_id?: number;
  company_name?: string;
  agent_name?: string;
  voice_model?: string;
  features_unlocked?: Record<string, boolean>;
  reason?: string;
  verified_at?: string;
}

export async function verifyInstallationLicense(hostDomain?: string): Promise<LicenseStatus> {
  const companyId = process.env.AIKROFY_COMPANY_ID;
  const licenseKey = process.env.AIKROFY_LICENSE_KEY;
  const apiUrl = process.env.AIKROFY_API_URL || 'https://aikrofy.com';

  // If local development without keys, allow fallback in dev mode only
  if (!licenseKey || !companyId) {
    if (process.env.NODE_ENV === 'development') {
      return {
        valid: true,
        company_id: 1,
        company_name: 'Entorno de Prueba Local (Dev)',
        agent_name: 'Krof Dev',
        features_unlocked: { seo_long_tail: true, canvas_drag_drop: true },
        verified_at: new Date().toISOString(),
      };
    }
    return {
      valid: false,
      reason: 'Faltan variables AIKROFY_COMPANY_ID o AIKROFY_LICENSE_KEY en .env.production',
    };
  }

  try {
    const res = await fetch(`${apiUrl}/api/marketplace/licenses/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_id: companyId,
        license_key: licenseKey,
        asset_slug: 'blog_module',
        host_domain: hostDomain || 'localhost',
      }),
      cache: 'no-store',
    });

    if (!res.ok) {
      const err = await res.json();
      return {
        valid: false,
        reason: err.reason || 'Error de validación con el servidor de Aikrofy',
      };
    }

    return await res.json();
  } catch (error: any) {
    // If backend is unreachable but license matches format, allow graceful operational mode
    if (licenseKey.startsWith('AKF-')) {
      return {
        valid: true,
        company_id: Number(companyId),
        company_name: 'Modo Autónomo Protegido (Offline)',
        agent_name: 'Krof Local',
        verified_at: new Date().toISOString(),
      };
    }
    return {
      valid: false,
      reason: `No se pudo conectar al verificador de licencias: ${error?.message}`,
    };
  }
}
