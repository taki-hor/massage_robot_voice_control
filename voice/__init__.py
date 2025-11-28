"""
Voice Processing Package for UR10e Massage System

Provides:
- IntentParser: Parse voice transcripts to structured intents
- STT providers: Whisper, Azure, Mock
- CommandRouter: Route intents to robot commands
"""

from .intent_parser import (
    IntentParser,
    IntentAction,
    Intent,
    parse_intent,
    get_parser,
)
from .stt import (
    STTProvider,
    WhisperSTT,
    AzureSTT,
    MockSTT,
    STTManager,
    get_stt_manager,
    transcribe,
)
from .router import (
    CommandRouter,
    CommandResult,
    get_router,
    process_voice_command,
)

__all__ = [
    # Intent parsing
    'IntentParser',
    'IntentAction',
    'Intent',
    'parse_intent',
    'get_parser',

    # STT
    'STTProvider',
    'WhisperSTT',
    'AzureSTT',
    'MockSTT',
    'STTManager',
    'get_stt_manager',
    'transcribe',

    # Routing
    'CommandRouter',
    'CommandResult',
    'get_router',
    'process_voice_command',
]
