import os
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from .models import LLMStreamResponse, FunctionCallRequest, MedicalQuery
from .medical_tools import MedicalFunctionTools
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import hashlib
from dotenv import load_dotenv


load_dotenv()

class LLMServiceWithFunctionCalling:
    """
    Advanced LLM service with function calling capability.
    Combines your MediAssist RAG with function calling.
    """
    
    def __init__(self) -> None:
        """Initialize Gemini client with API key"""
        # Get API key from environment
        self.api_key = os.getenv("GEMINI_API_KEY")  # or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables.\n"
                "Please add GEMINI_API_KEY=your_key_here to your .env file"
            )
        
        print(f"✅ Gemini API Key loaded: {self.api_key[:10]}...")
        
        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)


    async def search_medical_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search medical knowledge using vector search (from your MediAssist).
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of search results
        """
        results = []
        
        if self.embedding_model and self.collection:
            try:
                # Generate embedding
                query_embedding = self.embedding_model.encode([query])[0].tolist()
                
                # Search in ChromaDB
                search_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                if search_results and search_results['ids']:
                    for i in range(len(search_results['ids'][0])):
                        results.append({
                            'document': search_results['documents'][0][i],
                            'metadata': search_results['metadatas'][0][i] if search_results['metadatas'] else {},
                            'distance': search_results['distances'][0][i],
                            'source': 'chromadb'
                        })
            except Exception as e:
                print(f"Vector search error: {e}")
        
        # Fallback to keyword search in medical knowledge
        if not results:
            query_lower = query.lower()
            for topic, facts in self.medical_knowledge.items():
                if topic in query_lower:
                    for fact in facts[:top_k]:
                        results.append({
                            'document': fact,
                            'metadata': {'topic': topic},
                            'distance': 0.1,
                            'source': 'knowledge_base'
                        })
        
        return results[:top_k]
    
    async def process_with_function_calling(
        self, 
        query: str, 
        session_id: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[LLMStreamResponse, None]:
        """
        Process query with function calling capability.
        Demonstrates complex interaction beyond simple Q&A.
        
        Args:
            query: User query
            session_id: Session ID for context
            conversation_history: Previous conversation
            
        Yields:
            Streaming LLM responses
        """
        # Step 1: Search medical knowledge (your MediAssist RAG)
        search_results = await self.search_medical_knowledge(query)
        context = ""
        
        if search_results:
            context_parts = []
            for i, result in enumerate(search_results, 1):
                context_parts.append(f"[Source {i}] {result['document']}")
            context = "\n".join(context_parts)
        
        # Step 2: Prepare messages for LLM
        messages = []
        
        # System message with function calling instructions
        system_message = """You are MediAssist AI, a medical assistant with access to tools.
        
        Available tools:
        1. calculate_bmi - Calculate BMI from weight and height
        2. calculate_dosage - Calculate medication dosage
        3. check_symptoms - Analyze symptoms and suggest conditions
        4. get_medical_guidelines - Fetch medical guidelines
        5. schedule_appointment - Schedule medical appointment
        
        When user asks about medical calculations, symptoms, or appointments, use the appropriate tool.
        Otherwise, provide helpful medical information based on the context provided.
        
        Always add disclaimer: "⚠️ This is for educational purposes. Consult healthcare professional."
        """
        
        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history if available
        if conversation_history:
            # Convert to Gemini format
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                if msg["role"] == "user":
                    messages.append({"role": "user", "content": msg["content"]})
                else:
                    messages.append({"role": "assistant", "content": msg["content"]})
        
        # Add context if available
        if context:
            messages.append({
                "role": "user", 
                "content": f"Context from medical database:\n{context}\n\nUser question: {query}"
            })
        else:
            messages.append({"role": "user", "content": query})
        
        # Step 3: Check if function calling is needed
        requires_function_call = False
        function_to_call = None
        
        # Simple heuristic based on query
        function_triggers = {
            "calculate_bmi": ["bmi", "body mass", "weight height"],
            "calculate_dosage": ["dosage", "dose", "mg", "medication"],
            "check_symptoms": ["symptom", "pain", "fever", "cough"],
            "get_medical_guidelines": ["guideline", "protocol", "standard"],
            "schedule_appointment": ["appointment", "schedule", "book"]
        }
        
        query_lower = query.lower()
        for func_name, triggers in function_triggers.items():
            if any(trigger in query_lower for trigger in triggers):
                requires_function_call = True
                function_to_call = func_name
                break
        
        if requires_function_call and function_to_call:
            # Prepare function call
            function_def = self.available_functions[function_to_call]
            
            # For demo, create simple arguments
            arguments = {}
            if function_to_call == "calculate_bmi":
                arguments = {"weight_kg": 70, "height_cm": 175}
            elif function_to_call == "calculate_dosage":
                arguments = {"medication": "paracetamol", "weight_kg": 70, "condition": "fever"}
            
            yield LLMStreamResponse(
                content=f"I'll use the {function_to_call} tool to help with that...",
                function_call=FunctionCallRequest(
                    name=function_to_call,
                    arguments=arguments
                ),
                is_function_call=True
            )
        else:
            # Step 4: Generate standard response with streaming
            try:
                # Use Gemini for streaming response
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=messages,
                    stream=True
                )
                
                collected_content = ""
                async for chunk in response:
                    if chunk.text:
                        collected_content += chunk.text
                        yield LLMStreamResponse(content=chunk.text)
                
                # Yield completion marker
                yield LLMStreamResponse(is_complete=True)
                
            except Exception as e:
                yield LLMStreamResponse(content=f"Error: {str(e)}")
                yield LLMStreamResponse(is_complete=True)
    
    async def execute_function_call(
        self, 
        function_call: FunctionCallRequest, 
        session_id: str
    ) -> str:
        """
        Execute a function call and return result.
        
        Args:
            function_call: Function call request
            session_id: Session ID for logging
            
        Returns:
            Function execution result
        """
        try:
            result = await MedicalFunctionTools.execute_function(
                function_call.name,
                function_call.arguments
            )
            return result
        except Exception as e:
            return f"Function execution error: {str(e)}"
    
    async def generate_session_summary(
        self, 
        session_events: List[Dict[str, Any]]
    ) -> str:
        """
        Generate summary of session using LLM.
        Based on your MediAssist conversation summarization.
        
        Args:
            session_events: Session events
            
        Returns:
            Session summary
        """
        # Extract conversation
        conversation = []
        for event in session_events:
            if event["event_type"] in ["user_message", "ai_response"]:
                role = "User" if event["event_type"] == "user_message" else "MediAssist"
                conversation.append(f"{role}: {event['content'][:200]}")
        
        if not conversation:
            return "No conversation to summarize."
        
        conversation_text = "\n".join(conversation[-10:])  # Last 10 messages
        
        prompt = f"""Summarize this medical consultation:

{conversation_text}

Provide a concise summary covering:
1. Main topics discussed
2. Any medical calculations or tools used
3. Recommendations provided
4. Follow-up suggestions

Summary:"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Summary generation failed: {str(e)}"