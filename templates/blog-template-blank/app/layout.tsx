import './globals.css';
import type { Metadata } from 'next';
import Script from 'next/script';
import { getThemeConfig } from '@/lib/db';
import { verifyInstallationLicense } from '@/lib/license-shield';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Blog Agéntico — Optimizado para IA y SEO',
  description: 'Arquitectura natural de cola larga, navegación SPA instantánea y copiloto inteligente.',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const config = getThemeConfig();
  const license = await verifyInstallationLicense();

  return (
    <html lang="es" className={config.dark_mode ? 'dark' : ''}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
      </head>
      <body className="min-h-screen flex flex-col bg-[#090b10] text-[#f8fafc] selection:bg-purple-500/30 selection:text-purple-200">
        {!license.valid ? (
          <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center bg-gradient-to-b from-red-950/40 to-black">
            <div className="max-w-md glass-panel p-8 rounded-2xl border-red-500/30 space-y-4">
              <div className="w-16 h-16 mx-auto rounded-full bg-red-500/20 text-red-400 flex items-center justify-center text-3xl font-bold">
                ⚠️
              </div>
              <h1 className="text-2xl font-bold text-red-300">Licencia Aikrofy Requerida</h1>
              <p className="text-sm text-slate-300 leading-relaxed">
                Este módulo de blog está protegido criptográficamente. Para activarlo en tu servidor, adquiérelo en la tienda de materiales de Aikrofy y configura tus claves en el archivo <code className="bg-black/50 px-2 py-0.5 rounded text-violet-300">.env.production</code>.
              </p>
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                Motivo: {license.reason || 'Sin token de licencia firmado'}
              </div>
              <a
                href="https://aikrofy.com/pricing"
                target="_blank"
                rel="noreferrer"
                className="inline-block px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-sm transition-all shadow-lg shadow-violet-600/30"
              >
                Adquirir Módulo en Aikrofy
              </a>
            </div>
          </div>
        ) : (
          <>
            <Navbar themeConfig={config} />
            <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
              {children}
            </main>
            <Footer themeConfig={config} />

            {/* Widget de Agente Aikrofy Embebido para Lectores y Prospectos */}
            {config.widget_enabled && (
              <Script
                src="https://aikrofy.com/widget.js"
                data-widget-id={config.widget_id || 'f97f9776-e3e5-4891-ad7f-5e54f91462c1'}
                strategy="lazyOnload"
              />
            )}
          </>
        )}
      </body>
    </html>
  );
}
