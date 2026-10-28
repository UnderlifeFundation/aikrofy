import os
import asyncio
import logging
import subprocess
import requests
import base64
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

class VoiceService:
    @classmethod
    def _normalize_audio(cls, audio_path: str) -> tuple[str, bool]:
        """
        Normalizes input audio to 16kHz mono MP3 using ffmpeg to guarantee compatibility
        with Whisper across all browser codecs (WebM, Opus, Ogg, Safari AAC/M4A).
        Returns (target_path, is_temporary).
        """
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            return audio_path, False

        normalized_path = f"{os.path.splitext(audio_path)[0]}_norm.mp3"
        try:
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-vn", "-ar", "16000", "-ac", "1",
                "-c:a", "libmp3lame", "-b:a", "64k",
                normalized_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                logger.info(f"Audio normalized successfully with ffmpeg: {normalized_path} ({os.path.getsize(normalized_path)} bytes)")
                return normalized_path, True
            else:
                logger.warning(f"ffmpeg normalization warning (code {res.returncode}): {res.stderr[:200] if res.stderr else 'none'}")
        except Exception as e:
            logger.warning(f"Failed to normalize audio with ffmpeg: {e}")

        return audio_path, False

    @classmethod
    def transcribe(cls, audio_path: str, language: str = None) -> str:
        """
        Transcribes audio to text using a cascading model:
        0. Remote media.weblifetech.com micro-service API (Dedicated FFmpeg + Whisper engine, zero local CPU load)
        1. Groq Whisper (whisper-large-v3)
        2. OpenRouter Whisper (openai/whisper-1)
        3. OpenAI Whisper (whisper-1)
        """
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            logger.error(f"Audio file not found or empty for transcription: {audio_path}")
            return ""

        # Normalize language code to 2-letter ISO (e.g., 'es-MX' -> 'es')
        lang_code = language.split('-')[0].lower() if language else None

        # Determine MIME type dynamically
        ext_lower = audio_path.rsplit('.', 1)[-1].lower() if '.' in audio_path else ''
        mime_map = {
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
            'oga': 'audio/ogg',
            'opus': 'audio/ogg',
            'm4a': 'audio/mp4',
            'mp4': 'audio/mp4',
            'aac': 'audio/aac',
            'wav': 'audio/wav',
            'flac': 'audio/flac',
            'mp3': 'audio/mpeg',
        }
        mime_type = mime_map.get(ext_lower, 'audio/mpeg')

        # -------------------------------------------------------------
        # Step 0: Remote media.weblifetech.com Microservice (Priority 1)
        # Dedicated engine with its own FFmpeg + Whisper processing
        # -------------------------------------------------------------
        external_key = os.getenv("EXTERNAL_API_KEY") or getattr(Config, "EXTERNAL_API_KEY", "")
        if external_key:
            external_key = external_key.strip("'\"")

        auth_headers = {}
        if external_key:
            auth_headers["Authorization"] = f"Bearer {external_key}"
            auth_headers["X-API-Key"] = external_key

        try:
            logger.info(f"Attempting STT with remote media.weblifetech.com micro-engine...")
            micro_url = os.getenv("MEDIA_MICRO_STT_URL") or "https://media.weblifetech.com/api/micro/audio/transcribe"
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, mime_type)}
                data = {}
                if lang_code:
                    data["language"] = lang_code
                response = requests.post(micro_url, headers=auth_headers, files=files, data=data, timeout=35)
            if response.status_code == 200:
                resp_json = response.json()
                text = resp_json.get("text", "").strip()
                if text:
                    logger.info("Remote media.weblifetech.com micro-engine transcription successful.")
                    return text
            logger.warning(f"Remote media micro-engine returned code {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Remote media micro-engine error: {str(e)}")

        # Step 0.5: Remote media.weblifetech.com External API (if key is configured)
        if external_key:
            try:
                media_stt_url = os.getenv("MEDIA_STT_URL") or "https://media.weblifetech.com/api/external/transcribe"
                logger.info(f"Attempting STT with {media_stt_url} Whisper...")
                with open(audio_path, "rb") as f:
                    files = {"file": (os.path.basename(audio_path), f, mime_type)}
                    data = {}
                    if lang_code:
                        data["language"] = lang_code
                    response = requests.post(media_stt_url, headers=auth_headers, files=files, data=data, timeout=45)
                if response.status_code == 200:
                    text = response.json().get("text", "").strip()
                    if text:
                        logger.info("Remote media external Whisper transcription successful.")
                        return text
                logger.warning(f"Remote media external Whisper failed: status={response.status_code}")
            except Exception as e:
                logger.warning(f"Remote media external Whisper error: {str(e)}")

        # Step 1: Try Groq Whisper
        groq_key = os.getenv("GROQ_API_KEY") or getattr(Config, "GROQ_API_KEY", "")
        if groq_key:
            groq_key = groq_key.strip("'\"")
            try:
                logger.info("Attempting STT with Groq Whisper...")
                url = "https://api.groq.com/openai/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {groq_key}"}
                with open(audio_path, "rb") as f:
                    files = {"file": (os.path.basename(audio_path), f, mime_type)}
                    data = {"model": "whisper-large-v3"}
                    if lang_code:
                        data["language"] = lang_code
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if response.status_code == 200:
                    text = response.json().get("text", "").strip()
                    if text:
                        logger.info("Groq Whisper transcription successful.")
                        return text
                logger.warning(f"Groq Whisper failed: status={response.status_code}, response={response.text}")
            except Exception as e:
                logger.warning(f"Groq Whisper error: {str(e)}")

        # Step 2: Try OpenRouter Whisper
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or getattr(Config, "OPENROUTER_API_KEY", "")
        if openrouter_key:
            openrouter_key = openrouter_key.strip("'\"")
            try:
                logger.info("Attempting STT with OpenRouter Whisper...")
                url = "https://openrouter.ai/api/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
                
                with open(audio_path, "rb") as f:
                    audio_base64 = base64.b64encode(f.read()).decode("utf-8")
                
                ext = audio_path.split(".")[-1].lower()
                if ext not in ["wav", "mp3", "m4a", "ogg", "flac", "webm"]:
                    ext = "mp3"
                    
                payload = {
                    "model": "openai/whisper-1",
                    "input_audio": {
                        "data": audio_base64,
                        "format": ext
                    }
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    text = response.json().get("text", "").strip()
                    if text:
                        logger.info("OpenRouter Whisper transcription successful.")
                        return text
                logger.warning(f"OpenRouter Whisper failed: status={response.status_code}, response={response.text}")
            except Exception as e:
                logger.warning(f"OpenRouter Whisper error: {str(e)}")

        # Step 3: Try OpenAI Whisper
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(Config, "OPENAI_API_KEY", "")
        if openai_key:
            openai_key = openai_key.strip("'\"")
            try:
                logger.info("Attempting STT with OpenAI Whisper...")
                client = OpenAI(api_key=openai_key)
                with open(audio_path, "rb") as audio_file:
                    kwargs = {
                        "model": "whisper-1",
                        "file": audio_file
                    }
                    if lang_code:
                        kwargs["language"] = lang_code
                    transcript = client.audio.transcriptions.create(**kwargs)
                if transcript and transcript.text:
                    logger.info("OpenAI Whisper transcription successful.")
                    return transcript.text.strip()
            except Exception as e:
                logger.error(f"OpenAI Whisper error: {str(e)}")

        logger.error("All STT transcription engines in cascade failed.")
        return ""

    @classmethod
    async def synthesize_async(cls, text: str, voice: str, output_path: str) -> bool:
        """
        Synthesizes text to speech asynchronously using the cascade.
        """
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, cls.synthesize, text, voice, output_path)
        except Exception as e:
            logger.error(f"Error in async speech synthesis: {str(e)}")
            return False

    @classmethod
    def clean_text_for_tts(cls, text: str) -> str:
        """
        Cleans text to make it more friendly for Text-to-Speech (TTS).
        - Replaces underscores with spaces.
        - Replaces slashes with ' o '.
        - Removes technical markdown characters.
        - Replaces technical terms with user-friendly versions.
        """
        import re
        if not text:
            return ""

        # 1. Replace common technical labels/slugs
        text = text.replace("core_identity", "Identidad Core")
        text = text.replace("payment_protocol", "Protocolo de Pagos")
        text = text.replace("calendar_protocol", "Protocolo de Calendario")
        text = text.replace("ecommerce_sales_protocol", "Protocolo de Ventas")
        text = text.replace("tooling-usage-guide", "Guía de uso de herramientas")

        # 2. Replace technical characters
        text = text.replace("_", " ")
        text = text.replace("/", " o ")
        
        # 3. Remove Markdown bold/italic/code marks and links
        text = re.sub(r'https?://\S+', '', text)
        text = text.replace("**", "")
        text = text.replace("__", "")
        text = text.replace("`", "")
        text = text.replace("#", "")

        # 4. Normalize ALL-CAPS words (e.g. WEBLIFETECH -> Weblifetech) so TTS pronounces them as words instead of spelling letter-by-letter
        known_acronyms = {"USA", "RUC", "PDF", "URL", "API", "DNI", "IVA", "USD", "EUR", "GPS", "CRM", "ERP", "FAQ", "SMS", "HTML", "CSS", "SQL"}
        def _normalize_caps(match):
            word = match.group(0)
            if word in known_acronyms:
                return word
            return word.capitalize()

        text = re.sub(r'\b[A-ZÁÉÍÓÚÑ]{3,}\b', _normalize_caps, text)

        # 5. Cleanup multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    @classmethod
    def synthesize(cls, text: str, voice: str, output_path: str) -> bool:
        """
        Synthesizes text to speech using a cascading model:
        0. Remote media.weblifetech.com Edge-TTS API (Free & High-performance)
        1. Groq TTS (if available)
        2. OpenRouter TTS (hexgrad/kokoro-82m)
        3. HuggingFace TTS (facebook/mms-tts-spa)
        4. OpenAI TTS (tts-1)
        """
        clean_text = cls.clean_text_for_tts(text)
        if not clean_text:
            logger.warning("Empty text passed for voice synthesis.")
            return False

        logger.info(f"Synthesizing text: '{clean_text[:40]}...' using voice: '{voice}'")

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Helper to map voice genders accurately
        voice_lower = voice.lower() if voice else ""
        female_indicators = ["female", "dalia", "elvira", "salome", "elena", "paloma", "jenny", "aria", "sonia", "francisca", "raquel", "denise", "katja", "elsa", "ramona", "bella", "sarah", "shimmer", "nova"]
        is_female = any(ind in voice_lower for ind in female_indicators)

        # Step 0: Try Local Edge-TTS (High Fidelity, Zero Latency & Always Available)
        try:
            import edge_tts
            target_edge_voice = voice if (voice and "Neural" in voice) else ("es-MX-DaliaNeural" if is_female else "es-MX-JorgeNeural")
            logger.info(f"Attempting TTS with local Edge-TTS engine ({target_edge_voice})...")
            
            async def _run_local_edge_tts():
                comm = edge_tts.Communicate(clean_text, target_edge_voice)
                await comm.save(output_path)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        pool.submit(lambda: asyncio.run(_run_local_edge_tts())).result()
                else:
                    loop.run_until_complete(_run_local_edge_tts())
            except RuntimeError:
                asyncio.run(_run_local_edge_tts())

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Local Edge-TTS synthesis ({target_edge_voice}) successful.")
                return True
        except Exception as local_edge_err:
            logger.warning(f"Local Edge-TTS fallback triggered: {local_edge_err}")

        # Step 0.5: Try Remote media.weblifetech.com Edge-TTS API
        try:
            logger.info("Attempting TTS with remote media.weblifetech.com Edge-TTS API...")
            url = os.getenv("MEDIA_TTS_URL") or "https://media.weblifetech.com/api/tts/speak"
            external_key = os.getenv("EXTERNAL_API_KEY") or getattr(Config, "EXTERNAL_API_KEY", "")
            tts_headers = {}
            if external_key:
                tts_headers["Authorization"] = f"Bearer {external_key.strip('\'\"')}"
                tts_headers["X-API-Key"] = external_key.strip("'\"")
            payload = {
                "text": clean_text,
                "voice": voice if voice else ("es-MX-DaliaNeural" if is_female else "es-MX-JorgeNeural")
            }
            response = requests.post(url, headers=tts_headers, json=payload, timeout=15)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info("media.weblifetech.com Edge-TTS synthesis successful.")
                    return True
            logger.warning(f"media.weblifetech.com Edge-TTS failed: status={response.status_code}")
        except Exception as e:
            logger.warning(f"media.weblifetech.com Edge-TTS error: {str(e)}")

        # Step 1: Try Groq TTS (if configured)
        groq_key = os.getenv("GROQ_API_KEY") or getattr(Config, "GROQ_API_KEY", "")
        if groq_key:
            groq_key = groq_key.strip("'\"")
            try:
                logger.info("Attempting TTS with Groq TTS...")
                url = "https://api.groq.com/openai/v1/audio/speech"
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "canopylabs/orpheus-v1-english",
                    "input": clean_text,
                    "voice": "nova" if is_female else "onyx"
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info("Groq TTS synthesis successful.")
                        return True
                logger.warning(f"Groq TTS failed: status={response.status_code}")
            except Exception as e:
                logger.warning(f"Groq TTS error: {str(e)}")

        # Step 2: Try OpenRouter TTS (Kokoro)
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or getattr(Config, "OPENROUTER_API_KEY", "")
        if openrouter_key:
            openrouter_key = openrouter_key.strip("'\"")
            try:
                logger.info("Attempting TTS with OpenRouter Kokoro...")
                url = "https://openrouter.ai/api/v1/audio/speech"
                headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "hexgrad/kokoro-82m",
                    "input": clean_text,
                    "voice": "af_bella" if is_female else "am_adam"
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info("OpenRouter Kokoro synthesis successful.")
                        return True
                logger.warning(f"OpenRouter Kokoro failed: status={response.status_code}, response={response.text}")
            except Exception as e:
                logger.warning(f"OpenRouter Kokoro error: {str(e)}")

        # Step 3: Try HuggingFace TTS (facebook/mms-tts-spa)
        hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or getattr(Config, "HUGGINGFACE_API_KEY", "")
        try:
            logger.info("Attempting TTS with HuggingFace facebook/mms-tts-spa...")
            url = "https://api-inference.huggingface.co/models/facebook/mms-tts-spa"
            headers = {}
            if hf_token:
                hf_token = hf_token.strip("'\"")
                headers["Authorization"] = f"Bearer {hf_token}"
            payload = {"inputs": clean_text}
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            if response.status_code == 200:
                temp_wav = output_path + ".wav"
                with open(temp_wav, "wb") as f:
                    f.write(response.content)
                try:
                    cmd = ["ffmpeg", "-y", "-i", temp_wav, output_path]
                    subprocess.run(cmd, capture_output=True, text=True, check=False)
                except Exception as ffmpeg_err:
                    logger.warning(f"ffmpeg conversion failed: {str(ffmpeg_err)}. Saving raw bytes directly.")
                    os.replace(temp_wav, output_path)
                if os.path.exists(temp_wav):
                    try:
                        os.remove(temp_wav)
                    except:
                        pass
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info("HuggingFace MMS TTS synthesis successful.")
                    return True
            logger.warning(f"HuggingFace TTS failed: status={response.status_code}")
        except Exception as e:
            logger.warning(f"HuggingFace TTS error: {str(e)}")

        # Step 4: Try OpenAI TTS (tts-1)
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(Config, "OPENAI_API_KEY", "")
        if openai_key:
            openai_key = openai_key.strip("'\"")
            try:
                logger.info("Attempting TTS with OpenAI tts-1...")
                url = "https://api.openai.com/v1/audio/speech"
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "tts-1",
                    "input": clean_text,
                    "voice": "nova" if is_female else "onyx"
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info("OpenAI TTS synthesis successful.")
                        return True
                logger.warning(f"OpenAI TTS failed: status={response.status_code}")
            except Exception as e:
                logger.error(f"OpenAI TTS error: {str(e)}")

        logger.error("All TTS synthesis engines in cascade failed.")
        return False

    @classmethod
    def resolve_smart_voice(cls, gender: str = "neutral", language: str = "es", preferred_voice: str = None) -> str:
        """
        Intelligently resolves the optimal Edge-TTS voice based on language and agent gender.
        If preferred_voice is a specific voice (not 'smart'/'auto'/'dynamic'), it honors it.
        """
        if preferred_voice and preferred_voice.lower() not in ["", "smart", "auto", "dynamic", "none", "default"]:
            return preferred_voice

        lang = (language or "es").split("-")[0].lower()
        g = (gender or "neutral").lower()

        # Dynamic Voice Matrix by Language and Gender
        voice_matrix = {
            "es": {
                "female": "es-MX-DaliaNeural",
                "male": "es-MX-JorgeNeural",
                "neutral": "es-MX-DaliaNeural"
            },
            "en": {
                "female": "en-US-JennyNeural",
                "male": "en-US-BrianNeural",
                "neutral": "en-US-JennyNeural"
            },
            "pt": {
                "female": "pt-BR-FranciscaNeural",
                "male": "pt-BR-AntonioNeural",
                "neutral": "pt-BR-FranciscaNeural"
            },
            "fr": {
                "female": "fr-FR-DeniseNeural",
                "male": "fr-FR-HenriNeural",
                "neutral": "fr-FR-DeniseNeural"
            },
            "de": {
                "female": "de-DE-KatjaNeural",
                "male": "de-DE-ConradNeural",
                "neutral": "de-DE-KatjaNeural"
            },
            "it": {
                "female": "it-IT-ElsaNeural",
                "male": "it-IT-DiegoNeural",
                "neutral": "it-IT-ElsaNeural"
            }
        }

        lang_voices = voice_matrix.get(lang, voice_matrix["es"])
        return lang_voices.get(g, lang_voices["neutral"])

    @classmethod
    def get_voices(cls):
        """
        Returns high-quality neural voices from our cascading providers.
        """
        return [
            # Smart Dynamic Option
            {"ShortName": "smart", "FriendlyName": "⚡ Inteligente / Automático (Según idioma y género)", "Gender": "Auto", "Locale": "multilingual", "Category": "Smart"},
            
            # Spanish (Latin America & Spain)
            {"ShortName": "es-MX-DaliaNeural", "FriendlyName": "Dalia (Español México / Latam - Femenina)", "Gender": "Female", "Locale": "es-MX", "Country": "México / Latam"},
            {"ShortName": "es-MX-JorgeNeural", "FriendlyName": "Jorge (Español México / Latam - Masculina)", "Gender": "Male", "Locale": "es-MX", "Country": "México / Latam"},
            {"ShortName": "es-ES-ElviraNeural", "FriendlyName": "Elvira (Español España - Femenina)", "Gender": "Female", "Locale": "es-ES", "Country": "España"},
            {"ShortName": "es-ES-AlvaroNeural", "FriendlyName": "Álvaro (Español España - Masculina)", "Gender": "Male", "Locale": "es-ES", "Country": "España"},
            {"ShortName": "es-CO-SalomeNeural", "FriendlyName": "Salomé (Español Colombia - Femenina)", "Gender": "Female", "Locale": "es-CO", "Country": "Colombia"},
            {"ShortName": "es-CO-GonzaloNeural", "FriendlyName": "Gonzalo (Español Colombia - Masculina)", "Gender": "Male", "Locale": "es-CO", "Country": "Colombia"},
            {"ShortName": "es-AR-ElenaNeural", "FriendlyName": "Elena (Español Argentina - Femenina)", "Gender": "Female", "Locale": "es-AR", "Country": "Argentina"},
            {"ShortName": "es-AR-TomasNeural", "FriendlyName": "Tomás (Español Argentina - Masculina)", "Gender": "Male", "Locale": "es-AR", "Country": "Argentina"},
            {"ShortName": "es-US-PalomaNeural", "FriendlyName": "Paloma (Español EEUU - Femenina)", "Gender": "Female", "Locale": "es-US", "Country": "Estados Unidos"},

            # English (US & UK)
            {"ShortName": "en-US-JennyNeural", "FriendlyName": "Jenny (English US - Female)", "Gender": "Female", "Locale": "en-US", "Country": "USA"},
            {"ShortName": "en-US-BrianNeural", "FriendlyName": "Brian (English US - Male)", "Gender": "Male", "Locale": "en-US", "Country": "USA"},
            {"ShortName": "en-US-AriaNeural", "FriendlyName": "Aria (English US - Female Expressive)", "Gender": "Female", "Locale": "en-US", "Country": "USA"},
            {"ShortName": "en-US-GuyNeural", "FriendlyName": "Guy (English US - Male Warm)", "Gender": "Male", "Locale": "en-US", "Country": "USA"},
            {"ShortName": "en-GB-SoniaNeural", "FriendlyName": "Sonia (English UK - Female)", "Gender": "Female", "Locale": "en-GB", "Country": "UK"},
            {"ShortName": "en-GB-RyanNeural", "FriendlyName": "Ryan (English UK - Male)", "Gender": "Male", "Locale": "en-GB", "Country": "UK"},

            # Portuguese (Brazil & Portugal)
            {"ShortName": "pt-BR-FranciscaNeural", "FriendlyName": "Francisca (Português Brasil - Feminina)", "Gender": "Female", "Locale": "pt-BR", "Country": "Brasil"},
            {"ShortName": "pt-BR-AntonioNeural", "FriendlyName": "Antônio (Português Brasil - Masculino)", "Gender": "Male", "Locale": "pt-BR", "Country": "Brasil"},
            {"ShortName": "pt-PT-RaquelNeural", "FriendlyName": "Raquel (Português Portugal - Feminina)", "Gender": "Female", "Locale": "pt-PT", "Country": "Portugal"},

            # French & German
            {"ShortName": "fr-FR-DeniseNeural", "FriendlyName": "Denise (Français - Féminine)", "Gender": "Female", "Locale": "fr-FR", "Country": "France"},
            {"ShortName": "fr-FR-HenriNeural", "FriendlyName": "Henri (Français - Masculin)", "Gender": "Male", "Locale": "fr-FR", "Country": "France"},
            {"ShortName": "de-DE-KatjaNeural", "FriendlyName": "Katja (Deutsch - Weiblich)", "Gender": "Female", "Locale": "de-DE", "Country": "Deutschland"},
            {"ShortName": "de-DE-ConradNeural", "FriendlyName": "Conrad (Deutsch - Männlich)", "Gender": "Male", "Locale": "de-DE", "Country": "Deutschland"}
        ]

    @classmethod
    async def get_voices_async(cls):
        """
        Async wrapper for get_voices.
        """
        return cls.get_voices()
