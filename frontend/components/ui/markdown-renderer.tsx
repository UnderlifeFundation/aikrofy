'use client';

import React, { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

// Configure marked options once for speed
marked.setOptions({
    gfm: true,
    breaks: true
});

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
    const sanitizedHtml = useMemo(() => {
        if (!content) return '';
        try {
            // Parse Markdown to HTML
            const rawHtml = marked.parse(content) as string;
            // Sanitize HTML to prevent XSS
            return DOMPurify.sanitize(rawHtml, {
                ADD_ATTR: ['target', 'rel'], // Allow safe links attributes
                FORCE_BODY: true
            });
        } catch (e) {
            console.error('Error parsing markdown:', e);
            return content;
        }
    }, [content]);

    return (
        <div
            className={`prose dark:prose-invert max-w-none break-words leading-relaxed
                prose-p:leading-relaxed prose-p:my-1
                prose-headings:font-semibold prose-headings:leading-tight
                prose-h1:text-sm prose-h2:text-sm prose-h3:text-xs prose-h4:text-xs
                prose-h1:mt-2 prose-h2:mt-2 prose-h3:mt-1.5 prose-h4:mt-1
                prose-strong:font-semibold
                prose-pre:bg-muted prose-pre:text-foreground prose-pre:p-3 prose-pre:rounded-lg prose-pre:text-xs
                prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
                prose-ul:list-disc prose-ol:list-decimal prose-li:my-0.5 prose-li:text-xs
                prose-a:text-primary prose-a:underline
                prose-blockquote:border-l-2 prose-blockquote:border-border prose-blockquote:pl-3 prose-blockquote:italic
                prose-table:w-full prose-table:my-4 prose-table:border-collapse prose-table:border prose-table:border-border prose-table:rounded-xl prose-table:overflow-hidden prose-table:shadow-xs prose-table:text-xs
                prose-thead:bg-muted/60 prose-thead:border-b prose-thead:border-border
                prose-th:px-3.5 prose-th:py-2.5 prose-th:text-left prose-th:font-semibold prose-th:text-foreground prose-th:text-xs prose-th:border-r prose-th:border-border/50 last:prose-th:border-r-0
                prose-tbody:divide-y prose-tbody:divide-border/40
                prose-tr:hover:bg-muted/30 prose-tr:transition-colors
                prose-td:px-3.5 prose-td:py-2 prose-td:text-xs prose-td:text-muted-foreground prose-td:border-r prose-td:border-border/40 last:prose-td:border-r-0
                ${className}`}
            dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
    );
}
