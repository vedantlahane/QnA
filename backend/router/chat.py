"""
Chat Router - Advanced chat endpoints for React frontend
Provides additional chat functionality beyond the main API
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chat", tags=["Advanced Chat"])

# Pydantic models
class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[Dict[str, Any]] = Field(default=None)

class ConversationHistory(BaseModel):
    """Conversation history model"""
    thread_id: str
    messages: List[ChatMessage]
    created_at: str
    updated_at: str

class StreamingQueryRequest(BaseModel):
    """Request for streaming chat"""
    query: str
    thread_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None

# In-memory conversation storage (in production, use a database)
conversations: Dict[str, ConversationHistory] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.get("/conversations")
async def get_conversations():
    """Get all conversation threads"""
    try:
        conversation_list = []
        for thread_id, conversation in conversations.items():
            conversation_list.append({
                "thread_id": thread_id,
                "message_count": len(conversation.messages),
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "last_message": conversation.messages[-1].content[:100] + "..." if conversation.messages else ""
            })
        
        return {
            "success": True,
            "data": conversation_list,
            "message": "Conversations retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{thread_id}")
async def get_conversation(thread_id: str):
    """Get specific conversation history"""
    try:
        if thread_id not in conversations:
            return {
                "success": True,
                "data": {
                    "thread_id": thread_id,
                    "messages": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                "message": "New conversation created"
            }
        
        conversation = conversations[thread_id]
        return {
            "success": True,
            "data": conversation.dict(),
            "message": "Conversation retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{thread_id}")
async def delete_conversation(thread_id: str):
    """Delete a conversation thread"""
    try:
        if thread_id in conversations:
            del conversations[thread_id]
            message = f"Conversation {thread_id} deleted successfully"
        else:
            message = f"Conversation {thread_id} not found"
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{thread_id}/clear")
async def clear_conversation(thread_id: str):
    """Clear messages from a conversation"""
    try:
        if thread_id in conversations:
            conversations[thread_id].messages = []
            conversations[thread_id].updated_at = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": f"Conversation {thread_id} cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_query(request: StreamingQueryRequest):
    """Stream a chat response for real-time UI updates"""
    try:
        from main import agent_graph
        
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        def generate_response():
            """Generator for streaming response"""
            try:
                # This is a simplified streaming implementation
                # In a real implementation, you'd integrate with the agent's streaming capabilities
                
                # Add user message to conversation
                user_message = ChatMessage(
                    role="user",
                    content=request.query,
                    timestamp=datetime.now().isoformat()
                )
                
                if request.thread_id not in conversations:
                    conversations[request.thread_id] = ConversationHistory(
                        thread_id=request.thread_id,
                        messages=[],
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                
                conversations[request.thread_id].messages.append(user_message)
                
                # Yield user message
                yield f"data: {json.dumps({'type': 'user_message', 'data': user_message.dict()})}\n\n"
                
                # Yield processing status
                yield f"data: {json.dumps({'type': 'processing', 'data': {'status': 'analyzing_query'}})}\n\n"
                
                # Process query (this would be async in real implementation)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                response = loop.run_until_complete(
                    agent_graph.process_query(
                        query=request.query,
                        context=request.context,
                        thread_id=request.thread_id
                    )
                )
                loop.close()
                
                # Add assistant response to conversation
                assistant_message = ChatMessage(
                    role="assistant",
                    content=response["message"],
                    timestamp=datetime.now().isoformat(),
                    metadata={
                        "agent_type": response.get("agent_type"),
                        "confidence": response.get("confidence"),
                        "processing_time": response.get("processing_time")
                    }
                )
                
                conversations[request.thread_id].messages.append(assistant_message)
                conversations[request.thread_id].updated_at = datetime.now().isoformat()
                
                # Yield assistant response
                yield f"data: {json.dumps({'type': 'assistant_message', 'data': assistant_message.dict()})}\n\n"
                
                # Yield completion
                yield f"data: {json.dumps({'type': 'complete', 'data': {'success': True}})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            query = message_data.get("query", "")
            context = message_data.get("context", {})
            
            if query:
                # Send processing status
                await websocket.send_text(json.dumps({
                    "type": "processing",
                    "data": {"status": "processing_query"}
                }))
                
                try:
                    from main import agent_graph
                    
                    if agent_graph is None:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"error": "Agent Graph not initialized"}
                        }))
                        continue
                    
                    # Process query
                    response = await agent_graph.process_query(
                        query=query,
                        context=context,
                        thread_id=thread_id
                    )
                    
                    # Send response
                    await websocket.send_text(json.dumps({
                        "type": "response",
                        "data": response
                    }))
                    
                except Exception as e:
                    logger.error(f"Error processing WebSocket query: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"error": str(e)}
                    }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.get("/export/{thread_id}")
async def export_conversation(thread_id: str):
    """Export conversation as JSON"""
    try:
        if thread_id not in conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = conversations[thread_id]
        
        return {
            "success": True,
            "data": {
                "conversation": conversation.dict(),
                "export_timestamp": datetime.now().isoformat()
            },
            "message": "Conversation exported successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
