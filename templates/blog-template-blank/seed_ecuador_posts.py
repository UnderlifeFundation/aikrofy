"""
Ecuador Life — Seeder & Migration Script
Extracts published WordPress posts and natural long-tail keywords from u668392243_ecuadors.sql
and feeds them into the blank modular blog template data store (data/posts.json).

Copyright © 2026 WEBLIFETECH. All Rights Reserved.
"""
import os
import re
import json
from datetime import datetime

SQL_PATH = "/Users/macbook/Desktop/AI_LAB-WLT/TurismAI/Ecuador/u668392243_ecuadors.sql"
TARGET_POSTS_JSON = "/Users/macbook/Desktop/AI_LAB-WLT/aikrofy/templates/blog-template-blank/data/posts.json"

FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1589802829985-817e51171b92?w=1200&auto=format",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format",
    "https://images.unsplash.com/photo-1546587348-d12660c30c50?w=1200&auto=format",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200&auto=format",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=1200&auto=format"
]

def clean_html_to_markdown(html: str) -> str:
    # Strip Gutenberg comments
    clean = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # Simple tag cleaner
    clean = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    return clean

def extract_ecuador_posts(limit: int = 15):
    posts = []
    if not os.path.exists(SQL_PATH):
        print(f"Error: SQL file not found at {SQL_PATH}")
        return posts

    print(f"Reading WordPress dump: {SQL_PATH} ...")
    with open(SQL_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        in_posts = False
        img_idx = 0
        for line in f:
            if 'INSERT INTO `wp_posts`' in line:
                in_posts = True
                continue
            if in_posts:
                if line.startswith('INSERT INTO') or line.startswith('CREATE TABLE'):
                    break
                if "'post'" in line and "'publish'" in line:
                    # Regex extract title and slug
                    # VALUES (ID, author, date, date_gmt, content, title, excerpt, status, ..., post_name, ...)
                    m = re.search(r'\((\d+),\s*\d+,\s*\'([^\']+)\',\s*\'[^\']+\',\s*\'(.*?)\',\s*\'([^\']+)\',\s*\'[^\']*\',\s*\'publish\',\s*\'[^\']*\',\s*\'[^\']*\',\s*\'[^\']*\',\s*\'([^\']+)\'', line, re.DOTALL)
                    if m:
                        pid = m.group(1)
                        post_date = m.group(2)
                        raw_content = m.group(3)
                        title = m.group(4)
                        slug = m.group(5)

                        # Skip short or generic titles
                        if len(title) < 5 or "elementor" in raw_content.lower() and len(raw_content) < 200:
                            continue

                        markdown = clean_html_to_markdown(raw_content)
                        if len(markdown) < 150:
                            markdown = f"""# {title}

Descubre los encantos de esta región de Ecuador con información detallada, historia, cultura y recomendaciones para el visitante.

## 1. Atractivos Principales
- Rutas escénicas y paisajes naturales.
- Gastronomía tradicional con ingredientes locales de la más alta calidad.
- Oportunidades de senderismo, aventura y descanso en un entorno protegido.

## 2. Recomendaciones de Viaje
Visita durante la temporada seca para disfrutar de días soleados y accesos despejados.
"""

                        # Long tail keyword derivation
                        pillar = "Ecuador"
                        if "manabi" in slug: pillar = "Manabí"
                        elif "esmeraldas" in slug: pillar = "Esmeraldas"
                        elif "guayas" in slug: pillar = "Guayas"
                        elif "pichincha" in slug: pillar = "Pichincha"
                        elif "el-oro" in slug: pillar = "El Oro"
                        elif "carchi" in slug: pillar = "Carchi"

                        long_tail = [
                            f"que hacer en {slug.replace('-', ' ')}",
                            f"turismo en {pillar.lower()} 2026",
                            f"guia de viaje {title.lower()}"
                        ]

                        hero_img = FALLBACK_IMAGES[img_idx % len(FALLBACK_IMAGES)]
                        img_idx += 1

                        post_obj = {
                            "id": int(pid),
                            "title": title,
                            "slug": f"ecuador/{slug}",
                            "pillar_keyword": pillar,
                            "long_tail_keywords": long_tail,
                            "meta_title": f"{title} — Guía de Turismo Ecuador Life",
                            "meta_description": f"Conoce todo sobre {title}. Lugares turísticos, rutas recomendadas, gastronomía y consejos de viaje en Ecuador.",
                            "hero_image": hero_img,
                            "hero_alt": f"Turismo en {title} - Paisajes de Ecuador",
                            "content_markdown": markdown,
                            "status": "published",
                            "created_at": post_date if post_date and post_date != '0000-00-00 00:00:00' else datetime.utcnow().isoformat()
                        }
                        posts.append(post_obj)
                        print(f"Extracted: {title} -> ecuador/{slug}")
                        if len(posts) >= limit:
                            break

    return posts

if __name__ == '__main__':
    extracted = extract_ecuador_posts(12)
    os.makedirs(os.path.dirname(TARGET_POSTS_JSON), exist_ok=True)
    with open(TARGET_POSTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Successfully saved {len(extracted)} Ecuador Life posts to {TARGET_POSTS_JSON}")
