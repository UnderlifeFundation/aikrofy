import os
import requests

def generate_code(prompt: str) -> str:
    """
    Genera código usando el API de OpenRouter
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "https://screenshot-to-code.app",  # Tu dominio
                "X-Title": "Screenshot to Code App"
            },
            json={
                "model": "openrouter/meta-llama:llama-3-70b-instruct-nitro",  # Modelo predefinido
                "messages": [
                    {"role": "system", "content": "Tu rol es convertir pantallazos en código limpio y estructurado."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 32768
            }
        )
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        print(f"🚨 Error en OpenRouter: {str(e)}")
        return "Error al generar código con OpenRouter"