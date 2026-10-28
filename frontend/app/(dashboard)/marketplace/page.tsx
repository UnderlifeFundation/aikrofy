'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Package, Download, ShieldCheck, Key,
  Sparkles, Lock, Copy, Server, Clock, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface ModularAsset {
  id: number;
  slug: string;
  name: string;
  description: string;
  version: string;
  price_usd: number;
  credits_cost: number;
  is_purchased: boolean;
  license_key?: string;
  allowed_domains?: string[];
  status_message?: string;
  features?: Record<string, boolean>;
}

export default function MarketplaceStorePage() {
  const queryClient = useQueryClient();
  const [selectedAsset, setSelectedAsset] = useState<ModularAsset | null>(null);
  const [domainInput, setDomainInput] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState<string | null>(null);

  // Fetch catalog & purchase state
  const { data, isLoading } = useQuery({
    queryKey: ['marketplace-assets'],
    queryFn: async () => {
      const res = await apiClient.get('/marketplace/assets');
      return res.data;
    },
  });

  const purchaseMutation = useMutation({
    mutationFn: async ({ slug, domain }: { slug: string; domain: string }) => {
      const res = await apiClient.post('/marketplace/assets/purchase', { slug, domain });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || '¡Módulo adquirido con éxito!');
      queryClient.invalidateQueries({ queryKey: ['marketplace-assets'] });
      queryClient.invalidateQueries({ queryKey: ['me'] });
      setSelectedAsset(null);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.error || 'Error al adquirir el módulo');
    },
  });

  const handleDownload = async (slug: string) => {
    try {
      setIsDownloading(slug);
      toast.info('Generando y descargando paquete zip con tu licencia...');
      
      const response = await apiClient.get(`/marketplace/assets/download/${slug}`, {
        responseType: 'blob',
      });

      // Create blob link to download
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from headers or default
      const disposition = response.headers['content-disposition'];
      let filename = `aikrofy-${slug}.zip`;
      if (disposition && disposition.indexOf('filename=') !== -1) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Descarga iniciada exitosamente.');
    } catch (error: any) {
      console.error('Download error:', error);
      toast.error(error?.response?.data?.error || error?.message || 'Error al descargar el archivo ZIP');
    } finally {
      setIsDownloading(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(text);
    toast.success('Clave de licencia copiada al portapapeles');
    setTimeout(() => setCopiedKey(null), 3000);
  };

  const assets: ModularAsset[] = data?.assets || [];
  const creditBalance = data?.credit_balance ?? 0;

  // PayPal button rendering state for purchase modal
  const [purchaseMethod, setPurchaseMethod] = useState<'credits' | 'paypal'>('credits');
  const [paypalLoaded, setPaypalLoaded] = useState(false);
  const [paypalRendering, setPaypalRendering] = useState(false);
  const paypalContainerRef = React.useRef<HTMLDivElement>(null);

  // Load PayPal SDK if needed
  React.useEffect(() => {
    if (typeof window !== 'undefined' && !paypalLoaded) {
      if ((window as any).paypal) {
        setPaypalLoaded(true);
        return;
      }
      const clientId = process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID || 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in';
      const script = document.createElement('script');
      script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD&components=buttons&enable-funding=card`;
      script.async = true;
      script.onload = () => setPaypalLoaded(true);
      document.body.appendChild(script);
    }
  }, [paypalLoaded]);

  // Render PayPal buttons when modal opens with paypal payment method
  React.useEffect(() => {
    if (!selectedAsset || purchaseMethod !== 'paypal') return;

    let timer: NodeJS.Timeout | null = null;
    let isCancelled = false;
    let buttonInstance: any = null;

    const renderPayPal = () => {
      if (isCancelled) return;
      const win = window as any;
      const container = paypalContainerRef.current;
      if (!win.paypal || !win.paypal.Buttons || !container) {
        timer = setTimeout(renderPayPal, 150);
        return;
      }

      container.innerHTML = '';
      setPaypalRendering(true);

      try {
        buttonInstance = win.paypal.Buttons({
          style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'pay',
            height: 44,
          },
          createOrder: async () => {
            try {
              const res = await apiClient.post('/marketplace/assets/paypal/create-order', {
                slug: selectedAsset.slug,
                domain: domainInput,
              });
              if (res.data.already_owned) {
                toast.info('Ya posees este módulo.');
                setSelectedAsset(null);
                queryClient.invalidateQueries({ queryKey: ['marketplace-assets'] });
                return '';
              }
              return res.data.order_id;
            } catch (err: any) {
              toast.error(err?.response?.data?.error || 'Error al iniciar orden en PayPal');
              throw err;
            }
          },
          onApprove: async (data: any) => {
            try {
              toast.info('Verificando cobro y generando tu licencia cifrada...');
              const res = await apiClient.post('/marketplace/assets/paypal/capture-order', {
                order_id: data.orderID,
                slug: selectedAsset.slug,
                domain: domainInput,
              });
              toast.success(res.data.message || '¡Módulo adquirido exitosamente!');
              queryClient.invalidateQueries({ queryKey: ['marketplace-assets'] });
              queryClient.invalidateQueries({ queryKey: ['me'] });
              setSelectedAsset(null);
            } catch (err: any) {
              toast.error(err?.response?.data?.error || 'Error al procesar el pago');
            }
          },
          onError: (err: any) => {
            console.error('PayPal button error:', err);
            toast.error('Error al procesar el pago con PayPal');
          },
        });

        buttonInstance.render(container);
      } catch (err) {
        console.error('Render error:', err);
      } finally {
        setPaypalRendering(false);
      }
    };

    renderPayPal();

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
      if (buttonInstance && typeof buttonInstance.close === 'function') {
        try {
          buttonInstance.close();
        } catch {}
      }
    };
  }, [selectedAsset, purchaseMethod, domainInput, queryClient]);

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header Banner - Full Light & Dark Mode Compatible */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-8 rounded-3xl bg-gradient-to-r from-violet-500/10 via-purple-500/5 to-slate-500/10 dark:from-violet-950/40 dark:via-purple-950/20 dark:to-slate-900/60 border border-violet-500/20 shadow-xl">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20">
            <Package className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
            <span>Tienda de Módulos</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-black text-foreground tracking-tight">
            Módulos Agénticos Desacoplados
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl leading-relaxed">
            Adquiere componentes independientes para desplegar en tu propio VPS. Vienen precargados con verificación criptográfica anti-uso no autorizado, integración a WhatsApp por voz y sincronización de media optimizada.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border text-right shrink-0 shadow-sm">
          <p className="text-[11px] font-medium text-muted-foreground">Combustible IA Disponible</p>
          <p className="text-2xl font-black text-violet-600 dark:text-violet-300 font-mono">
            {creditBalance === -1 ? 'Ilimitado ♾️' : `${creditBalance.toLocaleString()} créditos`}
          </p>
        </div>
      </div>

      {/* Catalog Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {assets.map((asset) => {
          const isEcommerce = asset.slug === 'ecommerce_module' || asset.slug.includes('ecommerce');
          const isPurchased = !isEcommerce && (asset.is_purchased || creditBalance === -1);
          const priceUsd = asset.price_usd || 1200;
          const creditsEquivalent = asset.credits_cost || 120000;

          return (
            <div
              key={asset.slug}
              className={`rounded-3xl p-6 sm:p-8 flex flex-col justify-between space-y-6 transition-all border ${
                isPurchased
                  ? 'bg-violet-50/50 dark:bg-violet-950/20 border-violet-500/40 shadow-lg shadow-violet-500/10'
                  : 'bg-card border-border hover:border-violet-500/30 shadow-sm'
              }`}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-muted-foreground uppercase tracking-wider">
                    v{asset.version} • {asset.slug}
                  </span>
                  {isEcommerce ? (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20">
                      <Clock className="w-3.5 h-3.5 text-amber-500" />
                      <span>Próximamente</span>
                    </span>
                  ) : isPurchased ? (
                    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
                      <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      <span>Licencia Activa</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">
                      <Lock className="w-3.5 h-3.5" />
                      <span>Bloqueado</span>
                    </span>
                  )}
                </div>

                <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                  {asset.name}
                </h2>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed font-normal">
                  {asset.description}
                </p>

                {/* Feature Tags */}
                <div className="flex flex-wrap gap-2 pt-2">
                  <span className="text-[11px] bg-muted/60 border border-border px-2.5 py-1 rounded-lg text-foreground/80 font-medium">
                    ⚡ Navegación SPA Sin Recarga
                  </span>
                  <span className="text-[11px] bg-muted/60 border border-border px-2.5 py-1 rounded-lg text-foreground/80 font-medium">
                    🎙️ Control por Voz WhatsApp / Telegram
                  </span>
                  <span className="text-[11px] bg-muted/60 border border-border px-2.5 py-1 rounded-lg text-foreground/80 font-medium">
                    🛡️ Cifrado HMAC Anclado a Dominio
                  </span>
                  <span className="text-[11px] bg-muted/60 border border-border px-2.5 py-1 rounded-lg text-foreground/80 font-medium">
                    🖼️ MediaSuite & Storage en VPS del Cliente
                  </span>
                </div>

                {/* License Key Box if purchased */}
                {isPurchased && asset.license_key && (
                  <div className="p-4 rounded-2xl bg-muted/40 dark:bg-black/50 border border-violet-500/30 space-y-2 mt-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-bold flex items-center gap-1.5 text-violet-600 dark:text-violet-400">
                        <Key className="w-3.5 h-3.5" />
                        Tu Clave de Licencia Cifrada
                      </span>
                      <button
                        onClick={() => copyToClipboard(asset.license_key!)}
                        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      >
                        <Copy className="w-3 h-3" />
                        <span>{copiedKey === asset.license_key ? 'Copiado' : 'Copiar'}</span>
                      </button>
                    </div>
                    <div className="font-mono text-xs text-emerald-700 dark:text-emerald-300 break-all bg-background/80 dark:bg-black/40 p-2.5 rounded-xl border border-border">
                      {asset.license_key}
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      Incluida automáticamente en el archivo <code className="text-violet-600 dark:text-violet-300">.env.production</code> del ZIP descargable.
                    </p>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <span className="text-xs text-muted-foreground">Inversión:</span>
                  <div className="flex flex-col">
                    {isEcommerce ? (
                      <span className="text-sm font-semibold text-muted-foreground italic">
                        Próximamente disponible
                      </span>
                    ) : (
                      <>
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-2xl font-black text-foreground">
                            ${priceUsd.toLocaleString()} USD
                          </span>
                        </div>
                        <span className="text-[11px] text-muted-foreground font-medium">
                          o su equivalente en <strong className="text-violet-600 dark:text-violet-400 font-semibold">{creditsEquivalent.toLocaleString()} créditos</strong>
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {isEcommerce ? (
                  <Button
                    disabled
                    variant="outline"
                    className="w-full sm:w-auto text-xs px-5 py-2.5 rounded-xl opacity-70 cursor-not-allowed"
                  >
                    <Clock className="w-3.5 h-3.5 mr-1.5" />
                    Próximamente
                  </Button>
                ) : isPurchased ? (
                  <Button
                    onClick={() => handleDownload(asset.slug)}
                    disabled={isDownloading === asset.slug}
                    className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-violet-600/30 cursor-pointer"
                  >
                    {isDownloading === asset.slug ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Descargando...</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4" />
                        <span>Descargar ZIP para VPS</span>
                      </>
                    )}
                  </Button>
                ) : (
                  <Button
                    onClick={() => {
                      setSelectedAsset(asset);
                      setPurchaseMethod('credits');
                    }}
                    className="w-full sm:w-auto bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-xs px-6 py-2.5 rounded-xl shadow-lg shadow-violet-600/20 cursor-pointer"
                  >
                    Comprar Módulo
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Deployment Instructions Card - Full Theme Compatible */}
      <div className="p-6 sm:p-8 rounded-3xl bg-card border border-border space-y-4 shadow-sm">
        <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
          <Server className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          <span>¿Cómo funciona el despliegue del módulo en tu VPS?</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
          <div className="p-4 rounded-2xl bg-muted/40 border border-border space-y-2">
            <span className="font-bold text-violet-700 dark:text-violet-300">1. Descarga el ZIP</span>
            <p>El paquete incluye Next.js 15 compilado, la arquitectura de cola larga, el CMS Canvas y tu clave de licencia cifrada ya inyectada.</p>
          </div>
          <div className="p-4 rounded-2xl bg-muted/40 border border-border space-y-2">
            <span className="font-bold text-violet-700 dark:text-violet-300">2. Sube a tu VPS</span>
            <p>Descomprime y corre con <code className="text-emerald-700 dark:text-emerald-400 font-mono">npm start</code> o PM2 en el puerto 3020. Tus archivos, base de datos y recursos se ejecutan con total autonomía y privacidad en tu propia infraestructura.</p>
          </div>
          <div className="p-4 rounded-2xl bg-muted/40 border border-border space-y-2">
            <span className="font-bold text-violet-700 dark:text-violet-300">3. Controla por Voz</span>
            <p>Dicta artículos, pide fotos de Pexels o cambia colores enviando una nota de voz por WhatsApp a tu copiloto Krof.</p>
          </div>
        </div>
      </div>

      {/* Purchase Confirmation Modal with Dual Method: Credits or PayPal/Card */}
      {selectedAsset && (
        <Dialog open={!!selectedAsset} onOpenChange={() => setSelectedAsset(null)}>
          <DialogContent className="sm:max-w-lg bg-card border-border text-foreground">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                <span>Adquirir {selectedAsset.name}</span>
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-2 text-xs text-muted-foreground">
              {/* Method Selector */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                  Método de Pago
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setPurchaseMethod('credits')}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      purchaseMethod === 'credits'
                        ? 'bg-violet-500/10 border-violet-500 text-foreground font-semibold'
                        : 'bg-muted/30 border-border text-muted-foreground hover:border-violet-500/40'
                    }`}
                  >
                    <div className="font-bold text-xs">Combustible IA</div>
                    <div className="text-[11px] text-violet-600 dark:text-violet-400">
                      {(selectedAsset.credits_cost || 120000).toLocaleString()} créditos
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPurchaseMethod('paypal')}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      purchaseMethod === 'paypal'
                        ? 'bg-violet-500/10 border-violet-500 text-foreground font-semibold'
                        : 'bg-muted/30 border-border text-muted-foreground hover:border-violet-500/40'
                    }`}
                  >
                    <div className="font-bold text-xs">PayPal / Tarjeta</div>
                    <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                      ${(selectedAsset.price_usd || 1200).toLocaleString()} USD directo
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-muted-foreground mb-1.5">
                  Dominio de tu VPS (Opcional — ej: blog.miempresa.com o midominio.com)
                </label>
                <Input
                  placeholder="midominio.com"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  className="bg-background border-border text-foreground text-xs h-9"
                />
                <p className="text-[10px] text-muted-foreground mt-1">
                  La clave criptográfica se anclará a este dominio para proteger tu instalación en tu VPS.
                </p>
              </div>

              {purchaseMethod === 'credits' ? (
                <div className="p-3.5 rounded-xl bg-muted/40 border border-border space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span>Costo del Módulo:</span>
                    <strong className="text-foreground">{(selectedAsset.credits_cost || 120000).toLocaleString()} créditos</strong>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span>Tu saldo actual:</span>
                    <strong className="text-foreground">
                      {creditBalance === -1 ? 'Ilimitado ♾️' : `${creditBalance.toLocaleString()} créditos`}
                    </strong>
                  </div>
                  {creditBalance !== -1 && creditBalance < (selectedAsset.credits_cost || 120000) && (
                    <p className="text-[11px] text-amber-600 dark:text-amber-400 pt-1 font-semibold">
                      ⚠️ Saldo insuficiente en combustible IA. Puedes pagar directamente con PayPal o Tarjeta en la pestaña de arriba.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3 pt-1">
                  <p className="text-[11px] text-muted-foreground">
                    Paga de forma instantánea y segura usando tu saldo de <strong>PayPal</strong> o tu <strong>tarjeta de débito/crédito como invitado</strong>.
                  </p>
                  <div className="w-full flex justify-center pt-2">
                    <div ref={paypalContainerRef} className="w-full max-w-[360px] min-h-[44px]" />
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="ghost"
                onClick={() => setSelectedAsset(null)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Cancelar
              </Button>
              {purchaseMethod === 'credits' && (
                <Button
                  onClick={() => purchaseMutation.mutate({ slug: selectedAsset.slug, domain: domainInput })}
                  disabled={purchaseMutation.isPending || (creditBalance !== -1 && creditBalance < (selectedAsset.credits_cost || 120000))}
                  className="bg-violet-600 hover:bg-violet-500 text-white font-bold text-xs px-5 cursor-pointer"
                >
                  {purchaseMutation.isPending ? 'Procesando...' : 'Confirmar con Créditos'}
                </Button>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
