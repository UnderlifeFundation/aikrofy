'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import { getDeviceTelemetryHeaders, getFriendlyDeviceName } from '@/lib/device-telemetry';
import { Navigation, X, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/use-auth-store';
import { useTranslation } from 'react-i18next';

const LOCATION_CONSENT_KEY = 'aikrofy_location_consent';
const GPS_CACHE_KEY = 'aikrofy_device_gps_cache';
const LAST_KNOWN_GPS_KEY = 'aikrofy_device_last_known_gps';

export function DeviceTelemetrySync() {
    const { t } = useTranslation();
    const { user, isAuthenticated, isAuthReady, updateUser } = useAuthStore();

    const [gpsActive, setGpsActive] = useState(false);
    const [showBanner, setShowBanner] = useState(false);
    const lastSentRef = useRef<number>(0);
    const watchIdRef = useRef<number | null>(null);

    const sendLiveGpsBeacon = useCallback(async (position: GeolocationPosition) => {
        const now = Date.now();
        // Throttle transmissions to once every 3 seconds
        if (now - lastSentRef.current < 3000) return;
        lastSentRef.current = now;

        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const acc = position.coords.accuracy;
        const spd = position.coords.speed;
        const hdg = position.coords.heading;

        const coordsString = `${lat.toFixed(6)},${lng.toFixed(6)}`;

        try {
            sessionStorage.setItem(GPS_CACHE_KEY, coordsString);
            localStorage.setItem(LAST_KNOWN_GPS_KEY, coordsString);
        } catch {}

        setGpsActive(true);
        setShowBanner(false);

        const { name: deviceName, type: deviceType } = getFriendlyDeviceName();
        const headers = getDeviceTelemetryHeaders();

        try {
            await apiClient.post('/telemetry/live-gps', {
                lat,
                lng,
                accuracy: acc,
                speed: spd,
                heading: hdg,
                device_id: headers['X-Device-Id'],
                device_name: deviceName,
                device_type: deviceType,
            });
        } catch {
            // Silently handle transient errors
        }
    }, []);

    const startContinuousWatch = useCallback(() => {
        if (typeof window === 'undefined' || !navigator.geolocation) return;
        if (watchIdRef.current !== null) return;

        try {
            watchIdRef.current = navigator.geolocation.watchPosition(
                sendLiveGpsBeacon,
                () => {},
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        } catch {
            // Geolocation watch failed
        }
    }, [sendLiveGpsBeacon]);

    const requestGps = useCallback(() => {
        if (typeof window === 'undefined' || !navigator.geolocation) return;

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                // User approved sharing location
                try {
                    localStorage.setItem(LOCATION_CONSENT_KEY, 'granted');
                } catch {}

                sendLiveGpsBeacon(pos);
                startContinuousWatch();
                setShowBanner(false);

                // Persist consent to database
                try {
                    const headers = getDeviceTelemetryHeaders();
                    await apiClient.post('/telemetry/consent', {
                        consent: 'granted',
                        device_id: headers['X-Device-Id'],
                    });
                    updateUser({ location_consent: 'granted', has_hardware_gps: true } as any);
                } catch {}
            },
            async (err) => {
                setShowBanner(false);
                if (err.code === 1) { // PERMISSION_DENIED
                    try {
                        localStorage.setItem(LOCATION_CONSENT_KEY, 'denied');
                        const headers = getDeviceTelemetryHeaders();
                        await apiClient.post('/telemetry/consent', {
                            consent: 'denied',
                            device_id: headers['X-Device-Id'],
                        });
                    } catch {}
                }
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    }, [sendLiveGpsBeacon, startContinuousWatch, updateUser]);

    const handleDismiss = async () => {
        setShowBanner(false);
        try {
            localStorage.setItem(LOCATION_CONSENT_KEY, 'dismissed');
            const headers = getDeviceTelemetryHeaders();
            await apiClient.post('/telemetry/consent', {
                consent: 'dismissed',
                device_id: headers['X-Device-Id'],
            });
        } catch {}
    };

    useEffect(() => {
        // Only run when authenticated and auth store is ready inside the dashboard
        if (!isAuthReady || !isAuthenticated || typeof window === 'undefined' || !navigator.geolocation) {
            return;
        }

        let savedConsent: string | null = null;
        try {
            savedConsent = localStorage.getItem(LOCATION_CONSENT_KEY);
        } catch {}

        const userHasPriorConsent =
            savedConsent === 'granted' ||
            user?.location_consent === 'granted' ||
            user?.has_hardware_gps === true;

        if (userHasPriorConsent) {
            // Uber-style: Already consented previously. Stream location silently in background without asking.
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    sendLiveGpsBeacon(pos);
                    startContinuousWatch();
                },
                () => {
                    // Ignored or unavailable silently
                },
                { enableHighAccuracy: true, timeout: 6000, maximumAge: 0 }
            );
            return;
        }

        // IP-based geolocation is handled automatically by the backend on connect.
        // Hardware GPS popup prompt is disabled by default until explicitly requested by user.
        setShowBanner(false);

        return () => {
            if (watchIdRef.current !== null) {
                navigator.geolocation.clearWatch(watchIdRef.current);
                watchIdRef.current = null;
            }
        };
    }, [isAuthenticated, isAuthReady, user?.location_consent, user?.has_hardware_gps, sendLiveGpsBeacon, startContinuousWatch]);

    // Don't render anything if unauthenticated or banner not needed or GPS already active
    if (!isAuthenticated || !showBanner || gpsActive) {
        return null;
    }

    return (
        <div className="fixed bottom-4 right-4 max-w-md z-50 animate-in fade-in slide-in-from-bottom-5 duration-300">
            <div className="bg-card/95 backdrop-blur-md border border-primary/20 rounded-2xl p-4 shadow-2xl flex flex-col gap-3 text-xs">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                        <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                            <Navigation className="h-4 w-4 animate-pulse" />
                        </div>
                        <div>
                            <div className="font-semibold text-foreground text-sm flex items-center gap-1.5">
                                {t('telemetry.bannerTitle', 'Compartir ubicación en tiempo real')}
                                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                            </div>
                            <div className="text-muted-foreground mt-0.5 leading-relaxed">
                                {t('telemetry.bannerDesc', 'Permite registrar la telemetría y geolocalización de tu sesión de manera continua.')}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={handleDismiss}
                        className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-lg hover:bg-muted"
                        aria-label="Cerrar"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/40">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDismiss}
                        className="h-8 text-xs px-3 rounded-lg"
                    >
                        {t('telemetry.notNow', 'Ahora no')}
                    </Button>
                    <Button
                        size="sm"
                        onClick={requestGps}
                        className="h-8 text-xs px-3.5 font-medium rounded-lg shadow-sm"
                    >
                        {t('telemetry.allowAlways', 'Permitir siempre')}
                    </Button>
                </div>
            </div>
        </div>
    );
}
