'use client';
 
import React, { useState, useEffect } from 'react';
import { PayPalScriptProvider, PayPalButtons, usePayPalScriptReducer } from "@paypal/react-paypal-js";
import { Loader2, AlertCircle, CreditCard } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useTranslation } from 'react-i18next';
import apiClient from '@/lib/api-client';
import { toast } from 'sonner';

interface PayPalCheckoutProps {
    planId?: number; // Used for subscriptions
    amount?: number;  // Used for one-time credits top-up
    mode: 'subscription' | 'credits';
    onSuccess?: (data: any) => void;
    onError?: (error: any) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Inner component: renders SUBSCRIPTION buttons
// ─────────────────────────────────────────────────────────────────────────────
const SubscriptionButtons: React.FC<{
    config: any;
    onSuccess?: (data: any) => void;
    onError?: (error: any) => void;
}> = ({ config, onSuccess, onError }) => {
    const { t } = useTranslation();
    const [{ isPending, isRejected }] = usePayPalScriptReducer();

    if (isPending) {
        return (
            <div className="flex flex-col items-center justify-center p-6 space-y-3">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground text-center">{t('subscribe.checkout.loadingPayPal')}</p>
            </div>
        );
    }

    if (isRejected) {
        return (
            <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>{t('subscribe.checkout.scriptErrorTitle')}</AlertTitle>
                <AlertDescription>
                    {t('subscribe.checkout.scriptErrorDesc')}
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <PayPalButtons
            style={{ layout: 'vertical', shape: 'rect', label: 'subscribe', height: 48 }}
            createSubscription={(data, actions) => {
                return actions.subscription.create({
                    plan_id: config.paypal_plan_id,
                    custom_id: String(config.company_id),
                });
            }}
            onApprove={async (data) => {
                try {
                    await apiClient.post('/billing/verify-subscription', {
                        subscription_id: data.subscriptionID
                    });
                    toast.success(t('subscribe.checkout.successSubscription'));
                } catch (err) {
                    console.error("Direct subscription verification failed:", err);
                    toast.success(t('subscribe.checkout.successSubscription'));
                }
                if (onSuccess) onSuccess(data);
                window.location.href = '/subscribe';
            }}
            onError={(err) => {
                console.error("PayPal Subscription Error:", err);
                toast.error(t('subscribe.checkout.errorSubscription'));
                if (onError) onError(err);
            }}
            onCancel={() => {
                toast.info(t('subscribe.checkout.subscriptionCancelled'));
            }}
        />
    );
};

// ─────────────────────────────────────────────────────────────────────────────
// Inner component: renders ONE-TIME ORDER buttons (credit blocks)
// ─────────────────────────────────────────────────────────────────────────────
const OrderButtons: React.FC<{
    config: any;
    onSuccess?: (data: any) => void;
    onError?: (error: any) => void;
}> = ({ config, onSuccess, onError }) => {
    const { t } = useTranslation();
    const [{ isPending, isRejected }] = usePayPalScriptReducer();

    if (isPending) {
        return (
            <div className="flex flex-col items-center justify-center p-6 space-y-3">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground text-center">{t('subscribe.checkout.loadingPayPal')}</p>
            </div>
        );
    }

    if (isRejected) {
        return (
            <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>{t('subscribe.checkout.scriptErrorTitle')}</AlertTitle>
                <AlertDescription>
                    {t('subscribe.checkout.scriptErrorDesc')}
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <PayPalButtons
            style={{ layout: 'vertical', shape: 'rect', label: 'pay', height: 48 }}
            createOrder={() => {
                return Promise.resolve(config.order_id);
            }}
            onApprove={async (data) => {
                try {
                    const { data: captureData } = await apiClient.post('/billing/capture-order', {
                        order_id: data.orderID,
                    });
                    toast.success(t('subscribe.checkout.successOrder'));
                    if (onSuccess) onSuccess(captureData);
                } catch {
                    toast.error(t('subscribe.checkout.errorCapture'));
                }
            }}
            onError={(err) => {
                console.error("PayPal Order Error:", err);
                toast.error(t('subscribe.checkout.errorOrder'));
                if (onError) onError(err);
            }}
            onCancel={() => {
                toast.info(t('subscribe.checkout.cancelled'));
            }}
        />
    );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Exported Component
// ─────────────────────────────────────────────────────────────────────────────
export const PayPalCheckout: React.FC<PayPalCheckoutProps> = ({
    planId,
    amount,
    mode,
    onSuccess,
    onError,
}) => {
    const { t, i18n } = useTranslation();
    const currentLang = i18n.language || 'es';
    const [config, setConfig] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const getPayPalLocale = (lang: string) => {
        if (lang.startsWith('es')) return 'es_ES';
        if (lang.startsWith('pt')) return 'pt_BR';
        return 'en_US';
    };

    const fetchConfig = async () => {
        setLoading(true);
        setError(null);
        try {
            if (mode === 'subscription') {
                const { data } = await apiClient.post('/billing/subscribe', { plan_id: planId });
                setConfig(data);
            } else {
                const { data } = await apiClient.post('/billing/top-up', { amount });
                setConfig(data);
            }
        } catch (err: any) {
            const msg = err.response?.data?.error || t('subscribe.subscriptionError');
            setError(msg);
            toast.error(msg);
            if (onError) onError(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (mode === 'subscription' && planId) {
            fetchConfig();
        } else if (mode === 'credits' && amount) {
            fetchConfig();
        }
    }, [planId, amount, mode]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground text-center">{t('subscribe.checkout.preparingCheckout')}</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-3">
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>{t('subscribe.checkout.checkoutErrorTitle')}</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
                <Button variant="outline" size="sm" onClick={fetchConfig} className="w-full">
                    {t('subscribe.checkout.tryAgain')}
                </Button>
            </div>
        );
    }

    if (!config || !config.client_id) {
        return (
            <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>{t('subscribe.checkout.configErrorTitle')}</AlertTitle>
                <AlertDescription>
                    {t('subscribe.checkout.configErrorDesc')}
                </AlertDescription>
            </Alert>
        );
    }

    const isSubscription = config.type === 'subscription';

    const sdkOptions = isSubscription
        ? {
              clientId: config.client_id,
              intent: 'subscription' as const,
              vault: true,
              components: 'buttons',
              locale: getPayPalLocale(currentLang),
          }
        : {
              clientId: config.client_id,
              intent: 'capture' as const,
              vault: false,
              components: 'buttons',
              locale: getPayPalLocale(currentLang),
          };

    return (
        <div className="space-y-4 w-full text-foreground">
            <div className="flex items-center gap-2 text-sm text-muted-foreground justify-center">
                <CreditCard className="h-4 w-4 shrink-0" />
                <span>
                    {isSubscription
                        ? t('subscribe.checkout.recurringPayment')
                        : t('subscribe.checkout.oneTimePayment')}
                </span>
            </div>

            <div className="w-full min-h-[150px] flex flex-col justify-center [&_iframe]:!bg-transparent">
                <PayPalScriptProvider options={sdkOptions}>
                    {isSubscription ? (
                        <SubscriptionButtons
                            config={config}
                            onSuccess={onSuccess}
                            onError={onError}
                        />
                    ) : (
                        <OrderButtons
                            config={config}
                            onSuccess={onSuccess}
                            onError={onError}
                        />
                    )}
                </PayPalScriptProvider>
            </div>

            <p className="text-[11px] text-center text-muted-foreground leading-relaxed px-2">
                {isSubscription 
                    ? t('subscribe.checkout.recurringNote')
                    : t('subscribe.checkout.oneTimeNote')}
            </p>
        </div>
    );
};
