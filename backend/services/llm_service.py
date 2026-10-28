from routing import current_app
"""
LLM Service - Multi-provider LLM integration
"""
import os
from typing import Optional, List, Dict, Any



class LLMService:
    """Multi-provider LLM service"""
    
    PROVIDERS = {
        'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo', 'gpt-5-nano'],
        'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022'],
        'google': ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
        'groq': ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
        'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
        'openrouter': ['openai/gpt-4o-mini', 'anthropic/claude-3.5-sonnet', 'google/gemini-flash-1.5']
    }
    
    def __init__(self, company=None):
        self.company = company
        self._clients = {}
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        # First check company-specific keys
        if self.company and self.company.api_keys:
            key = self.company.api_keys.get(provider)
            if key:
                return key
        
        # Fall back to environment variables
        env_keys = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_AI_API_KEY',
            'groq': 'GROQ_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY'
        }
        return os.getenv(env_keys.get(provider, ''))

    def _get_openai_compatible_client(self, provider: str, base_url: str):
        """Get or create OpenAI-compatible client (Groq, DeepSeek, OpenRouter)"""
        if provider not in self._clients:
            try:
                from openai import OpenAI
                api_key = self._get_api_key(provider)
                if api_key:
                    self._clients[provider] = OpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                pass
        return self._clients.get(provider)
    
    def _get_openai_client(self):
        """Get or create OpenAI client"""
        if 'openai' not in self._clients:
            try:
                from openai import OpenAI
                api_key = self._get_api_key('openai')
                if api_key:
                    self._clients['openai'] = OpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get('openai')
    
    def _get_anthropic_client(self):
        """Get or create Anthropic client"""
        if 'anthropic' not in self._clients:
            try:
                import anthropic
                api_key = self._get_api_key('anthropic')
                if api_key:
                    self._clients['anthropic'] = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get('anthropic')
    
    def _get_google_client(self):
        """Get or create Google AI client"""
        if 'google' not in self._clients:
            try:
                import google.generativeai as genai
                api_key = self._get_api_key('google')
                if api_key:
                    genai.configure(api_key=api_key)
                    self._clients['google'] = genai
            except ImportError:
                pass
        return self._clients.get('google')
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send chat completion request to LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            provider: LLM provider (openai, anthropic, google)
            model: Model name
            temperature: Response temperature
            max_tokens: Maximum tokens in response
            tools: Optional list of tools for function calling
        
        Returns:
            Dict with 'content', 'tool_calls', 'usage', etc.
        """
        # Default provider/model from company or config
        if not provider:
            provider = (self.company.llm_provider if self.company 
                       else current_app.config.get('DEFAULT_LLM_PROVIDER', 'openai'))
        if not model:
            model = (self.company.llm_model if self.company 
                    else current_app.config.get('DEFAULT_LLM_MODEL', 'gpt-5-nano'))
        
        # Add system prompt if provided
        if system_prompt:
            messages = [{'role': 'system', 'content': system_prompt}] + messages
        
        # Route to appropriate provider
        if provider == 'openai':
            return self._openai_chat(messages, model, temperature, max_tokens, tools)
        elif provider == 'groq':
            return self._openai_chat(messages, model or 'llama-3.3-70b-versatile', temperature, max_tokens, tools, client_override=self._get_openai_compatible_client('groq', 'https://api.groq.com/openai/v1'))
        elif provider == 'deepseek':
            return self._openai_chat(messages, model or 'deepseek-chat', temperature, max_tokens, tools, client_override=self._get_openai_compatible_client('deepseek', 'https://api.deepseek.com/v1'))
        elif provider == 'openrouter':
            return self._openai_chat(messages, model or 'openai/gpt-4o-mini', temperature, max_tokens, tools, client_override=self._get_openai_compatible_client('openrouter', 'https://openrouter.ai/api/v1'))
        elif provider == 'anthropic':
            return self._anthropic_chat(messages, model, temperature, max_tokens, tools)
        elif provider == 'google':
            return self._google_chat(messages, model, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _openai_chat(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]] = None,
        client_override = None
    ) -> Dict[str, Any]:
        """OpenAI / OpenAI-compatible chat completion"""
        client = client_override or self._get_openai_client()
        if not client:
            raise ValueError("LLM client not configured (missing API key)")
            
        kwargs = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        if tools:
            kwargs['tools'] = tools
            kwargs['tool_choice'] = 'auto'
        
        response = client.chat.completions.create(**kwargs)
        
        result = {
            'content': response.choices[0].message.content,
            'tool_calls': [],
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            },
            'model': response.model
        }
        
        # Process tool calls if present
        if response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                result['tool_calls'].append({
                    'id': tc.id,
                    'name': tc.function.name,
                    'arguments': tc.function.arguments
                })
        
        return result
    
    def _anthropic_chat(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Anthropic chat completion"""
        client = self._get_anthropic_client()
        if not client:
            raise ValueError("Anthropic client not configured")
        
        # Extract system message
        system = ""
        filtered_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                filtered_messages.append(msg)
        
        kwargs = {
            'model': model,
            'messages': filtered_messages,
            'max_tokens': max_tokens
        }
        
        if system:
            kwargs['system'] = system
        
        if tools:
            kwargs['tools'] = self._convert_tools_to_anthropic(tools)
        
        response = client.messages.create(**kwargs)
        
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == 'text':
                content = block.text
            elif block.type == 'tool_use':
                tool_calls.append({
                    'id': block.id,
                    'name': block.name,
                    'arguments': block.input
                })
        
        return {
            'content': content,
            'tool_calls': tool_calls,
            'usage': {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            },
            'model': response.model
        }
    
    def _google_chat(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Google AI chat completion"""
        genai = self._get_google_client()
        if not genai:
            raise ValueError("Google AI client not configured")
        
        # Create model
        generation_config = {
            'temperature': temperature,
            'max_output_tokens': max_tokens
        }
        
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config
        )
        
        # Convert messages to Google format
        chat = model_instance.start_chat(history=[])
        
        # Process system message
        system_instruction = ""
        for msg in messages:
            if msg['role'] == 'system':
                system_instruction = msg['content']
                break
        
        # Send messages
        last_response = None
        for msg in messages:
            if msg['role'] == 'user':
                content = msg['content']
                if system_instruction and messages.index(msg) == next(
                    i for i, m in enumerate(messages) if m['role'] == 'user'
                ):
                    content = f"{system_instruction}\n\n{content}"
                last_response = chat.send_message(content)
        
        if not last_response:
            raise ValueError("No response from Google AI")
        
        return {
            'content': last_response.text,
            'tool_calls': [],
            'usage': {},
            'model': model
        }
    
    def _convert_tools_to_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-style tools to Anthropic format"""
        anthropic_tools = []
        for tool in tools:
            if tool.get('type') == 'function':
                func = tool['function']
                anthropic_tools.append({
                    'name': func['name'],
                    'description': func.get('description', ''),
                    'input_schema': func.get('parameters', {})
                })
        return anthropic_tools
    
    def get_embeddings(
        self,
        texts: List[str],
        model: str = 'text-embedding-3-small'
    ) -> List[List[float]]:
        """Get embeddings for texts using OpenAI"""
        client = self._get_openai_client()
        if not client:
            raise ValueError("OpenAI client not configured for embeddings")
        
        response = client.embeddings.create(
            model=model,
            input=texts
        )
        
        return [item.embedding for item in response.data]
