"""
Dashboard Client for UR10e Robot
Communicates with Dashboard Server on port 29999

Based on: Universal_Robot_External_GUI/robot_controller.py
"""

import socket
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RobotMode(Enum):
    """UR Robot modes from Dashboard server"""
    DISCONNECTED = -1
    CONFIRM_SAFETY = 0
    BOOTING = 1
    POWER_OFF = 2
    POWER_ON = 3
    IDLE = 4
    BACKDRIVE = 5
    RUNNING = 6


class SafetyMode(Enum):
    """UR Safety modes"""
    NORMAL = 1
    REDUCED = 2
    PROTECTIVE_STOP = 3
    RECOVERY = 4
    SAFEGUARD_STOP = 5
    SYSTEM_EMERGENCY_STOP = 6
    ROBOT_EMERGENCY_STOP = 7
    VIOLATION = 8
    FAULT = 9


@dataclass
class DashboardResponse:
    """Response from Dashboard server"""
    success: bool
    message: str
    value: Optional[str] = None


class DashboardClient:
    """
    Client for UR Dashboard Server (port 29999)

    Provides program control: load, play, stop, pause
    Provides status queries: robot mode, safety status
    """

    DEFAULT_PORT = 29999
    TIMEOUT = 5.0
    BUFFER_SIZE = 1024

    def __init__(self, robot_ip: str, port: int = DEFAULT_PORT):
        self.robot_ip = robot_ip
        self.port = port
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Establish connection to Dashboard server"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.TIMEOUT)
            self._socket.connect((self.robot_ip, self.port))

            # Read welcome message
            welcome = self._socket.recv(self.BUFFER_SIZE).decode('utf-8')
            logger.info(f"Dashboard connected: {welcome.strip()}")
            return True

        except Exception as e:
            logger.error(f"Dashboard connection failed: {e}")
            self._socket = None
            return False

    def disconnect(self) -> None:
        """Close Dashboard connection"""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            logger.info("Dashboard disconnected")

    def _send_command(self, command: str) -> DashboardResponse:
        """Send command and receive response"""
        if not self._socket:
            return DashboardResponse(False, "Not connected")

        try:
            # Send command with newline
            self._socket.send(f"{command}\n".encode('utf-8'))

            # Receive response
            response = self._socket.recv(self.BUFFER_SIZE).decode('utf-8').strip()

            # Parse response (format: "command result" or "value")
            success = not response.lower().startswith("error")

            return DashboardResponse(
                success=success,
                message=response,
                value=response.split()[-1] if response else None
            )

        except socket.timeout:
            return DashboardResponse(False, "Command timeout")
        except Exception as e:
            return DashboardResponse(False, f"Command failed: {e}")

    # Program Control

    def load_program(self, program_path: str) -> DashboardResponse:
        """Load a program file (.urp)"""
        return self._send_command(f"load {program_path}")

    def play(self) -> DashboardResponse:
        """Start/resume program execution"""
        return self._send_command("play")

    def stop(self) -> DashboardResponse:
        """Stop program execution"""
        return self._send_command("stop")

    def pause(self) -> DashboardResponse:
        """Pause program execution"""
        return self._send_command("pause")

    # Safety Control

    def unlock_protective_stop(self) -> DashboardResponse:
        """Unlock protective stop"""
        return self._send_command("unlock protective stop")

    def close_safety_popup(self) -> DashboardResponse:
        """Close safety popup"""
        return self._send_command("close safety popup")

    def restart_safety(self) -> DashboardResponse:
        """Restart safety system"""
        return self._send_command("restart safety")

    # Power Control

    def power_on(self) -> DashboardResponse:
        """Power on the robot"""
        return self._send_command("power on")

    def power_off(self) -> DashboardResponse:
        """Power off the robot"""
        return self._send_command("power off")

    def brake_release(self) -> DashboardResponse:
        """Release brakes"""
        return self._send_command("brake release")

    # Status Queries

    def get_robot_mode(self) -> Tuple[bool, Optional[RobotMode]]:
        """Get current robot mode"""
        response = self._send_command("robotmode")
        if response.success and response.value:
            try:
                # Response format: "Robotmode: RUNNING"
                mode_str = response.message.split(":")[-1].strip().upper()
                for mode in RobotMode:
                    if mode.name == mode_str:
                        return True, mode
            except Exception:
                pass
        return False, None

    def get_safety_mode(self) -> Tuple[bool, Optional[SafetyMode]]:
        """Get current safety mode"""
        response = self._send_command("safetymode")
        if response.success and response.value:
            try:
                mode_str = response.message.split(":")[-1].strip().upper()
                for mode in SafetyMode:
                    if mode.name == mode_str:
                        return True, mode
            except Exception:
                pass
        return False, None

    def is_program_running(self) -> bool:
        """Check if a program is currently running"""
        response = self._send_command("running")
        return response.success and "true" in response.message.lower()

    def get_loaded_program(self) -> Optional[str]:
        """Get currently loaded program path"""
        response = self._send_command("get loaded program")
        if response.success:
            return response.message.split(":")[-1].strip()
        return None

    def get_program_state(self) -> Optional[str]:
        """Get program state (STOPPED, PLAYING, PAUSED)"""
        response = self._send_command("programState")
        if response.success:
            return response.message.split(":")[-1].strip()
        return None

    # Popup Control

    def popup(self, message: str) -> DashboardResponse:
        """Show popup message on teach pendant"""
        return self._send_command(f"popup {message}")

    def close_popup(self) -> DashboardResponse:
        """Close popup on teach pendant"""
        return self._send_command("close popup")

    # Context manager support

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
