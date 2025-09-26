"""
Simple failover implementation for voice-mode.

This module provides a direct try-and-failover approach without health checks.
Connection refused errors are instant, so there's no performance penalty.
"""

import logging
from typing import Optional, Tuple, Dict, Any
from openai import AsyncOpenAI

from .config import TTS_BASE_URLS, STT_BASE_URLS, OPENAI_API_KEY
from .provider_discovery import detect_provider_type

logger = logging.getLogger("voice-mode")


async def simple_tts_failover(
    text: str,
    voice: str,
    model: str,
    **kwargs
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Simple TTS failover - try each endpoint in order until one works.
    
    Returns:
        Tuple of (success, metrics, config)
    """
    logger.info(f"simple_tts_failover called with: text='{text[:50]}...', voice={voice}, model={model}")
    logger.info(f"kwargs: {kwargs}")
    
    from .core import text_to_speech
    from .conversation_logger import get_conversation_logger
    
    last_error = None
    
    # Get conversation ID from logger
    conversation_logger = get_conversation_logger()
    conversation_id = conversation_logger.conversation_id
    
    # Try each TTS endpoint in order
    logger.info(f"simple_tts_failover: Starting with TTS_BASE_URLS = {TTS_BASE_URLS}")
    for base_url in TTS_BASE_URLS:
        try:
            logger.info(f"Trying TTS endpoint: {base_url}")
            
            # Create client for this endpoint
            provider_type = detect_provider_type(base_url)
            api_key = OPENAI_API_KEY if provider_type == "openai" else (OPENAI_API_KEY or "dummy-key-for-local")
            
            # Select appropriate voice for this provider
            if provider_type == "openai":
                # Map Kokoro voices to OpenAI equivalents, or use OpenAI default
                openai_voices = ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]
                if voice in openai_voices:
                    selected_voice = voice
                else:
                    # Map common Kokoro voices to OpenAI equivalents
                    voice_mapping = {
                        "af_sky": "nova",
                        "af_sarah": "nova", 
                        "af_alloy": "alloy",
                        "am_adam": "onyx",
                        "am_echo": "echo",
                        "am_onyx": "onyx",
                        "bm_fable": "fable"
                    }
                    selected_voice = voice_mapping.get(voice, "alloy")  # Default to alloy
                    logger.info(f"Mapped voice {voice} to {selected_voice} for OpenAI")
            else:
                selected_voice = voice  # Use original voice for Kokoro
            
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=30.0  # Reasonable timeout
            )
            
            # Create clients dict for text_to_speech
            openai_clients = {'tts': client}
            
            # Try TTS with this endpoint
            success, metrics = await text_to_speech(
                text=text,
                openai_clients=openai_clients,
                tts_model=model,
                tts_voice=selected_voice,
                tts_base_url=base_url,
                conversation_id=conversation_id,
                **kwargs
            )
            
            if success:
                config = {
                    'base_url': base_url,
                    'provider': provider_type,
                    'voice': selected_voice,  # Return the voice actually used
                    'model': model
                }
                logger.info(f"TTS succeeded with {base_url} using voice {selected_voice}")
                return True, metrics, config
                
        except Exception as e:
            last_error = str(e)
            logger.error(f"TTS failed for {base_url}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            if hasattr(e, '__dict__'):
                logger.error(f"Exception attributes: {e.__dict__}")
            # Continue to next endpoint
            continue
    
    # All endpoints failed
    logger.error(f"All TTS endpoints failed. Last error: {last_error}")
    error_config = {
        'error': last_error,
        'tried_urls': TTS_BASE_URLS
    }
    return False, None, error_config


async def simple_stt_failover(
    audio_file,
    model: str = "whisper-1",
    **kwargs
) -> Optional[str]:
    """
    Simple STT failover - try each endpoint in order until one works.
    
    Returns:
        Transcribed text or None
    """
    last_error = None
    
    # Try each STT endpoint in order
    for base_url in STT_BASE_URLS:
        try:
            logger.info(f"Trying STT endpoint: {base_url}")
            
            # Create client for this endpoint
            provider_type = detect_provider_type(base_url)
            api_key = OPENAI_API_KEY if provider_type == "openai" else (OPENAI_API_KEY or "dummy-key-for-local")
            
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=30.0
            )
            
            # Try STT with this endpoint
            transcription = await client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="text"
            )
            
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            
            if text:
                logger.info(f"STT succeeded with {base_url}")
                return text
                
        except Exception as e:
            last_error = str(e)
            logger.debug(f"STT failed for {base_url}: {e}")
            # Continue to next endpoint
            continue
    
    # All endpoints failed
    logger.error(f"All STT endpoints failed. Last error: {last_error}")
    return None