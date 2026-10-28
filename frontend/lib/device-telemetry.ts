/**
 * Physical Hardware Device Fingerprinting & GPS Telemetry Engine
 * Identifies physical hardware (laptops, phones) distinct from shared WiFi IP.
 */

// Cache in memory / localStorage
const DEVICE_STORAGE_KEY = 'aikrofy_device_telemetry_id';
const DEVICE_GPS_CACHE_KEY = 'aikrofy_device_gps_cache';

/**
 * Generate a consistent hardware fingerprint hash
 */
function generateHardwareFingerprint(): string {
    if (typeof window === 'undefined') return 'server_render_env';

    // Check existing persisted device ID
    try {
        const stored = localStorage.getItem(DEVICE_STORAGE_KEY);
        if (stored) return stored;
    } catch {
        // Storage restricted
    }

    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    let rendererInfo = 'generic_gpu';
    if (gl) {
        const debugInfo = (gl as any).getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
            rendererInfo = (gl as any).getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || 'generic_gpu';
        }
    }

    const screenData = `${window.screen.width}x${window.screen.height}x${window.screen.colorDepth}@${window.devicePixelRatio}`;
    const cpuCores = navigator.hardwareConcurrency || 4;
    const platform = navigator.platform || 'UnknownPlatform';
    const lang = navigator.language || 'es';
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

    // Simple robust hash
    const rawString = `${platform}|${rendererInfo}|${screenData}|${cpuCores}|${lang}|${timeZone}|${Date.now().toString(36)}`;
    let hash = 0;
    for (let i = 0; i < rawString.length; i++) {
        const char = rawString.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash |= 0;
    }

    const deviceId = `dev_${Math.abs(hash).toString(16)}_${Math.random().toString(36).substring(2, 9)}`;
    
    try {
        localStorage.setItem(DEVICE_STORAGE_KEY, deviceId);
    } catch {
        // Fallback
    }

    return deviceId;
}

/**
 * Resolve friendly hardware name (e.g. MacBook Pro, iPhone, Windows PC)
 */
export function getFriendlyDeviceName(): { name: string; type: 'desktop' | 'mobile' | 'tablet' } {
    if (typeof window === 'undefined') return { name: 'Servidor', type: 'desktop' };

    const ua = navigator.userAgent;
    let type: 'desktop' | 'mobile' | 'tablet' = 'desktop';

    if (/iPad|Tablet/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
        type = 'tablet';
    } else if (/Mobi|Android|iPhone|iPod/i.test(ua)) {
        type = 'mobile';
    }

    let os = 'Dispositivo';
    if (/Macintosh|Mac OS X/i.test(ua)) os = 'MacBook / Mac';
    else if (/Windows/i.test(ua)) os = 'PC Windows';
    else if (/iPhone/i.test(ua)) os = 'Apple iPhone';
    else if (/iPad/i.test(ua)) os = 'Apple iPad';
    else if (/Android/i.test(ua)) os = 'Dispositivo Android';
    else if (/Linux/i.test(ua)) os = 'Linux Workstation';

    let browser = 'Web';
    if (/Chrome/i.test(ua) && !/Edg/i.test(ua)) browser = 'Chrome';
    else if (/Safari/i.test(ua) && !/Chrome/i.test(ua)) browser = 'Safari';
    else if (/Firefox/i.test(ua)) browser = 'Firefox';
    else if (/Edg/i.test(ua)) browser = 'Edge';

    return {
        name: `${os} (${browser})`,
        type
    };
}

/**
 * Request high-precision GPS from device if granted
 */
export function requestDeviceGps(force: boolean = false): Promise<string | null> {
    return new Promise((resolve) => {
        if (typeof window === 'undefined' || !navigator.geolocation) {
            return resolve(null);
        }

        try {
            const cachedGps = sessionStorage.getItem(DEVICE_GPS_CACHE_KEY);
            if (cachedGps) {
                return resolve(cachedGps);
            }
            const consent = localStorage.getItem('aikrofy_location_consent');
            if (!force && consent !== 'granted') {
                return resolve(null);
            }
        } catch {}

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const coords = `${pos.coords.latitude.toFixed(6)},${pos.coords.longitude.toFixed(6)}`;
                try {
                    sessionStorage.setItem(DEVICE_GPS_CACHE_KEY, coords);
                    localStorage.setItem('aikrofy_device_last_known_gps', coords);
                } catch {}
                resolve(coords);
            },
            () => {
                // Denied or not available
                resolve(null);
            },
            { timeout: 3000, enableHighAccuracy: true }
        );
    });
}

/**
 * Returns telemetry headers to be attached to outgoing requests
 */
export function getDeviceTelemetryHeaders(): Record<string, string> {
    if (typeof window === 'undefined') return {};

    const deviceId = generateHardwareFingerprint();
    const { name: deviceName, type: deviceType } = getFriendlyDeviceName();

    const headers: Record<string, string> = {
        'X-Device-Id': deviceId,
        'X-Device-Name': deviceName,
        'X-Device-Type': deviceType
    };

    try {
        const cachedGps = sessionStorage.getItem(DEVICE_GPS_CACHE_KEY);
        if (cachedGps) {
            headers['X-Device-Gps'] = cachedGps;
        }
    } catch {}

    return headers;
}
