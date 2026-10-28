import React from 'react';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import Link from 'next/link';
import { getPostBySlug, getAllPosts } from '@/lib/db';
import { ArrowLeft, Calendar, Share2, Sparkles, MapPin, CheckCircle2 } from 'lucide-react';
import { marked } from 'marked';

interface Props {
  params: Promise<{ slug: string[] }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const fullSlug = slug.join('/');
  const post = getPostBySlug(fullSlug);

  if (!post) {
    return { title: 'Artículo no encontrado' };
  }

  return {
    title: post.meta_title || post.title,
    description: post.meta_description,
    openGraph: {
      title: post.meta_title || post.title,
      description: post.meta_description,
      images: [{ url: post.hero_image, alt: post.hero_alt }],
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title: post.meta_title || post.title,
      description: post.meta_description,
      images: [post.hero_image],
    },
  };
}

export default async function PostDetailPage({ params }: Props) {
  const { slug } = await params;
  const fullSlug = slug.join('/');
  const post = getPostBySlug(fullSlug);

  if (!post) {
    notFound();
  }

  // Schema.org JSON-LD para SEO natural e IA Search
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.meta_description,
    image: [post.hero_image],
    datePublished: post.created_at,
    dateModified: post.updated_at || post.created_at,
    author: {
      '@type': 'Organization',
      name: 'Ecuador Life & Travel',
    },
    keywords: [post.pillar_keyword, ...(post.long_tail_keywords || [])].join(', '),
  };

  return (
    <article className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-violet-400 hover:text-violet-300 font-semibold transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Volver al listado</span>
        </Link>
        <span className="bg-white/5 px-2.5 py-1 rounded-md text-[11px] text-slate-400">
          Publicación
        </span>
      </div>

      {/* Header Info */}
      <header className="space-y-4 text-center max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-violet-500/10 text-violet-300 border border-violet-500/20">
          <MapPin className="w-3.5 h-3.5 text-violet-400" />
          <span>{post.pillar_keyword}</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight">
          {post.title}
        </h1>
        <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-normal">
          {post.meta_description}
        </p>
        <div className="flex items-center justify-center gap-4 text-xs text-slate-400 pt-2">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {new Date(post.created_at).toLocaleDateString('es-ES', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
          <span>•</span>
          <span className="text-slate-400">Lectura de 4 min</span>
        </div>
      </header>

      {/* Hero Visual */}
      <div className="relative rounded-3xl overflow-hidden glass-panel border-white/10 shadow-2xl h-80 sm:h-[420px]">
        <img
          src={post.hero_image}
          alt={post.hero_alt}
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-3 right-3 bg-black/60 backdrop-blur-md px-3 py-1 rounded-lg text-[10px] text-slate-300">
          {post.hero_alt}
        </div>
      </div>

      {/* Body Content */}
      <div 
        className="glass-panel p-6 sm:p-10 rounded-3xl border-white/5 text-slate-200 leading-relaxed prose prose-invert prose-violet max-w-none prose-headings:font-bold prose-headings:tracking-tight prose-a:text-violet-400 prose-img:rounded-2xl"
        dangerouslySetInnerHTML={{ __html: marked.parse(post.content_markdown || '') as string }}
      />

      {/* Long Tail Keyword Pills */}
      {post.long_tail_keywords && post.long_tail_keywords.length > 0 && (
        <div className="p-4 rounded-2xl glass-panel border-white/5 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-400 mr-2">Temas Relacionados:</span>
          {post.long_tail_keywords.map((kw, i) => (
            <span
              key={i}
              className="text-xs bg-white/5 text-violet-300 px-3 py-1 rounded-full border border-white/5"
            >
              #{kw}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
