# UR10e Voice-Controlled Leg Massage System — Development Specification

**Version: 2025.12**
**For Codex / Claude Code Development**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Reusable Modules Analysis](#3-reusable-modules-analysis)
4. [Project Directory Structure](#4-project-directory-structure)
5. [Component Specifications](#5-component-specifications)
6. [API Endpoints](#6-api-endpoints)
7. [Development Phases](#7-development-phases)
8. [Integration Points](#8-integration-points)

---

## 1. Project Overview

### 1.1 Purpose

This system demonstrates:
- **Voice control** for operating UR10e robot arm
- Robot executing **leg massage patterns** (4 modes)
- Dual-panel UI:
  - **Voice Command Panel** — displays speech → intent → robot status
  - **Facial Expression Panel** — displays comfort level (😀😐😖) based on TCP force

### 1.2 Scope

- No Dummy Patient / Digital Twin (deferred)
- Pressure sensing via RTDE `actual_TCP_force` (mock data acceptable initially)
- Supports Chinese/English voice commands

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                              │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │      Voice Command Panel     │  │    Facial Expression Panel       │ │
│  │  ┌────────────────────────┐  │  │  ┌────────────────────────────┐  │ │
│  │  │ Transcript: "更大力"   │  │  │  │           😀              │  │ │
│  │  │ Intent: force +5N      │  │  │  │    Comfort Level: 80%      │  │ │
│  │  │ Status: Running        │  │  │  │    Force: 12N              │  │ │
│  │  └────────────────────────┘  │  │  └────────────────────────────┘  │ │
│  └──────────────────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              SERVER LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  /voice/stt │  │/voice/intent│  │/robot/command│  │  /robot/state  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘ │
└─────────┼────────────────┼───────────────┼───────────────────┼──────────┘
          │                │               │                   │
          ▼                ▼               ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             VOICE PIPELINE                               │
│  ┌───────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │   STT Module  │───▶│  Intent Parser │───▶│  Command Router      │   │
│  │ (Whisper/Azure)│    │                │    │                      │   │
│  └───────────────┘    └────────────────┘    └──────────┬───────────┘   │
└─────────────────────────────────────────────────────────┼───────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            ROBOT CONTROL                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        RobotAdapter                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │   │
│  │  │Dashboard Clnt│  │  RTDE Client │  │    Safety Monitor      │ │   │
│  │  │  (Port 29999)│  │  (Port 30004)│  │                        │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                               UR10e ROBOT                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   Resident URScript (massage_resident.script)    │   │
│  │  • Pattern execution loop                                        │   │
│  │  • Force mode control                                            │   │
│  │  • Safety monitoring integration                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Reusable Modules Analysis

### 3.1 From `Universal_Robot_External_GUI`

**Repository:** https://github.com/taki-hor/Universal_Robot_External_GUI

| Source File | Reusable Components | Target in New Project |
|-------------|---------------------|----------------------|
| `robot_controller.py` | RobotController class, RTDE connection, Dashboard integration, motion control, force mode | `robot_control/adapter.py` |
| `safety_monitor.py` | SafetyMonitor class, force thresholds, workspace limits, collision detection | `robot_control/safety.py` |
| `config.py` | Robot IP/ports, RTDE settings, safety limits, motion parameters | `config/robot_limits.yaml` |
| `error_handler.py` | Error handling patterns, logging | `robot_control/error_handler.py` |
| `data_logger.py` | Data logging utilities | `robot_control/data_logger.py` |
| `scripts/example.script` | URScript patterns, motion commands | `robot_control/scripts/massage_resident.script` |

#### Key Classes to Reuse from `robot_controller.py`:

```python
# DataReceiverThread - Background monitoring
class DataReceiverThread(QThread):
    # Signals: tcp_pose, joint_positions, force_data, robot_mode, safety_status
    # Error counting with auto connection loss detection
    # Configurable update rate

# RobotController - Main interface
class RobotController(QObject):
    # RTDEControlInterface + RTDEReceiveInterface
    # connect() / disconnect()
    # move_tcp() / move_joint()
    # enable_freedrive() / disable_freedrive()
    # start_force_mode() / stop_force_mode()
    # execute_urscript_code()
```

#### Key Functions from `safety_monitor.py`:

```python
class SafetyMonitor:
    # Force thresholds: MAX_FORCE_THRESHOLD (50N), MAX_TORQUE_THRESHOLD (10Nm)
    # Warning threshold: 80% of max
    # Freedrive relaxed: 80N force, 15Nm torque
    # Collision spike detection
    # Workspace boundary checking (5cm warning zone)
```

#### Configuration from `config.py`:

```yaml
# Connection
robot_ip: "192.168.1.100"
rtde_port: 30004
dashboard_port: 29999
rtde_frequency: 125  # Hz

# Motion
tcp_speed: 0.05  # m/s (range: 0.01-0.5)
tcp_accel: 0.5   # m/s² (range: 0.1-2.0)

# Force Control
force_target: 2.0  # N (range: 0.01-50.0)
max_displacement: 0.03  # m
force_timeout: 20  # seconds

# Workspace Limits
x_range: [-0.8, 0.8]  # m
y_range: [-0.8, 0.8]  # m
z_range: [0.0, 1.2]   # m

# Safety
max_force: 50  # N
max_torque: 10  # Nm
max_velocity: 1.0  # m/s
```

---

### 3.2 From `massage_chatbot`

**Repository:** https://github.com/taki-hor/massage_chatbot

| Source File | Reusable Components | Target in New Project |
|-------------|---------------------|----------------------|
| `main.py` | FastAPI routing, SSE streaming, health endpoints | `server/main.py` |
| `synonyms_config.py` | Synonym matching pattern, Chinese keyword groups | `voice/intent_parser.py` |
| `tailwind.config.js` | Theme colors, animations, spacing | `ui/tailwind.config.js` |
| `package.json` | Build scripts, dev dependencies | `ui/package.json` |
| `static/app.js` | Frontend JS patterns | `ui/src/` |
| `static/styles_tailwind.css` | Base Tailwind styles | `ui/src/index.css` |

#### Server Patterns from `main.py`:

```python
# FastAPI app structure
app = FastAPI()

# Health/Status endpoints
@app.get("/health")
@app.get("/models")

# Streaming response pattern
@app.post("/api/chat")
async def chat():
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )

# Request models
class TTSRequest(BaseModel):
    text: str
    voice: str = 'default'
    rate: int = 160

class ChatRequest(BaseModel):
    prompt: str
    model: str = 'default'
```

#### Synonym Pattern from `synonyms_config.py`:

```python
# Structure for intent matching
SYNONYM_GROUPS = {
    "creation": ["創辦", "成立", "建立", ...],
    "time": ["時間", "年份", "日期", ...],
    # ...
}

def get_word_synonyms(word: str) -> List[str]:
    """Find all synonyms for a given word"""
    ...

def add_synonym_group(name: str, words: List[str]):
    """Dynamically add synonym groups"""
    ...
```

#### Tailwind Config Highlights:

```javascript
// Healthcare-themed colors
colors: {
    primary: '#4A90E2',
    secondary: '#7ED9C3',
    success: '...',
    error: '...',
}

// Animations for UI feedback
animation: {
    'pulse-recording': '...',
    'pulse-listening': '...',
    'bounce-loading': '...',
}

// Custom spacing
spacing: {
    'sidebar': '320px',
    'topbar': '90px',
}
```

---

## 4. Project Directory Structure

```
massage_robot_voice_control/
│
├── robot_control/                      # Robot control layer
│   ├── __init__.py
│   ├── adapter.py                      # RobotAdapter - main interface
│   ├── rtde_client.py                  # RTDE communication wrapper
│   ├── dashboard_client.py             # Dashboard server client
│   ├── safety.py                       # Safety monitoring
│   ├── error_handler.py                # Error handling utilities
│   └── scripts/
│       └── massage_resident.script     # Resident URScript for massage
│
├── voice/                              # Voice processing layer
│   ├── __init__.py
│   ├── stt.py                          # Speech-to-text (Whisper/Azure)
│   ├── intent_parser.py                # Intent extraction from text
│   └── router.py                       # Route intents to robot commands
│
├── server/                             # API server layer
│   ├── __init__.py
│   ├── main.py                         # FastAPI application
│   └── models.py                       # Pydantic request/response models
│
├── ui/                                 # Frontend (Vite + React + TS)
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoicePanel.tsx          # Voice command display
│   │   │   └── FacialExpression.tsx    # Comfort emoji display
│   │   ├── hooks/
│   │   │   └── useRobotState.ts        # Robot state polling hook
│   │   ├── App.tsx                     # Main application
│   │   ├── main.tsx                    # Entry point
│   │   └── index.css                   # Tailwind imports
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── config/                             # Configuration files
│   ├── robot_limits.yaml               # Robot safety/workspace limits
│   ├── thresholds.yaml                 # Force thresholds for emotions
│   └── intents.yaml                    # Voice command intent mappings
│
├── tests/                              # Test suite
│   ├── test_robot_adapter.py
│   ├── test_intent_parser.py
│   └── test_api.py
│
├── docs/                               # Documentation
│   ├── DEVELOPMENT_SPEC.md             # This file
│   └── API_REFERENCE.md
│
├── requirements.txt                    # Python dependencies
├── Makefile                            # Build/run commands
└── README.md                           # Project overview
```

---

## 5. Component Specifications

### 5.1 RobotAdapter (`robot_control/adapter.py`)

Core interface integrating Dashboard and RTDE clients.

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import IntEnum

class MassagePattern(IntEnum):
    NONE = 0
    LINEAR_STROKE = 1      # 直線推
    CIRCULAR_RUBBING = 2   # 環形揉
    TRIGGER_PRESS = 3      # 點按
    KNEADING = 4           # 揉捏

@dataclass
class RobotState:
    is_connected: bool
    is_running: bool
    safety_status: str
    current_pattern: MassagePattern
    tcp_force: float  # N
    tcp_pose: list    # [x, y, z, rx, ry, rz]

class RobotAdapter:
    """Main robot control interface"""

    def __init__(self, robot_ip: str, rtde_port: int = 30004,
                 dashboard_port: int = 29999):
        ...

    def connect(self) -> bool:
        """Establish RTDE and Dashboard connections"""
        ...

    def disconnect(self) -> None:
        """Close all connections"""
        ...

    def load_and_run_resident(self) -> bool:
        """Load and start the resident URScript via Dashboard"""
        ...

    def stop(self) -> bool:
        """Stop current execution"""
        ...

    def pause(self) -> bool:
        """Pause current execution"""
        ...

    def resume(self) -> bool:
        """Resume paused execution"""
        ...

    def set_pattern(self, pattern: MassagePattern) -> bool:
        """Set massage pattern via RTDE register"""
        ...

    def set_force_target(self, force_n: float) -> bool:
        """Set target force (N) via RTDE register"""
        ...

    def adjust_force(self, delta_n: float) -> bool:
        """Increase/decrease force by delta"""
        ...

    def read_state(self) -> RobotState:
        """Get current robot state"""
        ...
```

### 5.2 Intent Parser (`voice/intent_parser.py`)

Maps voice transcripts to robot commands.

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class IntentAction(Enum):
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    CHANGE_PATTERN = "change_pattern"
    ADJUST_FORCE = "adjust_force"
    CHANGE_REGION = "change_region"

@dataclass
class Intent:
    action: IntentAction
    pattern: Optional[str] = None      # linear, circular, trigger, kneading
    force_delta: Optional[float] = None  # +/- N
    region: Optional[str] = None       # left_calf, right_calf

# Keyword mappings (Chinese + English)
INTENT_KEYWORDS = {
    "start": ["開始", "啟動", "start", "begin", "go"],
    "stop": ["停止", "結束", "stop", "end", "halt"],
    "pause": ["暫停", "pause", "wait"],
    "resume": ["繼續", "resume", "continue"],
    "harder": ["大力", "用力", "harder", "more", "強"],
    "softer": ["輕", "小力", "softer", "less", "gentle"],
    "linear": ["直線", "推", "linear", "stroke"],
    "circular": ["圓", "揉", "circular", "rub"],
    "trigger": ["點", "按", "trigger", "press", "point"],
    "kneading": ["捏", "knead"],
    "left": ["左", "left"],
    "right": ["右", "right"],
}

def parse_intent(transcript: str) -> Intent:
    """Parse voice transcript into structured intent"""
    ...
```

### 5.3 STT Module (`voice/stt.py`)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text"""
        ...

    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Stream transcription"""
        ...

class WhisperSTT(STTProvider):
    """OpenAI Whisper implementation"""
    ...

class AzureSTT(STTProvider):
    """Azure Speech Services implementation"""
    ...
```

### 5.4 UI Components

#### VoicePanel.tsx
```tsx
interface VoicePanelProps {
  transcript: string;
  intent: Intent | null;
  robotStatus: string;
  isListening: boolean;
}

export function VoicePanel({ transcript, intent, robotStatus, isListening }: VoicePanelProps) {
  return (
    <div className="voice-panel">
      <div className="listening-indicator">{isListening ? '🎤' : '⏸️'}</div>
      <div className="transcript">{transcript}</div>
      <div className="intent">{intent?.action}</div>
      <div className="status">{robotStatus}</div>
    </div>
  );
}
```

#### FacialExpression.tsx
```tsx
interface FacialExpressionProps {
  force: number;
  thresholds: { low: number; high: number };
}

export function FacialExpression({ force, thresholds }: FacialExpressionProps) {
  const emoji = force < thresholds.low ? '😀' :
                force > thresholds.high ? '😖' : '😐';

  const comfortLevel = Math.max(0, Math.min(100,
    100 - ((force - thresholds.low) / (thresholds.high - thresholds.low)) * 100
  ));

  return (
    <div className="facial-panel">
      <div className="emoji text-6xl">{emoji}</div>
      <div className="comfort-bar" style={{ width: `${comfortLevel}%` }} />
      <div className="force-display">{force.toFixed(1)}N</div>
    </div>
  );
}
```

---

## 6. API Endpoints

### 6.1 Voice Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/voice/stt` | Transcribe audio | `audio: File` | `{ transcript: string }` |
| POST | `/voice/intent` | Parse intent from text | `{ text: string }` | `Intent` |

### 6.2 Robot Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/robot/connect` | Connect to robot | — | `{ success: bool }` |
| POST | `/robot/command` | Execute command | `Intent` | `{ success: bool }` |
| GET | `/robot/state` | Get current state | — | `RobotState` |
| POST | `/robot/pattern` | Set massage pattern | `{ pattern: int }` | `{ success: bool }` |
| POST | `/robot/force` | Set/adjust force | `{ force?: float, delta?: float }` | `{ success: bool }` |

### 6.3 WebSocket Endpoints

| Endpoint | Description | Messages |
|----------|-------------|----------|
| `/ws/robot-state` | Real-time robot state | `RobotState` (100ms interval) |
| `/ws/voice` | Bidirectional voice stream | Audio chunks / transcripts |

---

## 7. Development Phases

### Phase 1: Robot Control Layer
**Priority: HIGHEST**

| Task | Source Reference | Output |
|------|------------------|--------|
| Dashboard client | `Universal_Robot_External_GUI/robot_controller.py` | `robot_control/dashboard_client.py` |
| RTDE client | `Universal_Robot_External_GUI/robot_controller.py` | `robot_control/rtde_client.py` |
| Safety monitor | `Universal_Robot_External_GUI/safety_monitor.py` | `robot_control/safety.py` |
| Robot adapter | Integrate above | `robot_control/adapter.py` |
| Resident script | Create new | `robot_control/scripts/massage_resident.script` |
| Config | `Universal_Robot_External_GUI/config.py` | `config/robot_limits.yaml` |

### Phase 2: Voice Pipeline
**Priority: HIGH**

| Task | Source Reference | Output |
|------|------------------|--------|
| STT module | New (Whisper/Azure SDK) | `voice/stt.py` |
| Intent parser | `massage_chatbot/synonyms_config.py` | `voice/intent_parser.py` |
| Command router | New | `voice/router.py` |
| Intent config | New | `config/intents.yaml` |

### Phase 3: Server Layer
**Priority: MEDIUM**

| Task | Source Reference | Output |
|------|------------------|--------|
| FastAPI app | `massage_chatbot/main.py` | `server/main.py` |
| Request models | New | `server/models.py` |
| WebSocket handlers | New | `server/main.py` |

### Phase 4: UI Layer
**Priority: MEDIUM**

| Task | Source Reference | Output |
|------|------------------|--------|
| Vite + React setup | New | `ui/` |
| Tailwind config | `massage_chatbot/tailwind.config.js` | `ui/tailwind.config.js` |
| Voice panel | New | `ui/src/components/VoicePanel.tsx` |
| Facial panel | New | `ui/src/components/FacialExpression.tsx` |
| State hooks | New | `ui/src/hooks/` |

### Phase 5: Integration & Testing
**Priority: HIGH**

| Task | Description |
|------|-------------|
| End-to-end flow | Voice → Intent → Robot → State → UI |
| Robot simulation | Mock RTDE for testing without hardware |
| Unit tests | All components |
| Integration tests | API endpoints |

---

## 8. Integration Points

### 8.1 RTDE Register Mapping

| Register | Type | Direction | Purpose |
|----------|------|-----------|---------|
| `input_int_register_0` | int32 | Write | Pattern ID (0-4) |
| `input_int_register_1` | int32 | Write | Control flags (start/pause/stop) |
| `input_double_register_0` | float64 | Write | Target force (N) |
| `output_double_register_0-5` | float64 | Read | TCP force [Fx,Fy,Fz,Tx,Ty,Tz] |
| `output_int_register_0` | int32 | Read | Current pattern |
| `output_int_register_1` | int32 | Read | Safety status |

### 8.2 Dashboard Commands

| Command | Usage |
|---------|-------|
| `load <program.urp>` | Load URP containing resident script |
| `play` | Start program execution |
| `stop` | Stop execution |
| `pause` | Pause execution |
| `unlock protective stop` | Clear protective stop |
| `get robot mode` | Query robot mode |
| `get safety status` | Query safety status |

### 8.3 URScript Resident Pattern

```urscript
# massage_resident.script structure
def massage_resident():
    # Constants
    PATTERN_NONE = 0
    PATTERN_LINEAR = 1
    PATTERN_CIRCULAR = 2
    PATTERN_TRIGGER = 3
    PATTERN_KNEADING = 4

    # Read input registers
    while True:
        pattern_id = read_input_integer_register(0)
        control_flag = read_input_integer_register(1)
        target_force = read_input_float_register(0)

        # Check control flags
        if control_flag == 0:  # stop
            stopj(1.0)
        elif control_flag == 1:  # run
            if pattern_id == PATTERN_LINEAR:
                linear_stroke(target_force)
            elif pattern_id == PATTERN_CIRCULAR:
                circular_rubbing(target_force)
            # ...

        # Write output registers
        tcp_force = get_tcp_force()
        write_output_float_register(0, tcp_force[0])
        # ...

        sync()
    end
end
```

---

## Appendix A: Dependencies

### Python (`requirements.txt`)

```
# Robot control
ur-rtde>=1.5.0

# Server
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0
pydantic>=2.0.0

# Voice
openai-whisper>=20231117
azure-cognitiveservices-speech>=1.30.0

# Utilities
pyyaml>=6.0
python-multipart>=0.0.6
```

### Node.js (`ui/package.json`)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

---

## Appendix B: References

- **Universal_Robot_External_GUI**: https://github.com/taki-hor/Universal_Robot_External_GUI
- **massage_chatbot**: https://github.com/taki-hor/massage_chatbot
- **UR RTDE Documentation**: https://www.universal-robots.com/articles/ur/interface-communication/real-time-data-exchange-rtde-guide/
- **UR Dashboard Server**: https://www.universal-robots.com/articles/ur/dashboard-server-e-series-port-29999/
