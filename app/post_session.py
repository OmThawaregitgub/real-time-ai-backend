import asyncio
from typing import Dict, Any, List
from datetime import datetime
from .models import PostSessionSummary

class PostSessionProcessor:
    """
    Handles post-session processing including summary generation.
    """
    
    def __init__(self, llm_service, supabase_manager):
        """
        Initialize post-session processor.
        
        Args:
            llm_service: LLM service instance
            supabase_manager: Supabase manager instance
        """
        self.llm_service = llm_service
        self.supabase = supabase_manager
    
    async def process_session(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process session after WebSocket closes.
        
        Args:
            session_id: Session ID
            session_data: Session data
            
        Returns:
            Processing results
        """
        try:
            # Step 1: Get session events from database
            session_events = await self.supabase.get_session_events(session_id)
            
            # Step 2: Generate session summary using LLM
            summary = await self.llm_service.generate_session_summary(session_events)
            
            # Step 3: Analyze conversation topics
            topics = await self._extract_topics(session_events)
            
            # Step 4: Count medical queries
            medical_queries = await self._extract_medical_queries(session_events)
            
            # Step 5: Get function calls used
            function_calls = await self.supabase.get_session_statistics(session_id)
            
            # Step 6: Create comprehensive summary
            final_summary = PostSessionSummary(
                session_id=session_id,
                total_messages=len([e for e in session_events if e["event_type"] in ["user_message", "ai_response"]]),
                topics_discussed=topics,
                medical_queries=medical_queries,
                function_calls_used=function_calls.get("function_calls", []),
                summary_text=summary,
                duration_seconds=session_data.get("duration", 0)
            )
            
            # Step 7: Update session in database with summary
            await self.supabase.update_session(
                session_id,
                {
                    "end_time": datetime.now().isoformat(),
                    "duration": session_data.get("duration", 0),
                    "summary": summary,
                    "status": "completed",
                    "metadata": {
                        "topics": topics,
                        "medical_queries": medical_queries,
                        "function_calls": function_calls.get("function_calls", []),
                        "processed_at": datetime.now().isoformat()
                    }
                }
            )
            
            # Step 8: Log summary event
            await self.supabase.log_event({
                "session_id": session_id,
                "event_type": "summary",
                "content": summary,
                "metadata": {
                    "topics": topics,
                    "total_messages": final_summary.total_messages,
                    "processing_time": datetime.now().isoformat()
                }
            })
            
            return {
                "success": True,
                "summary": final_summary.model_dump(),
                "message": f"Session {session_id} processed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to process session {session_id}"
            }
    
    async def _extract_topics(self, session_events: List[Dict[str, Any]]) -> List[str]:
        """
        Extract discussion topics from session events.
        
        Args:
            session_events: Session events
            
        Returns:
            List of topics
        """
        topics = set()
        medical_keywords = {
            "diabetes": ["diabetes", "blood sugar", "insulin", "a1c"],
            "hypertension": ["blood pressure", "hypertension", "bp"],
            "heart": ["heart", "cardio", "cholesterol"],
            "diet": ["diet", "nutrition", "food", "eating"],
            "exercise": ["exercise", "workout", "fitness"],
            "medication": ["medication", "drug", "pill", "dose"],
            "symptoms": ["symptom", "pain", "fever", "cough"]
        }
        
        for event in session_events:
            if event["event_type"] == "user_message":
                content_lower = event["content"].lower()
                for topic, keywords in medical_keywords.items():
                    if any(keyword in content_lower for keyword in keywords):
                        topics.add(topic)
        
        return list(topics)[:5]  # Return top 5 topics
    
    async def _extract_medical_queries(self, session_events: List[Dict[str, Any]]) -> List[str]:
        """
        Extract medical queries from session.
        
        Args:
            session_events: Session events
            
        Returns:
            List of medical queries
        """
        medical_queries = []
        medical_indicators = ["what is", "how to", "symptoms", "treatment", "diagnosis", "cause"]
        
        for event in session_events:
            if event["event_type"] == "user_message":
                content = event["content"]
                if any(indicator in content.lower() for indicator in medical_indicators):
                    if len(content) > 10 and len(content) < 200:  # Reasonable length
                        medical_queries.append(content[:150] + "..." if len(content) > 150 else content)
        
        return medical_queries[:10]  # Return top 10 queries