# Reusable Modules Reference

This document provides detailed guidance on modules to reuse from the source repositories.

---

## Source Repository 1: Universal_Robot_External_GUI

**URL:** https://github.com/taki-hor/Universal_Robot_External_GUI
**Branch:** `master`

### Module 1: Robot Controller (`robot_controller.py`)

**What to Extract:**

#### RTDE Connection Management
```python
# Key imports
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface

# Connection pattern
class RobotController:
    def __init__(self):
        self.rtde_c = None  # Control interface
        self.rtde_r = None  # Receive interface

    def connect(self):
        self.rtde_c = RTDEControlInterface(self.robot_ip)
        self.rtde_r = RTDEReceiveInterface(self.robot_ip)
```

#### Dashboard Integration
```python
# Dashboard client for program control
import socket

def dashboard_command(self, command: str) -> str:
    """Send command to Dashboard server (port 29999)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((self.robot_ip, 29999))
    sock.send(f"{command}\n".encode())
    response = sock.recv(1024).decode()
    sock.close()
    return response

# Usage:
# dashboard_command("load program.urp")
# dashboard_command("play")
# dashboard_command("stop")
# dashboard_command("unlock protective stop")
```

#### Motion Control Functions
```python
# TCP movement with safety
def move_tcp(self, pose, speed=0.05, accel=0.5):
    if self.safety_monitor.is_within_workspace(pose):
        self.rtde_c.moveL(pose, speed, accel)

# Force mode
def start_force_mode(self, task_frame, selection_vector, wrench, limits):
    self.rtde_c.forceMode(task_frame, selection_vector, wrench, 2, limits)

def stop_force_mode(self):
    self.rtde_c.forceModeStop()

# URScript execution
def execute_urscript_code(self, script: str):
    self.rtde_c.sendCustomScript(script)
```

#### State Monitoring Thread
```python
from PyQt5.QtCore import QThread, pyqtSignal

class DataReceiverThread(QThread):
    """Background thread for real-time robot state"""
    tcp_pose_updated = pyqtSignal(list)
    force_updated = pyqtSignal(list)
    safety_status_updated = pyqtSignal(int)

    def run(self):
        while self.running:
            tcp = self.rtde_r.getActualTCPPose()
            force = self.rtde_r.getActualTCPForce()
            safety = self.rtde_r.getSafetyMode()

            self.tcp_pose_updated.emit(tcp)
            self.force_updated.emit(force)
            self.safety_status_updated.emit(safety)

            time.sleep(1.0 / self.update_rate)
```

**Adaptation for New Project:**
- Remove PyQt5 dependency (use asyncio instead)
- Simplify to essential functions for massage control
- Add RTDE register read/write for pattern control

---

### Module 2: Safety Monitor (`safety_monitor.py`)

**What to Extract:**

#### Force/Torque Thresholds
```python
class SafetyMonitor:
    # From Config
    MAX_FORCE_THRESHOLD = 50.0      # N
    MAX_TORQUE_THRESHOLD = 10.0     # Nm
    WARNING_RATIO = 0.8             # 80%

    FREEDRIVE_MAX_FORCE = 80.0      # N (relaxed for freedrive)
    FREEDRIVE_MAX_TORQUE = 15.0     # Nm

    COLLISION_FORCE_SPIKE = 30.0    # N (sudden increase threshold)
```

#### Force Magnitude Calculation
```python
import math

def calculate_force_magnitude(self, force_vector: list) -> float:
    """Calculate total force from [Fx, Fy, Fz]"""
    fx, fy, fz = force_vector[:3]
    return math.sqrt(fx**2 + fy**2 + fz**2)
```

#### Workspace Boundary Check
```python
from enum import Enum

class SafetyZone(Enum):
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"

def check_position_safety(self, position: list) -> SafetyZone:
    """Check if position is within workspace limits"""
    x, y, z = position[:3]

    # Workspace limits (from Config)
    X_MIN, X_MAX = -0.8, 0.8
    Y_MIN, Y_MAX = -0.8, 0.8
    Z_MIN, Z_MAX = 0.0, 1.2

    WARNING_MARGIN = 0.05  # 5cm warning zone

    # Check critical (outside limits)
    if not (X_MIN <= x <= X_MAX and Y_MIN <= y <= Y_MAX and Z_MIN <= z <= Z_MAX):
        return SafetyZone.CRITICAL

    # Check warning (within margin of limits)
    near_limit = (
        x < X_MIN + WARNING_MARGIN or x > X_MAX - WARNING_MARGIN or
        y < Y_MIN + WARNING_MARGIN or y > Y_MAX - WARNING_MARGIN or
        z < Z_MIN + WARNING_MARGIN or z > Z_MAX - WARNING_MARGIN
    )

    return SafetyZone.WARNING if near_limit else SafetyZone.SAFE
```

#### Collision Detection
```python
def check_collision(self, current_force: float, baseline_force: float) -> bool:
    """Detect collision via force spike"""
    spike = abs(current_force - baseline_force)
    return spike > self.COLLISION_FORCE_SPIKE
```

**Adaptation for New Project:**
- Extract threshold values to `config/robot_limits.yaml`
- Simplify to functions (remove class if not needed)
- Add comfort-level mapping for facial expression

---

### Module 3: Configuration (`config.py`)

**Extract and Convert to YAML:**

```yaml
# config/robot_limits.yaml

connection:
  robot_ip: "192.168.1.100"
  rtde_port: 30004
  dashboard_port: 29999
  rtde_frequency_hz: 125

motion:
  tcp:
    speed_default: 0.05      # m/s
    speed_range: [0.01, 0.5]
    accel_default: 0.5       # m/s²
    accel_range: [0.1, 2.0]
  joint:
    speed_default: 0.1       # rad/s
    speed_range: [0.05, 0.4]
    accel_default: 1.0       # rad/s²
    accel_range: [0.1, 3.0]

force_control:
  target_default: 2.0        # N
  target_range: [0.01, 50.0]
  max_displacement: 0.03     # m
  timeout_seconds: 20

workspace:
  x: [-0.8, 0.8]             # m
  y: [-0.8, 0.8]
  z: [0.0, 1.2]

safety:
  max_force: 50              # N
  max_torque: 10             # Nm
  max_velocity: 1.0          # m/s
  warning_ratio: 0.8
  collision_spike: 30        # N

massage:
  force_range: [5, 30]       # N for massage patterns
  step_force: 2.0            # N per adjustment
```

---

### Module 4: URScript Template (`scripts/example.script`)

**Pattern Template for Resident Script:**

```urscript
# massage_resident.script

def massage_resident():
    # ============================
    # Configuration
    # ============================
    PATTERN_NONE = 0
    PATTERN_LINEAR = 1
    PATTERN_CIRCULAR = 2
    PATTERN_TRIGGER = 3
    PATTERN_KNEADING = 4

    FLAG_STOP = 0
    FLAG_RUN = 1
    FLAG_PAUSE = 2

    # Default positions (adjust for actual setup)
    home_pose = p[0.3, -0.4, 0.3, 0, 3.14, 0]

    # ============================
    # Helper Functions
    # ============================
    def linear_stroke(force_n):
        # Linear pushing motion along calf
        start_pos = get_actual_tcp_pose()
        end_pos = pose_add(start_pos, p[0, 0.15, 0, 0, 0, 0])

        # Enable force mode (Z direction)
        task_frame = p[0, 0, 0, 0, 0, 0]
        selection = [0, 0, 1, 0, 0, 0]
        wrench = [0, 0, force_n, 0, 0, 0]
        limits = [0.1, 0.1, 0.05, 1, 1, 1]

        force_mode(task_frame, selection, wrench, 2, limits)
        movel(end_pos, a=0.3, v=0.05)
        end_force_mode()
    end

    def circular_rubbing(force_n):
        # Circular rubbing motion
        center = get_actual_tcp_pose()
        radius = 0.03  # 3cm circles

        force_mode(p[0,0,0,0,0,0], [0,0,1,0,0,0], [0,0,force_n,0,0,0], 2, [0.1,0.1,0.05,1,1,1])

        # Draw circle
        i = 0
        while i < 360:
            angle = d2r(i)
            offset_x = radius * cos(angle)
            offset_y = radius * sin(angle)
            target = pose_add(center, p[offset_x, offset_y, 0, 0, 0, 0])
            servoj(get_inverse_kin(target), 0, 0, 0.008, 0.1, 300)
            i = i + 10
        end

        end_force_mode()
    end

    def trigger_press(force_n):
        # Point pressure hold
        current_pose = get_actual_tcp_pose()

        force_mode(p[0,0,0,0,0,0], [0,0,1,0,0,0], [0,0,force_n,0,0,0], 2, [0.1,0.1,0.03,1,1,1])
        sleep(2.0)  # Hold for 2 seconds
        end_force_mode()
    end

    def kneading(force_n):
        # Alternating pressure kneading
        i = 0
        while i < 5:
            trigger_press(force_n * 0.8)
            sleep(0.3)
            trigger_press(force_n * 1.0)
            sleep(0.3)
            i = i + 1
        end
    end

    # ============================
    # Main Loop
    # ============================
    while True:
        # Read control registers
        pattern_id = read_input_integer_register(0)
        control_flag = read_input_integer_register(1)
        target_force = read_input_float_register(0)

        # Safety check
        tcp_force = get_tcp_force()
        force_mag = sqrt(tcp_force[0]*tcp_force[0] + tcp_force[1]*tcp_force[1] + tcp_force[2]*tcp_force[2])

        if force_mag > 45:  # Near safety limit
            # Back off slightly
            current = get_actual_tcp_pose()
            safe_pos = pose_add(current, p[0, 0, 0.01, 0, 0, 0])
            movel(safe_pos, a=0.5, v=0.1)
        end

        # Execute based on flags
        if control_flag == FLAG_STOP:
            stopj(1.0)
        elif control_flag == FLAG_PAUSE:
            # Stay in position
            sleep(0.1)
        elif control_flag == FLAG_RUN:
            if pattern_id == PATTERN_LINEAR:
                linear_stroke(target_force)
            elif pattern_id == PATTERN_CIRCULAR:
                circular_rubbing(target_force)
            elif pattern_id == PATTERN_TRIGGER:
                trigger_press(target_force)
            elif pattern_id == PATTERN_KNEADING:
                kneading(target_force)
            end
        end

        # Write output registers
        write_output_float_register(0, tcp_force[0])
        write_output_float_register(1, tcp_force[1])
        write_output_float_register(2, tcp_force[2])
        write_output_integer_register(0, pattern_id)
        write_output_integer_register(1, robot_status())

        sync()
    end
end

massage_resident()
```

---

## Source Repository 2: massage_chatbot

**URL:** https://github.com/taki-hor/massage_chatbot
**Branch:** `master`

### Module 1: Server Routing Pattern (`main.py`)

**What to Extract:**

#### FastAPI Application Structure
```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Massage Robot Voice Control")

# Static files
app.mount("/static", StaticFiles(directory="ui/dist"), name="static")
```

#### Health Endpoint Pattern
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "robot_connected": robot_adapter.is_connected,
        "services": {
            "stt": stt_provider.is_available(),
            "robot": robot_adapter.is_connected
        }
    }
```

#### Streaming Response Pattern
```python
async def generate_state_stream():
    while True:
        state = robot_adapter.read_state()
        yield f"data: {json.dumps(state.__dict__)}\n\n"
        await asyncio.sleep(0.1)

@app.get("/robot/state/stream")
async def robot_state_stream():
    return StreamingResponse(
        generate_state_stream(),
        media_type="text/event-stream"
    )
```

#### WebSocket Pattern
```python
@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive audio chunks
            audio_data = await websocket.receive_bytes()

            # Transcribe
            transcript = await stt_provider.transcribe(audio_data)

            # Parse intent
            intent = parse_intent(transcript)

            # Send back
            await websocket.send_json({
                "transcript": transcript,
                "intent": intent.__dict__
            })
    except Exception as e:
        await websocket.close()
```

---

### Module 2: Synonym Matching Pattern (`synonyms_config.py`)

**Adapt for Intent Keywords:**

```python
# voice/intent_parser.py

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

class IntentAction(Enum):
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

# Keyword groups (Chinese + English)
INTENT_KEYWORDS: Dict[IntentAction, List[str]] = {
    IntentAction.START: [
        "開始", "啟動", "start", "begin", "go", "run",
        "按摩", "開始按摩"
    ],
    IntentAction.STOP: [
        "停止", "結束", "stop", "end", "halt", "quit",
        "停", "不要"
    ],
    IntentAction.PAUSE: [
        "暫停", "等一下", "pause", "wait", "hold"
    ],
    IntentAction.RESUME: [
        "繼續", "resume", "continue", "go on", "再開始"
    ],
    IntentAction.HARDER: [
        "大力", "用力", "harder", "more", "強",
        "加力", "重一點", "harder please", "more force"
    ],
    IntentAction.SOFTER: [
        "輕", "小力", "softer", "less", "gentle",
        "輕一點", "減力", "softer please", "less force"
    ],
    IntentAction.PATTERN_LINEAR: [
        "直線", "推", "linear", "stroke", "推拿"
    ],
    IntentAction.PATTERN_CIRCULAR: [
        "圓", "揉", "circular", "rub", "打圈"
    ],
    IntentAction.PATTERN_TRIGGER: [
        "點", "按", "trigger", "press", "point", "穴位"
    ],
    IntentAction.PATTERN_KNEADING: [
        "捏", "knead", "kneading", "揉捏"
    ],
    IntentAction.REGION_LEFT: [
        "左", "left", "左腿", "左邊"
    ],
    IntentAction.REGION_RIGHT: [
        "右", "right", "右腿", "右邊"
    ],
}

def find_intent_in_text(text: str) -> List[IntentAction]:
    """Find all matching intents in text"""
    text_lower = text.lower()
    found = []

    for action, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found.append(action)
                break

    return found

@dataclass
class Intent:
    action: IntentAction
    pattern: Optional[str] = None
    force_delta: Optional[float] = None
    region: Optional[str] = None

def parse_intent(transcript: str) -> Optional[Intent]:
    """Parse transcript into structured intent"""
    actions = find_intent_in_text(transcript)

    if not actions:
        return None

    # Priority: commands > adjustments > patterns
    primary_action = None
    pattern = None
    force_delta = None
    region = None

    for action in actions:
        if action in [IntentAction.START, IntentAction.STOP,
                      IntentAction.PAUSE, IntentAction.RESUME]:
            primary_action = action
        elif action == IntentAction.HARDER:
            force_delta = 5.0  # +5N
        elif action == IntentAction.SOFTER:
            force_delta = -5.0  # -5N
        elif action.name.startswith("PATTERN_"):
            pattern = action.name.replace("PATTERN_", "").lower()
        elif action.name.startswith("REGION_"):
            region = action.name.replace("REGION_", "").lower()

    if not primary_action:
        if pattern:
            primary_action = IntentAction.START
        elif force_delta:
            primary_action = IntentAction.HARDER if force_delta > 0 else IntentAction.SOFTER

    if not primary_action:
        return None

    return Intent(
        action=primary_action,
        pattern=pattern,
        force_delta=force_delta,
        region=region
    )
```

---

### Module 3: Tailwind Configuration (`tailwind.config.js`)

**Adapt for UI:**

```javascript
// ui/tailwind.config.js

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Medical/healthcare theme
        primary: '#4A90E2',
        secondary: '#7ED9C3',
        success: '#2ECC71',
        warning: '#F1C40F',
        error: '#E74C3C',
        lightBlue: {
          50: '#F0F7FF',
          100: '#E0EFFF',
        },
      },
      spacing: {
        'panel': '400px',
        'topbar': '64px',
      },
      animation: {
        'pulse-listening': 'pulse-listening 1.5s ease-in-out infinite',
        'pulse-recording': 'pulse-recording 1s ease-in-out infinite',
        'bounce-gentle': 'bounce-gentle 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-listening': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
        'pulse-recording': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'bounce-gentle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(74, 144, 226, 0.15)',
        'glow': '0 0 20px rgba(74, 144, 226, 0.3)',
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '24px',
      },
    },
  },
  plugins: [],
}
```

---

### Module 4: Package Configuration (`package.json`)

**Adapt for Vite + React + TypeScript:**

```json
{
  "name": "massage-robot-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.10"
  }
}
```

---

## Quick Reference: File Mapping

| Source Repo | Source File | Target File | Action |
|-------------|-------------|-------------|--------|
| UR GUI | `robot_controller.py` | `robot_control/adapter.py` | Extract & adapt |
| UR GUI | `robot_controller.py` | `robot_control/rtde_client.py` | Extract RTDE parts |
| UR GUI | `robot_controller.py` | `robot_control/dashboard_client.py` | Extract Dashboard parts |
| UR GUI | `safety_monitor.py` | `robot_control/safety.py` | Adapt |
| UR GUI | `config.py` | `config/robot_limits.yaml` | Convert to YAML |
| UR GUI | `scripts/example.script` | `robot_control/scripts/massage_resident.script` | Template base |
| Chatbot | `main.py` | `server/main.py` | Use routing pattern |
| Chatbot | `synonyms_config.py` | `voice/intent_parser.py` | Adapt for intents |
| Chatbot | `tailwind.config.js` | `ui/tailwind.config.js` | Customize |
| Chatbot | `package.json` | `ui/package.json` | Update deps |
