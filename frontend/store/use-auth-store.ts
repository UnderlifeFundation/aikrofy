import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import Cookies from 'js-cookie';
import type { User, PermissionsContext } from '@/types';

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    language: string;
    hydrated: boolean;
    /** Cached permissions context from the most recent /auth/me fetch. */
    permissionsContext: PermissionsContext | null;
    login: (user: User, accessToken: string, refreshToken: string) => void;
    logout: () => void;
    updateUser: (userUpdates: Partial<User>) => void;
    setPermissionsContext: (ctx: PermissionsContext) => void;
    setLanguage: (lang: string) => void;
    /** True once the store has rehydrated from localStorage AND a cookie exists,
     *  OR once login() has been called in this session. Use this instead of
     *  isAuthenticated for redirect guards to avoid race conditions. */
    isAuthReady: boolean;
    _setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            isAuthenticated: false,
            language: 'en',
            hydrated: false,
            permissionsContext: null,
            isAuthReady: false,
            _setHydrated: () => {
                const state = get();
                // isAuthReady is true only when both hydrated AND the cookie exists
                // (or there is already a user in the state)
                const hasCookie = typeof window !== 'undefined' && !!Cookies.get('access_token');
                set({
                    hydrated: true,
                    isAuthReady: state.isAuthenticated || hasCookie,
                });
            },
            login: (user, accessToken, refreshToken) => {
                Cookies.set('access_token', accessToken, {
                    expires: 1,
                    sameSite: 'Lax',
                    secure: window.location.protocol === 'https:',
                }); // 1 day
                Cookies.set('refresh_token', refreshToken, {
                    expires: 7,
                    sameSite: 'Lax',
                    secure: window.location.protocol === 'https:',
                });
                set({ user, isAuthenticated: true, language: 'en', isAuthReady: true });
            },
            logout: () => {
                Cookies.remove('access_token');
                Cookies.remove('refresh_token');
                set({ user: null, isAuthenticated: false, isAuthReady: false, permissionsContext: null });
            },
            updateUser: (userUpdates) =>
                set((state) => {
                    if (!state.user) return { user: null };
                    const currentUser = state.user as any;
                    return {
                        user: {
                            ...currentUser,
                            ...userUpdates,
                            // Only merge company updates if explicitly provided, don't bleed user-level
                            // fields (name, email, etc.) into the company object
                            company: userUpdates.company
                                ? { ...(currentUser.company || {}), ...userUpdates.company }
                                : currentUser.company || null,
                        },
                    };
                }),
            setPermissionsContext: (ctx) => set({ permissionsContext: ctx }),
            setLanguage: (lang) => set({ language: lang }),
        }),
        {
            name: 'auth-storage',
            onRehydrateStorage: () => (state) => {
                if (state) {
                    state._setHydrated();
                }
            },
        }
    )
);
