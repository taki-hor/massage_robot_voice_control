# UR10e Voice-Controlled Leg Massage System

A voice-controlled robotic massage system using UR10e robot arm with real-time UI feedback.

## Features

- **Voice Control**: Chinese/English voice commands for robot operation
- **4 Massage Patterns**: Linear stroke, circular rubbing, trigger press, kneading
- **Dual-Panel UI**:
  - Voice Command Panel (speech → intent → status)
  - Facial Expression Panel (comfort level: happy/neutral/uncomfortable)
- **Safety Monitoring**: Force limits, workspace boundaries, collision detection

## Architecture

```
User Voice → STT → Intent Parser → Robot Adapter → UR10e
                                        ↓
                                   RTDE State
                                        ↓
                              UI (Force → Emotion)
```

## Project Structure

```
massage_robot_voice_control/
├── robot_control/          # Robot control layer
│   ├── adapter.py          # Main RobotAdapter interface
│   ├── rtde_client.py      # RTDE communication
│   ├── dashboard_client.py # Dashboard server client
│   ├── safety.py           # Safety monitoring
│   └── scripts/            # URScript files
├── voice/                  # Voice processing
│   ├── stt.py             # Speech-to-text
│   ├── intent_parser.py   # Intent extraction
│   └── router.py          # Command routing
├── server/                 # API server (FastAPI)
│   └── main.py
├── ui/                     # Frontend (Vite + React + TS)
│   └── src/
├── config/                 # Configuration files
│   ├── robot_limits.yaml
│   ├── thresholds.yaml
│   └── intents.yaml
└── docs/                   # Documentation
    ├── DEVELOPMENT_SPEC.md
    └── REUSABLE_MODULES.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- UR10e robot (or simulator)

### Installation

```bash
# Python dependencies
pip install -r requirements.txt

# UI dependencies
cd ui && npm install
```

### Running

```bash
# Option 1: Use run.py (recommended)
python run.py

# Option 2: Use uvicorn directly
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# Option 3: Use module syntax
python -m server.main

# Start UI (separate terminal)
cd ui && npm run dev
```

Server will be available at: http://localhost:8000
API Docs at: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/stt` | Transcribe audio |
| POST | `/voice/intent` | Parse text to intent |
| POST | `/robot/command` | Execute robot command |
| GET | `/robot/state` | Get robot state |
| WS | `/ws/robot-state` | Real-time state stream |

## Voice Commands

| Command (中文) | Command (English) | Action |
|----------------|-------------------|--------|
| 開始 | start | Start massage |
| 停止 | stop | Stop robot |
| 暫停 | pause | Pause execution |
| 繼續 | resume | Resume execution |
| 大力 | harder | Increase force +5N |
| 輕一點 | softer | Decrease force -5N |
| 直線推 | linear | Linear stroke pattern |
| 打圈 | circular | Circular rubbing |
| 點按 | trigger | Point pressure |
| 揉捏 | kneading | Kneading pattern |

## Documentation

- [Development Specification](docs/DEVELOPMENT_SPEC.md) - Full system spec
- [Reusable Modules](docs/REUSABLE_MODULES.md) - Code reuse guide

## Source Repositories

This project integrates code from:
- [Universal_Robot_External_GUI](https://github.com/taki-hor/Universal_Robot_External_GUI) - Robot control
- [massage_chatbot](https://github.com/taki-hor/massage_chatbot) - Voice/UI patterns

## License

MIT
