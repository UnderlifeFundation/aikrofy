import axios from 'axios';
import Cookies from 'js-cookie';

// Extend Axios config type to allow our custom retry flag
declare module 'axios' {
    interface InternalAxiosRequestConfig {
        _retried?: boolean;
    }
}

const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Rutas públicas de auth — nunca redirigir desde estas rutas si hay un 401
const AUTH_PUBLIC_PATHS = ['/login', '/register', '/beta-register', '/privacy', '/terms'];

// Flag global para evitar múltiples redirects concurrentes al logout
let isRedirectingToLogin = false;

import { getDeviceTelemetryHeaders } from './device-telemetry';

apiClient.interceptors.request.use(
    (config) => {
        const token = Cookies.get('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Attach physical device hardware fingerprint & telemetry
        try {
            const deviceHeaders = getDeviceTelemetryHeaders();
            for (const [key, value] of Object.entries(deviceHeaders)) {
                if (value) {
                    config.headers[key] = value;
                }
            }
        } catch {
            // Ignore if in restricted context
        }

        // Attach active workspace company context for Agency accounts
        try {
            if (typeof window !== 'undefined') {
                const activeCompId = localStorage.getItem('aikrofy_active_company_id');
                if (activeCompId) {
                    config.headers['X-Company-Context'] = activeCompId;
                }
            }
        } catch {
            // Ignore if in restricted SSR context
        }

        return config;
    },
    (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            if (typeof window === 'undefined') {
                // SSR context — no redirect needed
                return Promise.reject(error);
            }

            const currentPath = window.location.pathname;

            // Never redirect if already on an auth/public page
            const isOnAuthPage = AUTH_PUBLIC_PATHS.some((p) => currentPath.startsWith(p));
            if (isOnAuthPage) {
                return Promise.reject(error);
            }

            // Avoid concurrent redirects (e.g. multiple parallel 401s)
            if (isRedirectingToLogin) {
                return Promise.reject(error);
            }

            // --- Smart retry: wait briefly to allow cookie propagation ---
            // This handles the race condition where the cookie was just set
            // by the login() action but hasn't propagated to this request yet.
            const tokenAfterWait = await new Promise<string | undefined>((resolve) => {
                setTimeout(() => resolve(Cookies.get('access_token')), 200);
            });

            if (tokenAfterWait && error.config && !error.config._retried) {
                // Token is now available — retry once with the fresh token
                error.config._retried = true;
                error.config.headers = {
                    ...error.config.headers,
                    Authorization: `Bearer ${tokenAfterWait}`,
                };
                return apiClient(error.config);
            }

            // If still no token after the wait, it's a genuine auth failure
            // Only redirect if the user is on a protected (dashboard) route
            const isOnProtectedRoute =
                currentPath.startsWith('/dashboard') ||
                currentPath.startsWith('/admin') ||
                currentPath.startsWith('/channels') ||
                currentPath.startsWith('/agents') ||
                currentPath.startsWith('/analytics') ||
                currentPath.startsWith('/contacts') ||
                currentPath.startsWith('/settings') ||
                currentPath.startsWith('/employees') ||
                currentPath.startsWith('/departments') ||
                currentPath.startsWith('/documents') ||
                currentPath.startsWith('/landing-pages') ||
                currentPath.startsWith('/chat') ||
                currentPath.startsWith('/billing') ||
                currentPath.startsWith('/subscribe') ||
                currentPath.startsWith('/activate-trial') ||
                currentPath.startsWith('/feedback') ||
                currentPath.startsWith('/onboarding');

            if (isOnProtectedRoute) {
                isRedirectingToLogin = true;
                try {
                    const { useAuthStore } = require('@/store/use-auth-store');
                    useAuthStore.getState().logout();
                } catch (e) {
                    // Fallback: manually clear cookies if the store is unavailable
                    Cookies.remove('access_token');
                    Cookies.remove('refresh_token');
                }
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default apiClient;
