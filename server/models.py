"""
API Models for FastAPI Server
Pydantic models for request/response validation
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ========== Robot Models ==========

class RobotStateResponse(BaseModel):
    """Robot state response"""
    is_connected: bool
    is_running: bool
    is_paused: bool
    safety_status: str
    safety_zone: str
    current_pattern: int
    pattern_name: str
    target_force: float
    current_force: float
    tcp_pose: List[float]
    comfort_emoji: str
    comfort_level: float
    timestamp: float


class RobotCommandRequest(BaseModel):
    """Generic robot command request"""
    action: str = Field(..., description="Command action: start, stop, pause, resume")
    pattern: Optional[str] = Field(None, description="Pattern: linear, circular, trigger, kneading")
    force: Optional[float] = Field(None, description="Target force in N")
    force_delta: Optional[float] = Field(None, description="Force adjustment in N")


class RobotCommandResponse(BaseModel):
    """Robot command response"""
    success: bool
    message: str
    action: str
    data: Optional[dict] = None


class PatternRequest(BaseModel):
    """Set pattern request"""
    pattern: str = Field(..., description="Pattern name: linear, circular, trigger, kneading")


class ForceRequest(BaseModel):
    """Set force request"""
    force: Optional[float] = Field(None, ge=5.0, le=30.0, description="Absolute force in N")
    delta: Optional[float] = Field(None, description="Force change in N")


# ========== Voice Models ==========

class TranscriptRequest(BaseModel):
    """Voice transcript request"""
    text: str = Field(..., min_length=1, description="Voice transcript text")


class IntentResponse(BaseModel):
    """Parsed intent response"""
    action: str
    pattern: Optional[str] = None
    force_delta: Optional[float] = None
    region: Optional[str] = None
    confidence: float
    raw_text: str


class VoiceCommandRequest(BaseModel):
    """Full voice command request"""
    transcript: str = Field(..., min_length=1, description="Voice transcript")


class VoiceCommandResponse(BaseModel):
    """Voice command execution response"""
    success: bool
    message: str
    action: str
    intent: IntentResponse
    robot_state: Optional[RobotStateResponse] = None


# ========== Health Models ==========

class ServiceStatus(BaseModel):
    """Individual service status"""
    available: bool
    name: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    robot_connected: bool
    services: dict


# ========== WebSocket Models ==========

class WSMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type: state, command, error")
    data: dict


class WSStateMessage(BaseModel):
    """WebSocket state update"""
    type: str = "state"
    state: RobotStateResponse


class WSCommandMessage(BaseModel):
    """WebSocket command message"""
    type: str = "command"
    action: str
    params: Optional[dict] = None


class WSErrorMessage(BaseModel):
    """WebSocket error message"""
    type: str = "error"
    message: str
    code: Optional[int] = None
