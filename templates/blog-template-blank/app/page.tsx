import React from 'react';
import Link from 'next/link';
import { getAllPosts, getThemeConfig } from '@/lib/db';
import { ArrowRight, MapPin, Calendar, Compass, Flame } from 'lucide-react';

export default async function HomePage() {
  const posts = getAllPosts();
  const theme = getThemeConfig();

  const featured = posts[0];
  const regularPosts = posts.slice(1);

  // Group unique categories/keywords
  const categories = Array.from(new Set(posts.map((p) => p.pillar_keyword))).filter(Boolean);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative rounded-3xl overflow-hidden glass-panel p-8 sm:p-14 border-white/10 bg-gradient-to-r from-violet-950/40 via-purple-900/15 to-slate-950/80 shadow-2xl">
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-300 border border-violet-500/20">
            <Compass className="w-3.5 h-3.5 text-violet-400" />
            <span>Guías, Artículos y Recomendaciones de Viaje</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white leading-tight">
            {theme.site_name}
          </h1>
          <p className="text-sm sm:text-base text-slate-300 font-normal leading-relaxed">
            {theme.tagline}. Descubre experiencias únicas, paisajes inolvidables y las mejores recomendaciones para tu próxima aventura.
          </p>

          {/* Categories Pills */}
          {categories.length > 0 && (
            <div className="pt-2 flex flex-wrap gap-2">
              {categories.slice(0, 6).map((cat) => (
                <span
                  key={cat}
                  className="px-2.5 py-1 text-[11px] rounded-lg bg-white/5 border border-white/10 text-slate-300"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Featured Article */}
      {featured && (
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-violet-400">
            <Flame className="w-4 h-4 text-amber-400" />
            <span>Artículo Destacado</span>
          </div>

          <Link
            href={`/post/${featured.slug}`}
            className="group block relative rounded-2xl overflow-hidden glass-panel border-white/10 glass-card-hover"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div className="relative h-64 md:h-80 w-full overflow-hidden bg-slate-800">
                <img
                  src={featured.hero_image}
                  alt={featured.hero_alt}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              <div className="p-6 md:p-8 space-y-4">
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span className="flex items-center gap-1 text-violet-400 font-semibold">
                    <MapPin className="w-3.5 h-3.5" />
                    {featured.pillar_keyword}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(featured.created_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-white group-hover:text-violet-300 transition-colors">
                  {featured.title}
                </h2>
                <p className="text-xs sm:text-sm text-slate-300 line-clamp-3">
                  {featured.meta_description}
                </p>
                <div className="pt-2 flex items-center gap-2 text-xs font-bold text-violet-400 group-hover:translate-x-1 transition-transform">
                  <span>Leer Artículo Completo</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            </div>
          </Link>
        </section>
      )}

      {/* Grid of Articles */}
      <section id="articulos" className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Últimas Publicaciones</h2>
          <span className="text-xs text-slate-400">{posts.length} publicaciones</span>
        </div>

        {regularPosts.length === 0 && !featured ? (
          <div className="text-center py-16 glass-panel rounded-2xl border-white/5 space-y-3">
            <p className="text-slate-400 text-sm">Aún no hay artículos publicados en este blog.</p>
            <p className="text-xs text-slate-500">
              Pronto compartiremos nuevas guías y novedades.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {regularPosts.map((post) => (
              <Link
                key={post.id}
                href={`/post/${post.slug}`}
                className="group flex flex-col rounded-2xl overflow-hidden glass-panel border-white/10 glass-card-hover"
              >
                <div className="relative h-48 w-full overflow-hidden bg-slate-800">
                  <img
                    src={post.hero_image}
                    alt={post.hero_alt}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-[11px] font-semibold text-violet-300 border border-white/10">
                    {post.pillar_keyword}
                  </div>
                </div>

                <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <h3 className="text-base font-bold text-white group-hover:text-violet-300 transition-colors line-clamp-2">
                      {post.title}
                    </h3>
                    <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                      {post.meta_description}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-white/5 text-[11px] text-slate-500 font-medium">
                    <span>
                      {new Date(post.created_at).toLocaleDateString('es-ES', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric'
                      })}
                    </span>
                    <span className="text-violet-400 font-bold flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                      Leer más <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
