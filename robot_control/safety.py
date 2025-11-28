"""
Safety Monitor for UR10e Robot
Force/torque monitoring, workspace limits, collision detection

Based on: Universal_Robot_External_GUI/safety_monitor.py
"""

import math
import logging
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class SafetyZone(Enum):
    """Safety zone classification"""
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


class SafetyEvent(Enum):
    """Safety event types"""
    FORCE_WARNING = "force_warning"
    FORCE_CRITICAL = "force_critical"
    TORQUE_WARNING = "torque_warning"
    TORQUE_CRITICAL = "torque_critical"
    WORKSPACE_WARNING = "workspace_warning"
    WORKSPACE_VIOLATION = "workspace_violation"
    COLLISION_DETECTED = "collision_detected"
    VELOCITY_EXCEEDED = "velocity_exceeded"


@dataclass
class SafetyLimits:
    """Safety threshold configuration"""
    # Force limits (N)
    max_force: float = 50.0
    max_force_massage: float = 30.0
    warning_ratio: float = 0.8

    # Torque limits (Nm)
    max_torque: float = 10.0

    # Collision detection
    collision_spike: float = 30.0  # N sudden increase

    # Velocity limits (m/s)
    max_velocity: float = 1.0

    # Workspace limits (m)
    workspace_x: Tuple[float, float] = (-0.8, 0.8)
    workspace_y: Tuple[float, float] = (-0.8, 0.8)
    workspace_z: Tuple[float, float] = (0.0, 1.2)
    warning_margin: float = 0.05  # 5cm warning zone

    @classmethod
    def from_yaml(cls, path: str) -> 'SafetyLimits':
        """Load limits from YAML config"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)

            safety = config.get('safety', {})
            workspace = config.get('workspace', {})
            massage = config.get('massage', {})

            return cls(
                max_force=safety.get('max_force', 50.0),
                max_force_massage=massage.get('force_range', [5, 30])[1],
                warning_ratio=safety.get('warning_ratio', 0.8),
                max_torque=safety.get('max_torque', 10.0),
                collision_spike=safety.get('collision_spike', 30.0),
                max_velocity=safety.get('max_velocity', 1.0),
                workspace_x=tuple(workspace.get('x', [-0.8, 0.8])),
                workspace_y=tuple(workspace.get('y', [-0.8, 0.8])),
                workspace_z=tuple(workspace.get('z', [0.0, 1.2])),
                warning_margin=workspace.get('warning_margin', 0.05),
            )
        except Exception as e:
            logger.warning(f"Failed to load safety config: {e}, using defaults")
            return cls()


@dataclass
class SafetyStatus:
    """Current safety status"""
    zone: SafetyZone = SafetyZone.SAFE
    force_magnitude: float = 0.0
    torque_magnitude: float = 0.0
    force_ratio: float = 0.0  # Current force / max force
    events: List[SafetyEvent] = None

    def __post_init__(self):
        if self.events is None:
            self.events = []


class SafetyMonitor:
    """
    Safety monitoring system for UR10e

    Monitors:
    - Force/torque thresholds
    - Workspace boundaries
    - Collision detection (force spikes)
    - Velocity limits
    """

    def __init__(self, limits: SafetyLimits = None, config_path: str = None):
        if config_path:
            self.limits = SafetyLimits.from_yaml(config_path)
        elif limits:
            self.limits = limits
        else:
            self.limits = SafetyLimits()

        self._baseline_force: Optional[float] = None
        self._last_force: float = 0.0
        self._callbacks: List[Callable[[SafetyEvent, SafetyStatus], None]] = []

        # Statistics
        self.stats = {
            'warnings': 0,
            'violations': 0,
            'collisions': 0,
        }

    def on_safety_event(self, callback: Callable[[SafetyEvent, SafetyStatus], None]) -> None:
        """Register callback for safety events"""
        self._callbacks.append(callback)

    def _notify(self, event: SafetyEvent, status: SafetyStatus) -> None:
        """Notify registered callbacks"""
        for callback in self._callbacks:
            try:
                callback(event, status)
            except Exception as e:
                logger.error(f"Safety callback error: {e}")

    def calculate_force_magnitude(self, force_vector: List[float]) -> float:
        """Calculate total force from [Fx, Fy, Fz, ...]"""
        if len(force_vector) < 3:
            return 0.0
        fx, fy, fz = force_vector[:3]
        return math.sqrt(fx*fx + fy*fy + fz*fz)

    def calculate_torque_magnitude(self, force_vector: List[float]) -> float:
        """Calculate total torque from [..., Tx, Ty, Tz]"""
        if len(force_vector) < 6:
            return 0.0
        tx, ty, tz = force_vector[3:6]
        return math.sqrt(tx*tx + ty*ty + tz*tz)

    def check_force(self, force_vector: List[float],
                    use_massage_limits: bool = True) -> SafetyStatus:
        """
        Check force against limits

        Args:
            force_vector: [Fx, Fy, Fz, Tx, Ty, Tz]
            use_massage_limits: Use lower massage-specific limits

        Returns:
            SafetyStatus with zone and events
        """
        force_mag = self.calculate_force_magnitude(force_vector)
        torque_mag = self.calculate_torque_magnitude(force_vector)

        max_force = self.limits.max_force_massage if use_massage_limits else self.limits.max_force
        warning_force = max_force * self.limits.warning_ratio
        warning_torque = self.limits.max_torque * self.limits.warning_ratio

        events = []
        zone = SafetyZone.SAFE

        # Check force
        if force_mag >= max_force:
            zone = SafetyZone.CRITICAL
            events.append(SafetyEvent.FORCE_CRITICAL)
            self.stats['violations'] += 1
        elif force_mag >= warning_force:
            zone = SafetyZone.WARNING
            events.append(SafetyEvent.FORCE_WARNING)
            self.stats['warnings'] += 1

        # Check torque
        if torque_mag >= self.limits.max_torque:
            zone = SafetyZone.CRITICAL
            events.append(SafetyEvent.TORQUE_CRITICAL)
            self.stats['violations'] += 1
        elif torque_mag >= warning_torque:
            if zone != SafetyZone.CRITICAL:
                zone = SafetyZone.WARNING
            events.append(SafetyEvent.TORQUE_WARNING)
            self.stats['warnings'] += 1

        status = SafetyStatus(
            zone=zone,
            force_magnitude=force_mag,
            torque_magnitude=torque_mag,
            force_ratio=force_mag / max_force,
            events=events
        )

        # Notify callbacks
        for event in events:
            self._notify(event, status)

        self._last_force = force_mag
        return status

    def check_collision(self, force_vector: List[float]) -> bool:
        """
        Detect collision via sudden force spike

        Returns:
            True if collision detected
        """
        force_mag = self.calculate_force_magnitude(force_vector)

        if self._baseline_force is None:
            self._baseline_force = force_mag
            return False

        spike = abs(force_mag - self._baseline_force)

        if spike > self.limits.collision_spike:
            self.stats['collisions'] += 1
            self._notify(SafetyEvent.COLLISION_DETECTED, SafetyStatus(
                zone=SafetyZone.CRITICAL,
                force_magnitude=force_mag,
                events=[SafetyEvent.COLLISION_DETECTED]
            ))
            return True

        # Update baseline with smoothing
        self._baseline_force = 0.9 * self._baseline_force + 0.1 * force_mag
        return False

    def check_workspace(self, position: List[float]) -> SafetyStatus:
        """
        Check if position is within workspace limits

        Args:
            position: [x, y, z, ...] in meters

        Returns:
            SafetyStatus with zone
        """
        if len(position) < 3:
            return SafetyStatus(zone=SafetyZone.SAFE)

        x, y, z = position[:3]
        events = []
        zone = SafetyZone.SAFE

        # Check each axis
        checks = [
            (x, self.limits.workspace_x, 'X'),
            (y, self.limits.workspace_y, 'Y'),
            (z, self.limits.workspace_z, 'Z'),
        ]

        for value, (min_val, max_val), axis in checks:
            # Critical: outside workspace
            if value < min_val or value > max_val:
                zone = SafetyZone.CRITICAL
                events.append(SafetyEvent.WORKSPACE_VIOLATION)
                self.stats['violations'] += 1
                logger.warning(f"Workspace violation: {axis}={value:.3f} outside [{min_val}, {max_val}]")
                break

            # Warning: near boundary
            margin = self.limits.warning_margin
            if value < min_val + margin or value > max_val - margin:
                if zone != SafetyZone.CRITICAL:
                    zone = SafetyZone.WARNING
                    events.append(SafetyEvent.WORKSPACE_WARNING)
                    self.stats['warnings'] += 1

        status = SafetyStatus(zone=zone, events=events)

        for event in events:
            self._notify(event, status)

        return status

    def is_within_workspace(self, position: List[float]) -> bool:
        """Simple check if position is within workspace"""
        status = self.check_workspace(position)
        return status.zone != SafetyZone.CRITICAL

    def check_velocity(self, velocity: float) -> SafetyStatus:
        """Check if velocity is within limits"""
        events = []
        zone = SafetyZone.SAFE

        if velocity > self.limits.max_velocity:
            zone = SafetyZone.CRITICAL
            events.append(SafetyEvent.VELOCITY_EXCEEDED)
            self.stats['violations'] += 1

        status = SafetyStatus(zone=zone, events=events)

        for event in events:
            self._notify(event, status)

        return status

    def reset_baseline(self) -> None:
        """Reset force baseline for collision detection"""
        self._baseline_force = None

    def reset_stats(self) -> None:
        """Reset safety statistics"""
        self.stats = {
            'warnings': 0,
            'violations': 0,
            'collisions': 0,
        }

    def get_force_for_comfort(self, force_magnitude: float,
                              low_threshold: float = 15.0,
                              high_threshold: float = 25.0) -> Tuple[str, float]:
        """
        Map force to comfort level for UI display

        Args:
            force_magnitude: Current force in N
            low_threshold: Force below this = comfortable
            high_threshold: Force above this = uncomfortable

        Returns:
            (emoji, comfort_percentage)
        """
        if force_magnitude < low_threshold:
            return ('😀', 100.0)
        elif force_magnitude > high_threshold:
            return ('😖', 0.0)
        else:
            # Linear interpolation
            comfort = 100.0 * (1.0 - (force_magnitude - low_threshold) / (high_threshold - low_threshold))
            return ('😐', comfort)
