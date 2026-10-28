/**
 * Channels Service
 * Handles API calls for WhatsApp session management
 */
import apiClient from '@/lib/api-client';

export interface WhatsAppStatusResponse {
    connected: boolean;
    phone?: string | null;
    status?: string | null;
}

export interface WhatsAppQRResponse {
    qr?: string;
    success?: boolean;
    error?: string;
}

export interface ChannelActionResponse {
    success: boolean;
    message?: string;
    error?: string;
    session_id?: string;
}

// ─── Meta Embedded Signup types ────────────────────────────────────────────

export interface MetaWaba {
    id: string;
    name: string;
    currency?: string;
    timezone_id?: string;
}

export interface MetaPhoneNumber {
    id: string;
    display_phone_number: string;
    verified_name: string;
    code_verification_status?: string;
    quality_rating?: string;
}

export type MetaSignupResult =
    | { action: 'connected'; status: 'connected'; phone_number: string; verified_name: string; waba_id: string; phone_number_id: string; webhook_subscribed: boolean; channel: any }
    | { action: 'select_waba'; access_token: string; waba_list: MetaWaba[] }
    | { action: 'select_phone'; access_token: string; waba_id: string; phone_numbers: MetaPhoneNumber[]; subscription_ok: boolean };

// ─── Service ────────────────────────────────────────────────────────────────

export const channelsService = {
    /**
     * Initialize WhatsApp session (triggers QR generation)
     */
    async initWhatsApp(): Promise<ChannelActionResponse> {
        const { data } = await apiClient.post<ChannelActionResponse>('/channels/connect', {
            type: 'whatsapp',
            provider: 'baileys'
        });
        return data;
    },

    /**
     * Connect WhatsApp with specific provider and credentials (legacy/manual path)
     */
    async connectWhatsApp(provider: string, credentials?: any): Promise<ChannelActionResponse> {
        const { data } = await apiClient.post<ChannelActionResponse>('/channels/connect', {
            type: 'whatsapp',
            provider,
            credentials
        });
        return data;
    },

    /**
     * Meta Embedded Signup — Step 1 (Tech Provider flow).
     *
     * Sends the authorization `code` (and optionally `waba_id` + `phone_number_id`
     * if the Meta SDK postMessage already included them) to the backend.
     *
     * The backend exchanges the code for an access token, auto-discovers
     * the WABA and phone number, subscribes webhooks automatically, and
     * returns one of three `action` values:
     *   - "connected"     → connection complete, no more steps needed
     *   - "select_waba"   → multiple WABAs found, frontend must let user pick
     *   - "select_phone"  → multiple phones found, frontend must let user pick
     */
    async embeddedSignupMeta(payload: {
        code: string;
        waba_id?: string;
        phone_number_id?: string;
    }): Promise<MetaSignupResult> {
        const { data } = await apiClient.post<MetaSignupResult>(
            '/channels/meta/embedded-signup',
            payload
        );
        return data;
    },

    /**
     * Meta Embedded Signup — Step 2 (only called when multiple phones/WABAs exist).
     * Completes connection using the user-selected phone number.
     */
    async selectMetaPhone(payload: {
        access_token: string;
        waba_id: string;
        phone_number_id: string;
    }): Promise<MetaSignupResult> {
        const { data } = await apiClient.post<MetaSignupResult>(
            '/channels/meta/select-phone',
            payload
        );
        return data;
    },

    /**
     * Meta Embedded Signup — called when user selects a WABA from a list.
     * Reuses embeddedSignupMeta but passes waba_id (skips WABA discovery).
     */
    async selectMetaWaba(payload: {
        access_token: string;
        waba_id: string;
    }): Promise<MetaSignupResult> {
        // We pass access_token as a dummy code since the backend now expects
        // the waba_id hint to skip WABA discovery.  We call select-phone
        // route with the full info once user picks the phone.
        // Actually, use embedded-signup with pre-known waba_id to discover phones:
        const { data } = await apiClient.post<MetaSignupResult>(
            '/channels/meta/embedded-signup',
            {
                code: payload.access_token,   // Re-use access_token directly (backend will detect no exchange needed)
                waba_id: payload.waba_id,
            }
        );
        return data;
    },

    /**
     * Get WhatsApp QR code for scanning
     */
    async getWhatsAppQR(): Promise<WhatsAppQRResponse> {
        try {
            const response = await apiClient.get('/channels/whatsapp/qr', {
                responseType: 'text', // Can be SVG text or JSON
                validateStatus: (status) => status >= 200 && status < 300
            });
            
            // If the server returns 202 Accepted, it's still waiting
            if (response.status === 202) {
                return { success: false };
            }

            // If it's an SVG string
            if (typeof response.data === 'string' && response.data.trim().startsWith('<svg')) {
                return { qr: response.data, success: true };
            }
            
            // If it's JSON
            if (typeof response.data === 'object') {
                if (response.data.qr) return { qr: response.data.qr, success: true };
                if (response.data.status === 'connected') return { success: true };
            }
            
            return { success: false };
        } catch (error) {
            return { success: false, error: 'failed' };
        }
    },

    /**
     * Get WhatsApp connection status
     */
    async getWhatsAppStatus(): Promise<WhatsAppStatusResponse> {
        const { data } = await apiClient.get<WhatsAppStatusResponse>('/channels/whatsapp/status');
        return data;
    },

    /**
     * Get Meta Configuration (app_id, config_id, verify_token)
     */
    async getMetaConfig(): Promise<{ app_id: string; config_id: string; verify_token: string }> {
        const { data } = await apiClient.get('/channels/meta/config');
        return data;
    },

    /**
     * Disconnect WhatsApp session
     */
    async disconnectWhatsApp(): Promise<ChannelActionResponse> {
        const { data } = await apiClient.post<ChannelActionResponse>('/channels/whatsapp/disconnect');
        return data;
    },
};

export default channelsService;
