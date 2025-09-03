# data_app/manager.py

import os
import threading
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool, BaseTool
from functools import partial

# Import core agent components
from .agent_core.agent_graph import build_graph, create_default_state
from .agent_core.tools import pdf_rag_tool, sql_tool, csv_rag_tool, tavily_search_tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Manager:
    """
    Enhanced manager for the agent's lifecycle, including data processing and agent invocation.
    This class is a singleton with thread-safety to ensure the agent graph is properly managed.
    """
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(Manager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not Manager._initialized:
            with Manager._lock:
                if not Manager._initialized:
                    self._initialize_manager()
                    Manager._initialized = True
    
    def _initialize_manager(self):
        """Initialize the manager with default settings."""
        self._agent_graph = None
        self._available_tools: Dict[str, BaseTool] = {}
        self._processed_files: Dict[int, Dict[str, Any]] = {}
        self._tool_lock = threading.Lock()
        
        # File processing function mapping
        self._file_processing_func_map = {
            '.pdf': pdf_rag_tool.process_and_vectorize,
            '.db': sql_tool.configure_database,
            '.sqlite': sql_tool.configure_database,
            '.sqlite3': sql_tool.configure_database,
            '.sql': sql_tool.configure_database,
            '.csv': csv_rag_tool.process_and_vectorize,
        }
        
        # File extension to tool mapping
        self._file_tool_map = {
            '.pdf': self._create_pdf_tool,
            '.db': self._create_sql_tool,
            '.sqlite': self._create_sql_tool,
            '.sqlite3': self._create_sql_tool,
            '.sql': self._create_sql_tool,
            '.csv': self._create_csv_tool,
        }
        
        self._initialize_agent()
        logger.info("Agent manager initialized successfully")
    
    def _create_pdf_tool(self, file_id: int) -> BaseTool:
        """Create a PDF-specific tool bound to a file ID."""
        @tool
        def pdf_query_tool(query: str) -> str:
            """Query the uploaded PDF document for information."""
            return pdf_rag_tool.answer_question_on_pdf(query, file_id)
        
        pdf_query_tool.name = f"pdf_tool_{file_id}"
        pdf_query_tool.description = f"Query PDF document with ID {file_id} for information."
        return pdf_query_tool
    
    def _create_csv_tool(self, file_id: int) -> BaseTool:
        """Create a CSV-specific tool bound to a file ID."""
        @tool
        def csv_query_tool(query: str) -> str:
            """Query the uploaded CSV data for information."""
            return csv_rag_tool.answer_question_on_csv(query, file_id)
        
        csv_query_tool.name = f"csv_tool_{file_id}"
        csv_query_tool.description = f"Query CSV data with ID {file_id} for information."
        return csv_query_tool
    
    def _create_sql_tool(self, file_id: int) -> BaseTool:
        """Create a SQL-specific tool bound to a file ID."""
        @tool
        def sql_query_tool(query: str) -> str:
            """Query the uploaded SQL database for information."""
            return sql_tool.query_sql_database(query, file_id)
        
        sql_query_tool.name = f"sql_tool_{file_id}"
        sql_query_tool.description = f"Query SQL database with ID {file_id} for information."
        return sql_query_tool
    
    def _initialize_agent(self):
        """Initialize the agent graph with default tools."""
        try:
            with self._tool_lock:
                # Add the default internet search tool
                self._available_tools = {
                    'tavily_search': tavily_search_tool.search_internet
                }
                
                # Build initial agent graph
                self._agent_graph = build_graph(list(self._available_tools.values()))
                
            logger.info("Agent graph initialized with base tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise RuntimeError(f"Agent initialization failed: {e}")
    
    def _validate_file_input(self, file_path: str, file_id: int) -> bool:
        """Validate file input parameters."""
        if not isinstance(file_path, str) or not file_path.strip():
            logger.error("Invalid file path provided")
            return False
        
        if not isinstance(file_id, int) or file_id <= 0:
            logger.error(f"Invalid file ID: {file_id}. Must be positive integer.")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False
        
        if not os.path.isfile(file_path):
            logger.error(f"Path is not a file: {file_path}")
            return False
        
        return True
    
    def _rebuild_agent_graph(self):
        """Rebuild the agent graph with current tools."""
        try:
            with self._tool_lock:
                tools_list = list(self._available_tools.values())
                self._agent_graph = build_graph(tools_list)
            
            logger.info(f"Agent graph rebuilt with {len(self._available_tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to rebuild agent graph: {e}")
            raise RuntimeError(f"Graph rebuild failed: {e}")
    
    def process_uploaded_file(self, uploaded_file_path: str, file_id: int, 
                            file_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Process a file based on its type and make a new tool available to the agent.
        
        Args:
            uploaded_file_path: Path to the uploaded file
            file_id: Unique identifier for the file
            file_metadata: Optional metadata about the file
        
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Validate inputs
            if not self._validate_file_input(uploaded_file_path, file_id):
                return False
            
            # Check if file is already processed
            if file_id in self._processed_files:
                logger.warning(f"File ID {file_id} already processed. Skipping.")
                return True
            
            # Get file extension
            file_extension = os.path.splitext(uploaded_file_path)[1].lower()
            
            # Check if file type is supported
            processing_func = self._file_processing_func_map.get(file_extension)
            tool_creator = self._file_tool_map.get(file_extension)
            
            if not processing_func or not tool_creator:
                supported_types = list(self._file_processing_func_map.keys())
                logger.error(f"Unsupported file type: {file_extension}. Supported: {supported_types}")
                return False
            
            logger.info(f"Processing file: {uploaded_file_path} (ID: {file_id})")
            
            # Process the file
            success = processing_func(uploaded_file_path, file_id)
            
            if not success:
                logger.error(f"File processing failed for {uploaded_file_path}")
                return False
            
            # Create and add the new tool
            with self._tool_lock:
                tool_name = f"{file_extension[1:]}_tool_{file_id}"  # Remove dot from extension
                new_tool = tool_creator(file_id)
                self._available_tools[tool_name] = new_tool
                
                # Store file metadata
                self._processed_files[file_id] = {
                    'file_path': uploaded_file_path,
                    'file_extension': file_extension,
                    'tool_name': tool_name,
                    'metadata': file_metadata or {},
                    'processed_at': os.path.getctime(uploaded_file_path)
                }
            
            # Rebuild agent graph with new tool
            self._rebuild_agent_graph()
            
            logger.info(f"Successfully processed file and added tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {uploaded_file_path}: {e}")
            return False
    
    def remove_processed_file(self, file_id: int) -> bool:
        """
        Remove a processed file and its associated tool.
        
        Args:
            file_id: ID of the file to remove
        
        Returns:
            bool: True if removal was successful
        """
        try:
            if file_id not in self._processed_files:
                logger.warning(f"File ID {file_id} not found in processed files")
                return False
            
            with self._tool_lock:
                file_info = self._processed_files[file_id]
                tool_name = file_info['tool_name']
                
                # Remove tool from available tools
                if tool_name in self._available_tools:
                    del self._available_tools[tool_name]
                
                # Remove file record
                del self._processed_files[file_id]
            
            # Clean up file-specific data based on type
            file_extension = file_info['file_extension']
            if file_extension == '.pdf':
                pdf_rag_tool.delete_pdf_index(file_id)
            elif file_extension == '.csv':
                csv_rag_tool.delete_csv_index(file_id)
            elif file_extension in ['.db', '.sqlite', '.sqlite3', '.sql']:
                sql_tool.close_database_connection(file_id)
            
            # Rebuild agent graph
            self._rebuild_agent_graph()
            
            logger.info(f"Successfully removed file {file_id} and tool {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing file {file_id}: {e}")
            return False
    
    def get_agent_response(self, query: str, session_id: Optional[str] = None,
                         user_id: Optional[str] = None) -> str:
        """
        Invoke the agent graph with the user's query and return the final answer.
        
        Args:
            query: User's question
            session_id: Optional session identifier
            user_id: Optional user identifier
        
        Returns:
            str: The agent's response
        """
        try:
            # Validate input
            if not isinstance(query, str) or not query.strip():
                return "Please provide a valid question."
            
            if not self._agent_graph:
                logger.error("Agent graph not initialized")
                return "System not ready. Please try again."
            
            # Prepare input with enhanced state
            state = create_default_state(user_id=user_id, session_id=session_id)
            state["messages"] = [HumanMessage(content=query.strip())]
            
            # Configure execution
            config = {
                "configurable": {
                    "thread_id": session_id or "default_thread",
                }
            }
            
            logger.info(f"Processing query: {query[:100]}...")
            
            # Invoke agent
            response = self._agent_graph.invoke(state, config=config)
            
            # Extract final answer
            messages = response.get('messages', [])
            if not messages:
                return "I couldn't generate a response. Please try rephrasing your question."
            
            last_message = messages[-1]
            
            if hasattr(last_message, 'content') and last_message.content:
                logger.info("Successfully generated response")
                return last_message.content
            else:
                return "I couldn't generate a proper response. Please try again."
            
        except Exception as e:
            logger.error(f"Error invoking agent for query '{query}': {e}")
            return "I'm experiencing technical difficulties. Please try again later."
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and statistics."""
        try:
            with self._tool_lock:
                processed_files_info = {}
                for file_id, info in self._processed_files.items():
                    processed_files_info[file_id] = {
                        'file_path': info['file_path'],
                        'file_type': info['file_extension'],
                        'tool_name': info['tool_name']
                    }
                
                return {
                    'agent_initialized': self._agent_graph is not None,
                    'total_tools': len(self._available_tools),
                    'processed_files_count': len(self._processed_files),
                    'processed_files': processed_files_info,
                    'supported_file_types': list(self._file_processing_func_map.keys()),
                    'available_tools': list(self._available_tools.keys())
                }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def list_processed_files(self) -> List[Dict[str, Any]]:
        """Get list of all processed files with their metadata."""
        try:
            with self._tool_lock:
                files_list = []
                for file_id, info in self._processed_files.items():
                    files_list.append({
                        'file_id': file_id,
                        'file_path': info['file_path'],
                        'file_name': os.path.basename(info['file_path']),
                        'file_type': info['file_extension'],
                        'tool_name': info['tool_name'],
                        'processed_at': info.get('processed_at'),
                        'metadata': info.get('metadata', {})
                    })
                
                return sorted(files_list, key=lambda x: x['file_id'])
        except Exception as e:
            logger.error(f"Error listing processed files: {e}")
            return []
    
    def cleanup_all_files(self) -> bool:
        """Remove all processed files and reset the system."""
        try:
            file_ids = list(self._processed_files.keys())
            
            for file_id in file_ids:
                self.remove_processed_file(file_id)
            
            # Reset to base configuration
            self._initialize_agent()
            
            logger.info("Successfully cleaned up all files")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

# Create global instance with proper error handling
try:
    agent_manager = Manager()
except Exception as e:
    logger.error(f"Failed to create agent manager: {e}")
    raise

# Public API functions
def process_file_for_agent(uploaded_file_path: str, file_id: int,
                          file_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Public function for views to process a file.
    
    Args:
        uploaded_file_path: Path to the uploaded file
        file_id: Unique file identifier
        file_metadata: Optional file metadata
    
    Returns:
        bool: True if processing was successful
    """
    return agent_manager.process_uploaded_file(uploaded_file_path, file_id, file_metadata)

def get_answer_from_agent(query: str, session_id: Optional[str] = None,
                         user_id: Optional[str] = None) -> str:
    """
    Public function for views to get a response from the agent.
    
    Args:
        query: User's question
        session_id: Optional session identifier
        user_id: Optional user identifier
    
    Returns:
        str: Agent's response
    """
    return agent_manager.get_agent_response(query, session_id, user_id)

def remove_file_from_agent(file_id: int) -> bool:
    """
    Public function to remove a processed file.
    
    Args:
        file_id: ID of file to remove
    
    Returns:
        bool: True if removal was successful
    """
    return agent_manager.remove_processed_file(file_id)

def get_agent_status() -> Dict[str, Any]:
    """Get current agent system status."""
    return agent_manager.get_system_status()

def list_agent_files() -> List[Dict[str, Any]]:
    """Get list of all processed files."""
    return agent_manager.list_processed_files()

def cleanup_agent_system() -> bool:
    """Clean up entire agent system."""
    return agent_manager.cleanup_all_files()

# Export all public functions
__all__ = [
    'Manager',
    'agent_manager',
    'process_file_for_agent',
    'get_answer_from_agent', 
    'remove_file_from_agent',
    'get_agent_status',
    'list_agent_files',
    'cleanup_agent_system'
]
