import { NextResponse } from 'next/server';
import { getAllPosts, savePost, deletePost, saveThemeConfig, getThemeConfig } from '@/lib/db';

export async function GET() {
  const posts = getAllPosts();
  return NextResponse.json({ posts });
}

export async function POST(req: Request) {
  try {
    const data = await req.json();
    if (!data.title) {
      return NextResponse.json({ error: 'Title is required' }, { status: 400 });
    }

    const cleanSlug = data.slug || data.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, '');
    const newPost = {
      id: data.id || Date.now(),
      title: data.title,
      slug: cleanSlug,
      pillar_keyword: data.pillar_keyword || 'Ecuador',
      long_tail_keywords: data.long_tail_keywords || [],
      meta_title: data.meta_title || `${data.title} | Ecuador Life`,
      meta_description: data.meta_description || data.title,
      hero_image: data.hero_image || 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format',
      hero_alt: data.hero_alt || data.title,
      content_markdown: data.content_markdown || `# ${data.title}\n\nContenido generado.`,
      status: data.status || 'published',
      created_at: data.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    savePost(newPost as any);
    return NextResponse.json({ success: true, post: newPost });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get('id');
    if (!id) {
      return NextResponse.json({ error: 'Post ID is required' }, { status: 400 });
    }
    deletePost(id);
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message }, { status: 500 });
  }
}
