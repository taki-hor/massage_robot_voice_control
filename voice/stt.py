"""
Speech-to-Text Module
Supports multiple STT providers: Whisper, Azure Speech Services

Provides both synchronous and streaming transcription.
"""

import io
import logging
import tempfile
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class STTProvider(ABC):
    """Abstract base class for STT providers"""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """
        Transcribe audio to text

        Args:
            audio_data: Audio bytes (WAV format preferred)
            language: Language code (zh, en, etc.)

        Returns:
            Transcribed text
        """
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: str = "zh"
    ) -> AsyncIterator[str]:
        """
        Stream transcription

        Args:
            audio_stream: Async iterator of audio chunks
            language: Language code

        Yields:
            Partial transcription results
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class WhisperSTT(STTProvider):
    """
    OpenAI Whisper STT Provider

    Uses local Whisper model for transcription.
    Good for offline use, supports multiple languages.
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper provider

        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self._model = None
        self._available = False

        try:
            import whisper
            self._whisper = whisper
            self._available = True
            logger.info(f"Whisper STT initialized (model: {model_size})")
        except ImportError:
            logger.warning("Whisper not installed: pip install openai-whisper")

    def _load_model(self):
        """Lazy load the model"""
        if self._model is None and self._available:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = self._whisper.load_model(self.model_size)

    def is_available(self) -> bool:
        return self._available

    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """Transcribe audio using Whisper"""
        if not self._available:
            raise RuntimeError("Whisper not available")

        self._load_model()

        # Write audio to temp file (Whisper requires file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Map language codes
            lang_map = {"zh": "Chinese", "en": "English", "ja": "Japanese"}
            whisper_lang = lang_map.get(language, language)

            result = self._model.transcribe(
                temp_path,
                language=whisper_lang if language != "auto" else None,
                task="transcribe"
            )
            return result["text"].strip()

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: str = "zh"
    ) -> AsyncIterator[str]:
        """
        Stream transcription (accumulates audio then transcribes)

        Note: Whisper doesn't support true streaming, so we accumulate
        audio chunks and transcribe periodically.
        """
        if not self._available:
            raise RuntimeError("Whisper not available")

        buffer = io.BytesIO()
        chunk_count = 0
        chunk_threshold = 10  # Transcribe every N chunks

        async for chunk in audio_stream:
            buffer.write(chunk)
            chunk_count += 1

            if chunk_count >= chunk_threshold:
                # Transcribe accumulated audio
                audio_data = buffer.getvalue()
                if len(audio_data) > 1000:  # Minimum audio size
                    text = await self.transcribe(audio_data, language)
                    if text:
                        yield text

                # Reset for next batch
                buffer = io.BytesIO()
                chunk_count = 0

        # Final transcription
        audio_data = buffer.getvalue()
        if len(audio_data) > 1000:
            text = await self.transcribe(audio_data, language)
            if text:
                yield text


class AzureSTT(STTProvider):
    """
    Azure Speech Services STT Provider

    Requires Azure subscription and speech resource.
    Supports real-time streaming transcription.
    """

    def __init__(
        self,
        subscription_key: str = None,
        region: str = "eastasia"
    ):
        """
        Initialize Azure STT provider

        Args:
            subscription_key: Azure Speech subscription key
            region: Azure region
        """
        self.subscription_key = subscription_key
        self.region = region
        self._available = False
        self._speech_sdk = None

        try:
            import azure.cognitiveservices.speech as speechsdk
            self._speech_sdk = speechsdk
            if subscription_key:
                self._available = True
                logger.info("Azure STT initialized")
            else:
                logger.warning("Azure STT: subscription_key not provided")
        except ImportError:
            logger.warning("Azure Speech SDK not installed: pip install azure-cognitiveservices-speech")

    def is_available(self) -> bool:
        return self._available

    def _get_speech_config(self, language: str):
        """Create speech config"""
        config = self._speech_sdk.SpeechConfig(
            subscription=self.subscription_key,
            region=self.region
        )

        # Map language codes to Azure locale
        lang_map = {
            "zh": "zh-HK",  # Cantonese
            "zh-CN": "zh-CN",  # Mandarin
            "en": "en-US",
            "ja": "ja-JP",
        }
        config.speech_recognition_language = lang_map.get(language, language)

        return config

    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """Transcribe audio using Azure Speech"""
        if not self._available:
            raise RuntimeError("Azure STT not available")

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            config = self._get_speech_config(language)
            audio_config = self._speech_sdk.audio.AudioConfig(filename=temp_path)

            recognizer = self._speech_sdk.SpeechRecognizer(
                speech_config=config,
                audio_config=audio_config
            )

            result = recognizer.recognize_once()

            if result.reason == self._speech_sdk.ResultReason.RecognizedSpeech:
                return result.text.strip()
            elif result.reason == self._speech_sdk.ResultReason.NoMatch:
                logger.warning("No speech recognized")
                return ""
            else:
                logger.error(f"Speech recognition failed: {result.reason}")
                return ""

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: str = "zh"
    ) -> AsyncIterator[str]:
        """
        Stream transcription using Azure

        Note: Full streaming would require push stream,
        simplified implementation accumulates and transcribes.
        """
        if not self._available:
            raise RuntimeError("Azure STT not available")

        buffer = io.BytesIO()

        async for chunk in audio_stream:
            buffer.write(chunk)

        audio_data = buffer.getvalue()
        if len(audio_data) > 1000:
            text = await self.transcribe(audio_data, language)
            if text:
                yield text


class MockSTT(STTProvider):
    """
    Mock STT Provider for testing

    Returns predefined responses for testing without real STT.
    """

    def __init__(self):
        self._responses = [
            "開始按摩",
            "大力一點",
            "輕一點",
            "直線推",
            "打圈",
            "暫停",
            "繼續",
            "停止",
        ]
        self._index = 0
        logger.info("Mock STT initialized")

    def is_available(self) -> bool:
        return True

    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """Return mock transcription"""
        # Cycle through mock responses
        response = self._responses[self._index % len(self._responses)]
        self._index += 1
        return response

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: str = "zh"
    ) -> AsyncIterator[str]:
        """Stream mock transcription"""
        # Consume the stream
        async for _ in audio_stream:
            pass

        yield await self.transcribe(b"", language)


class STTManager:
    """
    Manager for STT providers

    Provides fallback between providers and unified interface.
    """

    def __init__(self):
        self._providers: Dict[str, STTProvider] = {}
        self._primary: Optional[str] = None

    def register(self, name: str, provider: STTProvider, primary: bool = False):
        """Register an STT provider"""
        self._providers[name] = provider
        if primary or self._primary is None:
            if provider.is_available():
                self._primary = name

    def get_provider(self, name: str = None) -> Optional[STTProvider]:
        """Get provider by name or primary"""
        if name:
            return self._providers.get(name)
        if self._primary:
            return self._providers.get(self._primary)
        return None

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "zh",
        provider: str = None
    ) -> str:
        """Transcribe using specified or primary provider"""
        p = self.get_provider(provider)
        if not p:
            raise RuntimeError("No STT provider available")
        return await p.transcribe(audio_data, language)


# Default manager instance
_manager: Optional[STTManager] = None


def get_stt_manager() -> STTManager:
    """Get or create default STT manager"""
    global _manager
    if _manager is None:
        _manager = STTManager()

        # Register available providers
        _manager.register("whisper", WhisperSTT(), primary=True)
        _manager.register("mock", MockSTT())

        # Azure requires config, register if available
        import os
        azure_key = os.environ.get("AZURE_SPEECH_KEY")
        if azure_key:
            _manager.register("azure", AzureSTT(subscription_key=azure_key))

    return _manager


async def transcribe(audio_data: bytes, language: str = "zh") -> str:
    """Convenience function for transcription"""
    return await get_stt_manager().transcribe(audio_data, language)
