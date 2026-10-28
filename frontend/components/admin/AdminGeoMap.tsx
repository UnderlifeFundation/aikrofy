'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Globe,
  Radio,
  Building2,
  Users,
  ShieldAlert,
  ShieldCheck,
  Search,
  RefreshCw,
  Clock,
  Coins,
  Target,
  Sparkles,
  MapPin,
  ExternalLink,
  ChevronRight,
  Filter,
  Eye,
  Activity,
  Ban,
  CheckCircle2,
  Wifi,
  Server,
  Laptop,
  Smartphone,
  Network
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api-client';
import { toast } from 'sonner';

export interface GeoPoint {
  id: string;
  entity_type: 'company' | 'beta_lead' | 'user';
  name: string;
  user_name: string;
  email: string;
  phone: string;
  industry: string;
  role_in_company?: string;
  employee_count?: string;
  products_services?: string;
  ai_expectations?: string;
  ai_experience?: string;
  is_demo?: boolean;
  demo_expires_at?: string | null;
  ip_address: string;
  isp?: string;
  is_ip_blocked?: boolean;
  device_name?: string;
  device_type?: 'desktop' | 'mobile' | 'tablet';
  has_hardware_gps?: boolean;
  gps_accuracy?: number;
  gps_speed?: number;
  gps_heading?: number;
  network_cluster_count?: number;
  devices?: Array<{
    device_id: string;
    device_name: string;
    device_type: string;
    network_ip: string;
    has_hardware_gps: boolean;
    gps_lat?: number;
    gps_lng?: number;
    last_seen_at?: string;
  }>;
  lat: number;
  lng: number;
  city: string;
  country: string;
  country_code: string;
  is_live_ip?: boolean;
  is_online: boolean;
  plan: string;
  tier: string;
  credit_balance: number;
  conversations_count: number;
  usage_time_hours: number;
  lead_score: number;
  pipeline_stage: string;
  last_active: string;
  created_at: string;
  security_alert: boolean;
  security_reason?: string | null;
  logo_url?: string | null;
}

export interface BlockedIpRecord {
  id: number;
  ip_address: string;
  reason: string;
  blocked_at: string;
  is_active: boolean;
}

export interface GeoRadarResponse {
  success: boolean;
  timestamp: string;
  summary: {
    total_points: number;
    total_companies: number;
    total_beta_leads: number;
    live_online_now: number;
    total_usage_hours: number;
    anomalies_count: number;
    blocked_ips_count: number;
    countries_count: number;
    country_distribution: Record<string, number>;
    stage_distribution: Record<string, number>;
  };
  points: GeoPoint[];
  blocked_ips?: BlockedIpRecord[];
}

interface AdminGeoMapProps {
  data: GeoRadarResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export default function AdminGeoMap({ data, isLoading, onRefresh }: AdminGeoMapProps) {
  const { t } = useTranslation();
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const leafletMapRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);

  const [selectedPoint, setSelectedPoint] = useState<GeoPoint | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'companies' | 'beta' | 'online' | 'alerts' | 'blocked'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [mapTheme, setMapTheme] = useState<'dark' | 'standard'>('dark');
  const [isBlockingAction, setIsBlockingAction] = useState(false);

  // Filtered list of points based on search and tab filter
  const filteredPoints = useMemo(() => {
    if (!data?.points) return [];
    return data.points.filter((pt) => {
      // Type filter
      if (filterType === 'companies' && pt.entity_type !== 'company') return false;
      if (filterType === 'beta' && pt.entity_type !== 'beta_lead') return false;
      if (filterType === 'online' && !pt.is_online) return false;
      if (filterType === 'alerts' && !pt.security_alert) return false;
      if (filterType === 'blocked' && !pt.is_ip_blocked) return false;

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          pt.name.toLowerCase().includes(q) ||
          pt.user_name.toLowerCase().includes(q) ||
          pt.email.toLowerCase().includes(q) ||
          pt.ip_address.toLowerCase().includes(q) ||
          pt.city.toLowerCase().includes(q) ||
          pt.country.toLowerCase().includes(q) ||
          pt.plan.toLowerCase().includes(q) ||
          pt.industry.toLowerCase().includes(q);
        if (!matches) return false;
      }

      return true;
    });
  }, [data?.points, filterType, searchQuery]);

  // Handle IP Blocking / Unblocking
  const handleToggleBlockIp = async (ip: string, isCurrentlyBlocked: boolean) => {
    if (!ip || ip.includes('No registrada') || ip === '127.0.0.1') {
      toast.error('No se puede bloquear una dirección local o no registrada.');
      return;
    }

    try {
      setIsBlockingAction(true);
      if (isCurrentlyBlocked) {
        await apiClient.post('/admin/ip-unblock', { ip });
        toast.success(`IP ${ip} desbloqueada exitosamente.`);
      } else {
        await apiClient.post('/admin/ip-block', {
          ip,
          reason: `Bloqueo manual desde Radar Geo-Analítico para ${selectedPoint?.name || 'usuario'}`
        });
        toast.warning(`IP ${ip} ha sido bloqueada y añadida a la lista negra.`);
      }
      onRefresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Error al procesar la acción de bloqueo');
    } finally {
      setIsBlockingAction(false);
    }
  };

  // Initialize and update Leaflet Map
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let isMounted = true;

    async function initMap() {
      try {
        if (!document.getElementById('leaflet-css')) {
          const link = document.createElement('link');
          link.id = 'leaflet-css';
          link.rel = 'stylesheet';
          link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
          document.head.appendChild(link);
        }
        const L = (await import('leaflet')).default;

        if (!mapContainerRef.current) return;

      // Initialize map instance if not existing
      if (!leafletMapRef.current) {
        const map = L.map(mapContainerRef.current, {
          center: [-0.1807, -78.4678], // Latam default
          zoom: 4,
          minZoom: 2,
          maxZoom: 18,
          zoomControl: false
        });

        L.control.zoom({ position: 'topright' }).addTo(map);

        const tileUrl =
          mapTheme === 'dark'
            ? 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
            : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

        L.tileLayer(tileUrl, {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
          subdomains: 'abcd',
          maxZoom: 19
        }).addTo(map);

        leafletMapRef.current = map;
        markersLayerRef.current = L.layerGroup().addTo(map);
      }

      // Update markers on data change
      if (markersLayerRef.current && leafletMapRef.current) {
        markersLayerRef.current.clearLayers();

        filteredPoints.forEach((point) => {
          const isOnline = point.is_online;
          const isBlocked = point.is_ip_blocked;
          const isAlert = point.security_alert || isBlocked;
          const isBeta = point.entity_type === 'beta_lead';

          let pinColor = '#3b82f6'; // Blue (Client)
          let glowClass = 'shadow-blue-500/50';
          if (isBlocked) {
            pinColor = '#991b1b'; // Dark Red (Blacklisted)
            glowClass = 'shadow-red-800/80 animate-pulse';
          } else if (isAlert) {
            pinColor = '#ef4444'; // Red (Alert)
            glowClass = 'shadow-red-500/60 animate-pulse';
          } else if (isOnline) {
            pinColor = '#10b981'; // Green (Online Live)
            glowClass = 'shadow-emerald-500/60 animate-bounce';
          } else if (isBeta) {
            pinColor = '#f59e0b'; // Amber (Beta)
            glowClass = 'shadow-amber-500/50';
          }

          const customIcon = L.divIcon({
            className: 'custom-geo-pin',
            html: `
              <div class="relative flex items-center justify-center cursor-pointer group">
                ${
                  isOnline || isAlert
                    ? `<div class="absolute -inset-2 rounded-full opacity-75 animate-ping" style="background-color: ${pinColor}"></div>`
                    : ''
                }
                <div class="relative w-8 h-8 rounded-full flex items-center justify-center text-white font-bold shadow-lg ${glowClass} border-2 border-white dark:border-zinc-900 transition-transform duration-200 transform group-hover:scale-125" style="background-color: ${pinColor}">
                  <span class="text-[10px] uppercase">${isBlocked ? '🚫' : point.entity_type === 'company' ? '🏢' : '🧪'}</span>
                </div>
              </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -18]
          });

          // Uber-grade Accuracy Radius Circle
          if (point.has_hardware_gps || (point.gps_accuracy && point.gps_accuracy < 100)) {
            L.circle([point.lat, point.lng], {
              radius: Math.max(8, point.gps_accuracy || 15),
              color: '#3b82f6',
              fillColor: '#60a5fa',
              fillOpacity: 0.18,
              weight: 1.5
            }).addTo(markersLayerRef.current);
          }

          const marker = L.marker([point.lat, point.lng], { icon: customIcon });

          const popupContent = `
            <div class="p-3 max-w-[310px] font-sans text-zinc-900 dark:text-zinc-100">
              <div class="flex items-center justify-between gap-2 border-b border-zinc-200 dark:border-zinc-700 pb-2 mb-2">
                <div class="font-bold text-sm truncate text-indigo-600 dark:text-indigo-400">${point.name}</div>
                <span class="text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                  isBlocked
                    ? 'bg-red-900 text-white'
                    : isOnline
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                    : 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'
                }">${isBlocked ? '🚫 Bloqueada' : isOnline ? '🟢 En Vivo' : point.plan}</span>
              </div>
              
              <div class="space-y-2 text-xs">
                <!-- Seccion 1: Lead & Contacto -->
                <div class="bg-zinc-50 dark:bg-zinc-800/50 p-2 rounded-lg space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-medium text-xs truncate">👤 ${point.user_name}</span>
                    <span class="text-[10px] text-amber-600 dark:text-amber-400 font-bold">${point.pipeline_stage}</span>
                  </div>
                  <div class="text-[10px] text-zinc-500 truncate">${point.role_in_company || point.industry} • ${point.email}</div>
                </div>

                <!-- Seccion 2: Ubicacion & Hardware -->
                <div class="space-y-1 bg-indigo-50/50 dark:bg-indigo-950/30 p-2 rounded-lg text-[11px]">
                  <div class="flex items-center justify-between font-mono">
                    <span class="flex items-center gap-1">🌐 ${point.ip_address}</span>
                    <span class="text-[10px] font-sans text-zinc-500">📍 ${point.city}, ${point.country_code}</span>
                  </div>
                  <div class="flex items-center justify-between text-zinc-600 dark:text-zinc-300">
                    <span>💻 ${point.device_name || 'Equipo Principal'}</span>
                    <span class="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">${point.has_hardware_gps ? '🎯 GPS ±5m' : '📶 WiFi IP'}</span>
                  </div>
                </div>

                <!-- Lead Score & Uso -->
                <div class="grid grid-cols-2 gap-2 pt-1 border-t border-zinc-100 dark:border-zinc-800">
                  <div class="bg-zinc-100/70 dark:bg-zinc-800/80 p-1.5 rounded text-center">
                    <div class="text-[9px] text-zinc-400 uppercase font-bold">Lead Score</div>
                    <div class="font-bold text-xs text-amber-500">${point.lead_score}/100</div>
                  </div>
                  <div class="bg-zinc-100/70 dark:bg-zinc-800/80 p-1.5 rounded text-center">
                    <div class="text-[9px] text-zinc-400 uppercase font-bold">Uso Total</div>
                    <div class="font-bold text-xs">${point.usage_time_hours}h</div>
                  </div>
                </div>

                ${
                  point.security_alert
                    ? `<div class="text-[10px] text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50 p-1 rounded font-semibold">⚠️ ${point.security_reason || 'Anomalía de uso'}</div>`
                    : ''
                }
              </div>
            </div>
          `;

          marker.bindPopup(popupContent, {
            className: 'custom-leaflet-popup shadow-2xl rounded-xl border border-zinc-200 dark:border-zinc-800',
            closeButton: false
          });

          marker.on('mouseover', function () {
            marker.openPopup();
          });
          marker.on('click', () => {
            setSelectedPoint(point);
          });

          markersLayerRef.current.addLayer(marker);
        });
      }
    } catch (err) {
      console.warn('Leaflet initialization skipped or failed:', err);
    }
  }

    initMap();

    return () => {
      isMounted = false;
    };
  }, [filteredPoints, mapTheme]);

  return (
    <div className="space-y-6">
      {/* ── HEADER & ACTIONS ──────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight flex items-center gap-2">
              <Globe className="h-6 w-6 text-indigo-500 animate-pulse" />
              Radar Geo-Analítico
            </h1>
            <Badge variant="outline" className="border-indigo-500/30 text-indigo-500 bg-indigo-500/10 font-bold uppercase tracking-wider text-[10px]">
              Geolocalización & Telemetría
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Geolocalización por IP en tiempo real, rastreo GPS, lead scoring y bloqueo perimetral de accesos no autorizados.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setMapTheme((t) => (t === 'dark' ? 'standard' : 'dark'))}
            className="text-xs"
          >
            {mapTheme === 'dark' ? '☀️ Mapa Claro' : '🌙 Mapa Satelital/Radar'}
          </Button>
          <Button
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-500/20"
          >
            <RefreshCw className={cn('h-4 w-4 mr-1.5', isLoading && 'animate-spin')} />
            {isLoading ? 'Actualizando...' : 'Actualizar Radar'}
          </Button>
        </div>
      </div>

      {/* ── KPI METRICS CARDS ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center shrink-0">
              <Globe className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">Puntos Totales</div>
              <div className="text-xl font-bold">{data?.summary.total_points ?? 0}</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
              <Radio className="h-5 w-5 animate-ping" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">En Vivo (Live)</div>
              <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                {data?.summary.live_online_now ?? 0}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">Empresas</div>
              <div className="text-xl font-bold">{data?.summary.total_companies ?? 0}</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">Beta Leads</div>
              <div className="text-xl font-bold">{data?.summary.total_beta_leads ?? 0}</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">Horas de Uso</div>
              <div className="text-xl font-bold">{data?.summary.total_usage_hours ?? 0}h</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-md border-border/60 shadow-xs">
          <CardContent className="p-3.5 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-red-500/10 text-red-500 flex items-center justify-center shrink-0">
              <Ban className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-medium">IPs Bloqueadas</div>
              <div className="text-xl font-bold text-red-600 dark:text-red-400">
                {data?.summary.blocked_ips_count ?? 0}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── FILTER TABS & SEARCH BAR ──────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-muted/40 p-2.5 rounded-xl border border-border/50">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
          <Button
            variant={filterType === 'all' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('all')}
            className="text-xs h-8"
          >
            Todos ({data?.summary.total_points ?? 0})
          </Button>
          <Button
            variant={filterType === 'companies' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('companies')}
            className="text-xs h-8"
          >
            🏢 Empresas ({data?.summary.total_companies ?? 0})
          </Button>
          <Button
            variant={filterType === 'beta' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('beta')}
            className="text-xs h-8"
          >
            🧪 Beta ({data?.summary.total_beta_leads ?? 0})
          </Button>
          <Button
            variant={filterType === 'online' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('online')}
            className="text-xs h-8 text-emerald-600 dark:text-emerald-400 font-bold"
          >
            🟢 En Vivo ({data?.summary.live_online_now ?? 0})
          </Button>
          <Button
            variant={filterType === 'alerts' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('alerts')}
            className="text-xs h-8 text-amber-600 dark:text-amber-400 font-bold"
          >
            ⚠️ Alertas ({data?.summary.anomalies_count ?? 0})
          </Button>
          <Button
            variant={filterType === 'blocked' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilterType('blocked')}
            className="text-xs h-8 text-red-600 dark:text-red-400 font-bold"
          >
            🚫 Blacklist ({data?.summary.blocked_ips_count ?? 0})
          </Button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Buscar por IP, nombre, email, ciudad..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-xs h-8 bg-background"
          />
        </div>
      </div>

      {/* ── MAP CONTAINER & DETAIL DRAWER ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main Map Box */}
        <div className="lg:col-span-2 relative rounded-2xl overflow-hidden border border-border/80 shadow-2xl h-[600px] bg-zinc-950">
          <div ref={mapContainerRef} className="w-full h-full z-0" />

          {/* Floating Map Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-background/90 backdrop-blur-md p-3 rounded-xl border border-border shadow-xl text-xs space-y-1.5">
            <div className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
              Telemetría Geoespacial
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-ping" />
              <span>Conexión IP En Vivo</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-blue-500" />
              <span>Cliente Activo / Tenant</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span>Beta Lead / Solicitud</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-red-600 animate-pulse" />
              <span>IP Bloqueada / Alerta</span>
            </div>
          </div>
        </div>

        {/* Detail Inspection Card (Selected Marker or Top Leads List) */}
        <div className="space-y-4">
          {selectedPoint ? (
            <Card className="border-indigo-500/40 shadow-xl bg-card">
              <CardHeader className="p-4 pb-2 border-b">
                <div className="flex items-start justify-between">
                  <div>
                    <Badge
                      className={cn(
                        'text-[10px] font-bold mb-1.5',
                        selectedPoint.is_ip_blocked
                          ? 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/40'
                          : selectedPoint.is_online
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                          : 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/30'
                      )}
                    >
                      {selectedPoint.is_ip_blocked
                        ? '🚫 IP En Lista Negra'
                        : selectedPoint.entity_type === 'company'
                        ? '🏢 Tenant Empresa'
                        : '🧪 Beta Lead'}
                    </Badge>
                    <CardTitle className="text-base font-bold">{selectedPoint.name}</CardTitle>
                    <CardDescription className="text-xs">{selectedPoint.industry}</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedPoint(null)} className="h-7 text-xs px-2">
                    ✕
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3 text-xs">
                <Tabs defaultValue="location" className="w-full">
                  <TabsList className="grid grid-cols-2 w-full mb-3 h-9 bg-muted/60 p-1">
                    <TabsTrigger value="location" className="text-xs font-semibold flex items-center justify-center gap-1.5 data-[state=active]:bg-background data-[state=active]:text-indigo-600 dark:data-[state=active]:text-indigo-400">
                      <MapPin className="h-3.5 w-3.5" />
                      Ubicación & Red
                    </TabsTrigger>
                    <TabsTrigger value="lead" className="text-xs font-semibold flex items-center justify-center gap-1.5 data-[state=active]:bg-background data-[state=active]:text-amber-600 dark:data-[state=active]:text-amber-400">
                      <Users className="h-3.5 w-3.5" />
                      Datos Lead & Historial
                    </TabsTrigger>
                  </TabsList>

                  {/* ── PESTAÑA 1: DATOS DE UBICACIÓN & TELEMETRÍA ──────────── */}
                  <TabsContent value="location" className="space-y-3 mt-0 focus-visible:outline-none">
                    {/* Dual-Layer Telemetry: Hardware Device & WiFi Network */}
                    <div className="space-y-2 bg-indigo-500/5 border border-indigo-500/20 p-3 rounded-xl">
                      <div className="flex items-center justify-between text-[11px] font-bold text-indigo-600 dark:text-indigo-400">
                        <span className="flex items-center gap-1.5">
                          <Laptop className="h-3.5 w-3.5" /> Dispositivo Físico & Red
                        </span>
                        <Badge variant="outline" className="text-[9px] border-emerald-500/40 text-emerald-600 bg-emerald-500/10 font-mono">
                          {selectedPoint.has_hardware_gps ? 'GPS SATELITAL' : selectedPoint.is_live_ip ? 'WIFI GPS LIVE' : 'GEO IP'}
                        </Badge>
                      </div>

                      {/* Physical Hardware info */}
                      <div className="bg-background/80 p-2 rounded-lg border border-border/50 space-y-1">
                        <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider flex items-center gap-1">
                          {selectedPoint.device_type === 'mobile' ? <Smartphone className="h-3 w-3" /> : <Laptop className="h-3 w-3" />}
                          Equipo Físico Registrado
                        </div>
                        <div className="font-semibold text-xs flex items-center justify-between">
                          <span>{selectedPoint.device_name || 'Dispositivo Principal de Trabajo'}</span>
                          <span className="text-[10px] text-indigo-500 uppercase font-mono">{selectedPoint.device_type || 'desktop'}</span>
                        </div>
                      </div>

                      {/* WiFi Network & ISP info */}
                      <div className="space-y-1 pt-1">
                        <div className="font-mono text-xs font-semibold flex items-center justify-between">
                          <span className="flex items-center gap-1"><Wifi className="h-3 w-3 text-muted-foreground" /> WiFi: {selectedPoint.ip_address}</span>
                          <span className="text-[10px] text-muted-foreground font-sans truncate max-w-[120px]">
                            {selectedPoint.isp}
                          </span>
                        </div>
                        {selectedPoint.network_cluster_count && selectedPoint.network_cluster_count > 1 && (
                          <div className="text-[10px] text-indigo-600 dark:text-indigo-400 font-semibold flex items-center gap-1 bg-indigo-500/10 px-2 py-1 rounded">
                            <Network className="h-3 w-3" />
                            <span>Cluster WiFi: {selectedPoint.network_cluster_count} dispositivos vinculados en esta sede</span>
                          </div>
                        )}
                        {selectedPoint.has_hardware_gps && (
                          <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center justify-between bg-emerald-500/10 px-2 py-1 rounded">
                            <span>🎯 Precisión Satelital: ±{selectedPoint.gps_accuracy || 5} metros</span>
                            {selectedPoint.gps_speed ? <span>🚗 {(selectedPoint.gps_speed * 3.6).toFixed(1)} km/h</span> : <span>📍 En Punto Fijo</span>}
                          </div>
                        )}
                        <div className="text-[11px] text-muted-foreground flex items-center justify-between pt-1 border-t border-border/40">
                          <span>📍 {selectedPoint.city}, {selectedPoint.country}</span>
                          <span className="font-mono text-[10px]">
                            {selectedPoint.lat.toFixed(6)}, {selectedPoint.lng.toFixed(6)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Geolocation Demographics Card */}
                    <div className="bg-muted/30 p-2.5 rounded-lg space-y-1.5 border border-border/40">
                      <div className="font-semibold text-[10px] text-muted-foreground uppercase flex items-center gap-1">
                        <Globe className="h-3 w-3 text-indigo-500" /> Datos Demográficos de Ubicación
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Ciudad / Cantón:</span>
                          <span className="font-medium">{selectedPoint.city}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block text-[10px]">País / Código:</span>
                          <span className="font-medium">{selectedPoint.country} ({selectedPoint.country_code})</span>
                        </div>
                      </div>
                    </div>

                    {/* Security Action: Block / Unblock IP */}
                    <div className="pt-1 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Estado Perimetral:</span>
                        <Badge variant={selectedPoint.is_ip_blocked ? 'destructive' : 'secondary'} className="text-[10px]">
                          {selectedPoint.is_ip_blocked ? '🚫 IP Bloqueada' : '🛡️ Acceso Autorizado'}
                        </Badge>
                      </div>

                      {selectedPoint.ip_address && !selectedPoint.ip_address.includes('No registrada') && (
                        <Button
                          variant={selectedPoint.is_ip_blocked ? 'default' : 'destructive'}
                          size="sm"
                          disabled={isBlockingAction}
                          onClick={() => handleToggleBlockIp(selectedPoint.ip_address, Boolean(selectedPoint.is_ip_blocked))}
                          className="w-full text-xs font-bold flex items-center justify-center gap-1.5 h-8"
                        >
                          {selectedPoint.is_ip_blocked ? (
                            <>
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                              Desbloquear IP ({selectedPoint.ip_address})
                            </>
                          ) : (
                            <>
                              <Ban className="h-3.5 w-3.5" />
                              Bloquear IP ({selectedPoint.ip_address})
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </TabsContent>

                  {/* ── PESTAÑA 2: DATOS DE LEAD & HISTORIAL ────────────────── */}
                  <TabsContent value="lead" className="space-y-3 mt-0 focus-visible:outline-none">
                    {/* Pipeline Stage & Lifecycle Banner */}
                    <div className="bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl flex items-center justify-between">
                      <div>
                        <div className="text-[10px] text-amber-700 dark:text-amber-300 font-bold uppercase tracking-wider">Etapa del Embudo / Demo</div>
                        <div className="font-extrabold text-xs text-foreground mt-0.5">{selectedPoint.pipeline_stage}</div>
                      </div>
                      <Badge className={cn(
                        'text-[10px] font-bold',
                        selectedPoint.pipeline_stage.includes('Activo') ? 'bg-emerald-600 text-white' :
                        selectedPoint.pipeline_stage.includes('Espera') ? 'bg-amber-600 text-white' :
                        'bg-indigo-600 text-white'
                      )}>
                        {selectedPoint.plan}
                      </Badge>
                    </div>

                    {/* Contact Profile */}
                    <div className="bg-muted/30 p-2.5 rounded-lg space-y-1 border border-border/40">
                      <div className="font-semibold text-[10px] text-muted-foreground uppercase">Información de Contacto & Cargo</div>
                      <div className="font-bold text-sm text-foreground">{selectedPoint.user_name}</div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium">{selectedPoint.role_in_company || 'Decision Maker'}</div>
                      <div className="text-muted-foreground text-xs">{selectedPoint.email}</div>
                      <div className="text-muted-foreground text-xs">Tel: {selectedPoint.phone}</div>
                    </div>

                    {/* Company & Demographics */}
                    <div className="bg-background/80 p-2.5 rounded-lg border border-border/60 space-y-1.5">
                      <div className="font-semibold text-[10px] text-muted-foreground uppercase flex items-center gap-1">
                        <Building2 className="h-3 w-3 text-indigo-500" /> Perfil de la Organización
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Industria:</span>
                          <span className="font-medium">{selectedPoint.industry}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Equipo / Colaboradores:</span>
                          <span className="font-medium">{selectedPoint.employee_count || '10-50'}</span>
                        </div>
                      </div>
                      {selectedPoint.products_services && (
                        <div className="text-[11px] text-muted-foreground pt-1 border-t border-border/30">
                          <span className="font-semibold text-foreground">Productos/Servicios:</span> {selectedPoint.products_services}
                        </div>
                      )}
                      {selectedPoint.ai_expectations && (
                        <div className="text-[11px] text-muted-foreground">
                          <span className="font-semibold text-foreground">Expectativa IA:</span> {selectedPoint.ai_expectations}
                        </div>
                      )}
                    </div>

                    {/* Lead Score & Intent */}
                    <div className="space-y-1.5 bg-amber-500/5 p-2.5 rounded-lg border border-amber-500/20">
                      <div className="flex items-center justify-between text-xs font-semibold">
                        <span className="flex items-center gap-1 text-amber-500">
                          <Target className="h-3.5 w-3.5" /> Calificación de Lead (Score)
                        </span>
                        <span className="font-bold text-amber-600 dark:text-amber-400">{selectedPoint.lead_score} / 100</span>
                      </div>
                      <Progress value={selectedPoint.lead_score} className="h-2 bg-amber-500/20" />
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-0.5">
                        <span>Intención de Compra</span>
                        <span className="font-bold text-foreground">
                          {selectedPoint.lead_score >= 80 ? '🔥 Caliente (Alta Conversión)' : selectedPoint.lead_score >= 50 ? '⚡ Templado (En Interacción)' : '❄️ Frío / Exploratorio'}
                        </span>
                      </div>
                    </div>

                    {/* Usage & Telemetry Stats Grid */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 bg-muted/40 rounded-lg border border-border/50">
                        <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> Horas de Uso
                        </div>
                        <div className="font-bold text-sm mt-0.5">{selectedPoint.usage_time_hours} hrs</div>
                      </div>

                      <div className="p-2 bg-muted/40 rounded-lg border border-border/50">
                        <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Coins className="h-3 w-3" /> Saldo Créditos
                        </div>
                        <div className="font-bold text-sm mt-0.5">{selectedPoint.credit_balance}</div>
                      </div>
                    </div>

                    <div className="text-[10px] text-muted-foreground flex items-center justify-between px-1 pt-1 border-t border-border/40">
                      <span>Conversaciones: {selectedPoint.conversations_count}</span>
                      <span>Última Actividad: {selectedPoint.last_active}</span>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border shadow-md">
              <CardHeader className="p-4 pb-2 border-b">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-indigo-500" />
                  Puntos en Radar ({filteredPoints.length})
                </CardTitle>
                <CardDescription className="text-xs">
                  Haz clic en un punto para inspeccionar su IP, ISP, lead scoring o ejecutar bloqueos.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-2 max-h-[500px] overflow-y-auto space-y-1.5">
                {filteredPoints.length === 0 ? (
                  <div className="p-6 text-center text-xs text-muted-foreground">
                    No se encontraron puntos con los filtros actuales.
                  </div>
                ) : (
                  filteredPoints.map((pt) => (
                    <div
                      key={pt.id}
                      onClick={() => setSelectedPoint(pt)}
                      className={cn(
                        'p-2.5 rounded-lg border border-border/50 hover:border-indigo-500/50 hover:bg-muted/50 cursor-pointer transition-all flex items-center justify-between group',
                        pt.is_ip_blocked && 'border-red-500/30 bg-red-500/5'
                      )}
                    >
                      <div className="space-y-0.5 truncate pr-2">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs">{pt.is_ip_blocked ? '🚫' : pt.entity_type === 'company' ? '🏢' : '🧪'}</span>
                          <span className="font-semibold text-xs truncate group-hover:text-indigo-500 transition-colors">
                            {pt.name}
                          </span>
                          {pt.is_online && (
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          )}
                        </div>
                        <div className="text-[10px] text-muted-foreground flex items-center gap-2">
                          <span className="font-mono">{pt.ip_address}</span>
                          <span>•</span>
                          <span>{pt.city}, {pt.country_code}</span>
                        </div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform shrink-0" />
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
