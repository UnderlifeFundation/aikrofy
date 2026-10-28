"""
Landing Generation Service — AI-Powered HTML Generation
Bridges the main Aikrofy backend with the screenshot-to-code microservice.
Supports: text prompts, screenshot URLs, Figma URLs.
Default model: gpt-5-nano (gpt-4.1-nano-2025-04-14)
Enterprise: supports any OpenAI-compatible model with BYO API key.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import os
import logging
import asyncio
import base64
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Default platform model mapping
# 'gpt-5-nano' is our internal alias for gpt-4.1-nano-2025-04-14 (fast + cost-effective)
PLATFORM_DEFAULT_MODEL = 'gpt-4.1-nano-2025-04-14'
PLATFORM_DEFAULT_PROVIDER = 'openai'

# Model alias resolution
MODEL_ALIASES = {
    'gpt-5-nano': 'gpt-4.1-nano-2025-04-14',
    'gpt-4.1-nano': 'gpt-4.1-nano-2025-04-14',
    'gpt-4o-mini': 'gpt-4o-mini',
    'claude-haiku': 'claude-3-haiku-20240307',
    'claude-sonnet': 'claude-sonnet-4-20250514',
    'gemini-flash': 'gemini-2.0-flash',
}

# Landing page system prompt (business-focused HTML generation)
LANDING_PAGE_SYSTEM_PROMPT = """You are an expert landing page designer and developer. Your task is to generate stunning, conversion-optimized, fully responsive HTML landing pages.

Guidelines:
- Output ONLY complete, self-contained HTML (no markdown, no backticks, no explanation)
- Use Tailwind CSS CDN for styling (include the CDN script in <head>)
- Make the design premium: dark/glassmorphism or vibrant gradients depending on the brand
- Use semantic HTML5 elements
- Include proper meta tags for SEO
- Make it fully responsive (mobile-first)
- Add smooth CSS animations and hover effects
- Include CTA buttons with data-cta attributes for tracking (e.g. data-cta="main-cta")
- Forms should have proper names for tracking (email, phone, name fields)
- Include sections: hero, features/benefits, social proof/testimonials, pricing (if applicable), CTA, footer
- Use web-safe Google Fonts (Outfit, Inter, or similar premium fonts via Google Fonts CDN)
- Optimize for conversion: clear value proposition, strong CTA, trust signals
- All images should use realistic Unsplash URLs (https://images.unsplash.com/photo-...?w=1200&auto=format)
- Include JavaScript only for micro-interactions (no frameworks)
- The aikrofy-tracker.js will be injected automatically — do NOT include tracking code

Output format: Pure HTML document starting with <!DOCTYPE html>"""


class LandingGenerationService:
    """Service for AI-powered landing page generation."""

    @staticmethod
    def resolve_model(llm_model: str, llm_config: Dict[str, Any]) -> tuple[str, str, Optional[str], Optional[str]]:
        """
        Resolve the actual model name, provider, API key, and base URL.
        Returns: (model_name, provider, api_key, base_url)
        """
        # Resolve alias
        actual_model = MODEL_ALIASES.get(llm_model, llm_model)
        
        # Get platform API key from env
        platform_openai_key = os.environ.get('OPENAI_API_KEY')
        platform_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        platform_gemini_key = os.environ.get('GEMINI_API_KEY')
        
        # Enterprise BYO config override
        enterprise_api_key = llm_config.get('api_key')
        enterprise_base_url = llm_config.get('base_url')
        enterprise_provider = llm_config.get('provider', '').lower()
        
        # Determine provider from model name
        if enterprise_provider:
            provider = enterprise_provider
        elif 'claude' in actual_model or 'anthropic' in actual_model:
            provider = 'anthropic'
        elif 'gemini' in actual_model:
            provider = 'gemini'
        else:
            provider = 'openai'
        
        # Resolve API key (Enterprise override > Platform key)
        if enterprise_api_key:
            api_key = enterprise_api_key
        elif provider == 'anthropic':
            api_key = platform_anthropic_key
        elif provider == 'gemini':
            api_key = platform_gemini_key
        else:
            api_key = platform_openai_key
        
        base_url = enterprise_base_url or None
        
        return actual_model, provider, api_key, base_url

    @staticmethod
    def build_messages_from_text(prompt: str) -> list:
        """Build OpenAI-compatible messages for text-only generation."""
        user_content = f"""Create a professional, high-converting landing page for:

{prompt}

Make it visually stunning with modern design principles. Output only the HTML."""
        return [
            {'role': 'system', 'content': LANDING_PAGE_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_content},
        ]

    @staticmethod
    def build_messages_from_screenshot(prompt: str, image_b64: str) -> list:
        """Build messages for screenshot/image-based generation."""
        user_content = [
            {
                'type': 'image_url',
                'image_url': {'url': f'data:image/jpeg;base64,{image_b64}', 'detail': 'high'},
            },
            {
                'type': 'text',
                'text': f'Recreate this landing page design as a fully responsive, production-ready HTML page.{" " + prompt if prompt else ""}',
            },
        ]
        return [
            {'role': 'system', 'content': LANDING_PAGE_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_content},
        ]

    @staticmethod
    def build_update_messages(prompt: str, current_html: str) -> list:
        """Build messages for updating an existing landing page."""
        user_content = f"""Here is the current landing page HTML:

<current_html>
{current_html[:8000]}
</current_html>

Apply the following changes while preserving the overall design and structure:
{prompt}

Output the complete updated HTML document."""
        return [
            {'role': 'system', 'content': LANDING_PAGE_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_content},
        ]

    @staticmethod
    async def call_openai(messages: list, model: str, api_key: str, base_url: Optional[str] = None) -> str:
        """Call OpenAI-compatible API for HTML generation."""
        import openai
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or 'https://api.openai.com/v1',
        )
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=8192,
            temperature=0.7,
        )
        return response.choices[0].message.content or ''

    @staticmethod
    async def call_anthropic(messages: list, model: str, api_key: str) -> str:
        """Call Anthropic Claude API for HTML generation."""
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        # Extract system from messages
        system = next((m['content'] for m in messages if m['role'] == 'system'), '')
        user_messages = [m for m in messages if m['role'] != 'system']
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system,
            messages=user_messages,
        )
        return response.content[0].text if response.content else ''

    @staticmethod
    async def call_gemini(messages: list, model: str, api_key: str) -> str:
        """Call Google Gemini API for HTML generation via OpenAI-compatible endpoint."""
        import openai
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
        )
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=8192,
        )
        return response.choices[0].message.content or ''

    @classmethod
    async def generate(
        cls,
        prompt: str,
        generation_type: str = 'create',
        screenshot_url: Optional[str] = None,
        figma_url: Optional[str] = None,
        current_html: Optional[str] = None,
        llm_model: str = 'gpt-5-nano',
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Main generation method. Returns complete HTML string.
        Raises Exception on failure.
        """
        if llm_config is None:
            llm_config = {}
        
        actual_model, provider, api_key, base_url = cls.resolve_model(llm_model, llm_config)
        
        if not api_key:
            raise ValueError(f'No API key found for provider: {provider}. Configure your API keys in the backend .env file.')
        
        # Build messages based on input type
        if generation_type == 'update' and current_html:
            messages = cls.build_update_messages(prompt, current_html)
        elif screenshot_url and generation_type == 'create':
            # Download and encode the screenshot image
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(screenshot_url)
                    resp.raise_for_status()
                    image_b64 = base64.b64encode(resp.content).decode()
                messages = cls.build_messages_from_screenshot(prompt, image_b64)
            except Exception as e:
                logger.warning(f'Failed to download screenshot {screenshot_url}: {e}. Falling back to text-only.')
                messages = cls.build_messages_from_text(prompt or 'Professional landing page')
        else:
            messages = cls.build_messages_from_text(prompt or 'Professional landing page')
        
        # Call appropriate provider
        if provider == 'anthropic':
            html = await cls.call_anthropic(messages, actual_model, api_key)
        elif provider == 'gemini':
            html = await cls.call_gemini(messages, actual_model, api_key)
        else:  # default: openai
            html = await cls.call_openai(messages, actual_model, api_key, base_url)
        
        # Extract and clean HTML
        html = cls.extract_html(html)
        return html

    @staticmethod
    def extract_html(raw: str) -> str:
        """Extract clean HTML from LLM response (handles markdown code blocks)."""
        if not raw:
            return '<!DOCTYPE html><html><body><p>Generation failed.</p></body></html>'
        
        # Remove markdown code blocks if present
        if '```html' in raw:
            start = raw.find('```html') + 7
            end = raw.rfind('```')
            if end > start:
                raw = raw[start:end].strip()
        elif '```' in raw:
            start = raw.find('```') + 3
            end = raw.rfind('```')
            if end > start:
                raw = raw[start:end].strip()
        
        # Ensure proper DOCTYPE
        if '<!DOCTYPE html>' not in raw and '<html' not in raw:
            raw = f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body>{raw}</body></html>'
        
        return raw.strip()


def generate_landing_page_sync(
    prompt: str,
    generation_type: str = 'create',
    screenshot_url: Optional[str] = None,
    figma_url: Optional[str] = None,
    current_html: Optional[str] = None,
    llm_model: str = 'gpt-5-nano',
    llm_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Synchronous wrapper for use in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            LandingGenerationService.generate(
                prompt=prompt,
                generation_type=generation_type,
                screenshot_url=screenshot_url,
                figma_url=figma_url,
                current_html=current_html,
                llm_model=llm_model,
                llm_config=llm_config or {},
            )
        )
    finally:
        loop.close()
