"""
Voice Command Router
Routes parsed intents to robot control actions
"""

import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .intent_parser import Intent, IntentAction, parse_intent

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    message: str
    action: str
    data: Optional[Dict[str, Any]] = None


class CommandRouter:
    """
    Routes voice intents to robot control actions

    Provides:
    - Intent to robot command mapping
    - Command execution with error handling
    - Callback support for UI updates
    """

    def __init__(self, robot_adapter=None):
        """
        Initialize router

        Args:
            robot_adapter: RobotAdapter instance for robot control
        """
        self._robot = robot_adapter
        self._callbacks: Dict[str, Callable] = {}
        self._last_intent: Optional[Intent] = None

    def set_robot_adapter(self, adapter) -> None:
        """Set or update robot adapter"""
        self._robot = adapter

    def on_command(self, callback: Callable[[CommandResult], None]) -> None:
        """Register callback for command results"""
        self._callbacks['command'] = callback

    def on_intent(self, callback: Callable[[Intent], None]) -> None:
        """Register callback for parsed intents"""
        self._callbacks['intent'] = callback

    def _notify(self, event: str, data: Any) -> None:
        """Notify registered callback"""
        callback = self._callbacks.get(event)
        if callback:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def process_transcript(self, transcript: str) -> CommandResult:
        """
        Process voice transcript end-to-end

        Args:
            transcript: Voice transcript text

        Returns:
            CommandResult with execution status
        """
        # Parse intent
        intent = parse_intent(transcript)
        self._last_intent = intent
        self._notify('intent', intent)

        # Route to command
        return await self.execute_intent(intent)

    async def execute_intent(self, intent: Intent) -> CommandResult:
        """
        Execute parsed intent

        Args:
            intent: Parsed Intent object

        Returns:
            CommandResult
        """
        if not self._robot:
            return CommandResult(
                success=False,
                message="Robot not connected",
                action=intent.action.value
            )

        try:
            result = await self._execute_action(intent)
            self._notify('command', result)
            return result

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            result = CommandResult(
                success=False,
                message=str(e),
                action=intent.action.value
            )
            self._notify('command', result)
            return result

    async def _execute_action(self, intent: Intent) -> CommandResult:
        """Execute specific action"""
        action = intent.action

        # Emergency stop - highest priority
        if action == IntentAction.EMERGENCY:
            self._robot.stop()
            return CommandResult(
                success=True,
                message="緊急停止已執行 / Emergency stop executed",
                action="emergency_stop"
            )

        # Control commands
        if action == IntentAction.START:
            # If pattern specified, set it first
            if intent.pattern:
                self._robot.set_pattern_by_name(intent.pattern)
                return CommandResult(
                    success=True,
                    message=f"開始 {intent.pattern} 按摩 / Starting {intent.pattern} massage",
                    action="start",
                    data={"pattern": intent.pattern}
                )
            else:
                # Resume or start with current pattern
                self._robot.resume()
                return CommandResult(
                    success=True,
                    message="開始按摩 / Starting massage",
                    action="start"
                )

        if action == IntentAction.STOP:
            self._robot.stop()
            return CommandResult(
                success=True,
                message="停止按摩 / Massage stopped",
                action="stop"
            )

        if action == IntentAction.PAUSE:
            self._robot.pause()
            return CommandResult(
                success=True,
                message="暫停按摩 / Massage paused",
                action="pause"
            )

        if action == IntentAction.RESUME:
            self._robot.resume()
            return CommandResult(
                success=True,
                message="繼續按摩 / Massage resumed",
                action="resume"
            )

        if action == IntentAction.HOME:
            self._robot.stop()
            # Could add home position command here
            return CommandResult(
                success=True,
                message="回到原點 / Returning home",
                action="home"
            )

        # Force adjustments
        if action == IntentAction.HARDER:
            delta = intent.force_delta or 5.0
            self._robot.adjust_force(delta)
            state = self._robot.read_state()
            return CommandResult(
                success=True,
                message=f"力度增加至 {state.target_force:.1f}N / Force increased to {state.target_force:.1f}N",
                action="harder",
                data={"force": state.target_force}
            )

        if action == IntentAction.SOFTER:
            delta = intent.force_delta or -5.0
            self._robot.adjust_force(delta)
            state = self._robot.read_state()
            return CommandResult(
                success=True,
                message=f"力度減少至 {state.target_force:.1f}N / Force decreased to {state.target_force:.1f}N",
                action="softer",
                data={"force": state.target_force}
            )

        # Pattern changes (without explicit start)
        if action in [IntentAction.PATTERN_LINEAR, IntentAction.PATTERN_CIRCULAR,
                      IntentAction.PATTERN_TRIGGER, IntentAction.PATTERN_KNEADING]:
            pattern = intent.pattern
            if pattern:
                self._robot.set_pattern_by_name(pattern)
                return CommandResult(
                    success=True,
                    message=f"切換至 {pattern} 模式 / Switched to {pattern} mode",
                    action="pattern_change",
                    data={"pattern": pattern}
                )

        # Unknown action
        return CommandResult(
            success=False,
            message=f"未知指令: {intent.raw_text} / Unknown command",
            action="unknown"
        )

    def get_last_intent(self) -> Optional[Intent]:
        """Get most recent parsed intent"""
        return self._last_intent


# Module-level router instance
_router: Optional[CommandRouter] = None


def get_router(robot_adapter=None) -> CommandRouter:
    """Get or create default router"""
    global _router
    if _router is None:
        _router = CommandRouter(robot_adapter)
    elif robot_adapter:
        _router.set_robot_adapter(robot_adapter)
    return _router


async def process_voice_command(transcript: str, robot_adapter=None) -> CommandResult:
    """Convenience function for processing voice commands"""
    router = get_router(robot_adapter)
    return await router.process_transcript(transcript)
