/**
 * Local Data Storage Engine for Client VPS
 * Stores posts, long-tail URLs, styling settings and media metadata
 * completely independent from Aikrofy servers to guarantee zero hosting costs for central platform.
 */
import fs from 'fs';
import path from 'path';

export interface BlogPost {
  id: string | number;
  title: string;
  slug: string; // e.g. "ecuador/manabi/playas-tranquilas"
  pillar_keyword: string;
  long_tail_keywords: string[];
  meta_title: string;
  meta_description: string;
  hero_image: string;
  hero_alt: string;
  content_markdown: string;
  status: 'published' | 'draft';
  created_at: string;
  updated_at?: string;
  media_gallery?: Array<{ url: string; alt: string; photographer?: string }>;
}

export interface BlogThemeConfig {
  site_name: string;
  tagline: string;
  primary_color: string;
  accent_color: string;
  font_family: string;
  dark_mode: boolean;
  widget_enabled: boolean;
  widget_id?: string;
}

const DB_FILE = path.join(process.cwd(), 'data', 'posts.json');
const CONFIG_FILE = path.join(process.cwd(), 'data', 'config.json');

function ensureFiles() {
  const dir = path.dirname(DB_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  if (!fs.existsSync(CONFIG_FILE)) {
    const defaultConfig: BlogThemeConfig = {
      site_name: 'Ecuador Life & Travel',
      tagline: 'Explora lo auténtico de Ecuador con inteligencia agéntica',
      primary_color: '#7c3aed',
      accent_color: '#10b981',
      font_family: 'Inter, system-ui, sans-serif',
      dark_mode: true,
      widget_enabled: true,
      widget_id: process.env.AIKROFY_WIDGET_ID || 'f97f9776-e3e5-4891-ad7f-5e54f91462c1',
    };
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(defaultConfig, null, 2));
  }

  if (!fs.existsSync(DB_FILE)) {
    fs.writeFileSync(DB_FILE, JSON.stringify([], null, 2));
  }
}

export function getAllPosts(): BlogPost[] {
  ensureFiles();
  try {
    const data = fs.readFileSync(DB_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return [];
  }
}

export function getPostBySlug(slug: string): BlogPost | undefined {
  const posts = getAllPosts();
  const normalized = slug.replace(/^\/+|\/+$/g, '').toLowerCase();
  return posts.find((p) => p.slug.replace(/^\/+|\/+$/g, '').toLowerCase() === normalized);
}

export function savePost(post: BlogPost): BlogPost {
  ensureFiles();
  const posts = getAllPosts();
  const idx = posts.findIndex((p) => String(p.id) === String(post.id) || p.slug === post.slug);
  if (idx >= 0) {
    posts[idx] = { ...posts[idx], ...post, updated_at: new Date().toISOString() };
  } else {
    posts.unshift(post);
  }
  fs.writeFileSync(DB_FILE, JSON.stringify(posts, null, 2));
  return post;
}

export function deletePost(id: string | number): boolean {
  ensureFiles();
  const posts = getAllPosts();
  const filtered = posts.filter((p) => String(p.id) !== String(id));
  fs.writeFileSync(DB_FILE, JSON.stringify(filtered, null, 2));
  return true;
}

export function getThemeConfig(): BlogThemeConfig {
  ensureFiles();
  try {
    const data = fs.readFileSync(CONFIG_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return {
      site_name: 'Ecuador Life & Travel',
      tagline: 'Explora Ecuador',
      primary_color: '#7c3aed',
      accent_color: '#10b981',
      font_family: 'Inter, sans-serif',
      dark_mode: true,
      widget_enabled: true,
    };
  }
}

export function saveThemeConfig(config: Partial<BlogThemeConfig>): BlogThemeConfig {
  ensureFiles();
  const current = getThemeConfig();
  const updated = { ...current, ...config };
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(updated, null, 2));
  return updated;
}
