"""
Agent Manager Module for Q&A System

This module provides the core management functionality for the Q&A agent system.
It implements a singleton pattern to manage the agent's lifecycle, handle file
processing, and coordinate interactions between the agent and various tools.

The module serves as the main interface between the Django application views
and the underlying agent system, providing a clean API for file processing
and question answering.

Key Features:
    - Singleton pattern for efficient resource management
    - Dynamic tool registration based on uploaded files
    - Lazy loading of agent graph for performance
    - Comprehensive error handling and logging
    - Support for multiple file types (PDF, CSV, SQL)

Architecture:
    The Manager class acts as a central coordinator that:
    1. Maintains a registry of available tools
    2. Processes uploaded files and creates corresponding tools
    3. Builds and manages the agent graph with current tools
    4. Handles user queries and returns agent responses

Supported File Types:
    - PDF: Document Q&A using RAG (Retrieval-Augmented Generation)
    - CSV: Tabular data Q&A using RAG
    - SQL: Database schema analysis and query generation

Dependencies:
    - langchain_core: For message handling
    - agent_core.agent_graph: For agent graph construction
    - agent_core.tools: For file processing and tool functions

Integration:
    This module is designed to be used by Django views for:
    - File upload processing
    - Question answering
    - Agent lifecycle management

Author: Q&A Agent System
Created: 2025
"""

import os
from typing import Dict, List, Any, Optional, Union
from langchain_core.messages import HumanMessage, AIMessage

# Import core agent components
from .agent_core.agent_graph import build_graph
from .agent_core.tools import pdf_rag_tool, sql_tool, csv_rag_tool, tavily_search_tool


class Manager:
    """
    Singleton manager for the Q&A agent's lifecycle and operations.

    This class implements the singleton pattern to ensure only one instance
    manages the agent throughout the application lifecycle. It handles:

    - Agent graph initialization and rebuilding
    - Dynamic tool registration for uploaded files
    - File processing coordination
    - Query processing and response generation

    The manager uses lazy loading for the agent graph to minimize startup time
    and rebuilds the graph dynamically when new tools are added.

    Class Attributes:
        _instance: Singleton instance reference (internal use only)
        _agent_graph: Compiled LangGraph agent (internal use only)
        _available_tools: Dictionary mapping tool names to tool functions
        _file_processing_func_map: Mapping of file extensions to processing functions

    Instance Attributes:
        Dynamically managed through singleton pattern

    Example:
        >>> manager = Manager()
        >>> manager.process_uploaded_file("document.pdf", 123)
        >>> response = manager.get_agent_response("What is in the document?")
        >>> print(response)
        "The document contains information about..."
    """

    # Class-level attributes for singleton pattern
    _instance = None
    _agent_graph = None

    # Dictionary to hold tool name to function mapping
    # Key: tool name (string), Value: callable tool function
    _available_tools: Dict[str, Any] = {}

    # Mapping of file extensions to their respective processing functions
    # This allows easy extension for new file types
    _file_processing_func_map = {
        '.pdf': pdf_rag_tool.process_and_vectorize,
        '.sql': sql_tool.configure_database,
        '.csv': csv_rag_tool.process_and_vectorize,
    }

    def __new__(cls, *args, **kwargs) -> 'Manager':
        """
        Create or return the singleton instance of Manager.

        This method ensures only one Manager instance exists throughout
        the application lifecycle, implementing the singleton pattern.

        Args:
            *args: Variable positional arguments (passed to __init__)
            **kwargs: Variable keyword arguments (passed to __init__)

        Returns:
            Manager: The singleton instance of the Manager class

        Note:
            The singleton pattern prevents multiple agent graphs from
            being created, ensuring efficient resource usage.
        """
        if not cls._instance:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_agent()
        return cls._instance

    def _initialize_agent(self) -> None:
        """
        Initialize the agent with default tools and build the initial graph.

        This method sets up the basic agent configuration with the default
        internet search tool and creates the initial agent graph. The graph
        will be rebuilt dynamically when new tools are added.

        The initialization includes:
        1. Setting up default tools (internet search)
        2. Building the initial agent graph
        3. Logging successful initialization

        Note:
            This method is called automatically during singleton instantiation.
            Manual calling may cause duplicate initialization.
        """
        # Start with the tavily search tool as the default
        # This provides basic internet search capability
        self._available_tools = {
            'tavily_search': tavily_search_tool.search_internet
        }

        # Build the initial agent graph with default tools
        # The graph will be rebuilt when new file-based tools are added
        self._agent_graph = build_graph(list(self._available_tools.values()))

        print("Agent manager initialized. Agent graph is ready.")

    def process_uploaded_file(self, uploaded_file_path: str, file_id: int) -> bool:
        """
        Process an uploaded file and make it available as a tool to the agent.
        Returns True on success, False on failure.

        This method handles file processing based on file type, creates
        appropriate tools, and rebuilds the agent graph to include the new tool.

        The process involves:
        1. File type detection and validation
        2. Calling appropriate processing function
        3. Creating tool mapping for the processed file
        4. Rebuilding agent graph with new tool

        Args:
            uploaded_file_path (str): Absolute path to the uploaded file
            file_id (int): Unique identifier for the file (from database)

        Returns:
            bool: True if file processed and tool registered successfully, False otherwise

        Raises:
            None: All exceptions are caught internally and logged

        Supported File Types:
            - .pdf: Creates PDF RAG tool for document Q&A
            - .csv: Creates CSV RAG tool for tabular data Q&A
            - .sql: Creates SQL tool for database query generation

        Example:
            >>> manager.process_uploaded_file("/uploads/document.pdf", 123)
            Processing file: /uploads/document.pdf
            Successfully processed file and rebuilt agent with new tool: pdf_tool_123

        Note:
            The method uses file extension to determine processing type.
            Unsupported file types are logged and ignored.
        """
        # Extract and normalize file extension for case-insensitive comparison
        # os.path.splitext returns (path, extension) tuple
        file_extension = os.path.splitext(uploaded_file_path)[1].lower()

        # Get the appropriate processing function based on file extension
        processing_func = self._file_processing_func_map.get(file_extension)

        if not processing_func:
            print(f"Unsupported file type: {file_extension}. File not processed.")
            return False

        print(f"Processing file: {uploaded_file_path}")

        try:
            # Execute the file processing function
            # Each processing function handles vectorization and storage
            processing_func(uploaded_file_path, file_id)

            # Create dynamic tool mapping based on file type and ID
            # Tool names include file_id to ensure uniqueness
            if file_extension == '.pdf':
                tool_name = f"pdf_tool_{file_id}"
                new_tool = pdf_rag_tool.answer_question_on_pdf
            elif file_extension == '.csv':
                tool_name = f"csv_tool_{file_id}"
                new_tool = csv_rag_tool.answer_question_on_csv
            elif file_extension == '.sql':
                tool_name = f"sql_tool_{file_id}"
                new_tool = sql_tool.query_sql_database
            else:
                # This shouldn't happen due to the check above, but safety first
                print(f"Unexpected file extension: {file_extension}")
                return False

            # Register the new tool in the available tools dictionary
            self._available_tools[tool_name] = new_tool

            # Rebuild the agent graph with the updated tool set
            # This ensures the agent can use the newly processed file
            self._agent_graph = build_graph(list(self._available_tools.values()))

            print(f"Successfully processed file and rebuilt agent with new tool: {tool_name}")
            return True

        except Exception as e:
            # Comprehensive error handling for file processing failures
            print(f"Error processing file: {e}")
            return False

    def get_agent_response(self, query: str) -> str:
        """
        Process a user query through the agent and return the response.

        This method serves as the main interface for question answering.
        It invokes the agent graph with the user's query and extracts
        the final answer from the agent's response.

        The process involves:
        1. Validating agent graph availability
        2. Formatting query as LangChain message
        3. Invoking agent with proper configuration
        4. Extracting and returning the final answer

        Args:
            query (str): The user's question or query string

        Returns:
            str: The agent's response to the query, or error message if failed

        Raises:
            None: All exceptions are caught internally and return error strings

        Example:
            >>> response = manager.get_agent_response("What is machine learning?")
            >>> print(response)
            "Machine learning is a subset of artificial intelligence..."

        Note:
            The method uses a default thread_id for conversation continuity.
            For multi-user applications, consider using unique thread_ids per user.
        """
        # Ensure agent graph is available (fallback for edge cases)
        if not self._agent_graph:
            print("Warning: Agent graph not found, reinitializing...")
            self._initialize_agent()

        # Format the query as a LangChain HumanMessage
        # This follows LangChain's message format for agent interactions
        inputs = {"messages": [HumanMessage(content=query)]}

        # Configuration for the agent execution
        # thread_id enables conversation memory and state persistence
        config = {"configurable": {"thread_id": "default_thread"}}

        try:
            # Invoke the agent graph with the query
            # The agent will automatically select appropriate tools based on the query
            response = self._agent_graph.invoke(inputs, config=config)

            # Extract the final answer from the last message in the response
            # LangGraph returns a dictionary with 'messages' containing the conversation
            messages = response.get('messages', [])
            if messages:
                last_message = messages[-1]
                # Return the content of the last message (should be the agent's final answer)
                return last_message.content
            else:
                return "No response generated by the agent."

        except Exception as e:
            # Handle various potential errors during agent invocation
            print(f"Error invoking agent: {e}")
            return "Sorry, I am unable to process your request at this time."


# --- Global Manager Instance ---
# Create a single global instance for easy access throughout the application
# This follows the singleton pattern established in the Manager class
agent_manager = Manager()


def process_file_for_agent(uploaded_file_path: str, file_id: int) -> bool:
    """
    Public interface function for processing uploaded files.
    Returns True on success, False on failure.
    """
    return agent_manager.process_uploaded_file(uploaded_file_path, file_id)


def get_answer_from_agent(query: str) -> str:
    """
    Public interface function for getting agent responses.

    This function provides a clean API for Django views and other components
    to query the agent without directly accessing the Manager class.

    Args:
        query (str): The user's question or query

    Returns:
        str: The agent's response to the query

    Example:
        >>> answer = get_answer_from_agent("What is AI?")
        >>> print(answer)
        "AI stands for Artificial Intelligence..."

    Note:
        This function uses the global agent_manager instance.
        All queries go through the singleton Manager for consistency.
    """
    return agent_manager.get_agent_response(query)


"""
USAGE INFORMATION:

This module provides the main interface for the Q&A agent system:

1. File Processing:
   >>> from data_app.manager import process_file_for_agent
   >>> process_file_for_agent("/path/to/file.pdf", 123)

2. Question Answering:
   >>> from data_app.manager import get_answer_from_agent
   >>> answer = get_answer_from_agent("What is in the document?")

3. Direct Manager Access (for advanced use):
   >>> from data_app.manager import agent_manager
   >>> response = agent_manager.get_agent_response("Custom query")

ARCHITECTURE NOTES:

- Singleton Pattern: Ensures only one agent manager exists
- Lazy Loading: Agent graph is built on first use
- Dynamic Tools: Tools are added based on uploaded files
- Error Resilience: Comprehensive error handling throughout
- Thread Safety: Uses LangGraph's built-in thread management

INTEGRATION WITH DJANGO:

This module is designed to be called from Django views:

    from data_app.manager import process_file_for_agent, get_answer_from_agent

    def upload_view(request):
        # Process uploaded file
        process_file_for_agent(file_path, file_id)
        return JsonResponse({"status": "processed"})

    def chat_view(request):
        query = request.POST.get("query")
        answer = get_answer_from_agent(query)
        return JsonResponse({"answer": answer})

PERFORMANCE CONSIDERATIONS:

- Agent graph is rebuilt when new tools are added (acceptable for file uploads)
- Singleton pattern prevents multiple graph instances
- File processing is done asynchronously in production
- Memory usage scales with number of uploaded files

TROUBLESHOOTING:

1. "Agent graph not found":
   - Check if Manager singleton is properly initialized
   - Verify all required dependencies are installed

2. "File processing failed":
   - Check file permissions and paths
   - Verify supported file types
   - Check tool-specific error logs

3. "No response from agent":
   - Verify agent graph is built with tools
   - Check LangChain/LangGraph configuration
   - Review error logs for specific failures
"""
