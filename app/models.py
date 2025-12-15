from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from enum import Enum

class EventType(str, Enum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_MESSAGE = "user_message"
    AI_RESPONSE = "ai_response"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"
    SUMMARY = "summary"
    ERROR = "error"

class SessionCreate(BaseModel):
    """Model for creating a new session"""
    user_id: str = Field(..., description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionUpdate(BaseModel):
    """Model for updating session information"""
    end_time: datetime
    duration: int
    summary: str
    status: str = "completed"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EventCreate(BaseModel):
    """Model for creating event log entries"""
    session_id: str
    event_type: EventType
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class WebSocketMessage(BaseModel):
    """Model for WebSocket messages"""
    type: str
    content: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class FunctionCallRequest(BaseModel):
    """Model for function call requests from LLM"""
    name: str
    arguments: Dict[str, Any]

class FunctionCallResponse(BaseModel):
    """Model for function call responses"""
    function_name: str
    arguments: Dict[str, Any]
    result: str
    success: bool

class LLMStreamResponse(BaseModel):
    """Model for streaming LLM responses"""
    content: Optional[str] = None
    function_call: Optional[FunctionCallRequest] = None
    is_function_call: bool = False
    is_complete: bool = False

class MedicalQuery(BaseModel):
    """Model for medical queries (from your MediAssist)"""
    query: str
    context: Optional[List[str]] = None
    require_citation: bool = True

class VectorSearchResult(BaseModel):
    """Model for vector search results"""
    id: str
    document: str
    metadata: Dict[str, Any]
    distance: float
    source: str

class PostSessionSummary(BaseModel):
    """Model for post-session summary"""
    session_id: str
    total_messages: int
    topics_discussed: List[str]
    medical_queries: List[str]
    function_calls_used: List[str]
    summary_text: str
    duration_seconds: int