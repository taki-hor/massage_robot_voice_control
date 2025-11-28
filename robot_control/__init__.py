"""
Robot Control Package for UR10e Massage System

Provides:
- RobotAdapter: Main interface for robot control
- DashboardClient: Dashboard server communication
- RTDEClient: Real-time data exchange
- SafetyMonitor: Force/workspace safety monitoring
"""

from .adapter import RobotAdapter, MassagePattern, ControlFlag, RobotState, create_adapter
from .dashboard_client import DashboardClient, RobotMode, SafetyMode
from .rtde_client import RTDEClient, SafetyStatus as RTDESafetyStatus
from .safety import SafetyMonitor, SafetyLimits, SafetyZone, SafetyEvent

__all__ = [
    # Main adapter
    'RobotAdapter',
    'MassagePattern',
    'ControlFlag',
    'RobotState',
    'create_adapter',

    # Dashboard
    'DashboardClient',
    'RobotMode',
    'SafetyMode',

    # RTDE
    'RTDEClient',
    'RTDESafetyStatus',

    # Safety
    'SafetyMonitor',
    'SafetyLimits',
    'SafetyZone',
    'SafetyEvent',
]
