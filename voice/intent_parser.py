"""
Intent Parser for Voice Commands
Parses voice transcripts into structured intents for robot control

Based on: massage_chatbot/synonyms_config.py pattern
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class IntentAction(Enum):
    """Recognized intent actions"""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    HARDER = "harder"
    SOFTER = "softer"
    PATTERN_LINEAR = "pattern_linear"
    PATTERN_CIRCULAR = "pattern_circular"
    PATTERN_TRIGGER = "pattern_trigger"
    PATTERN_KNEADING = "pattern_kneading"
    REGION_LEFT = "region_left"
    REGION_RIGHT = "region_right"
    EMERGENCY = "emergency"
    HOME = "home"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Parsed intent from voice command"""
    action: IntentAction
    pattern: Optional[str] = None
    force_delta: Optional[float] = None
    region: Optional[str] = None
    confidence: float = 1.0
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            'action': self.action.value,
            'pattern': self.pattern,
            'force_delta': self.force_delta,
            'region': self.region,
            'confidence': self.confidence,
            'raw_text': self.raw_text,
        }


# Default keyword mappings (Chinese + English)
DEFAULT_KEYWORDS: Dict[IntentAction, List[str]] = {
    IntentAction.START: [
        "開始", "啟動", "start", "begin", "go", "run",
        "按摩", "開始按摩", "開機"
    ],
    IntentAction.STOP: [
        "停止", "結束", "stop", "end", "halt", "quit",
        "停", "不要", "關機"
    ],
    IntentAction.PAUSE: [
        "暫停", "等一下", "pause", "wait", "hold",
        "等等", "停一下"
    ],
    IntentAction.RESUME: [
        "繼續", "resume", "continue", "go on",
        "再開始", "接續", "恢復"
    ],
    IntentAction.HARDER: [
        "大力", "用力", "harder", "more", "強",
        "加力", "重一點", "harder please", "more force",
        "大力一點", "再大力"
    ],
    IntentAction.SOFTER: [
        "輕", "小力", "softer", "less", "gentle",
        "輕一點", "減力", "softer please", "less force",
        "輕輕", "小力一點"
    ],
    IntentAction.PATTERN_LINEAR: [
        "直線", "推", "linear", "stroke", "推拿",
        "直線推", "推推"
    ],
    IntentAction.PATTERN_CIRCULAR: [
        "圓", "揉", "circular", "rub", "打圈",
        "環形", "轉圈", "揉揉"
    ],
    IntentAction.PATTERN_TRIGGER: [
        "點", "按", "trigger", "press", "point",
        "穴位", "點按", "按按", "壓"
    ],
    IntentAction.PATTERN_KNEADING: [
        "捏", "knead", "kneading", "揉捏",
        "捏捏", "揉一揉"
    ],
    IntentAction.REGION_LEFT: [
        "左", "left", "左腿", "左邊", "左小腿"
    ],
    IntentAction.REGION_RIGHT: [
        "右", "right", "右腿", "右邊", "右小腿"
    ],
    IntentAction.EMERGENCY: [
        "緊急停止", "emergency", "危險", "danger",
        "緊急", "救命", "痛"
    ],
    IntentAction.HOME: [
        "回家", "home", "回原點", "歸位"
    ],
}

# Force delta values for adjustments
FORCE_DELTAS = {
    IntentAction.HARDER: 5.0,   # +5N
    IntentAction.SOFTER: -5.0,  # -5N
}

# Pattern name mapping
PATTERN_MAP = {
    IntentAction.PATTERN_LINEAR: "linear",
    IntentAction.PATTERN_CIRCULAR: "circular",
    IntentAction.PATTERN_TRIGGER: "trigger",
    IntentAction.PATTERN_KNEADING: "kneading",
}

# Region mapping
REGION_MAP = {
    IntentAction.REGION_LEFT: "left",
    IntentAction.REGION_RIGHT: "right",
}


class IntentParser:
    """
    Parser for voice command intents

    Supports:
    - Chinese and English keywords
    - Multiple intents in single utterance
    - Configurable keywords via YAML
    """

    def __init__(self, config_path: str = None):
        """
        Initialize parser

        Args:
            config_path: Path to intents.yaml config file
        """
        self.keywords = DEFAULT_KEYWORDS.copy()
        self.force_deltas = FORCE_DELTAS.copy()

        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path: str) -> None:
        """Load keywords from YAML config"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Load action keywords
            actions = config.get('actions', {})
            for action_name, action_config in actions.items():
                try:
                    action = IntentAction(action_name)
                    keywords = action_config.get('keywords', [])
                    if keywords:
                        self.keywords[action] = keywords
                except ValueError:
                    pass

            # Load force adjustments
            adjustments = config.get('force_adjustments', {})
            for adj_name, adj_config in adjustments.items():
                try:
                    action = IntentAction(adj_name)
                    delta = adj_config.get('delta_n', 5.0)
                    self.force_deltas[action] = delta
                    keywords = adj_config.get('keywords', [])
                    if keywords:
                        self.keywords[action] = keywords
                except ValueError:
                    pass

            # Load pattern keywords
            patterns = config.get('patterns', {})
            for pattern_name, pattern_config in patterns.items():
                action_name = f"pattern_{pattern_name}"
                try:
                    action = IntentAction(action_name)
                    keywords = pattern_config.get('keywords', [])
                    if keywords:
                        self.keywords[action] = keywords
                except ValueError:
                    pass

            # Load region keywords
            regions = config.get('regions', {})
            for region_name, region_config in regions.items():
                action_name = f"region_{region_name}"
                try:
                    action = IntentAction(action_name)
                    keywords = region_config.get('keywords', [])
                    if keywords:
                        self.keywords[action] = keywords
                except ValueError:
                    pass

            logger.info(f"Loaded intent config from {config_path}")

        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")

    def find_actions(self, text: str) -> List[Tuple[IntentAction, str]]:
        """
        Find all matching actions in text

        Args:
            text: Input text to parse

        Returns:
            List of (action, matched_keyword) tuples
        """
        text_lower = text.lower()
        found = []

        for action, keywords in self.keywords.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower:
                    found.append((action, keyword))
                    break  # Only count each action once

        return found

    def parse(self, transcript: str) -> Intent:
        """
        Parse transcript into structured intent

        Args:
            transcript: Voice command transcript

        Returns:
            Intent object with parsed action and parameters
        """
        if not transcript or not transcript.strip():
            return Intent(
                action=IntentAction.UNKNOWN,
                raw_text=transcript or ""
            )

        transcript = transcript.strip()
        matches = self.find_actions(transcript)

        if not matches:
            return Intent(
                action=IntentAction.UNKNOWN,
                raw_text=transcript
            )

        # Extract components
        primary_action = None
        pattern = None
        force_delta = None
        region = None

        # Priority order: emergency > control > adjustment > pattern > region
        priority_order = [
            IntentAction.EMERGENCY,
            IntentAction.STOP,
            IntentAction.START,
            IntentAction.PAUSE,
            IntentAction.RESUME,
            IntentAction.HOME,
            IntentAction.HARDER,
            IntentAction.SOFTER,
        ]

        for action, _ in matches:
            # Check for emergency first
            if action == IntentAction.EMERGENCY:
                return Intent(
                    action=IntentAction.EMERGENCY,
                    raw_text=transcript,
                    confidence=1.0
                )

            # Control actions
            if action in [IntentAction.START, IntentAction.STOP,
                          IntentAction.PAUSE, IntentAction.RESUME,
                          IntentAction.HOME]:
                if primary_action is None:
                    primary_action = action

            # Force adjustments
            elif action in [IntentAction.HARDER, IntentAction.SOFTER]:
                force_delta = self.force_deltas.get(action, 5.0 if action == IntentAction.HARDER else -5.0)
                if primary_action is None:
                    primary_action = action

            # Patterns
            elif action in PATTERN_MAP:
                pattern = PATTERN_MAP[action]
                if primary_action is None:
                    primary_action = IntentAction.START

            # Regions
            elif action in REGION_MAP:
                region = REGION_MAP[action]

        # Default action if only pattern/region found
        if primary_action is None:
            if pattern:
                primary_action = IntentAction.START
            elif force_delta:
                primary_action = IntentAction.HARDER if force_delta > 0 else IntentAction.SOFTER
            else:
                primary_action = IntentAction.UNKNOWN

        # Calculate confidence based on match specificity
        confidence = min(1.0, 0.5 + 0.1 * len(matches))

        return Intent(
            action=primary_action,
            pattern=pattern,
            force_delta=force_delta,
            region=region,
            confidence=confidence,
            raw_text=transcript
        )

    def get_action_keywords(self, action: IntentAction) -> List[str]:
        """Get keywords for a specific action"""
        return self.keywords.get(action, [])

    def add_keyword(self, action: IntentAction, keyword: str) -> None:
        """Add a keyword for an action"""
        if action not in self.keywords:
            self.keywords[action] = []
        if keyword not in self.keywords[action]:
            self.keywords[action].append(keyword)


# Module-level parser instance
_default_parser: Optional[IntentParser] = None


def get_parser(config_path: str = None) -> IntentParser:
    """Get or create default parser instance"""
    global _default_parser
    if _default_parser is None:
        # Try to find config in default location
        if config_path is None:
            default_path = Path(__file__).parent.parent / 'config' / 'intents.yaml'
            if default_path.exists():
                config_path = str(default_path)
        _default_parser = IntentParser(config_path)
    return _default_parser


def parse_intent(transcript: str) -> Intent:
    """Convenience function to parse intent using default parser"""
    return get_parser().parse(transcript)
