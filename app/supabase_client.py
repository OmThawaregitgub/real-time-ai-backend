import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from .models import SessionCreate, SessionUpdate, EventCreate, FunctionCallResponse

load_dotenv()

class SupabaseManager:
    """
    Manages all Supabase database operations.
    Based on your SQLite skills but adapted for Supabase.
    """
    
    def __init__(self):
        """Initialize Supabase client with environment variables"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
    
    # --- Session Management ---
    
    async def create_session(self, session_data: SessionCreate) -> Dict[str, Any]:
        """
        Create a new session in the database.
        
        Args:
            session_data: Session creation data
            
        Returns:
            Created session record
        """
        session_dict = session_data.model_dump()
        
        # Generate session_id if not provided
        if 'session_id' not in session_dict:
            import uuid
            session_dict['session_id'] = str(uuid.uuid4())
        
        response = self.client.table("sessions").insert(session_dict).execute()
        
        if not response.data:
            raise Exception("Failed to create session")
        
        return response.data[0]
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Session data or None if not found
        """
        response = self.client.table("sessions")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    async def update_session(self, session_id: str, update_data: SessionUpdate) -> Dict[str, Any]:
        """
        Update session with completion data.
        
        Args:
            session_id: Session UUID
            update_data: Update data
            
        Returns:
            Updated session record
        """
        update_dict = update_data.model_dump()
        
        response = self.client.table("sessions")\
            .update(update_dict)\
            .eq("session_id", session_id)\
            .execute()
        
        if not response.data:
            raise Exception("Failed to update session")
        
        return response.data[0]
    
    # --- Event Logging ---
    
    async def log_event(self, event_data: EventCreate) -> Dict[str, Any]:
        """
        Log an event to the session_events table.
        
        Args:
            event_data: Event data to log
            
        Returns:
            Created event record
        """
        event_dict = event_data.model_dump()
        
        response = self.client.table("session_events")\
            .insert(event_dict)\
            .execute()
        
        if not response.data:
            raise Exception("Failed to log event")
        
        return response.data[0]
    
    async def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all events for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            List of event records
        """
        response = self.client.table("session_events")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("timestamp")\
            .execute()
        
        return response.data or []
    
    # --- Function Call Logging ---
    
    async def log_function_call(self, session_id: str, function_call: FunctionCallResponse) -> Dict[str, Any]:
        """
        Log a function call execution.
        
        Args:
            session_id: Session UUID
            function_call: Function call data
            
        Returns:
            Created function call record
        """
        function_data = {
            "session_id": session_id,
            "function_name": function_call.function_name,
            "arguments": function_call.arguments,
            "result": function_call.result
        }
        
        response = self.client.table("function_calls")\
            .insert(function_data)\
            .execute()
        
        if not response.data:
            raise Exception("Failed to log function call")
        
        return response.data[0]
    
    # --- Vector Search Cache ---
    
    async def cache_vector_search(self, query: str, results: List[Dict[str, Any]]) -> bool:
        """
        Cache vector search results for future use.
        Based on your MediAssist RAG pattern.
        
        Args:
            query: Search query
            results: Search results
            
        Returns:
            True if cached successfully
        """
        import hashlib
        
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        
        cache_data = {
            "query_hash": query_hash,
            "query_text": query,
            "search_results": results,
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        try:
            # Try to insert, if conflict then update
            response = self.client.table("vector_cache")\
                .upsert(cache_data)\
                .execute()
            
            return bool(response.data)
        except Exception as e:
            print(f"Failed to cache vector search: {e}")
            return False
    
    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached vector search results.
        
        Args:
            query: Search query
            
        Returns:
            Cached results or None
        """
        import hashlib
        
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        
        response = self.client.table("vector_cache")\
            .select("search_results")\
            .eq("query_hash", query_hash)\
            .gt("expires_at", datetime.now().isoformat())\
            .execute()
        
        if response.data:
            return response.data[0]["search_results"]
        
        return None
    
    # --- Analytics ---
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Session statistics
        """
        # Get events count by type
        events_response = self.client.rpc('get_session_stats', {
            'target_session_id': session_id
        }).execute()
        
        # Get function calls
        functions_response = self.client.table("function_calls")\
            .select("function_name")\
            .eq("session_id", session_id)\
            .execute()
        
        return {
            "events_by_type": events_response.data or {},
            "function_calls": [fc["function_name"] for fc in functions_response.data] if functions_response.data else [],
            "total_events": len(events_response.data) if events_response.data else 0
        }