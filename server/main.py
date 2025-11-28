"""
FastAPI Server for UR10e Voice-Controlled Massage System

Provides:
- REST API endpoints for robot control
- Voice command processing
- WebSocket for real-time state updates
- Static file serving for UI
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

try:
    from .models import (
        RobotStateResponse,
        RobotCommandRequest,
        RobotCommandResponse,
        PatternRequest,
        ForceRequest,
        TranscriptRequest,
        IntentResponse,
        VoiceCommandRequest,
        VoiceCommandResponse,
        HealthResponse,
    )
except ImportError:
    from server.models import (
        RobotStateResponse,
        RobotCommandRequest,
        RobotCommandResponse,
        PatternRequest,
        ForceRequest,
        TranscriptRequest,
        IntentResponse,
        VoiceCommandRequest,
        VoiceCommandResponse,
        HealthResponse,
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import robot and voice modules
try:
    from robot_control import RobotAdapter, create_adapter
    ROBOT_AVAILABLE = True
except ImportError:
    logger.warning("robot_control not available")
    ROBOT_AVAILABLE = False
    RobotAdapter = None

try:
    from voice import parse_intent, get_router, transcribe
    VOICE_AVAILABLE = True
except ImportError:
    logger.warning("voice module not available")
    VOICE_AVAILABLE = False

# Global instances
robot_adapter: Optional[RobotAdapter] = None
ws_clients: set = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global robot_adapter

    logger.info("Starting server...")

    # Initialize robot adapter (mock mode if not configured)
    if ROBOT_AVAILABLE:
        config_path = Path(__file__).parent.parent / 'config' / 'robot_limits.yaml'
        robot_ip = os.environ.get('ROBOT_IP', '192.168.1.100')

        try:
            robot_adapter = create_adapter(robot_ip=robot_ip)
            # Try to connect (will use mock if robot unavailable)
            robot_adapter.connect()
            logger.info(f"Robot adapter initialized (connected: {robot_adapter.is_connected})")
        except Exception as e:
            logger.warning(f"Robot initialization failed: {e}")
            robot_adapter = None

    # Start state broadcast task
    broadcast_task = asyncio.create_task(broadcast_state_loop())

    yield

    # Cleanup
    broadcast_task.cancel()
    if robot_adapter:
        robot_adapter.disconnect()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="UR10e Voice Massage Control",
    description="Voice-controlled massage robot API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Health Endpoints ==========

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server and service health"""
    robot_connected = robot_adapter.is_connected if robot_adapter else False

    return HealthResponse(
        status="healthy",
        robot_connected=robot_connected,
        services={
            "robot": {"available": ROBOT_AVAILABLE, "connected": robot_connected},
            "voice": {"available": VOICE_AVAILABLE},
            "stt": {"available": VOICE_AVAILABLE},
        }
    )


@app.get("/")
async def root():
    """Serve UI or return API info"""
    ui_path = Path(__file__).parent.parent / 'ui' / 'dist' / 'index.html'
    if ui_path.exists():
        return FileResponse(ui_path)
    return {"message": "UR10e Voice Massage Control API", "docs": "/docs"}


# ========== Robot Control Endpoints ==========

@app.get("/robot/state", response_model=RobotStateResponse)
async def get_robot_state():
    """Get current robot state"""
    if not robot_adapter:
        raise HTTPException(status_code=503, detail="Robot not available")

    state = robot_adapter.read_state()
    return RobotStateResponse(**state.to_dict())


@app.post("/robot/connect")
async def connect_robot():
    """Connect to robot"""
    if not robot_adapter:
        raise HTTPException(status_code=503, detail="Robot adapter not initialized")

    success = robot_adapter.connect()
    return {"success": success, "connected": robot_adapter.is_connected}


@app.post("/robot/disconnect")
async def disconnect_robot():
    """Disconnect from robot"""
    if robot_adapter:
        robot_adapter.disconnect()
    return {"success": True, "connected": False}


@app.post("/robot/command", response_model=RobotCommandResponse)
async def execute_command(request: RobotCommandRequest):
    """Execute robot command"""
    if not robot_adapter:
        raise HTTPException(status_code=503, detail="Robot not available")

    try:
        action = request.action.lower()

        if action == "start":
            if request.pattern:
                robot_adapter.set_pattern_by_name(request.pattern)
            else:
                robot_adapter.resume()
            message = f"Started {request.pattern or 'massage'}"

        elif action == "stop":
            robot_adapter.stop()
            message = "Stopped"

        elif action == "pause":
            robot_adapter.pause()
            message = "Paused"

        elif action == "resume":
            robot_adapter.resume()
            message = "Resumed"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        return RobotCommandResponse(
            success=True,
            message=message,
            action=action,
            data={"pattern": request.pattern} if request.pattern else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Command error: {e}")
        return RobotCommandResponse(
            success=False,
            message=str(e),
            action=request.action
        )


@app.post("/robot/pattern")
async def set_pattern(request: PatternRequest):
    """Set massage pattern"""
    if not robot_adapter:
        raise HTTPException(status_code=503, detail="Robot not available")

    success = robot_adapter.set_pattern_by_name(request.pattern)
    return {"success": success, "pattern": request.pattern}


@app.post("/robot/force")
async def set_force(request: ForceRequest):
    """Set or adjust force"""
    if not robot_adapter:
        raise HTTPException(status_code=503, detail="Robot not available")

    if request.force is not None:
        robot_adapter.set_force_target(request.force)
    elif request.delta is not None:
        robot_adapter.adjust_force(request.delta)
    else:
        raise HTTPException(status_code=400, detail="Must provide force or delta")

    state = robot_adapter.read_state()
    return {"success": True, "force": state.target_force}


@app.get("/robot/patterns")
async def get_patterns():
    """Get available massage patterns"""
    if not robot_adapter:
        return {"patterns": ["linear", "circular", "trigger", "kneading"]}
    return {"patterns": robot_adapter.get_pattern_names()}


# ========== Voice Endpoints ==========

@app.post("/voice/intent", response_model=IntentResponse)
async def parse_voice_intent(request: TranscriptRequest):
    """Parse voice transcript to intent"""
    if not VOICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Voice module not available")

    intent = parse_intent(request.text)
    return IntentResponse(**intent.to_dict())


@app.post("/voice/command", response_model=VoiceCommandResponse)
async def execute_voice_command(request: VoiceCommandRequest):
    """Process voice command end-to-end"""
    if not VOICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Voice module not available")

    # Parse intent
    intent = parse_intent(request.transcript)

    # Get router and execute
    router = get_router(robot_adapter)
    result = await router.execute_intent(intent)

    # Get updated state
    state = None
    if robot_adapter:
        state_obj = robot_adapter.read_state()
        state = RobotStateResponse(**state_obj.to_dict())

    return VoiceCommandResponse(
        success=result.success,
        message=result.message,
        action=result.action,
        intent=IntentResponse(**intent.to_dict()),
        robot_state=state
    )


@app.post("/voice/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio file to text"""
    if not VOICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Voice module not available")

    try:
        audio_data = await audio.read()
        text = await transcribe(audio_data)
        return {"transcript": text}
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== WebSocket Endpoints ==========

@app.websocket("/ws/robot-state")
async def websocket_robot_state(websocket: WebSocket):
    """WebSocket for real-time robot state"""
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket client connected ({len(ws_clients)} total)")

    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_ws_command(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(ws_clients)} remaining)")


async def handle_ws_command(websocket: WebSocket, message: dict):
    """Handle WebSocket command"""
    msg_type = message.get("type")

    if msg_type == "command" and robot_adapter:
        action = message.get("action")
        if action == "start":
            pattern = message.get("pattern")
            if pattern:
                robot_adapter.set_pattern_by_name(pattern)
            robot_adapter.resume()
        elif action == "stop":
            robot_adapter.stop()
        elif action == "pause":
            robot_adapter.pause()
        elif action == "harder":
            robot_adapter.increase_force()
        elif action == "softer":
            robot_adapter.decrease_force()

    elif msg_type == "get_state":
        if robot_adapter:
            state = robot_adapter.read_state()
            await websocket.send_json({
                "type": "state",
                "state": state.to_dict()
            })


async def broadcast_state_loop():
    """Broadcast robot state to all connected WebSocket clients"""
    while True:
        if ws_clients and robot_adapter:
            try:
                state = robot_adapter.read_state()
                message = json.dumps({
                    "type": "state",
                    "state": state.to_dict()
                })

                # Broadcast to all clients
                disconnected = set()
                for ws in ws_clients:
                    try:
                        await ws.send_text(message)
                    except Exception:
                        disconnected.add(ws)

                # Remove disconnected clients
                ws_clients.difference_update(disconnected)

            except Exception as e:
                logger.error(f"Broadcast error: {e}")

        await asyncio.sleep(0.1)  # 10 Hz update rate


@app.get("/robot/state/stream")
async def robot_state_stream():
    """SSE stream for robot state"""
    async def generate():
        while True:
            if robot_adapter:
                state = robot_adapter.read_state()
                yield f"data: {json.dumps(state.to_dict())}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# ========== Static Files ==========

# Mount UI static files if available
ui_dist = Path(__file__).parent.parent / 'ui' / 'dist'
if ui_dist.exists():
    app.mount("/assets", StaticFiles(directory=ui_dist / 'assets'), name="assets")


# ========== Main Entry ==========

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the server"""
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server(reload=True)
