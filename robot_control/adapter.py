"""
Robot Adapter - Main interface for UR10e Massage Control
Integrates Dashboard, RTDE, and Safety modules

This is the primary API that the voice control system uses.
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import IntEnum
from pathlib import Path

import yaml

from .dashboard_client import DashboardClient, RobotMode as DashboardRobotMode
from .rtde_client import RTDEClient, RobotState as RTDEState, SafetyStatus as RTDESafetyStatus
from .safety import SafetyMonitor, SafetyLimits, SafetyZone, SafetyEvent

logger = logging.getLogger(__name__)


class MassagePattern(IntEnum):
    """Massage pattern IDs - must match URScript"""
    NONE = 0
    LINEAR_STROKE = 1
    CIRCULAR_RUBBING = 2
    TRIGGER_PRESS = 3
    KNEADING = 4


class ControlFlag(IntEnum):
    """Control flags for URScript - must match URScript"""
    STOP = 0
    RUN = 1
    PAUSE = 2


@dataclass
class RobotState:
    """Complete robot state for API responses"""
    is_connected: bool = False
    is_running: bool = False
    is_paused: bool = False
    safety_status: str = "unknown"
    safety_zone: str = "safe"
    current_pattern: int = 0
    pattern_name: str = "none"
    target_force: float = 10.0
    current_force: float = 0.0
    tcp_pose: list = None
    comfort_emoji: str = "😀"
    comfort_level: float = 100.0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.tcp_pose is None:
            self.tcp_pose = [0.0] * 6

    def to_dict(self) -> dict:
        return asdict(self)


class RobotAdapter:
    """
    Main interface for controlling UR10e massage robot

    Provides:
    - Connection management (Dashboard + RTDE)
    - Program control (load, play, stop, pause)
    - Massage pattern control
    - Force adjustment
    - State monitoring with safety checks
    """

    # Default configuration
    DEFAULT_CONFIG = {
        'robot_ip': '192.168.1.100',
        'rtde_port': 30004,
        'dashboard_port': 29999,
        'rtde_frequency': 125,
        'default_force': 10.0,
        'force_step': 2.0,
        'force_min': 5.0,
        'force_max': 30.0,
        'resident_program': 'massage_resident.urp',
    }

    def __init__(self, config_path: str = None, **kwargs):
        """
        Initialize RobotAdapter

        Args:
            config_path: Path to YAML config file
            **kwargs: Override config values
        """
        self.config = self._load_config(config_path, kwargs)

        # Initialize clients
        self._dashboard = DashboardClient(
            self.config['robot_ip'],
            self.config['dashboard_port']
        )
        self._rtde = RTDEClient(
            self.config['robot_ip'],
            self.config['rtde_frequency']
        )
        self._safety = SafetyMonitor(config_path=config_path)

        # State
        self._connected = False
        self._current_pattern = MassagePattern.NONE
        self._control_flag = ControlFlag.STOP
        self._target_force = self.config['default_force']

        # Register safety callbacks
        self._safety.on_safety_event(self._on_safety_event)

    def _load_config(self, config_path: str, overrides: dict) -> dict:
        """Load configuration from file and apply overrides"""
        config = self.DEFAULT_CONFIG.copy()

        if config_path:
            try:
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)

                # Map YAML structure to flat config
                conn = yaml_config.get('connection', {})
                config['robot_ip'] = conn.get('robot_ip', config['robot_ip'])
                config['rtde_port'] = conn.get('rtde_port', config['rtde_port'])
                config['dashboard_port'] = conn.get('dashboard_port', config['dashboard_port'])
                config['rtde_frequency'] = conn.get('rtde_frequency_hz', config['rtde_frequency'])

                massage = yaml_config.get('massage', {})
                force_range = massage.get('force_range', [5, 30])
                config['force_min'] = force_range[0]
                config['force_max'] = force_range[1]
                config['force_step'] = massage.get('step_force', 2.0)

                force_ctrl = yaml_config.get('force_control', {})
                config['default_force'] = force_ctrl.get('target_default', 10.0)

            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        # Apply overrides
        config.update(overrides)
        return config

    def _on_safety_event(self, event: SafetyEvent, status) -> None:
        """Handle safety events"""
        if event in [SafetyEvent.FORCE_CRITICAL, SafetyEvent.COLLISION_DETECTED]:
            logger.warning(f"Safety event: {event.value}, stopping robot")
            self._emergency_reduce_force()

    def _emergency_reduce_force(self) -> None:
        """Emergency force reduction"""
        self._target_force = self.config['force_min']
        self._write_force_register()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """
        Connect to robot (Dashboard + RTDE)

        Returns:
            True if both connections successful
        """
        logger.info(f"Connecting to robot at {self.config['robot_ip']}...")

        # Connect Dashboard
        if not self._dashboard.connect():
            logger.error("Dashboard connection failed")
            return False

        # Connect RTDE
        if not self._rtde.connect():
            logger.error("RTDE connection failed")
            self._dashboard.disconnect()
            return False

        self._connected = True
        logger.info("Robot connected successfully")
        return True

    def disconnect(self) -> None:
        """Disconnect from robot"""
        self.stop()
        self._rtde.disconnect()
        self._dashboard.disconnect()
        self._connected = False
        logger.info("Robot disconnected")

    def load_and_run_resident(self, program: str = None) -> bool:
        """
        Load and start the resident massage URScript program

        Args:
            program: Program path (default: from config)

        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected")
            return False

        program = program or self.config['resident_program']

        # Load program
        response = self._dashboard.load_program(program)
        if not response.success:
            logger.error(f"Failed to load program: {response.message}")
            return False

        # Start program
        response = self._dashboard.play()
        if not response.success:
            logger.error(f"Failed to start program: {response.message}")
            return False

        logger.info(f"Resident program '{program}' started")
        return True

    def stop(self) -> bool:
        """Stop robot execution"""
        self._control_flag = ControlFlag.STOP
        self._current_pattern = MassagePattern.NONE

        # Write to RTDE registers
        self._write_control_registers()

        # Dashboard stop as backup
        if self._connected:
            self._dashboard.stop()

        logger.info("Robot stopped")
        return True

    def pause(self) -> bool:
        """Pause robot execution"""
        self._control_flag = ControlFlag.PAUSE
        self._write_control_registers()
        logger.info("Robot paused")
        return True

    def resume(self) -> bool:
        """Resume robot execution"""
        if self._current_pattern == MassagePattern.NONE:
            logger.warning("No pattern set, cannot resume")
            return False

        self._control_flag = ControlFlag.RUN
        self._write_control_registers()
        logger.info("Robot resumed")
        return True

    def set_pattern(self, pattern: MassagePattern) -> bool:
        """
        Set massage pattern

        Args:
            pattern: MassagePattern enum value

        Returns:
            True if successful
        """
        self._current_pattern = pattern
        self._control_flag = ControlFlag.RUN
        self._write_control_registers()
        logger.info(f"Pattern set to {pattern.name}")
        return True

    def set_pattern_by_name(self, name: str) -> bool:
        """
        Set pattern by name string

        Args:
            name: Pattern name (linear, circular, trigger, kneading)
        """
        name_map = {
            'linear': MassagePattern.LINEAR_STROKE,
            'circular': MassagePattern.CIRCULAR_RUBBING,
            'trigger': MassagePattern.TRIGGER_PRESS,
            'kneading': MassagePattern.KNEADING,
            'none': MassagePattern.NONE,
        }
        pattern = name_map.get(name.lower())
        if pattern is None:
            logger.error(f"Unknown pattern: {name}")
            return False
        return self.set_pattern(pattern)

    def set_force_target(self, force_n: float) -> bool:
        """
        Set target force

        Args:
            force_n: Target force in Newtons

        Returns:
            True if successful
        """
        # Clamp to limits
        force_n = max(self.config['force_min'],
                      min(self.config['force_max'], force_n))

        self._target_force = force_n
        self._write_force_register()
        logger.info(f"Force target set to {force_n:.1f}N")
        return True

    def adjust_force(self, delta_n: float) -> bool:
        """
        Adjust force by delta

        Args:
            delta_n: Force change in Newtons (+/-)

        Returns:
            True if successful
        """
        new_force = self._target_force + delta_n
        return self.set_force_target(new_force)

    def increase_force(self) -> bool:
        """Increase force by configured step"""
        return self.adjust_force(self.config['force_step'])

    def decrease_force(self) -> bool:
        """Decrease force by configured step"""
        return self.adjust_force(-self.config['force_step'])

    def _write_control_registers(self) -> None:
        """Write pattern and control flag to RTDE registers"""
        self._rtde.write_input_int_register(
            RTDEClient.INPUT_INT_PATTERN,
            self._current_pattern.value
        )
        self._rtde.write_input_int_register(
            RTDEClient.INPUT_INT_CONTROL,
            self._control_flag.value
        )

    def _write_force_register(self) -> None:
        """Write target force to RTDE register"""
        self._rtde.write_input_float_register(
            RTDEClient.INPUT_FLOAT_FORCE,
            self._target_force
        )

    def read_state(self) -> RobotState:
        """
        Get current robot state

        Returns:
            RobotState with all current values
        """
        rtde_state = self._rtde.state
        force_mag = self._rtde.get_tcp_force_magnitude()

        # Safety check
        safety_status = self._safety.check_force(rtde_state.tcp_force)

        # Comfort level
        emoji, comfort = self._safety.get_force_for_comfort(force_mag)

        return RobotState(
            is_connected=self._connected,
            is_running=self._control_flag == ControlFlag.RUN,
            is_paused=self._control_flag == ControlFlag.PAUSE,
            safety_status=rtde_state.safety_status.name if hasattr(rtde_state.safety_status, 'name') else str(rtde_state.safety_status),
            safety_zone=safety_status.zone.value,
            current_pattern=self._current_pattern.value,
            pattern_name=self._current_pattern.name.lower(),
            target_force=self._target_force,
            current_force=force_mag,
            tcp_pose=list(rtde_state.tcp_pose),
            comfort_emoji=emoji,
            comfort_level=comfort,
            timestamp=time.time()
        )

    def unlock_protective_stop(self) -> bool:
        """Unlock protective stop via Dashboard"""
        if not self._connected:
            return False
        response = self._dashboard.unlock_protective_stop()
        return response.success

    def get_pattern_names(self) -> list:
        """Get list of available pattern names"""
        return [p.name.lower() for p in MassagePattern if p != MassagePattern.NONE]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


# Convenience function for quick testing
def create_adapter(robot_ip: str = None, mock: bool = False) -> RobotAdapter:
    """
    Create a RobotAdapter instance

    Args:
        robot_ip: Robot IP address (None = use default)
        mock: If True, use mock mode (no real robot)

    Returns:
        Configured RobotAdapter
    """
    config_path = Path(__file__).parent.parent / 'config' / 'robot_limits.yaml'

    kwargs = {}
    if robot_ip:
        kwargs['robot_ip'] = robot_ip

    return RobotAdapter(
        config_path=str(config_path) if config_path.exists() else None,
        **kwargs
    )
