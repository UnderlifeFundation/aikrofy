'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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

const registerSchema = z.object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Enter a valid email'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
    company_name: z.string().min(2, 'Business name is required'),
    business_category: z.string().optional(),
    country: z.string().optional(),
    language: z.string().optional(),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
    const router = useRouter();
    const { t, i18n } = useTranslation();
    const login = useAuthStore((s) => s.login);
    const setLanguage = useAuthStore((s) => s.setLanguage);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        // If beta mode is active, send users straight to beta registration
        apiClient.get('/beta/status')
            .then((res) => {
                if (res.data?.data?.beta_mode) {
                    router.replace('/beta-register');
                }
            })
            .catch(() => {});
    }, [router]);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<RegisterFormValues>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            language: 'es',
            business_category: 'emprendimiento',
        },
    });

    const onSubmit = async (values: RegisterFormValues) => {
        setIsLoading(true);
        try {
            const { data } = await apiClient.post<AuthResponse>('/auth/register', values);
            const res = data.data;

            login(res.user, res.access_token, res.refresh_token);
            setLanguage(values.language || 'en');
            // Also sync i18n UI language with registration preference
            i18n.changeLanguage(values.language || 'en');
            localStorage.setItem('i18nextLng', values.language || 'en');
            toast.success(t('auth.accountCreated'));
            // Small yield to guarantee cookie propagation before navigating
            await new Promise((resolve) => setTimeout(resolve, 50));
            router.push('/dashboard');
        } catch (err: unknown) {
            const error = err as { response?: { data?: { error?: string; is_waitlist?: boolean; message?: string } } };
            if (error.response?.data?.is_waitlist) {
                toast.info(error.response.data.message || 'Beta activa. Redirigiendo al formulario de registro a la lista de espera...');
                router.push('/beta-register');
                return;
            }
            toast.error(error.response?.data?.error || t('auth.registrationFailed'));
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
            setLanguage('en');
            toast.success(t('auth.googleAuthSuccess'));

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
                toast.info(error.response.data.message || 'Beta activa. Redirigiendo al formulario de registro a la lista de espera...');
                router.push('/beta-register');
                return;
            }
            toast.error(error.response?.data?.error || t('auth.googleSignupFailed'));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card className="border-border/50 shadow-xl">
            <CardHeader className="text-center">
                <CardTitle className="text-2xl font-bold tracking-tight">
                    {t('auth.createAccount')}
                </CardTitle>
                <CardDescription>
                    {t('auth.createAccountDescription')}
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="mb-4 flex justify-center">
                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={() => toast.error(t('auth.googleLoginFailed'))}
                        theme="outline"
                        width="100%"
                        text="signup_with"
                    />
                </div>
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
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">{t('auth.yourName')}</Label>
                            <Input
                                id="name"
                                placeholder="John Doe"
                                {...register('name')}
                                disabled={isLoading}
                            />
                            {errors.name && (
                                <p className="text-sm text-destructive">{errors.name.message}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="company_name">{t('auth.businessName')}</Label>
                            <Input
                                id="company_name"
                                placeholder="My Wellness Co."
                                {...register('company_name')}
                                disabled={isLoading}
                            />
                            {errors.company_name && (
                                <p className="text-sm text-destructive">
                                    {errors.company_name.message}
                                </p>
                            )}
                        </div>
                    </div>
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
                    <div className="space-y-2">
                        <Label htmlFor="business_category">Tipo de Organización / Negocio</Label>
                        <select
                            id="business_category"
                            {...register('business_category')}
                            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            disabled={isLoading}
                        >
                            <option value="emprendimiento">Emprendimiento / Profesional Independiente (Subsidio Fundación Underlife)</option>
                            <option value="micro_negocio">Micro Negocio / Local Comercial (Subsidio Fundación Underlife)</option>
                            <option value="pyme">Pequeña y Mediana Empresa (PyME)</option>
                            <option value="community">Proyecto Comunitario / ONG / Estudiantil (Open-Core)</option>
                            <option value="enterprise">Corporativo / Enterprise (WEBLIFETECH SLA)</option>
                        </select>
                        <p className="text-xs text-muted-foreground">
                            Los negocios en fase de emprendimiento y PyME reciben créditos de cortesía de bienvenida otorgados por Fundación Underlife.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="language">{t('auth.preferredLanguage')}</Label>
                        <select
                            id="language"
                            {...register('language')}
                            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            disabled={isLoading}
                        >
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="pt">Português</option>
                        </select>
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? t('auth.creatingAccount') : t('auth.createAccount')}
                    </Button>
                </form>
            </CardContent>
            <CardFooter className="flex justify-center">
                <p className="text-sm text-muted-foreground">
                    {t('auth.alreadyHaveAccount')}{' '}
                    <Link href="/login" className="text-primary underline-offset-4 hover:underline">
                        {t('auth.signInLink')}
                    </Link>
                </p>
            </CardFooter>
        </Card>
    );
}
