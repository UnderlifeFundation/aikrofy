'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BlogThemeConfig } from '@/lib/db';
import { Compass, Search, BookOpen, Layers, Settings, X } from 'lucide-react';

export function Navbar({ themeConfig }: { themeConfig: BlogThemeConfig }) {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/5 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-violet-600/30 group-hover:scale-105 transition-transform">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight text-white group-hover:text-violet-300 transition-colors">
              {themeConfig.site_name}
            </span>
            <p className="text-[11px] text-slate-400 font-medium -mt-0.5 hidden sm:block">
              {themeConfig.tagline}
            </p>
          </div>
        </Link>

        {/* Public Navigation */}
        <nav className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5 text-xs font-semibold">
          <Link
            href="/"
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              pathname === '/' ? 'text-white bg-violet-600 shadow-sm shadow-violet-600/30' : 'text-slate-300 hover:text-white'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Inicio</span>
          </Link>
          <a
            href="/#articulos"
            className="px-3 py-1.5 rounded-lg text-slate-300 hover:text-white transition-colors flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Artículos</span>
          </a>
        </nav>

        {/* Search & Subtle Owner Access */}
        <div className="flex items-center gap-2">
          {searchOpen ? (
            <div className="relative flex items-center">
              <input
                type="text"
                placeholder="Buscar artículos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    window.location.href = `/?q=${encodeURIComponent(searchQuery)}`;
                  }
                }}
                className="w-48 sm:w-64 bg-slate-900 border border-violet-500/40 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-violet-400"
                autoFocus
              />
              <button
                onClick={() => setSearchOpen(false)}
                className="absolute right-2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setSearchOpen(true)}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
              title="Buscar contenido"
            >
              <Search className="w-4 h-4" />
            </button>
          )}

          {/* Discreet Owner Dashboard Access */}
          <Link
            href="/admin"
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-violet-300 transition-colors"
            title="Panel de Administración"
          >
            <Settings className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
