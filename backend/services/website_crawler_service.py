"""
Website Crawler & Auto-Sync RAG Service
Crawls multi-page websites, extracts clean content, chunks and vectorizes into Pinecone,
and automatically synchronizes vector embeddings when website content is updated.
"""
import os
import re
import time
import hashlib
import logging
from datetime import datetime
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Tuple

import requests
from bs4 import BeautifulSoup
import html2text

from extensions import db
from models.document import Document, DocumentType, DocumentStatus
from models.company import Company
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; AikrofyRAGCrawlingBot/2.0; +https://aikrofy.com)"
REQUEST_TIMEOUT = 12  # seconds per page


class WebsiteCrawlerService:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False

    @staticmethod
    def normalize_url(url: str) -> str:
        """Strip anchors and trailing slashes for canonical comparison."""
        parsed = urlparse(url)
        # remove fragments like #section
        clean_path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        return f"{parsed.scheme}://{parsed.netloc}{clean_path}"

    @classmethod
    def fetch_sitemap_urls(cls, base_url: str) -> List[str]:
        """Attempt to extract canonical URLs from /sitemap.xml or robots.txt"""
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        sitemap_candidates = [
            f"{domain}/sitemap.xml",
            f"{domain}/sitemap_index.xml",
            f"{domain}/sitemap-pages.xml"
        ]
        
        headers = {'User-Agent': USER_AGENT}
        discovered_urls = []
        
        for sm_url in sitemap_candidates:
            try:
                resp = requests.get(sm_url, headers=headers, timeout=6)
                if resp.status_code == 200 and ('xml' in resp.headers.get('Content-Type', '') or '<urlset' in resp.text or '<sitemapindex' in resp.text):
                    soup = BeautifulSoup(resp.content, 'xml')
                    locs = soup.find_all('loc')
                    for loc in locs:
                        loc_text = loc.get_text().strip()
                        if cls.is_valid_url(loc_text) and parsed.netloc in loc_text:
                            discovered_urls.append(cls.normalize_url(loc_text))
                    if discovered_urls:
                        logger.info(f"Discovered {len(discovered_urls)} URLs from sitemap: {sm_url}")
                        break
            except Exception as e:
                logger.debug(f"Sitemap check failed for {sm_url}: {e}")
                
        return list(dict.fromkeys(discovered_urls))

    @classmethod
    def clean_html_to_markdown(cls, html_content: str, page_url: str) -> Tuple[str, str, str]:
        """
        Parses raw HTML, removes boilerplates (navs, footers, modals, ads),
        and converts main article text to structured markdown.
        Returns (title, meta_description, clean_markdown).
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Extract Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text().strip()
        else:
            title = page_url
            
        # 2. Extract Meta Description
        meta_desc = ""
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag and desc_tag.get('content'):
            meta_desc = desc_tag['content'].strip()

        # 3. Strip non-content and noisy elements
        for tag in soup(['script', 'style', 'noscript', 'svg', 'canvas', 'form', 'iframe', 'nav', 'footer', 'header']):
            tag.decompose()
            
        # Remove cookie banners, popups, and typical noise
        for noise in soup.find_all(attrs={'class': re.compile(r'(cookie|banner|modal|popup|advertisement|widget)', re.I)}):
            noise.decompose()

        # Select main body content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', id=re.compile(r'(content|main|app)', re.I)) or soup.body or soup

        # Convert to Clean Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # No hard wrapping
        
        markdown_text = h.handle(str(main_content)).strip()
        
        # Clean extra newlines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        return title, meta_desc, markdown_text

    @classmethod
    def crawl_website(
        cls,
        root_url: str,
        max_pages: int = 25,
        deep_crawl: bool = True
    ) -> List[Dict]:
        """
        Recursively crawls a website up to max_pages within the same domain.
        Returns list of scraped page dicts: [{url, title, description, content, hash, content_length}]
        """
        if not cls.is_valid_url(root_url):
            raise ValueError(f"Invalid URL: {root_url}")

        parsed_root = urlparse(root_url)
        allowed_netloc = parsed_root.netloc.lower()
        
        normalized_root = cls.normalize_url(root_url)
        queue: List[str] = [normalized_root]
        visited: Set[str] = set()
        pages_scraped: List[Dict] = []
        
        # Check sitemap first if deep crawl enabled
        if deep_crawl:
            sitemap_urls = cls.fetch_sitemap_urls(root_url)
            for sm_u in sitemap_urls:
                if sm_u not in queue and len(queue) < max_pages * 2:
                    queue.append(sm_u)
                    
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8,pt;q=0.7'
        }

        while queue and len(pages_scraped) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
                
            visited.add(current_url)
            logger.info(f"[Crawler] Scraping: {current_url} ({len(pages_scraped) + 1}/{max_pages})")
            
            try:
                resp = requests.get(current_url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                if resp.status_code != 200:
                    logger.warning(f"[Crawler] Skipping {current_url} (HTTP {resp.status_code})")
                    continue
                    
                content_type = resp.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    continue
                    
                title, description, markdown = cls.clean_html_to_markdown(resp.text, current_url)
                
                # Verify content is substantial
                if len(markdown.strip()) < 80:
                    logger.debug(f"[Crawler] Content too sparse for {current_url}")
                    continue
                    
                content_hash = hashlib.sha256(markdown.encode('utf-8')).hexdigest()
                
                pages_scraped.append({
                    'url': current_url,
                    'title': title,
                    'description': description,
                    'content': markdown,
                    'hash': content_hash,
                    'content_length': len(markdown),
                    'scraped_at': datetime.utcnow().isoformat()
                })
                
                # Extract internal links if deep crawling
                if deep_crawl and len(pages_scraped) < max_pages:
                    soup = BeautifulSoup(resp.content, 'lxml')
                    for a in soup.find_all('a', href=True):
                        href = a['href'].strip()
                        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
                            continue
                        absolute_url = cls.normalize_url(urljoin(current_url, href))
                        parsed_link = urlparse(absolute_url)
                        
                        # Only follow links on the exact same root domain and without file downloads
                        if parsed_link.netloc.lower() == allowed_netloc:
                            path_lower = parsed_link.path.lower()
                            if not any(path_lower.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.exe', '.mp3', '.mp4', '.svg']):
                                if absolute_url not in visited and absolute_url not in queue:
                                    queue.append(absolute_url)
                                    
                time.sleep(0.15)  # Polite crawling delay
                
            except Exception as e:
                logger.error(f"[Crawler] Error scraping {current_url}: {e}")
                
        return pages_scraped

    @classmethod
    def index_website_document(
        cls,
        document_id: int,
        company_id: Optional[int],
        max_pages: int = 25,
        deep_crawl: bool = True,
        auto_sync: bool = True
    ) -> bool:
        """
        Performs full crawl of a website document and vectors all pages to Pinecone.
        """
        db.session.rollback()
        document = Document.query.get(document_id)
        if not document:
            logger.error(f"Document #{document_id} not found.")
            return False
            
        try:
            document.status = DocumentStatus.PROCESSING
            db.session.commit()
            
            root_url = document.original_filename
            company = Company.query.get(company_id) if company_id else None
            rag_service = RAGService(company)
            
            # Crawl website
            pages = cls.crawl_website(root_url, max_pages=max_pages, deep_crawl=deep_crawl)
            
            if not pages:
                document.status = DocumentStatus.ERROR
                document.error_message = f"No se pudo extraer contenido legible del sitio web {root_url}."
                db.session.commit()
                return False
                
            all_vector_ids = []
            page_records = {}
            total_text_length = 0
            
            # Vectorize each page individually with rich metadata
            for idx, page in enumerate(pages):
                page_meta = {
                    'title': page['title'],
                    'source_url': page['url'],
                    'root_url': root_url,
                    'document_id': document.id,
                    'filename': page['url'],
                    'file_type': 'url'
                }
                if document.department_id:
                    page_meta['department_id'] = document.department_id
                    
                # Format page content header for enhanced context
                page_doc_text = f"# {page['title']}\n**URL:** {page['url']}\n\n{page['content']}"
                total_text_length += len(page_doc_text)
                
                vector_ids = rag_service.index_document(
                    document_id=document.id,
                    content=page_doc_text,
                    metadata=page_meta
                )
                
                all_vector_ids.extend(vector_ids)
                page_records[page['url']] = {
                    'title': page['title'],
                    'hash': page['hash'],
                    'chunk_count': len(vector_ids),
                    'vector_ids': vector_ids,
                    'scraped_at': page['scraped_at']
                }
                
            document.pinecone_ids = all_vector_ids
            document.chunk_count = len(all_vector_ids)
            document.file_size = total_text_length
            document.status = DocumentStatus.INDEXED
            document.processed_at = datetime.utcnow()
            document.error_message = None
            document.doc_metadata = {
                'crawl_url': root_url,
                'pages_indexed': len(pages),
                'max_pages': max_pages,
                'deep_crawl': deep_crawl,
                'auto_sync': auto_sync,
                'last_synced_at': datetime.utcnow().isoformat(),
                'pages': page_records
            }
            db.session.commit()
            
            logger.info(f"✓ Website #{document_id} ({root_url}) indexed successfully: {len(pages)} pages, {len(all_vector_ids)} chunks.")
            return True
            
        except Exception as e:
            logger.error(f"Failed indexing website #{document_id}: {e}", exc_info=True)
            try:
                document.status = DocumentStatus.ERROR
                document.error_message = str(e)[:400]
                db.session.commit()
            except Exception:
                pass
            return False

    @classmethod
    def sync_website_document(cls, document_id: int) -> Dict:
        """
        Re-crawls website, detects updated, added, or deleted pages,
        and dynamically synchronizes vector embeddings in Pinecone.
        """
        db.session.rollback()
        document = Document.query.get(document_id)
        if not document or document.file_type != DocumentType.URL:
            return {'status': 'error', 'message': 'Document not found or is not a website URL'}
            
        meta = document.doc_metadata or {}
        root_url = meta.get('crawl_url', document.original_filename)
        max_pages = meta.get('max_pages', 25)
        deep_crawl = meta.get('deep_crawl', True)
        old_pages = meta.get('pages', {})
        
        company = document.company
        rag_service = RAGService(company)
        
        logger.info(f"[Auto-Sync] Re-checking website #{document_id} ({root_url})...")
        
        try:
            fresh_pages = cls.crawl_website(root_url, max_pages=max_pages, deep_crawl=deep_crawl)
            if not fresh_pages:
                return {'status': 'skipped', 'message': 'Could not reach website during sync'}
                
            fresh_urls_map = {p['url']: p for p in fresh_pages}
            
            updated_pages = []
            added_pages = []
            unchanged_pages = []
            deleted_urls = []
            
            new_page_records = {}
            active_pinecone_ids = []
            
            # 1. Process Fresh Pages (Added, Modified, or Unchanged)
            for url, fresh_page in fresh_urls_map.items():
                old_record = old_pages.get(url)
                
                if not old_record:
                    # Brand New Page
                    logger.info(f"[Auto-Sync] Found new page: {url}")
                    page_meta = {
                        'title': fresh_page['title'],
                        'source_url': url,
                        'root_url': root_url,
                        'document_id': document.id,
                        'filename': url,
                        'file_type': 'url'
                    }
                    if document.department_id:
                        page_meta['department_id'] = document.department_id
                        
                    content_text = f"# {fresh_page['title']}\n**URL:** {url}\n\n{fresh_page['content']}"
                    vector_ids = rag_service.index_document(document.id, content_text, page_meta)
                    
                    new_page_records[url] = {
                        'title': fresh_page['title'],
                        'hash': fresh_page['hash'],
                        'chunk_count': len(vector_ids),
                        'vector_ids': vector_ids,
                        'scraped_at': fresh_page['scraped_at']
                    }
                    active_pinecone_ids.extend(vector_ids)
                    added_pages.append(url)
                    
                elif old_record.get('hash') != fresh_page['hash']:
                    # Modified Page -> Delete old vectors and re-index fresh content
                    logger.info(f"[Auto-Sync] Page modified: {url}. Updating embeddings...")
                    old_vector_ids = old_record.get('vector_ids', [])
                    if old_vector_ids and rag_service._get_index():
                        try:
                            rag_service._get_index().delete(ids=old_vector_ids, namespace=rag_service._get_namespace(document.department_id))
                        except Exception as de:
                            logger.warning(f"Could not delete old vectors for {url}: {de}")
                            
                    page_meta = {
                        'title': fresh_page['title'],
                        'source_url': url,
                        'root_url': root_url,
                        'document_id': document.id,
                        'filename': url,
                        'file_type': 'url'
                    }
                    if document.department_id:
                        page_meta['department_id'] = document.department_id
                        
                    content_text = f"# {fresh_page['title']}\n**URL:** {url}\n\n{fresh_page['content']}"
                    vector_ids = rag_service.index_document(document.id, content_text, page_meta)
                    
                    new_page_records[url] = {
                        'title': fresh_page['title'],
                        'hash': fresh_page['hash'],
                        'chunk_count': len(vector_ids),
                        'vector_ids': vector_ids,
                        'scraped_at': fresh_page['scraped_at']
                    }
                    active_pinecone_ids.extend(vector_ids)
                    updated_pages.append(url)
                    
                else:
                    # Unchanged Page -> Keep existing vectors, 0 token cost!
                    new_page_records[url] = old_record
                    active_pinecone_ids.extend(old_record.get('vector_ids', []))
                    unchanged_pages.append(url)
                    
            # 2. Process Deleted Pages
            for old_url, old_record in old_pages.items():
                if old_url not in fresh_urls_map:
                    logger.info(f"[Auto-Sync] Page removed from site: {old_url}")
                    old_vector_ids = old_record.get('vector_ids', [])
                    if old_vector_ids and rag_service._get_index():
                        try:
                            rag_service._get_index().delete(ids=old_vector_ids, namespace=rag_service._get_namespace(document.department_id))
                        except Exception:
                            pass
                    deleted_urls.append(old_url)
                    
            # Update Document state
            document.pinecone_ids = active_pinecone_ids
            document.chunk_count = len(active_pinecone_ids)
            document.processed_at = datetime.utcnow()
            document.doc_metadata = {
                **meta,
                'pages_indexed': len(new_page_records),
                'last_synced_at': datetime.utcnow().isoformat(),
                'pages': new_page_records,
                'last_sync_stats': {
                    'updated': len(updated_pages),
                    'added': len(added_pages),
                    'unchanged': len(unchanged_pages),
                    'deleted': len(deleted_urls)
                }
            }
            db.session.commit()
            
            result_summary = {
                'status': 'synced',
                'pages_total': len(new_page_records),
                'updated_pages': len(updated_pages),
                'added_pages': len(added_pages),
                'unchanged_pages': len(unchanged_pages),
                'deleted_pages': len(deleted_urls)
            }
            logger.info(f"[Auto-Sync] Completed for #{document_id}: {result_summary}")
            return result_summary
            
        except Exception as e:
            logger.error(f"[Auto-Sync] Error syncing website #{document_id}: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    @classmethod
    def sync_all_active_websites(cls) -> Dict:
        """
        Cron/worker task: Finds all URL documents with auto_sync=True and runs selective sync.
        """
        db.session.rollback()
        url_docs = Document.query.filter_by(file_type=DocumentType.URL, status=DocumentStatus.INDEXED).all()
        results = []
        for doc in url_docs:
            meta = doc.doc_metadata or {}
            if meta.get('auto_sync', True):
                res = cls.sync_website_document(doc.id)
                results.append({'document_id': doc.id, 'url': doc.original_filename, 'result': res})
        return {'total_checked': len(url_docs), 'sync_results': results}
