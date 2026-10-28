import { NextResponse } from 'next/server';
import { savePost, saveThemeConfig } from '@/lib/db';

export async function POST(req: Request) {
  try {
    const payload = await req.json();

    // Event 1: Style changed from WhatsApp voice note or Copilot
    if (payload.event === 'blog_style_changed' || payload.style_prompt) {
      const prompt = (payload.style_prompt || '').toLowerCase();
      const updates: any = {};
      if (prompt.includes('oscuro') || prompt.includes('dark')) updates.dark_mode = true;
      if (prompt.includes('claro') || prompt.includes('light')) updates.dark_mode = false;
      if (prompt.includes('violeta') || prompt.includes('morado')) updates.primary_color = '#8b5cf6';
      if (prompt.includes('azul')) updates.primary_color = '#3b82f6';
      if (prompt.includes('verde') || prompt.includes('esmeralda')) updates.primary_color = '#10b981';
      saveThemeConfig(updates);
      return NextResponse.json({ success: true, action: 'style_updated' });
    }

    // Event 2: New article pushed by Celery / MediaSuite
    if (payload.title && payload.slug) {
      savePost(payload);
      return NextResponse.json({ success: true, action: 'post_saved' });
    }

    return NextResponse.json({ received: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
