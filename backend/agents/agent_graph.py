"""
Agent Graph - Orchestrates Multiple Specialized Agents using LangGraph
This module coordinates between the Router, SQL, CSV, and RAG agents to provide comprehensive Q&A capabilities.
Uses LangGraph for proper state management and workflow orchestration.
"""

from typing import Dict, Any, List, Optional, Union, Annotated, TypedDict
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from dataclasses import dataclass
import logging
import asyncio
import os
import tempfile
from datetime import datetime
import json

# Import our specialized agents
from .router_agent import RouterAgent, create_router_agent
from .sql_agent import SQLAgent, create_sql_agent
from .csv_agent import CSVAgent, create_csv_agent
from .rag_agent import RAGAgent, create_rag_agent

logger = logging.getLogger(__name__)

# State definition for LangGraph
class AgentState(TypedDict):
    """State passed between agents in the graph"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    query_classification: Optional[Dict[str, Any]]
    agent_response: Optional[Dict[str, Any]]
    context: Dict[str, Any]
    routing_history: List[str]
    processing_metadata: Dict[str, Any]

@dataclass
class AgentResponse:
    """Standardized response from any agent"""
    success: bool
    response: str
    agent_type: str
    confidence: float
    metadata: Dict[str, Any]
    processing_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "response": self.response,
            "agent_type": self.agent_type,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "error": self.error
        }

class AgentGraph:
    """
    Agent Graph that coordinates multiple specialized agents using LangGraph.
    Routes queries through the Router Agent and delegates to appropriate specialized agents.
    Maintains conversation state and provides comprehensive Q&A capabilities.
    """
    
    def __init__(
        self,
        llm: ChatOpenAI = None,
        embeddings: OpenAIEmbeddings = None,
        sql_database_url: str = None,
        vector_store_path: str = "./vector_store",
        enable_fallback: bool = True,
        enable_memory: bool = True
    ):
        # Initialize shared LLM and embeddings
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.embeddings = embeddings or OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Configuration
        self.sql_database_url = sql_database_url
        self.vector_store_path = vector_store_path
        self.enable_fallback = enable_fallback
        self.enable_memory = enable_memory
        
        # Initialize agents
        self.router_agent = None
        self.sql_agent = None
        self.csv_agent = None
        self.rag_agent = None
        
        # System state
        self.system_context = {
            "has_sql_data": False,
            "has_csv_data": False,
            "has_documents": False,
            "available_agents": [],
            "data_sources": {}
        }
        
        # LangGraph components
        self.graph = None
        self.memory = MemorySaver() if enable_memory else None
        
        # Initialize all agents and build graph
        self._initialize_agents()
        self._build_graph()
    
    def _initialize_agents(self) -> None:
        """Initialize all specialized agents"""
        try:
            # Always initialize router and basic agents
            self.router_agent = create_router_agent(self.llm)
            self.csv_agent = create_csv_agent(self.llm)
            self.rag_agent = create_rag_agent(
                llm=self.llm,
                embeddings=self.embeddings,
                vector_store_path=self.vector_store_path
            )
            
            # Initialize SQL agent if database URL provided
            if self.sql_database_url:
                self.sql_agent = create_sql_agent(
                    database_url=self.sql_database_url,
                    llm=self.llm
                )
                self.system_context["has_sql_data"] = True
            
            # Update available agents
            self._update_system_context()
            
            logger.info("Agent Graph initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow"""
        try:
            # Create the graph
            workflow = StateGraph(AgentState)
            
            # Add nodes
            workflow.add_node("router", self._router_node)
            workflow.add_node("sql_agent", self._sql_agent_node)
            workflow.add_node("csv_agent", self._csv_agent_node)
            workflow.add_node("rag_agent", self._rag_agent_node)
            workflow.add_node("general_agent", self._general_agent_node)
            workflow.add_node("fallback_handler", self._fallback_node)
            workflow.add_node("response_formatter", self._response_formatter_node)
            
            # Add edges - start with router
            workflow.add_edge(START, "router")
            
            # Add conditional edges from router to agents
            workflow.add_conditional_edges(
                "router",
                self._route_decision,
                {
                    "sql": "sql_agent",
                    "csv": "csv_agent", 
                    "rag": "rag_agent",
                    "general": "general_agent",
                    "fallback": "fallback_handler"
                }
            )
            
            # All agents go to response formatter
            workflow.add_edge("sql_agent", "response_formatter")
            workflow.add_edge("csv_agent", "response_formatter")
            workflow.add_edge("rag_agent", "response_formatter")
            workflow.add_edge("general_agent", "response_formatter")
            workflow.add_edge("fallback_handler", "response_formatter")
            
            # End at response formatter
            workflow.add_edge("response_formatter", END)
            
            # Compile the graph
            self.graph = workflow.compile(
                checkpointer=self.memory,
                interrupt_before=None,
                interrupt_after=None
            )
            
            logger.info("LangGraph workflow built successfully")
            
        except Exception as e:
            logger.error(f"Error building graph: {e}")
            raise
    
    # LangGraph Node Methods
    async def _router_node(self, state: AgentState) -> AgentState:
        """Router node that classifies the user query"""
        try:
            user_query = state.get("user_query", "")
            if not user_query and state.get("messages"):
                # Extract query from last human message
                for msg in reversed(state["messages"]):
                    if isinstance(msg, HumanMessage):
                        user_query = msg.content
                        break
            
            # Classify the query
            classification = await self.router_agent.process_query(
                user_query, 
                context=self.system_context
            )
            
            # Update state
            state["query_classification"] = classification
            state["routing_history"] = state.get("routing_history", []) + [classification["should_route_to"]]
            state["processing_metadata"] = {
                "classification_confidence": classification["confidence"],
                "classification_reasoning": classification["reasoning"]
            }
            
            logger.info(f"Query routed to: {classification['should_route_to']} (confidence: {classification['confidence']:.2f})")
            
            return state
            
        except Exception as e:
            logger.error(f"Router node error: {e}")
            state["query_classification"] = {
                "should_route_to": "fallback",
                "confidence": 0.0,
                "reasoning": f"Router error: {str(e)}"
            }
            return state
    
    def _route_decision(self, state: AgentState) -> str:
        """Determine which agent to route to based on classification"""
        classification = state.get("query_classification", {})
        agent_type = classification.get("should_route_to", "general")
        
        # Check if the required agent/data is available
        if agent_type == "sql" and not self.system_context["has_sql_data"]:
            return "fallback"
        elif agent_type == "csv" and not self.system_context["has_csv_data"]:
            return "fallback"
        elif agent_type == "rag" and not self.system_context["has_documents"]:
            return "fallback"
        
        return agent_type
    
    async def _sql_agent_node(self, state: AgentState) -> AgentState:
        """SQL agent processing node"""
        try:
            user_query = state["user_query"]
            context = state.get("context", {})
            
            result = await self.sql_agent.process_natural_language_query(user_query, context)
            
            if result.get("success"):
                agent_response = AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="sql",
                    confidence=0.9,
                    metadata={
                        "sql_query": result.get("sql_query"),
                        "original_query": user_query
                    },
                    processing_time=0.0
                )
            else:
                agent_response = AgentResponse(
                    success=False,
                    response=result.get("error", "SQL processing failed"),
                    agent_type="sql",
                    confidence=0.0,
                    metadata={"error_details": result},
                    processing_time=0.0,
                    error=result.get("error")
                )
            
            state["agent_response"] = agent_response.to_dict()
            state["messages"].append(AIMessage(content=agent_response.response))
            
            return state
            
        except Exception as e:
            logger.error(f"SQL agent node error: {e}")
            error_response = AgentResponse(
                success=False,
                response=f"SQL agent error: {str(e)}",
                agent_type="sql",
                confidence=0.0,
                metadata={"error": str(e)},
                processing_time=0.0,
                error=str(e)
            )
            state["agent_response"] = error_response.to_dict()
            return state
    
    async def _csv_agent_node(self, state: AgentState) -> AgentState:
        """CSV agent processing node"""
        try:
            user_query = state["user_query"]
            context = state.get("context", {})
            
            result = await self.csv_agent.process_natural_language_query(user_query, context)
            
            if result.get("success"):
                agent_response = AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="csv",
                    confidence=0.9,
                    metadata={
                        "dataframe_name": result.get("dataframe_name"),
                        "dataframe_shape": result.get("dataframe_shape"),
                        "original_query": user_query
                    },
                    processing_time=0.0
                )
            else:
                agent_response = AgentResponse(
                    success=False,
                    response=result.get("error", "CSV processing failed"),
                    agent_type="csv",
                    confidence=0.0,
                    metadata={"error_details": result},
                    processing_time=0.0,
                    error=result.get("error")
                )
            
            state["agent_response"] = agent_response.to_dict()
            state["messages"].append(AIMessage(content=agent_response.response))
            
            return state
            
        except Exception as e:
            logger.error(f"CSV agent node error: {e}")
            error_response = AgentResponse(
                success=False,
                response=f"CSV agent error: {str(e)}",
                agent_type="csv",
                confidence=0.0,
                metadata={"error": str(e)},
                processing_time=0.0,
                error=str(e)
            )
            state["agent_response"] = error_response.to_dict()
            return state
    
    async def _rag_agent_node(self, state: AgentState) -> AgentState:
        """RAG agent processing node"""
        try:
            user_query = state["user_query"]
            context = state.get("context", {})
            
            result = await self.rag_agent.answer_question(user_query, context)
            
            if result.get("success"):
                agent_response = AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="rag",
                    confidence=0.9,
                    metadata={
                        "supporting_documents": len(result.get("supporting_documents", [])),
                        "source_count": result.get("source_count", 0),
                        "original_query": user_query
                    },
                    processing_time=0.0
                )
            else:
                agent_response = AgentResponse(
                    success=False,
                    response=result.get("error", "RAG processing failed"),
                    agent_type="rag",
                    confidence=0.0,
                    metadata={"error_details": result},
                    processing_time=0.0,
                    error=result.get("error")
                )
            
            state["agent_response"] = agent_response.to_dict()
            state["messages"].append(AIMessage(content=agent_response.response))
            
            return state
            
        except Exception as e:
            logger.error(f"RAG agent node error: {e}")
            error_response = AgentResponse(
                success=False,
                response=f"RAG agent error: {str(e)}",
                agent_type="rag",
                confidence=0.0,
                metadata={"error": str(e)},
                processing_time=0.0,
                error=str(e)
            )
            state["agent_response"] = error_response.to_dict()
            return state
    
    async def _general_agent_node(self, state: AgentState) -> AgentState:
        """General agent processing node"""
        try:
            user_query = state["user_query"]
            
            # Simple general response using the LLM
            system_prompt = """You are a helpful AI assistant for a Q&A system. Answer the user's question directly and helpfully. 
            If it's a greeting, respond warmly. If it's a question about capabilities, explain what the system can do.
            Keep responses concise and friendly."""
            
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query)
            ])
            
            agent_response = AgentResponse(
                success=True,
                response=response.content,
                agent_type="general",
                confidence=0.8,
                metadata={"original_query": user_query},
                processing_time=0.0
            )
            
            state["agent_response"] = agent_response.to_dict()
            state["messages"].append(AIMessage(content=agent_response.response))
            
            return state
            
        except Exception as e:
            logger.error(f"General agent node error: {e}")
            error_response = AgentResponse(
                success=False,
                response=f"General processing error: {str(e)}",
                agent_type="general",
                confidence=0.0,
                metadata={"error": str(e)},
                processing_time=0.0,
                error=str(e)
            )
            state["agent_response"] = error_response.to_dict()
            return state
    
    async def _fallback_node(self, state: AgentState) -> AgentState:
        """Fallback handler when primary agent is unavailable"""
        try:
            user_query = state["user_query"]
            classification = state.get("query_classification", {})
            intended_agent = classification.get("should_route_to", "unknown")
            
            # Try to find alternative agent
            if intended_agent == "sql" and self.system_context["has_csv_data"]:
                logger.info("Falling back from SQL to CSV agent")
                return await self._csv_agent_node(state)
            elif intended_agent == "csv" and self.system_context["has_sql_data"]:
                logger.info("Falling back from CSV to SQL agent")
                return await self._sql_agent_node(state)
            elif self.system_context["has_documents"]:
                logger.info(f"Falling back from {intended_agent} to RAG agent")
                return await self._rag_agent_node(state)
            else:
                # Final fallback to general
                logger.info(f"Final fallback from {intended_agent} to general agent")
                fallback_message = f"I understand you're asking about {intended_agent} data, but that data source isn't currently available. However, I can help with general questions."
                
                agent_response = AgentResponse(
                    success=True,
                    response=fallback_message,
                    agent_type="fallback",
                    confidence=0.5,
                    metadata={
                        "intended_agent": intended_agent,
                        "fallback_reason": "Data source not available"
                    },
                    processing_time=0.0
                )
                
                state["agent_response"] = agent_response.to_dict()
                state["messages"].append(AIMessage(content=agent_response.response))
                
                return state
            
        except Exception as e:
            logger.error(f"Fallback node error: {e}")
            error_response = AgentResponse(
                success=False,
                response=f"Fallback processing failed: {str(e)}",
                agent_type="fallback",
                confidence=0.0,
                metadata={"error": str(e)},
                processing_time=0.0,
                error=str(e)
            )
            state["agent_response"] = error_response.to_dict()
            return state
    
    async def _response_formatter_node(self, state: AgentState) -> AgentState:
        """Format the final response for the frontend"""
        try:
            agent_response = state.get("agent_response", {})
            classification = state.get("query_classification", {})
            
            # Add additional metadata
            agent_response["metadata"]["routing_info"] = {
                "classification": classification,
                "routing_history": state.get("routing_history", []),
                "system_context": {
                    "available_agents": self.system_context["available_agents"],
                    "data_sources_available": {
                        "sql": self.system_context["has_sql_data"],
                        "csv": self.system_context["has_csv_data"],
                        "documents": self.system_context["has_documents"]
                    }
                }
            }
            
            # Calculate total processing time
            start_time = state.get("processing_metadata", {}).get("start_time")
            if start_time:
                total_time = (datetime.now() - start_time).total_seconds()
                agent_response["processing_time"] = total_time
            
            state["agent_response"] = agent_response
            
            return state
            
        except Exception as e:
            logger.error(f"Response formatter error: {e}")
            # Don't fail here, just log the error
            return state
    
    def _update_system_context(self) -> None:
        """Update system context based on available data sources"""
        available_agents = []
        
        if self.router_agent:
            available_agents.append("router")
        if self.sql_agent and self.system_context["has_sql_data"]:
            available_agents.append("sql")
        if self.csv_agent and self.system_context["has_csv_data"]:
            available_agents.append("csv")
        if self.rag_agent and self.system_context["has_documents"]:
            available_agents.append("rag")
        
        self.system_context["available_agents"] = available_agents
    
    # Main Query Processing (Updated for React Frontend)
    async def process_query(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        thread_id: str = "default",
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process user query through the LangGraph workflow
        
        Args:
            query: User's question or request
            context: Additional context for processing
            thread_id: Thread ID for conversation memory
            stream: Whether to stream the response
            
        Returns:
            Dictionary with comprehensive results formatted for React frontend
        """
        start_time = datetime.now()
        
        try:
            # Prepare initial state
            initial_state = AgentState(
                messages=[HumanMessage(content=query)],
                user_query=query,
                query_classification=None,
                agent_response=None,
                context=context or {},
                routing_history=[],
                processing_metadata={
                    "start_time": start_time,
                    "thread_id": thread_id
                }
            )
            
            # Configure for memory if enabled
            config = {"configurable": {"thread_id": thread_id}} if self.enable_memory else {}
            
            # Execute the graph
            if stream:
                # For streaming responses (useful for React real-time updates)
                events = []
                async for event in self.graph.astream(initial_state, config=config):
                    events.append(event)
                final_state = events[-1] if events else initial_state
            else:
                # Standard execution
                final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Extract response
            agent_response = final_state.get("agent_response", {})
            
            # Format response for React frontend
            response = {
                "success": agent_response.get("success", False),
                "message": agent_response.get("response", "No response generated"),
                "agent_type": agent_response.get("agent_type", "unknown"),
                "confidence": agent_response.get("confidence", 0.0),
                "processing_time": agent_response.get("processing_time", 0.0),
                "metadata": {
                    "query": query,
                    "thread_id": thread_id,
                    "timestamp": start_time.isoformat(),
                    "routing_info": agent_response.get("metadata", {}).get("routing_info", {}),
                    "system_status": self._get_system_status_summary()
                },
                "suggestions": self._get_contextual_suggestions(agent_response.get("agent_type"))
            }
            
            # Add error information if present
            if agent_response.get("error"):
                response["error"] = agent_response["error"]
            
            # Add visualization data if available (for CSV agent)
            if agent_response.get("agent_type") == "csv" and "visualization" in agent_response.get("metadata", {}):
                response["visualization"] = agent_response["metadata"]["visualization"]
            
            # Add SQL query if available (for SQL agent)
            if agent_response.get("agent_type") == "sql" and "sql_query" in agent_response.get("metadata", {}):
                response["sql_query"] = agent_response["metadata"]["sql_query"]
            
            # Add supporting documents if available (for RAG agent)
            if agent_response.get("agent_type") == "rag" and "supporting_documents" in agent_response.get("metadata", {}):
                response["supporting_documents"] = agent_response["metadata"]["supporting_documents"]
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": False,
                "message": f"Error processing query: {str(e)}",
                "agent_type": "error",
                "confidence": 0.0,
                "processing_time": processing_time,
                "error": str(e),
                "metadata": {
                    "query": query,
                    "thread_id": thread_id,
                    "timestamp": start_time.isoformat(),
                    "error_details": str(e)
                },
                "suggestions": ["Please try rephrasing your question", "Check if the required data source is loaded"]
            }
    
    def _get_system_status_summary(self) -> Dict[str, Any]:
        """Get a summary of system status for frontend"""
        return {
            "agents_available": self.system_context["available_agents"],
            "data_sources": {
                "sql_connected": self.system_context["has_sql_data"],
                "csv_loaded": self.system_context["has_csv_data"],
                "documents_loaded": self.system_context["has_documents"]
            },
            "capabilities": {
                "can_query_database": self.system_context["has_sql_data"],
                "can_analyze_csv": self.system_context["has_csv_data"],
                "can_search_documents": self.system_context["has_documents"],
                "can_chat": True
            }
        }
    
    def _get_contextual_suggestions(self, agent_type: str) -> List[str]:
        """Get contextual suggestions based on the agent that was used"""
        base_suggestions = []
        
        if agent_type == "sql" and self.sql_agent:
            base_suggestions = self.sql_agent.get_query_suggestions()[:3]
        elif agent_type == "csv" and self.csv_agent:
            base_suggestions = self.csv_agent.get_query_suggestions()[:3]
        elif agent_type == "rag" and self.rag_agent:
            base_suggestions = self.rag_agent.get_query_suggestions()[:3]
        
        # Add general suggestions
        general_suggestions = [
            "What other data sources are available?",
            "Can you explain this in more detail?",
            "Show me the system status"
        ]
        
        return base_suggestions + general_suggestions
    
    # Data Source Management (Enhanced for React Frontend)
    def connect_sql_database(self, database_url: str) -> Dict[str, Any]:
        """
        Connect to SQL database
        
        Args:
            database_url: Database connection string
            
        Returns:
            Connection status and database info formatted for React
        """
        try:
            if not self.sql_agent:
                self.sql_agent = create_sql_agent(
                    database_url=database_url,
                    llm=self.llm
                )
            else:
                success = self.sql_agent.connect_to_database(database_url)
                if not success:
                    return {
                        "success": False, 
                        "error": "Failed to connect to database",
                        "message": "Database connection failed"
                    }
            
            self.sql_database_url = database_url
            self.system_context["has_sql_data"] = True
            self._update_system_context()
            
            # Get database info
            db_info = self.sql_agent.get_database_info()
            
            return {
                "success": True,
                "message": "SQL database connected successfully",
                "data": {
                    "database_info": db_info,
                    "connection_url": database_url,
                    "tables_available": db_info.get("tables", []),
                    "capabilities": ["query_database", "analytics", "reporting"]
                },
                "system_status": self._get_system_status_summary()
            }
            
        except Exception as e:
            logger.error(f"Error connecting SQL database: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to connect to SQL database"
            }
    
    def load_csv_file(self, file_path: str, name: str = None) -> Dict[str, Any]:
        """
        Load CSV file for analysis
        
        Args:
            file_path: Path to CSV file
            name: Name to store the dataframe under
            
        Returns:
            Loading status and file info formatted for React
        """
        try:
            result = self.csv_agent.load_csv_file(file_path, name)
            
            if result.get("success"):
                self.system_context["has_csv_data"] = True
                self.system_context["data_sources"]["csv"] = {
                    "name": result["name"],
                    "shape": result["shape"],
                    "columns": result["columns"]
                }
                self._update_system_context()
                
                return {
                    "success": True,
                    "message": f"CSV file '{result['name']}' loaded successfully",
                    "data": {
                        "file_info": result,
                        "capabilities": ["data_analysis", "visualization", "statistics"],
                        "sample_data": result.get("sample_data", [])
                    },
                    "system_status": self._get_system_status_summary()
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": "Failed to load CSV file"
                }
            
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error loading CSV file"
            }
    
    def load_csv_from_upload(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Load CSV from uploaded file content (for React file upload)
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            
        Returns:
            Loading status formatted for React
        """
        try:
            # Convert bytes to string
            csv_content = file_content.decode('utf-8')
            name = filename.replace('.csv', '') if filename.endswith('.csv') else filename
            
            result = self.csv_agent.load_csv_from_string(csv_content, name)
            
            if result.get("success"):
                self.system_context["has_csv_data"] = True
                self.system_context["data_sources"]["csv"] = {
                    "name": result["name"],
                    "shape": result["shape"],
                    "columns": result["columns"]
                }
                self._update_system_context()
                
                return {
                    "success": True,
                    "message": f"CSV file '{name}' uploaded and loaded successfully",
                    "data": {
                        "file_info": result,
                        "filename": filename,
                        "capabilities": ["data_analysis", "visualization", "statistics"]
                    },
                    "system_status": self._get_system_status_summary()
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": "Failed to process uploaded CSV file"
                }
            
        except Exception as e:
            logger.error(f"Error loading CSV from upload: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error processing uploaded CSV file"
            }
    
    def load_documents_from_upload(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load documents from uploaded files (for React file upload)
        
        Args:
            files: List of file dictionaries with 'content', 'filename', 'content_type'
            
        Returns:
            Loading status formatted for React
        """
        try:
            total_loaded = 0
            errors = []
            
            for file_info in files:
                try:
                    content = file_info['content']
                    filename = file_info['filename']
                    content_type = file_info.get('content_type', '')
                    
                    # Handle different file types
                    if content_type == 'text/plain' or filename.endswith('.txt'):
                        text_content = content.decode('utf-8') if isinstance(content, bytes) else content
                        result = self.rag_agent.load_document_from_text(text_content, filename)
                    else:
                        # For other file types, save temporarily and load
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
                            tmp_file.write(content if isinstance(content, bytes) else content.encode())
                            tmp_file.flush()
                            result = self.rag_agent.load_document_from_file(tmp_file.name)
                            os.unlink(tmp_file.name)  # Clean up
                    
                    if result.get("success"):
                        total_loaded += 1
                    else:
                        errors.append(f"{filename}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    errors.append(f"{file_info.get('filename', 'unknown')}: {str(e)}")
            
            if total_loaded > 0:
                self.system_context["has_documents"] = True
                self.system_context["data_sources"]["documents"] = self.rag_agent.get_document_summary()
                self._update_system_context()
                
                return {
                    "success": True,
                    "message": f"Successfully loaded {total_loaded} document(s)",
                    "data": {
                        "documents_loaded": total_loaded,
                        "errors": errors,
                        "document_summary": self.rag_agent.get_document_summary(),
                        "capabilities": ["document_search", "question_answering", "summarization"]
                    },
                    "system_status": self._get_system_status_summary()
                }
            else:
                return {
                    "success": False,
                    "error": "No documents were successfully loaded",
                    "message": "Failed to load any documents",
                    "data": {"errors": errors}
                }
            
        except Exception as e:
            logger.error(f"Error loading documents from upload: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error processing uploaded documents"
            }
    
    # System Information and Management (Enhanced for React)
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for React dashboard"""
        try:
            status = {
                "system_info": {
                    "version": "1.0.0",
                    "status": "active",
                    "uptime": "N/A",  # Could track actual uptime
                    "total_queries_processed": "N/A"  # Could track with counter
                },
                "agents": {
                    "router": {
                        "status": "active" if self.router_agent else "inactive",
                        "description": "Query classification and routing"
                    },
                    "sql": {
                        "status": "active" if self.sql_agent else "inactive",
                        "description": "Database queries and analytics",
                        "connected": self.system_context["has_sql_data"]
                    },
                    "csv": {
                        "status": "active" if self.csv_agent else "inactive", 
                        "description": "Spreadsheet and data analysis",
                        "data_loaded": self.system_context["has_csv_data"]
                    },
                    "rag": {
                        "status": "active" if self.rag_agent else "inactive",
                        "description": "Document search and Q&A",
                        "documents_loaded": self.system_context["has_documents"]
                    }
                },
                "data_sources": {},
                "capabilities": {
                    "available_features": [],
                    "supported_file_types": ["CSV", "PDF", "TXT", "MD", "DOCX"],
                    "supported_databases": ["SQLite", "PostgreSQL", "MySQL", "SQL Server"]
                }
            }
            
            # Add detailed data source information
            if self.sql_agent and self.system_context["has_sql_data"]:
                db_info = self.sql_agent.get_database_info()
                status["data_sources"]["sql"] = {
                    "type": "database",
                    "status": "connected",
                    "details": db_info,
                    "capabilities": ["query", "analytics", "reporting"]
                }
                status["capabilities"]["available_features"].append("SQL Queries")
            
            if self.csv_agent and self.system_context["has_csv_data"]:
                df_info = self.csv_agent.list_dataframes()
                status["data_sources"]["csv"] = {
                    "type": "spreadsheet",
                    "status": "loaded",
                    "details": df_info,
                    "capabilities": ["analysis", "visualization", "statistics"]
                }
                status["capabilities"]["available_features"].append("Data Analysis")
            
            if self.rag_agent and self.system_context["has_documents"]:
                doc_info = self.rag_agent.get_document_summary()
                status["data_sources"]["documents"] = {
                    "type": "knowledge_base",
                    "status": "loaded",
                    "details": doc_info,
                    "capabilities": ["search", "qa", "summarization"]
                }
                status["capabilities"]["available_features"].append("Document Q&A")
            
            # Always available
            status["capabilities"]["available_features"].append("General Chat")
            
            return {
                "success": True,
                "data": status,
                "message": "System status retrieved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve system status"
            }
    
    def get_query_suggestions(self) -> Dict[str, Any]:
        """Get comprehensive query suggestions formatted for React"""
        try:
            suggestions = {
                "general": [
                    "Hello, what can you help me with?",
                    "What data sources are available?",
                    "Show me the system status",
                    "What types of questions can I ask?"
                ],
                "by_category": {}
            }
            
            # Add suggestions from available agents
            if self.sql_agent and self.system_context["has_sql_data"]:
                sql_suggestions = self.sql_agent.get_query_suggestions()
                suggestions["by_category"]["sql"] = {
                    "name": "Database Queries",
                    "description": "Ask questions about your database",
                    "examples": sql_suggestions[:5]
                }
            
            if self.csv_agent and self.system_context["has_csv_data"]:
                csv_suggestions = self.csv_agent.get_query_suggestions()
                suggestions["by_category"]["csv"] = {
                    "name": "Data Analysis",
                    "description": "Analyze your CSV data",
                    "examples": csv_suggestions[:5]
                }
            
            if self.rag_agent and self.system_context["has_documents"]:
                rag_suggestions = self.rag_agent.get_query_suggestions()
                suggestions["by_category"]["documents"] = {
                    "name": "Document Questions",
                    "description": "Ask questions about your documents",
                    "examples": rag_suggestions[:5]
                }
            
            return {
                "success": True,
                "data": suggestions,
                "message": "Query suggestions retrieved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error getting query suggestions: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve query suggestions"
            }
    
    def clear_data_source(self, source_type: str) -> Dict[str, Any]:
        """Clear a specific data source"""
        try:
            if source_type == "sql":
                self.sql_agent = None
                self.system_context["has_sql_data"] = False
                self.sql_database_url = None
                message = "SQL database disconnected"
                
            elif source_type == "csv":
                if self.csv_agent:
                    self.csv_agent.dataframes.clear()
                    self.csv_agent.current_df = None
                    self.csv_agent.current_df_name = None
                self.system_context["has_csv_data"] = False
                message = "CSV data cleared"
                
            elif source_type == "documents":
                if self.rag_agent:
                    self.rag_agent.clear_vector_store()
                self.system_context["has_documents"] = False
                message = "Documents cleared"
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown data source type: {source_type}",
                    "message": "Invalid data source type"
                }
            
            self._update_system_context()
            
            return {
                "success": True,
                "message": message,
                "system_status": self._get_system_status_summary()
            }
            
        except Exception as e:
            logger.error(f"Error clearing data source {source_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to clear {source_type} data source"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check for all components"""
        try:
            health = {
                "overall_status": "healthy",
                "components": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Check each component
            components = [
                ("router_agent", self.router_agent),
                ("sql_agent", self.sql_agent),
                ("csv_agent", self.csv_agent),
                ("rag_agent", self.rag_agent),
                ("langgraph", self.graph)
            ]
            
            for name, component in components:
                if component is not None:
                    health["components"][name] = {
                        "status": "healthy",
                        "available": True
                    }
                else:
                    health["components"][name] = {
                        "status": "not_initialized",
                        "available": False
                    }
            
            # Check LLM connectivity
            try:
                test_response = self.llm.invoke("Hello")
                health["components"]["llm"] = {
                    "status": "healthy",
                    "available": True,
                    "model": self.llm.model_name
                }
            except Exception as e:
                health["components"]["llm"] = {
                    "status": "error",
                    "available": False,
                    "error": str(e)
                }
                health["overall_status"] = "degraded"
            
            return {
                "success": True,
                "data": health,
                "message": "Health check completed"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Health check failed"
            }
    
    # Main Query Processing
    async def process_query(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process user query through the agent graph
        
        Args:
            query: User's question or request
            context: Additional context for processing
            
        Returns:
            AgentResponse with results
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Route the query
            routing_result = await self.router_agent.process_query(
                query, 
                context=self.system_context
            )
            
            agent_type = routing_result["should_route_to"]
            confidence = routing_result["confidence"]
            reasoning = routing_result["reasoning"]
            
            logger.info(f"Query routed to {agent_type} (confidence: {confidence:.2f})")
            
            # Step 2: Process with appropriate agent
            if agent_type == "sql" and self.sql_agent and self.system_context["has_sql_data"]:
                result = await self._process_sql_query(query, context)
            elif agent_type == "csv" and self.csv_agent and self.system_context["has_csv_data"]:
                result = await self._process_csv_query(query, context)
            elif agent_type == "rag" and self.rag_agent and self.system_context["has_documents"]:
                result = await self._process_rag_query(query, context)
            elif agent_type == "general":
                result = await self._process_general_query(query, context)
            else:
                # Fallback handling
                if self.enable_fallback:
                    result = await self._handle_fallback(query, context, agent_type)
                else:
                    result = AgentResponse(
                        success=False,
                        response=f"Agent type '{agent_type}' is not available or no data loaded",
                        agent_type=agent_type,
                        confidence=confidence,
                        metadata={"routing": routing_result},
                        processing_time=0.0,
                        error=f"No {agent_type} data available"
                    )
            
            # Add routing metadata
            result.metadata["routing"] = {
                "original_routing": agent_type,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=False,
                response=f"Error processing query: {str(e)}",
                agent_type="error",
                confidence=0.0,
                metadata={"error_details": str(e)},
                processing_time=processing_time,
                error=str(e)
            )
    
    async def _process_sql_query(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Process query with SQL agent"""
        try:
            result = await self.sql_agent.process_natural_language_query(query, context)
            
            if result.get("success"):
                return AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="sql",
                    confidence=0.9,
                    metadata={
                        "sql_query": result.get("sql_query"),
                        "original_query": query
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    response=result.get("error", "SQL processing failed"),
                    agent_type="sql",
                    confidence=0.0,
                    metadata={"error_details": result},
                    error=result.get("error")
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                response=f"SQL agent error: {str(e)}",
                agent_type="sql",
                confidence=0.0,
                metadata={"error": str(e)},
                error=str(e)
            )
    
    async def _process_csv_query(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Process query with CSV agent"""
        try:
            result = await self.csv_agent.process_natural_language_query(query, context)
            
            if result.get("success"):
                return AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="csv",
                    confidence=0.9,
                    metadata={
                        "dataframe_name": result.get("dataframe_name"),
                        "dataframe_shape": result.get("dataframe_shape"),
                        "original_query": query
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    response=result.get("error", "CSV processing failed"),
                    agent_type="csv",
                    confidence=0.0,
                    metadata={"error_details": result},
                    error=result.get("error")
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                response=f"CSV agent error: {str(e)}",
                agent_type="csv",
                confidence=0.0,
                metadata={"error": str(e)},
                error=str(e)
            )
    
    async def _process_rag_query(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Process query with RAG agent"""
        try:
            result = await self.rag_agent.answer_question(query, context)
            
            if result.get("success"):
                return AgentResponse(
                    success=True,
                    response=result["answer"],
                    agent_type="rag",
                    confidence=0.9,
                    metadata={
                        "supporting_documents": len(result.get("supporting_documents", [])),
                        "source_count": result.get("source_count", 0),
                        "original_query": query
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    response=result.get("error", "RAG processing failed"),
                    agent_type="rag",
                    confidence=0.0,
                    metadata={"error_details": result},
                    error=result.get("error")
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                response=f"RAG agent error: {str(e)}",
                agent_type="rag",
                confidence=0.0,
                metadata={"error": str(e)},
                error=str(e)
            )
    
    async def _process_general_query(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Process general queries directly with LLM"""
        try:
            # Simple general response using the LLM
            system_prompt = """You are a helpful AI assistant. Answer the user's question directly and helpfully. 
            If it's a greeting, respond warmly. If it's a question about capabilities, explain what you can do.
            Keep responses concise and friendly."""
            
            response = await self.llm.ainvoke([
                ("system", system_prompt),
                ("human", query)
            ])
            
            return AgentResponse(
                success=True,
                response=response.content,
                agent_type="general",
                confidence=0.8,
                metadata={"original_query": query}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                response=f"General processing error: {str(e)}",
                agent_type="general",
                confidence=0.0,
                metadata={"error": str(e)},
                error=str(e)
            )
    
    async def _handle_fallback(
        self, 
        query: str, 
        context: Dict[str, Any], 
        intended_agent: str
    ) -> AgentResponse:
        """Handle fallback when intended agent is not available"""
        try:
            # Try to route to available agents based on content
            if intended_agent == "sql" and self.system_context["has_csv_data"]:
                logger.info("Falling back from SQL to CSV agent")
                return await self._process_csv_query(query, context)
            elif intended_agent == "csv" and self.system_context["has_sql_data"]:
                logger.info("Falling back from CSV to SQL agent")
                return await self._process_sql_query(query, context)
            elif self.system_context["has_documents"]:
                logger.info(f"Falling back from {intended_agent} to RAG agent")
                return await self._process_rag_query(query, context)
            else:
                # Final fallback to general
                logger.info(f"Falling back from {intended_agent} to general agent")
                fallback_response = f"I understand you're asking about {intended_agent} data, but that data source isn't currently available. However, I can still help with general questions."
                return await self._process_general_query(query, context)
            
        except Exception as e:
            return AgentResponse(
                success=False,
                response=f"Fallback processing failed: {str(e)}",
                agent_type="fallback",
                confidence=0.0,
                metadata={"intended_agent": intended_agent, "error": str(e)},
                error=str(e)
            )
    
    # System Information and Management
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                "system_context": self.system_context,
                "agents": {},
                "data_sources": {}
            }
            
            # Agent status
            status["agents"]["router"] = "active" if self.router_agent else "inactive"
            status["agents"]["sql"] = "active" if self.sql_agent else "inactive"
            status["agents"]["csv"] = "active" if self.csv_agent else "inactive"
            status["agents"]["rag"] = "active" if self.rag_agent else "inactive"
            
            # Data source details
            if self.sql_agent and self.system_context["has_sql_data"]:
                db_info = self.sql_agent.get_database_info()
                status["data_sources"]["sql"] = db_info
            
            if self.csv_agent and self.system_context["has_csv_data"]:
                df_info = self.csv_agent.list_dataframes()
                status["data_sources"]["csv"] = df_info
            
            if self.rag_agent and self.system_context["has_documents"]:
                doc_info = self.rag_agent.get_document_summary()
                status["data_sources"]["rag"] = doc_info
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def get_query_suggestions(self) -> List[str]:
        """Get query suggestions from all available agents"""
        all_suggestions = []
        
        try:
            # Add suggestions from available agents
            if self.sql_agent and self.system_context["has_sql_data"]:
                sql_suggestions = self.sql_agent.get_query_suggestions()
                all_suggestions.extend([f"[SQL] {s}" for s in sql_suggestions[:5]])
            
            if self.csv_agent and self.system_context["has_csv_data"]:
                csv_suggestions = self.csv_agent.get_query_suggestions()
                all_suggestions.extend([f"[CSV] {s}" for s in csv_suggestions[:5]])
            
            if self.rag_agent and self.system_context["has_documents"]:
                rag_suggestions = self.rag_agent.get_query_suggestions()
                all_suggestions.extend([f"[Docs] {s}" for s in rag_suggestions[:5]])
            
            # Add general suggestions
            general_suggestions = [
                "Hello, what can you help me with?",
                "What data sources are available?",
                "Can you give me an overview of the system?",
                "What types of questions can I ask?"
            ]
            all_suggestions.extend(general_suggestions)
            
            return all_suggestions[:20]  # Return top 20 suggestions
            
        except Exception as e:
            logger.error(f"Error getting query suggestions: {e}")
            return ["Error loading suggestions"]

# Factory function for easy instantiation
def create_agent_graph(
    llm: ChatOpenAI = None,
    embeddings: OpenAIEmbeddings = None,
    sql_database_url: str = None,
    vector_store_path: str = "./vector_store"
) -> AgentGraph:
    """Create a configured agent graph instance"""
    return AgentGraph(
        llm=llm,
        embeddings=embeddings,
        sql_database_url=sql_database_url,
        vector_store_path=vector_store_path
    )

# Example usage and testing
if __name__ == "__main__":
    async def test_agent_graph():
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Initialize agent graph
        graph = create_agent_graph()
        
        # Test system status
        print("System Status:")
        status = graph.get_system_status()
        print(f"Available agents: {status['system_context']['available_agents']}")
        
        # Test general queries
        test_queries = [
            "Hello, how are you?",
            "What can you help me with?",
            "What data sources are currently available?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = await graph.process_query(query)
            print(f"Agent: {result.agent_type}")
            print(f"Success: {result.success}")
            print(f"Response: {result.response}")
            print(f"Confidence: {result.confidence}")
            print(f"Processing time: {result.processing_time:.2f}s")
    
    # Run test
    # asyncio.run(test_agent_graph())
