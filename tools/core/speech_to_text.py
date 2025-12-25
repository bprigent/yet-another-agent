"""Speech-to-text transcription service using OpenAI Whisper API."""

import os
from io import BytesIO
from typing import Optional
from openai import OpenAI
from logging_config import get_logger

logger = get_logger(__name__)


class SpeechToTextService:
    """Service for transcribing audio to text using OpenAI Whisper API."""
    
    def __init__(self):
        """Initialize the speech-to-text service."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not found. Voice input will not work. "
                "Set OPENAI_API_KEY in your .env file to enable voice input."
            )
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
            logger.info("Speech-to-text service initialized with OpenAI Whisper")
    
    def is_available(self) -> bool:
        """Check if the service is available (API key configured)."""
        return self.client is not None
    
    def transcribe_audio(self, audio_data: bytes, language: Optional[str] = None) -> str:
        """
        Transcribe audio data to text using OpenAI Whisper API.
        
        Args:
            audio_data: Raw audio bytes (typically WAV or WebM format from browser)
            language: Optional language code (e.g., 'en', 'fr', 'es'). 
                     If None, Whisper will auto-detect.
        
        Returns:
            Transcribed text string
        
        Raises:
            ValueError: If service is not available or API key is missing
            Exception: If transcription fails
        """
        if not self.is_available():
            raise ValueError(
                "Speech-to-text service not available. "
                "Please set OPENAI_API_KEY in your .env file."
            )
        
        try:
            logger.info(f"Transcribing audio ({len(audio_data)} bytes)")
            
            # Create a file-like object from bytes
            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.webm"  # Chainlit typically sends WebM format
            
            # Prepare transcription parameters
            transcription_params = {
                "model": "whisper-1",
                "file": audio_file,
            }
            
            if language:
                transcription_params["language"] = language
            
            # Call OpenAI Whisper API
            transcript = self.client.audio.transcriptions.create(**transcription_params)
            
            text = transcript.text.strip()
            logger.info(f"Transcription successful: {text[:100]}{'...' if len(text) > 100 else ''}")
            
            return text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")


# Global service instance
_speech_to_text_service = None


def get_speech_to_text_service() -> SpeechToTextService:
    """Get or create the global speech-to-text service instance."""
    global _speech_to_text_service
    if _speech_to_text_service is None:
        _speech_to_text_service = SpeechToTextService()
    return _speech_to_text_service

