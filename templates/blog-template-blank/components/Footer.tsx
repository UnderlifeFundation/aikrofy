import React from 'react';
import Link from 'next/link';
import { BlogThemeConfig } from '@/lib/db';
import { Globe } from 'lucide-react';

export function Footer({ themeConfig }: { themeConfig: BlogThemeConfig }) {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="w-full glass-panel border-t border-white/5 py-10 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-violet-400">
            <Globe className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-200">{themeConfig.site_name}</p>
            <p className="text-[11px] text-slate-500">{themeConfig.tagline}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-6 text-xs text-slate-400">
          <Link href="/" className="hover:text-white transition-colors">
            Inicio
          </Link>
          <a href="/#articulos" className="hover:text-white transition-colors">
            Explorar
          </a>
          <p>© {currentYear} {themeConfig.site_name}. Todos los derechos reservados.</p>
        </div>
      </div>
    </footer>
  );
}
