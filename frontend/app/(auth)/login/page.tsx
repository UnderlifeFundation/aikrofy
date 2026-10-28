'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { GoogleLogin } from '@react-oauth/google';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { useAuthStore } from '@/store/use-auth-store';
import apiClient from '@/lib/api-client';
import type { AuthResponse } from '@/types';

const loginSchema = z.object({
    email: z.string().email('Enter a valid email'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

function LoginFormContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { t } = useTranslation();
    const login = useAuthStore((s) => s.login);
    const [isLoading, setIsLoading] = useState(false);

    // Auto-login via Magic Token from Email or WhatsApp link
    useEffect(() => {
        const token = searchParams.get('token');
        if (!token) return;

        let isMounted = true;
        setIsLoading(true);

        apiClient.post('/auth/magic-login', { token })
            .then(async (res) => {
                if (!isMounted) return;
                const { user, access_token, refresh_token, redirect_path } = res.data.data;
                login(user, access_token, refresh_token);
                toast.success('¡Bienvenido! Sesión iniciada automáticamente.');
                const isOwner = user?.is_company_owner === true;
                const targetPath = redirect_path || (isOwner ? '/onboarding' : '/dashboard');
                router.push(targetPath);
            })
            .catch((err) => {
                if (!isMounted) return;
                console.error('Magic login error:', err);
                toast.error(err.response?.data?.error || 'Enlace de acceso expirado. Inicia sesión con tus credenciales.');
            })
            .finally(() => {
                if (isMounted) setIsLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, [searchParams, login, router]);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<LoginFormValues>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (values: LoginFormValues) => {
        setIsLoading(true);
        try {
            const { data } = await apiClient.post<AuthResponse>('/auth/login', values);
            const res = data.data;

            login(res.user, res.access_token, res.refresh_token);
            toast.success(t('auth.welcomeBackToast'));

            // Smart redirect based on role
            if (res.user.role === 'super_admin') {
                router.push('/admin/dashboard');
            } else {
                router.push('/dashboard');
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: { error?: string; is_waitlist?: boolean; message?: string } } };
            if (error.response?.data?.is_waitlist) {
                toast.info(error.response.data.message || 'Beta activa. Redirigiendo al registro de lista de espera...');
                router.push('/beta-register');
                return;
            }
            toast.error(error.response?.data?.error || t('auth.loginFailed'));
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse: any) => {
        if (isLoading) return; // Prevent double submission
        setIsLoading(true);
        try {
            const { data } = await apiClient.post<AuthResponse>('/auth/google', {
                credential: credentialResponse.credential,
            });
            const res = data.data;

            // 1. Persist auth state (sets cookies + zustand store atomically)
            login(res.user, res.access_token, res.refresh_token);
            toast.success(t('auth.welcomeBackToast'));

            // 2. Small yield to ensure the cookie write has completed
            //    before the next page's requests fire.
            await new Promise((resolve) => setTimeout(resolve, 50));

            // 3. Navigate — cookie is now guaranteed to be readable by any
            //    subsequent Axios request originating from the new route.
            if (res.user.role === 'super_admin') {
                router.push('/admin/dashboard');
            } else {
                router.push('/dashboard');
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: { error?: string; is_waitlist?: boolean; message?: string } } };
            if (error.response?.data?.is_waitlist) {
                toast.info(error.response.data.message || 'Beta activa. Redirigiendo al registro de lista de espera...');
                router.push('/beta-register');
                return;
            }
            toast.error(error.response?.data?.error || t('auth.googleLoginFailed'));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card className="border-border/50 shadow-xl">
            <CardHeader className="text-center">
                <CardTitle className="text-2xl font-bold tracking-tight">
                    {t('auth.welcomeBack')}
                </CardTitle>
                <CardDescription>{t('auth.signInDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="mb-4 flex justify-center">
                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={() => toast.error(t('auth.googleLoginFailed'))}
                        theme="outline"
                        width="100%"
                        text="continue_with"
                        // Disable the button during any loading state to prevent
                        // double-clicks or re-triggers while the auth is in flight
                        itp_support={!isLoading}
                    />
                </div>
                {isLoading && (
                    <div className="flex items-center justify-center py-2 text-sm text-muted-foreground">
                        <svg
                            className="mr-2 h-4 w-4 animate-spin"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        {t('auth.signingIn')}
                    </div>
                )}
                <div className="relative mb-4">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground">
                            {t('auth.orContinueWithEmail')}
                        </span>
                    </div>
                </div>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">{t('common.email')}</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="you@example.com"
                            {...register('email')}
                            disabled={isLoading}
                        />
                        {errors.email && (
                            <p className="text-sm text-destructive">{errors.email.message}</p>
                        )}
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="password">{t('common.password')}</Label>
                        <Input
                            id="password"
                            type="password"
                            placeholder="••••••"
                            {...register('password')}
                            disabled={isLoading}
                        />
                        {errors.password && (
                            <p className="text-sm text-destructive">
                                {errors.password.message}
                            </p>
                        )}
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? t('auth.signingIn') : t('auth.signIn')}
                    </Button>
                </form>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
                <p className="text-sm text-center text-muted-foreground">
                    {t('auth.dontHaveAccount')}{' '}
                    <Link href="/register" className="text-primary underline-offset-4 hover:underline">
                        {t('auth.register')}
                    </Link>
                </p>
                <div className="flex gap-4 text-xs text-muted-foreground pt-4 border-t w-full justify-center">
                    <Link href="/privacy" className="hover:text-primary transition-colors">
                        {t('legal.privacyTitle')}
                    </Link>
                    <span>•</span>
                    <Link href="/terms" className="hover:text-primary transition-colors">
                        {t('legal.termsTitle')}
                    </Link>
                </div>
            </CardFooter>
        </Card>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={<div className="text-center py-8 text-muted-foreground">Cargando...</div>}>
            <LoginFormContent />
        </Suspense>
    );
}
