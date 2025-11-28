"""
RTDE Client for UR10e Robot
Real-Time Data Exchange interface for robot state and control

Based on: Universal_Robot_External_GUI/robot_controller.py
Uses ur_rtde library for communication
"""

import logging
import threading
import time
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)

# Try to import ur_rtde, provide mock if not available
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
    RTDE_AVAILABLE = True
except ImportError:
    logger.warning("ur_rtde not installed, using mock interface")
    RTDE_AVAILABLE = False
    RTDEControlInterface = None
    RTDEReceiveInterface = None


class SafetyStatus(IntEnum):
    """UR Safety status codes"""
    NORMAL = 1
    REDUCED = 2
    PROTECTIVE_STOP = 3
    RECOVERY = 4
    SAFEGUARD_STOP = 5
    SYSTEM_EMERGENCY_STOP = 6
    ROBOT_EMERGENCY_STOP = 7
    VIOLATION = 8
    FAULT = 9


class RobotMode(IntEnum):
    """UR Robot mode codes"""
    DISCONNECTED = -1
    CONFIRM_SAFETY = 0
    BOOTING = 1
    POWER_OFF = 2
    POWER_ON = 3
    IDLE = 4
    BACKDRIVE = 5
    RUNNING = 6


@dataclass
class RobotState:
    """Current robot state from RTDE"""
    tcp_pose: List[float] = field(default_factory=lambda: [0.0] * 6)
    tcp_force: List[float] = field(default_factory=lambda: [0.0] * 6)
    joint_positions: List[float] = field(default_factory=lambda: [0.0] * 6)
    joint_velocities: List[float] = field(default_factory=lambda: [0.0] * 6)
    safety_status: SafetyStatus = SafetyStatus.NORMAL
    robot_mode: RobotMode = RobotMode.DISCONNECTED
    is_program_running: bool = False
    timestamp: float = 0.0


class RTDEClient:
    """
    RTDE Client for real-time communication with UR robot

    Provides:
    - Real-time state reading (TCP pose, force, joints, safety)
    - Register read/write for URScript communication
    - Motion control commands
    - Force mode control
    """

    DEFAULT_PORT = 30004
    DEFAULT_FREQUENCY = 125  # Hz

    # RTDE Register mapping for massage control
    INPUT_INT_PATTERN = 0      # Pattern ID (0-4)
    INPUT_INT_CONTROL = 1      # Control flag (0=stop, 1=run, 2=pause)
    INPUT_FLOAT_FORCE = 0      # Target force (N)

    OUTPUT_FLOAT_FORCE_START = 0  # TCP force Fx, Fy, Fz (registers 0-2)
    OUTPUT_INT_PATTERN = 0        # Current pattern
    OUTPUT_INT_STATUS = 1         # Robot status

    def __init__(self, robot_ip: str, frequency: int = DEFAULT_FREQUENCY):
        self.robot_ip = robot_ip
        self.frequency = frequency

        self._rtde_c: Optional[RTDEControlInterface] = None
        self._rtde_r: Optional[RTDEReceiveInterface] = None

        self._connected = False
        self._state = RobotState()
        self._state_lock = threading.Lock()

        self._receiver_thread: Optional[threading.Thread] = None
        self._running = False

        # Callbacks for state updates
        self._callbacks: Dict[str, List[Callable]] = {
            'state_update': [],
            'force_update': [],
            'safety_change': [],
        }

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def state(self) -> RobotState:
        with self._state_lock:
            return RobotState(**self._state.__dict__)

    def connect(self) -> bool:
        """Connect to robot via RTDE"""
        if not RTDE_AVAILABLE:
            logger.warning("RTDE not available, using mock mode")
            self._connected = True
            self._start_mock_receiver()
            return True

        try:
            logger.info(f"Connecting to robot at {self.robot_ip}...")

            # Connect control interface
            self._rtde_c = RTDEControlInterface(self.robot_ip)
            logger.info("RTDE Control interface connected")

            # Connect receive interface
            self._rtde_r = RTDEReceiveInterface(self.robot_ip, self.frequency)
            logger.info("RTDE Receive interface connected")

            self._connected = True

            # Start receiver thread
            self._start_receiver()

            return True

        except Exception as e:
            logger.error(f"RTDE connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from robot"""
        self._running = False

        if self._receiver_thread:
            self._receiver_thread.join(timeout=2.0)
            self._receiver_thread = None

        if self._rtde_c:
            try:
                self._rtde_c.disconnect()
            except Exception:
                pass
            self._rtde_c = None

        if self._rtde_r:
            try:
                self._rtde_r.disconnect()
            except Exception:
                pass
            self._rtde_r = None

        self._connected = False
        logger.info("RTDE disconnected")

    def _start_receiver(self) -> None:
        """Start background receiver thread"""
        self._running = True
        self._receiver_thread = threading.Thread(
            target=self._receiver_loop,
            daemon=True,
            name="RTDEReceiver"
        )
        self._receiver_thread.start()

    def _start_mock_receiver(self) -> None:
        """Start mock receiver for testing without robot"""
        self._running = True
        self._receiver_thread = threading.Thread(
            target=self._mock_receiver_loop,
            daemon=True,
            name="MockRTDEReceiver"
        )
        self._receiver_thread.start()

    def _receiver_loop(self) -> None:
        """Background loop to receive robot state"""
        interval = 1.0 / self.frequency

        while self._running and self._rtde_r:
            try:
                with self._state_lock:
                    self._state.tcp_pose = list(self._rtde_r.getActualTCPPose())
                    self._state.tcp_force = list(self._rtde_r.getActualTCPForce())
                    self._state.joint_positions = list(self._rtde_r.getActualQ())
                    self._state.joint_velocities = list(self._rtde_r.getActualQd())
                    self._state.safety_status = SafetyStatus(self._rtde_r.getSafetyMode())
                    self._state.robot_mode = RobotMode(self._rtde_r.getRobotMode())
                    self._state.is_program_running = self._rtde_r.isConnected()
                    self._state.timestamp = time.time()

                # Notify callbacks
                self._notify_callbacks('state_update', self._state)

            except Exception as e:
                logger.error(f"RTDE receive error: {e}")

            time.sleep(interval)

    def _mock_receiver_loop(self) -> None:
        """Mock receiver for testing"""
        import math
        t = 0.0
        interval = 1.0 / 10  # 10 Hz for mock

        while self._running:
            with self._state_lock:
                # Simulate varying force
                self._state.tcp_force = [
                    5.0 * math.sin(t),
                    3.0 * math.cos(t),
                    10.0 + 5.0 * math.sin(t * 0.5),
                    0.1, 0.1, 0.1
                ]
                self._state.tcp_pose = [0.3, -0.4, 0.3, 0, 3.14, 0]
                self._state.safety_status = SafetyStatus.NORMAL
                self._state.robot_mode = RobotMode.RUNNING
                self._state.is_program_running = True
                self._state.timestamp = time.time()

            self._notify_callbacks('state_update', self._state)
            t += interval
            time.sleep(interval)

    def _notify_callbacks(self, event: str, data: Any) -> None:
        """Notify registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def on(self, event: str, callback: Callable) -> None:
        """Register callback for event"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    # Register Read/Write for URScript communication

    def write_input_int_register(self, index: int, value: int) -> bool:
        """Write to input integer register"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.setInputIntRegister(index, value)
            return True
        except Exception as e:
            logger.error(f"Write int register failed: {e}")
            return False

    def write_input_float_register(self, index: int, value: float) -> bool:
        """Write to input float register"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.setInputDoubleRegister(index, value)
            return True
        except Exception as e:
            logger.error(f"Write float register failed: {e}")
            return False

    def read_output_int_register(self, index: int) -> Optional[int]:
        """Read output integer register"""
        if not self._rtde_r:
            return None
        try:
            return self._rtde_r.getOutputIntRegister(index)
        except Exception as e:
            logger.error(f"Read int register failed: {e}")
            return None

    def read_output_float_register(self, index: int) -> Optional[float]:
        """Read output float register"""
        if not self._rtde_r:
            return None
        try:
            return self._rtde_r.getOutputDoubleRegister(index)
        except Exception as e:
            logger.error(f"Read float register failed: {e}")
            return None

    # Motion Control

    def move_l(self, pose: List[float], speed: float = 0.05,
               acceleration: float = 0.5, asynchronous: bool = False) -> bool:
        """Linear move to pose"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.moveL(pose, speed, acceleration, asynchronous)
            return True
        except Exception as e:
            logger.error(f"MoveL failed: {e}")
            return False

    def move_j(self, joints: List[float], speed: float = 0.1,
               acceleration: float = 1.0, asynchronous: bool = False) -> bool:
        """Joint move"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.moveJ(joints, speed, acceleration, asynchronous)
            return True
        except Exception as e:
            logger.error(f"MoveJ failed: {e}")
            return False

    def stop_robot(self, deceleration: float = 1.0) -> bool:
        """Stop robot motion"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.stopL(deceleration)
            return True
        except Exception as e:
            logger.error(f"Stop failed: {e}")
            return False

    # Force Mode Control

    def start_force_mode(self, task_frame: List[float],
                         selection_vector: List[int],
                         wrench: List[float],
                         force_type: int = 2,
                         limits: List[float] = None) -> bool:
        """
        Start force mode

        Args:
            task_frame: Pose of force frame
            selection_vector: 6-element list, 1 = force control, 0 = position control
            wrench: Target force/torque [Fx, Fy, Fz, Tx, Ty, Tz]
            force_type: 1 = force frame, 2 = tool frame
            limits: Max allowed speed/deviation
        """
        if not self._rtde_c:
            return False

        if limits is None:
            limits = [0.1, 0.1, 0.1, 1.0, 1.0, 1.0]

        try:
            self._rtde_c.forceMode(task_frame, selection_vector, wrench, force_type, limits)
            return True
        except Exception as e:
            logger.error(f"Force mode start failed: {e}")
            return False

    def stop_force_mode(self) -> bool:
        """Stop force mode"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.forceModeStop()
            return True
        except Exception as e:
            logger.error(f"Force mode stop failed: {e}")
            return False

    # URScript Execution

    def send_script(self, script: str) -> bool:
        """Send URScript code for execution"""
        if not self._rtde_c:
            return False
        try:
            # Remove any BOM or special characters
            script = script.strip()
            self._rtde_c.sendCustomScript(script)
            return True
        except Exception as e:
            logger.error(f"Script send failed: {e}")
            return False

    # Freedrive Mode

    def enable_freedrive(self) -> bool:
        """Enable freedrive mode"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.teachMode()
            return True
        except Exception as e:
            logger.error(f"Freedrive enable failed: {e}")
            return False

    def disable_freedrive(self) -> bool:
        """Disable freedrive mode"""
        if not self._rtde_c:
            return False
        try:
            self._rtde_c.endTeachMode()
            return True
        except Exception as e:
            logger.error(f"Freedrive disable failed: {e}")
            return False

    # Utility

    def get_tcp_force_magnitude(self) -> float:
        """Calculate total TCP force magnitude"""
        import math
        with self._state_lock:
            fx, fy, fz = self._state.tcp_force[:3]
            return math.sqrt(fx*fx + fy*fy + fz*fz)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
