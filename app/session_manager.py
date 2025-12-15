import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from .models import EventType

class SessionManager:
    """
    Manages active WebSocket sessions and conversation state.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = asyncio.Lock()
    
    async def create_session(self, user_id: str, websocket) -> str:
        """
        Create a new session.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        async with self.session_lock:
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "user_id": user_id,
                "start_time": datetime.now(),
                "conversation_history": [],
                "function_calls": [],
                "events": [],
                "status": "active"
            }
        
        return session_id
    
    async def add_message_to_session(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add message to session history.
        
        Args:
            session_id: Session ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata
        """
        async with self.session_lock:
            if session_id in self.active_sessions:
                message = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata or {}
                }
                self.active_sessions[session_id]["conversation_history"].append(message)
    
    async def add_event_to_session(
        self,
        session_id: str,
        event_type: EventType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add event to session events.
        
        Args:
            session_id: Session ID
            event_type: Type of event
            content: Event content
            metadata: Optional metadata
        """
        async with self.session_lock:
            if session_id in self.active_sessions:
                event = {
                    "event_type": event_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata or {}
                }
                self.active_sessions[session_id]["events"].append(event)
    
    async def add_function_call(
        self,
        session_id: str,
        function_name: str,
        arguments: Dict[str, Any],
        result: str
    ):
        """
        Add function call to session.
        
        Args:
            session_id: Session ID
            function_name: Function name
            arguments: Function arguments
            result: Function result
        """
        async with self.session_lock:
            if session_id in self.active_sessions:
                function_call = {
                    "function_name": function_name,
                    "arguments": arguments,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                self.active_sessions[session_id]["function_calls"].append(function_call)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        async with self.session_lock:
            return self.active_sessions.get(session_id)
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Conversation history
        """
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            return session["conversation_history"] if session else []
    
    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """
        Close session and return session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data
        """
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session:
                session["status"] = "closed"
                session["end_time"] = datetime.now()
                
                # Calculate duration
                if session["start_time"] and session["end_time"]:
                    duration = (session["end_time"] - session["start_time"]).total_seconds()
                    session["duration"] = int(duration)
                
                # Remove from active sessions
                session_data = self.active_sessions.pop(session_id)
                return session_data
            
            return {}
    
    async def get_active_session_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        async with self.session_lock:
            return len([s for s in self.active_sessions.values() if s["status"] == "active"])