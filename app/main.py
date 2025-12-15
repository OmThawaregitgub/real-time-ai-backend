import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List  # CRITICAL: Add this import
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import logging

# Try importing your services with error handling
try:
    from .llm_service import LLMServiceWithFunctionCalling
    from .supabase_client import SupabaseManager
    from .session_manager import SessionManager
    from .post_session import PostSessionProcessor
    from .models import (
        WebSocketMessage, EventCreate, EventType,
        SessionCreate, FunctionCallResponse
    )
    SERVICES_LOADED = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import some modules: {e}")
    print("Creating minimal app for testing...")
    SERVICES_LOADED = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Medical AI Backend with WebSockets",
    description="Real-time AI backend with function calling and Supabase persistence",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services only if they loaded
if SERVICES_LOADED:
    llm_service = LLMServiceWithFunctionCalling()
    supabase_manager = SupabaseManager()
    session_manager = SessionManager()
    post_processor = PostSessionProcessor(llm_service, supabase_manager)
else:
    # Create dummy services for testing
    llm_service = None
    supabase_manager = None
    session_manager = None
    post_processor = None
    logger.warning("Running in minimal mode - some features disabled")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    if SERVICES_LOADED:
        logger.info("Starting Medical AI Backend Service")
        logger.info("Services initialized: LLM, Supabase, Session Manager")
    else:
        logger.info("Starting Minimal Medical AI Backend Service")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Medical AI Backend with WebSockets",
        "version": "1.0.0",
        "status": "SERVICES_LOADED" if SERVICES_LOADED else "MINIMAL_MODE",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "docs": "/docs",
            "create_session": "/api/sessions" if SERVICES_LOADED else "disabled"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        active_sessions = 0
        if session_manager:
            active_sessions = await session_manager.get_active_session_count()
        
        return {
            "status": "healthy",
            "mode": "full" if SERVICES_LOADED else "minimal",
            "services": {
                "llm": "available" if llm_service else "disabled",
                "supabase": "available" if supabase_manager else "disabled",
                "sessions": f"{active_sessions} active"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Only add session endpoints if services are loaded
if SERVICES_LOADED:
    @app.post("/api/sessions")
    async def create_session(session_data: SessionCreate):
        """
        Create a new session via HTTP.
        """
        try:
            session = await supabase_manager.create_session(session_data)
            
            await supabase_manager.log_event(EventCreate(
                session_id=session["session_id"],
                event_type=EventType.SESSION_START,
                content="Session created via HTTP API",
                metadata={"user_id": session_data.user_id}
            ))
            
            return {
                "success": True,
                "session_id": session["session_id"],
                "message": "Session created successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws/session/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """
        Main WebSocket endpoint for real-time medical conversations.
        """
        await websocket.accept()
        
        session = await supabase_manager.get_session(session_id)
        
        if not session:
            user_id = f"user_{str(uuid.uuid4())[:8]}"
            session = await supabase_manager.create_session(SessionCreate(
                user_id=user_id,
                metadata={"connection_type": "websocket"}
            ))
            session_id = session["session_id"]
        
        await session_manager.create_session(session["user_id"], websocket)
        
        await supabase_manager.log_event(EventCreate(
            session_id=session_id,
            event_type=EventType.SESSION_START,
            content="WebSocket connection established",
            metadata={"user_id": session["user_id"]}
        ))
        
        welcome_message = {
            "type": "system",
            "content": "🔬 Welcome to MediAssist AI!",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(welcome_message)
        
        try:
            while True:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    ws_message = WebSocketMessage(**message)
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Invalid message format: {str(e)}"
                    })
                    continue
                
                await supabase_manager.log_event(EventCreate(
                    session_id=session_id,
                    event_type=EventType.USER_MESSAGE,
                    content=ws_message.content,
                    metadata=ws_message.metadata or {}
                ))
                
                await session_manager.add_message_to_session(
                    session_id,
                    "user",
                    ws_message.content,
                    ws_message.metadata
                )
                
                conversation_history = await session_manager.get_conversation_history(session_id)
                
                async for llm_response in llm_service.process_with_function_calling(
                    query=ws_message.content,
                    session_id=session_id,
                    conversation_history=conversation_history
                ):
                    if llm_response.is_function_call and llm_response.function_call:
                        function_call = llm_response.function_call
                        
                        await supabase_manager.log_event(EventCreate(
                            session_id=session_id,
                            event_type=EventType.FUNCTION_CALL,
                            content=f"Calling function: {function_call.name}",
                            metadata={
                                "function_name": function_call.name,
                                "arguments": function_call.arguments
                            }
                        ))
                        
                        function_result = await llm_service.execute_function_call(
                            function_call,
                            session_id
                        )
                        
                        await supabase_manager.log_event(EventCreate(
                            session_id=session_id,
                            event_type=EventType.FUNCTION_RESULT,
                            content=function_result,
                            metadata={
                                "function_name": function_call.name,
                                "success": True
                            }
                        ))
                        
                        await supabase_manager.log_function_call(
                            session_id,
                            FunctionCallResponse(
                                function_name=function_call.name,
                                arguments=function_call.arguments,
                                result=function_result,
                                success=True
                            )
                        )
                        
                        await websocket.send_json({
                            "type": "function_result",
                            "content": function_result,
                            "function_name": function_call.name,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        await session_manager.add_message_to_session(
                            session_id,
                            "assistant",
                            f"Function result: {function_result}",
                            {"function_call": function_call.name}
                        )
                        
                    elif llm_response.content:
                        await websocket.send_json({
                            "type": "ai_response",
                            "content": llm_response.content,
                            "chunk": True,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        if llm_response.is_complete:
                            history = await session_manager.get_conversation_history(session_id)
                            assistant_messages = [m for m in history if m["role"] == "assistant"]
                            if assistant_messages:
                                last_msg = assistant_messages[-1]
                                await session_manager.add_message_to_session(
                                    session_id,
                                    "assistant",
                                    last_msg["content"],
                                    last_msg.get("metadata", {})
                                )
                                
                                await supabase_manager.log_event(EventCreate(
                                    session_id=session_id,
                                    event_type=EventType.AI_RESPONSE,
                                    content=last_msg["content"][:500],
                                    metadata={"response_type": "streaming"}
                                ))
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
            
            session_data = await session_manager.close_session(session_id)
            
            await supabase_manager.log_event(EventCreate(
                session_id=session_id,
                event_type=EventType.SESSION_END,
                content="WebSocket connection closed",
                metadata={
                    "duration_seconds": session_data.get("duration", 0),
                    "message_count": len(session_data.get("conversation_history", []))
                }
            ))
            
            asyncio.create_task(
                handle_post_session_processing(session_id, session_data)
            )
            
        except Exception as e:
            logger.error(f"Error in WebSocket session {session_id}: {e}")
            
            await supabase_manager.log_event(EventCreate(
                session_id=session_id,
                event_type=EventType.ERROR,
                content=f"WebSocket error: {str(e)}",
                metadata={"error_type": "websocket_error"}
            ))
            
            try:
                await websocket.close(code=1011, reason=str(e))
            except:
                pass

    async def handle_post_session_processing(session_id: str, session_data: Dict[str, Any]):
        """Handle post-session processing"""
        try:
            logger.info(f"Starting post-session processing for {session_id}")
            
            result = await post_processor.process_session(session_id, session_data)
            
            if result["success"]:
                logger.info(f"✅ Session {session_id} processed successfully")
            else:
                logger.error(f"❌ Failed to process session {session_id}: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error in post-session processing for {session_id}: {e}")

    @app.get("/api/sessions/{session_id}/summary")
    async def get_session_summary(session_id: str):
        """Get summary of a session."""
        try:
            session = await supabase_manager.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            events = await supabase_manager.get_session_events(session_id)
            
            return {
                "session_id": session_id,
                "user_id": session["user_id"],
                "start_time": session["start_time"],
                "end_time": session["end_time"],
                "duration": session.get("duration"),
                "summary": session.get("summary"),
                "total_events": len(events),
                "events_by_type": await _count_events_by_type(events)
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _count_events_by_type(events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count events by type"""
        counts = {}
        for event in events:
            event_type = event["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

else:
    @app.get("/api/sessions")
    async def sessions_disabled():
        """Sessions endpoint disabled in minimal mode"""
        return {
            "message": "Sessions disabled - running in minimal mode",
            "hint": "Check if all required modules are installed"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)