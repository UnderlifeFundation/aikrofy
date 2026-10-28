'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Plus, Save, Trash2, ArrowLeft, MoveUp, MoveDown,
  Sparkles, Image as ImageIcon, Layout, Type, Palette,
  CheckCircle2, Mic, Eye, Settings, FileText, Globe, RefreshCw,
  ExternalLink, Wand2, Hash, Layers, ListOrdered, Quote
} from 'lucide-react';
import { marked } from 'marked';

interface CanvasBlock {
  id: string;
  type: 'heading' | 'subheading' | 'paragraph' | 'image' | 'bullets' | 'quote' | 'callout';
  content: string;
  extra?: string; // caption or style
}

export default function AdminCanvasPage() {
  const [posts, setPosts] = useState<any[]>([]);
  const [selectedPost, setSelectedPost] = useState<any | null>(null);
  const [blocks, setBlocks] = useState<CanvasBlock[]>([]);
  const [activeTab, setActiveTab] = useState<'canvas' | 'seo' | 'preview'>('canvas');
  const [isSaving, setIsSaving] = useState(false);
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Inspector settings
  const [title, setTitle] = useState('');
  const [slug, setSlug] = useState('');
  const [pillar, setPillar] = useState('Ecuador');
  const [heroImage, setHeroImage] = useState('');
  const [metaTitle, setMetaTitle] = useState('');
  const [metaDescription, setMetaDescription] = useState('');
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [status, setStatus] = useState<'published' | 'draft'>('published');

  // Load existing posts
  const fetchPosts = () => {
    fetch('/api/posts')
      .then((res) => res.json())
      .then((data) => {
        if (data.posts) {
          setPosts(data.posts);
          if (!selectedPost && data.posts.length > 0) {
            selectPostForCanvas(data.posts[0]);
          }
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  const selectPostForCanvas = (post: any) => {
    setSelectedPost(post);
    setTitle(post.title || '');
    setSlug(post.slug || '');
    setPillar(post.pillar_keyword || 'Ecuador');
    setHeroImage(post.hero_image || '');
    setMetaTitle(post.meta_title || '');
    setMetaDescription(post.meta_description || '');
    setKeywords(post.long_tail_keywords || []);
    setStatus(post.status || 'published');

    // Parse Markdown into structured Gutenberg/WordPress style Canvas blocks
    const chunks = (post.content_markdown || '').split('\n\n').filter(Boolean);
    const parsedBlocks: CanvasBlock[] = chunks.map((chunk: string, i: number) => {
      const trimmed = chunk.trim();
      if (trimmed.startsWith('# ')) {
        return { id: `b-${i}`, type: 'heading', content: trimmed.replace(/^#\s+/, '') };
      }
      if (trimmed.startsWith('## ')) {
        return { id: `b-${i}`, type: 'heading', content: trimmed.replace(/^##\s+/, '') };
      }
      if (trimmed.startsWith('### ')) {
        return { id: `b-${i}`, type: 'subheading', content: trimmed.replace(/^###\s+/, '') };
      }
      if (trimmed.startsWith('>')) {
        return { id: `b-${i}`, type: 'quote', content: trimmed.replace(/^>\s*/, '') };
      }
      if (trimmed.startsWith('![')) {
        const m = trimmed.match(/!\[(.*?)\]\((.*?)\)/);
        return {
          id: `b-${i}`,
          type: 'image',
          content: m ? m[2] : trimmed,
          extra: m ? m[1] : ''
        };
      }
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return { id: `b-${i}`, type: 'bullets', content: trimmed };
      }
      return { id: `b-${i}`, type: 'paragraph', content: trimmed };
    });

    setBlocks(parsedBlocks.length > 0 ? parsedBlocks : [
      { id: 'b-default', type: 'paragraph', content: 'Comienza a redactar tu artículo en el Canvas...' }
    ]);
  };

  const handleCreateNewPost = () => {
    const newEmptyPost = {
      id: Date.now(),
      title: 'Nuevo Artículo Agéntico',
      slug: `articulo-${Date.now().toString().slice(-4)}`,
      pillar_keyword: 'Turismo',
      long_tail_keywords: ['guia de viaje', 'mejores destinos'],
      meta_title: 'Nuevo Artículo | Ecuador Life',
      meta_description: 'Descripción optimizada para motores de búsqueda y lectores.',
      hero_image: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format',
      hero_alt: 'Destino destacado',
      content_markdown: '## Introducción\n\nEscribe aquí el contenido de tu nuevo artículo...',
      status: 'draft',
      created_at: new Date().toISOString()
    };
    selectPostForCanvas(newEmptyPost);
  };

  const moveBlock = (index: number, direction: 'up' | 'down') => {
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= blocks.length) return;
    const updated = [...blocks];
    const [moved] = updated.splice(index, 1);
    updated.splice(targetIdx, 0, moved);
    setBlocks(updated);
  };

  const updateBlockContent = (index: number, text: string) => {
    const updated = [...blocks];
    updated[index].content = text;
    setBlocks(updated);
  };

  const addBlock = (type: CanvasBlock['type']) => {
    let initialContent = '';
    if (type === 'heading') initialContent = 'Nuevo Encabezado H2';
    if (type === 'subheading') initialContent = 'Subtítulo H3 Relevante';
    if (type === 'paragraph') initialContent = 'Escribe aquí tu párrafo de contenido...';
    if (type === 'image') initialContent = 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format';
    if (type === 'bullets') initialContent = '- Primer punto clave\n- Segundo punto relevante\n- Tercera recomendación';
    if (type === 'quote') initialContent = 'La autenticidad de un lugar radica en la memoria de su gente.';
    if (type === 'callout') initialContent = '💡 Consejo de viaje: Visita temprano por la mañana para evitar aglomeraciones.';

    const newBlock: CanvasBlock = {
      id: `b-${Date.now()}`,
      type,
      content: initialContent,
      extra: type === 'image' ? 'Descripción de la imagen' : undefined
    };
    setBlocks([...blocks, newBlock]);
  };

  const deleteBlock = (index: number) => {
    const updated = blocks.filter((_, i) => i !== index);
    setBlocks(updated);
  };

  const handleDeletePost = async () => {
    if (!selectedPost || !confirm(`¿Estás seguro de eliminar "${selectedPost.title}"?`)) return;
    try {
      const res = await fetch(`/api/posts?id=${selectedPost.id}`, { method: 'DELETE' });
      if (res.ok) {
        setToastMessage('Publicación eliminada');
        setTimeout(() => setToastMessage(null), 3000);
        fetchPosts();
        setSelectedPost(null);
      }
    } catch {
      alert('Error eliminando publicación');
    }
  };

  // Agentic Copilot AI Actions
  const runAiCopilot = async (action: string, promptText?: string) => {
    setIsGeneratingAi(true);
    try {
      const currentMd = blocksToMarkdown();
      const res = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          prompt: promptText || '',
          title,
          pillar,
          currentContent: currentMd
        })
      });

      const data = await res.json();
      if (data.meta_title) {
        setMetaTitle(data.meta_title);
        setMetaDescription(data.meta_description);
        if (data.keywords) setKeywords(data.keywords);
        setToastMessage('✨ ¡Metadatos y SEO generados por IA!');
      } else if (data.result) {
        // Append generated blocks
        const generatedChunk = data.result;
        const newBlock: CanvasBlock = {
          id: `ai-${Date.now()}`,
          type: 'paragraph',
          content: generatedChunk
        };
        setBlocks([...blocks, newBlock]);
        setToastMessage('✨ ¡Contenido agéntico incorporado al Canvas!');
      }
      setTimeout(() => setToastMessage(null), 3500);
    } catch {
      alert('Error al conectar con copiloto agéntico');
    } finally {
      setIsGeneratingAi(false);
    }
  };

  // Convert canvas blocks back to markdown
  const blocksToMarkdown = () => {
    return blocks
      .map((b) => {
        if (b.type === 'heading') return `## ${b.content}`;
        if (b.type === 'subheading') return `### ${b.content}`;
        if (b.type === 'image') return `![${b.extra || 'Imagen'}](${b.content})`;
        if (b.type === 'quote') return `> ${b.content}`;
        if (b.type === 'callout') return `> ${b.content}`;
        return b.content;
      })
      .join('\n\n');
  };

  // Save changes to database
  const handleSaveCanvas = async () => {
    setIsSaving(true);
    const md = blocksToMarkdown();
    const payload = {
      id: selectedPost?.id || Date.now(),
      title,
      slug: slug || title.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      pillar_keyword: pillar,
      long_tail_keywords: keywords,
      meta_title: metaTitle || `${title} | Ecuador Life`,
      meta_description: metaDescription || title,
      hero_image: heroImage || 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format',
      hero_alt: title,
      content_markdown: md,
      status,
      created_at: selectedPost?.created_at || new Date().toISOString()
    };

    try {
      const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const json = await res.json();
        setToastMessage('¡Publicación guardada exitosamente en VPS!');
        setTimeout(() => setToastMessage(null), 3000);
        fetchPosts();
        setSelectedPost(json.post);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 glass-panel px-4 py-3 rounded-xl border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2 shadow-2xl animate-bounce">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-5 rounded-2xl border-white/5">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-300 transition-colors"
            title="Volver a la vista pública"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Layout className="w-5 h-5 text-violet-400" />
              <span>Canvas Visual Gutenberg — CMS Agéntico</span>
            </h1>
            <p className="text-xs text-slate-400">
              Edición visual por bloques, copilot inteligente e indexación SEO autónoma en VPS.
            </p>
          </div>
        </div>

        {/* Top actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCreateNewPost}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white font-medium text-xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5 text-violet-400" />
            <span>Nuevo Artículo</span>
          </button>
          <button
            onClick={handleSaveCanvas}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-violet-600/30 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Guardando...' : 'Guardar Cambios'}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Posts Explorer (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="glass-panel p-4 rounded-2xl border-white/5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Publicaciones ({posts.length})
              </h2>
              <button
                onClick={fetchPosts}
                className="text-slate-400 hover:text-white"
                title="Refrescar lista"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">
              {posts.map((p) => (
                <button
                  key={p.id}
                  onClick={() => selectPostForCanvas(p)}
                  className={`w-full text-left p-3 rounded-xl text-xs transition-all ${
                    selectedPost?.id === p.id
                      ? 'bg-violet-600 text-white font-semibold shadow-md shadow-violet-600/20'
                      : 'text-slate-300 hover:bg-white/5'
                  }`}
                >
                  <div className="line-clamp-1 font-medium">{p.title}</div>
                  <div className="flex items-center justify-between text-[10px] opacity-75 mt-1">
                    <span>{p.pillar_keyword}</span>
                    <span className="font-mono">/{p.slug?.split('/').pop()}</span>
                  </div>
                </button>
              ))}
            </div>

            {/* WhatsApp Voice Copilot info */}
            <div className="pt-3 border-t border-white/5">
              <div className="p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl space-y-1.5 text-violet-300 text-xs">
                <div className="font-bold flex items-center gap-1.5">
                  <Mic className="w-4 h-4 text-violet-400" />
                  <span>Control de Voz por WhatsApp</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  Envía una nota de voz a tu asistente de WhatsApp de Aikrofy para dictar un borrador y aparecerá aquí automáticamente.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column: Visual Canvas Area (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          {/* Main Title and Tabs */}
          <div className="glass-panel p-5 rounded-2xl border-white/5 space-y-4">
            <div className="space-y-2">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Título del Artículo
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ingresa el título principal..."
                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-lg sm:text-xl font-black text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>

            {/* View Tabs */}
            <div className="flex items-center justify-between border-t border-white/5 pt-3">
              <div className="flex items-center gap-1 bg-black/30 p-1 rounded-xl border border-white/5 text-xs font-semibold">
                <button
                  onClick={() => setActiveTab('canvas')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                    activeTab === 'canvas' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Layout className="w-3.5 h-3.5" />
                  <span>Canvas Visual</span>
                </button>
                <button
                  onClick={() => setActiveTab('seo')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                    activeTab === 'seo' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>SEO y Metadatos</span>
                </button>
                <button
                  onClick={() => setActiveTab('preview')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                    activeTab === 'preview' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Previsualizar</span>
                </button>
              </div>

              {selectedPost && (
                <Link
                  href={`/post/${selectedPost.slug}`}
                  target="_blank"
                  className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                >
                  <span>Ver en vivo</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              )}
            </div>
          </div>

          {activeTab === 'canvas' && (
            <div className="space-y-4">
              {/* Gutenberg Block inserter toolbar */}
              <div className="glass-panel p-3 rounded-xl border-white/5 flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-bold text-slate-400 mr-2 flex items-center gap-1">
                  <Layers className="w-3.5 h-3.5 text-violet-400" />
                  <span>Añadir Bloque:</span>
                </span>
                <button
                  onClick={() => addBlock('heading')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <Type className="w-3.5 h-3.5 text-violet-400" />
                  <span>H2</span>
                </button>
                <button
                  onClick={() => addBlock('subheading')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <Type className="w-3 h-3 text-indigo-400" />
                  <span>H3</span>
                </button>
                <button
                  onClick={() => addBlock('paragraph')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Párrafo</span>
                </button>
                <button
                  onClick={() => addBlock('bullets')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <ListOrdered className="w-3.5 h-3.5 text-amber-400" />
                  <span>Lista</span>
                </button>
                <button
                  onClick={() => addBlock('image')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <ImageIcon className="w-3.5 h-3.5 text-blue-400" />
                  <span>Imagen</span>
                </button>
                <button
                  onClick={() => addBlock('quote')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-200"
                >
                  <Quote className="w-3.5 h-3.5 text-pink-400" />
                  <span>Cita</span>
                </button>
              </div>

              {/* Dynamic Interactive Blocks */}
              <div className="space-y-3">
                {blocks.map((block, idx) => (
                  <div
                    key={block.id}
                    className="group glass-panel p-4 rounded-2xl border-white/5 hover:border-violet-500/30 transition-all space-y-2 relative"
                  >
                    {/* Block meta & sorting controls */}
                    <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-white/5">
                      <span className="font-mono text-[10px] text-violet-400 uppercase font-bold">
                        Bloque {idx + 1} • {block.type}
                      </span>

                      <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                        <button
                          onClick={() => moveBlock(idx, 'up')}
                          disabled={idx === 0}
                          className="p-1 rounded hover:bg-white/10 disabled:opacity-20 text-slate-300"
                          title="Mover arriba"
                        >
                          <MoveUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => moveBlock(idx, 'down')}
                          disabled={idx === blocks.length - 1}
                          className="p-1 rounded hover:bg-white/10 disabled:opacity-20 text-slate-300"
                          title="Mover abajo"
                        >
                          <MoveDown className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteBlock(idx)}
                          className="p-1 rounded hover:bg-red-500/20 text-red-400 ml-2"
                          title="Eliminar bloque"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Block Editor Content */}
                    {block.type === 'heading' && (
                      <input
                        type="text"
                        value={block.content}
                        onChange={(e) => updateBlockContent(idx, e.target.value)}
                        className="w-full bg-transparent text-xl font-bold text-white border-0 focus:ring-1 focus:ring-violet-500 rounded p-1"
                        placeholder="Encabezado H2..."
                      />
                    )}

                    {block.type === 'subheading' && (
                      <input
                        type="text"
                        value={block.content}
                        onChange={(e) => updateBlockContent(idx, e.target.value)}
                        className="w-full bg-transparent text-base font-semibold text-violet-300 border-0 focus:ring-1 focus:ring-violet-500 rounded p-1"
                        placeholder="Subtítulo H3..."
                      />
                    )}

                    {block.type === 'paragraph' && (
                      <textarea
                        rows={4}
                        value={block.content}
                        onChange={(e) => updateBlockContent(idx, e.target.value)}
                        className="w-full bg-transparent text-sm text-slate-200 border-0 focus:ring-1 focus:ring-violet-500 rounded p-1 leading-relaxed"
                        placeholder="Redacta el contenido del párrafo..."
                      />
                    )}

                    {block.type === 'bullets' && (
                      <textarea
                        rows={4}
                        value={block.content}
                        onChange={(e) => updateBlockContent(idx, e.target.value)}
                        className="w-full bg-transparent text-xs text-slate-300 border-0 focus:ring-1 focus:ring-violet-500 rounded p-1 font-mono leading-relaxed"
                        placeholder="- Elemento de lista..."
                      />
                    )}

                    {block.type === 'quote' && (
                      <div className="border-l-2 border-violet-500 pl-3">
                        <textarea
                          rows={2}
                          value={block.content}
                          onChange={(e) => updateBlockContent(idx, e.target.value)}
                          className="w-full bg-transparent text-sm italic text-slate-300 border-0 focus:ring-1 focus:ring-violet-500 rounded p-1"
                          placeholder="Texto de la cita destacada..."
                        />
                      </div>
                    )}

                    {block.type === 'image' && (
                      <div className="space-y-2">
                        <div className="h-44 w-full rounded-xl overflow-hidden bg-black/40 relative">
                          <img src={block.content} alt="Preview" className="w-full h-full object-cover" />
                        </div>
                        <input
                          type="text"
                          value={block.content}
                          onChange={(e) => updateBlockContent(idx, e.target.value)}
                          placeholder="URL de la imagen..."
                          className="w-full bg-black/30 text-xs text-violet-300 font-mono border border-white/10 rounded-lg p-2"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab: SEO & Metadata */}
          {activeTab === 'seo' && (
            <div className="glass-panel p-6 rounded-2xl border-white/5 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Globe className="w-4 h-4 text-violet-400" />
                  <span>Optimización SEO y Motores de Búsqueda</span>
                </h3>
                <button
                  onClick={() => runAiCopilot('generate_seo')}
                  disabled={isGeneratingAi}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 text-violet-300 border border-violet-500/30 hover:bg-violet-600/30 text-xs font-semibold"
                >
                  <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                  <span>Generar con IA</span>
                </button>
              </div>

              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Meta Título (Google Search)</label>
                  <input
                    type="text"
                    value={metaTitle}
                    onChange={(e) => setMetaTitle(e.target.value)}
                    className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-xs text-white"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Meta Descripción</label>
                  <textarea
                    rows={3}
                    value={metaDescription}
                    onChange={(e) => setMetaDescription(e.target.value)}
                    className="w-full bg-black/20 border border-white/10 rounded-lg p-2.5 text-xs text-white leading-relaxed"
                  />
                </div>

                {/* Google Search Result Preview */}
                <div className="p-4 bg-slate-950 rounded-xl border border-white/10 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">
                    Vista previa en Google
                  </span>
                  <div className="text-sm font-semibold text-blue-400 truncate">
                    {metaTitle || title || 'Título del artículo'}
                  </div>
                  <div className="text-xs text-emerald-400 font-mono">
                    https://tusitio.com/post/{slug || 'url-del-articulo'}
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    {metaDescription || 'Descripción del artículo en resultados de búsqueda...'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Tab: Real-Time Preview */}
          {activeTab === 'preview' && (
            <div className="glass-panel p-6 sm:p-8 rounded-2xl border-white/5 space-y-6">
              <div className="space-y-2 text-center pb-4 border-b border-white/5">
                <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">
                  {pillar}
                </span>
                <h1 className="text-2xl sm:text-3xl font-black text-white">
                  {title || 'Título del Artículo'}
                </h1>
                <p className="text-xs text-slate-400 max-w-xl mx-auto">
                  {metaDescription}
                </p>
              </div>

              {heroImage && (
                <div className="h-64 rounded-2xl overflow-hidden">
                  <img src={heroImage} alt="Hero" className="w-full h-full object-cover" />
                </div>
              )}

              <div
                className="prose prose-invert prose-violet max-w-none text-slate-200"
                dangerouslySetInnerHTML={{ __html: marked.parse(blocksToMarkdown()) as string }}
              />
            </div>
          )}
        </div>

        {/* Right Column: Inspector Settings & Agentic Copilot (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Agentic Copilot Box */}
          <div className="glass-panel p-4 rounded-2xl border-violet-500/30 bg-gradient-to-b from-violet-950/30 to-black space-y-3 shadow-xl">
            <div className="flex items-center gap-2 text-violet-300 font-bold text-xs uppercase tracking-wider">
              <Wand2 className="w-4 h-4 text-violet-400 animate-pulse" />
              <span>Copiloto Agéntico Aikrofy</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Potencia tu redacción, estructura y SEO con capacidades autónomas de IA.
            </p>

            <div className="space-y-2 pt-1">
              <button
                onClick={() => runAiCopilot('generate_full_post')}
                disabled={isGeneratingAi}
                className="w-full py-2 px-3 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition-all flex items-center justify-center gap-2 shadow-md shadow-violet-600/30 disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isGeneratingAi ? 'Generando...' : 'Generar Post Completo'}</span>
              </button>

              <button
                onClick={() => runAiCopilot('improve_writing')}
                disabled={isGeneratingAi}
                className="w-full py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 font-medium text-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Wand2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Mejorar Redacción</span>
              </button>

              <button
                onClick={() => runAiCopilot('add_cta')}
                disabled={isGeneratingAi}
                className="w-full py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 font-medium text-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5 text-amber-400" />
                <span>Insertar Llamada a Acción</span>
              </button>
            </div>
          </div>

          {/* Inspector Properties */}
          <div className="glass-panel p-4 rounded-2xl border-white/5 space-y-4">
            <div className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-wider">
              <Settings className="w-4 h-4 text-violet-400" />
              <span>Propiedades del Artículo</span>
            </div>

            {/* Status */}
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Estado de Publicación</label>
              <select
                value={status}
                onChange={(e: any) => setStatus(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg p-2 text-xs text-white"
              >
                <option value="published">Publicado</option>
                <option value="draft">Borrador</option>
              </select>
            </div>

            {/* Slug */}
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Slug de URL</label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="ej: ecuador/playas"
                className="w-full bg-black/30 border border-white/10 rounded-lg p-2 text-xs text-white font-mono"
              />
            </div>

            {/* Pillar Keyword / Category */}
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Pilar / Categoría</label>
              <input
                type="text"
                value={pillar}
                onChange={(e) => setPillar(e.target.value)}
                placeholder="ej: Manabí, Pichincha"
                className="w-full bg-black/30 border border-white/10 rounded-lg p-2 text-xs text-white"
              />
            </div>

            {/* Hero Image */}
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Imagen Destacada (URL)</label>
              <input
                type="text"
                value={heroImage}
                onChange={(e) => setHeroImage(e.target.value)}
                placeholder="https://images.unsplash.com/..."
                className="w-full bg-black/30 border border-white/10 rounded-lg p-2 text-xs text-violet-300 font-mono"
              />
            </div>

            {/* Keywords */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Palabras Clave (SEO)</label>
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newKeyword.trim()) {
                      e.preventDefault();
                      setKeywords([...keywords, newKeyword.trim()]);
                      setNewKeyword('');
                    }
                  }}
                  placeholder="Añadir palabra clave..."
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg p-1.5 text-xs text-white"
                />
                <button
                  onClick={() => {
                    if (newKeyword.trim()) {
                      setKeywords([...keywords, newKeyword.trim()]);
                      setNewKeyword('');
                    }
                  }}
                  className="px-2.5 bg-violet-600 text-white rounded-lg text-xs"
                >
                  +
                </button>
              </div>
              <div className="flex flex-wrap gap-1">
                {keywords.map((kw, i) => (
                  <span
                    key={i}
                    onClick={() => setKeywords(keywords.filter((_, idx) => idx !== i))}
                    className="text-[10px] bg-white/5 hover:bg-red-500/20 text-slate-300 hover:text-red-300 px-2 py-0.5 rounded cursor-pointer transition-colors"
                    title="Click para eliminar"
                  >
                    #{kw} ×
                  </span>
                ))}
              </div>
            </div>

            {/* Delete button */}
            {selectedPost && (
              <div className="pt-3 border-t border-white/5">
                <button
                  onClick={handleDeletePost}
                  className="w-full py-2 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Eliminar Artículo</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
