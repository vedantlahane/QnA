"""
Agent Manager Module for Q&A System

This module manages the agent's lifecycle, file-driven dynamic tool registration,
and routes questions through a LangGraph-powered agent.

Key Features:
- Singleton manager with lazy graph build
- Thread-safe graph rebuilds on tool changes
- Dynamic per-file @tool wrappers with bound file_id for PDF/CSV/SQL
- Default internet search tool always available
"""

import os
import threading
import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from .agent_core.agent_graph import build_graph
from .agent_core.tools import pdf_rag_tool, sql_tool, csv_rag_tool, tavily_search_tool

logger = logging.getLogger('data_app.manager')


class Manager:
    """Singleton manager for the Q&A agent lifecycle and operations."""

    _instance = None
    _agent_graph = None
    _rebuild_lock = threading.Lock()
    _available_tools: Dict[str, Any] = {}

    # Map file extensions to processing/configuration functions
    _file_processing_func_map = {
        '.pdf': pdf_rag_tool.process_and_vectorize,
        '.csv': csv_rag_tool.process_and_vectorize,
        '.sql': sql_tool.configure_database,
        '.db': sql_tool.configure_database,
        '.sqlite': sql_tool.configure_database,
    }

    def __new__(cls, *args, **kwargs) -> 'Manager':
        if not cls._instance:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_agent()
        return cls._instance

    def _initialize_agent(self) -> None:
        # Default tool: internet search capability
        self._available_tools = {
            'tavily_search': tavily_search_tool.search_internet,
        }
        with self._rebuild_lock:
            self._agent_graph = build_graph(list(self._available_tools.values()))
        logger.info("Agent manager initialized. Agent graph is ready.")

    def _create_pdf_tool(self, fid: int):
        @tool
        def answer_pdf(query: str) -> str:
            """Answer questions about PDF content for this specific file."""
            # Delegate to the existing tool, binding file_id
            try:
                return pdf_rag_tool.answer_question_on_pdf.invoke({
                    'query': query,
                    'file_id': fid,
                })
            except Exception as e:
                return f"Error answering PDF question for file {fid}: {e}"
        answer_pdf.name = f"answer_pdf_{fid}"
        answer_pdf.description = f"Answer questions about PDF file {fid} using RAG."
        return answer_pdf

    def _create_csv_tool(self, fid: int):
        @tool
        def answer_csv(query: str) -> str:
            """Answer questions about CSV content for this specific file."""
            try:
                return csv_rag_tool.answer_question_on_csv.invoke({
                    'query': query,
                    'file_id': fid,
                })
            except Exception as e:
                return f"Error answering CSV question for file {fid}: {e}"
        answer_csv.name = f"answer_csv_{fid}"
        answer_csv.description = f"Answer questions about CSV file {fid} using RAG."
        return answer_csv

    def _create_sql_tool(self, fid: int):
        @tool
        def query_sql(query: str) -> str:
            """Run a natural-language query against the configured SQL database for this file."""
            try:
                return sql_tool.query_sql_database.invoke({
                    'query': query,
                    'file_id': fid,
                })
            except Exception as e:
                return f"Error querying SQL database for file {fid}: {e}"
        query_sql.name = f"query_sql_{fid}"
        query_sql.description = f"Query the SQL database bound to file {fid}."
        return query_sql

    def process_uploaded_file(self, uploaded_file_path: str, file_id: int) -> bool:
        """Process an uploaded file and register a bound tool for the agent."""
        ext = os.path.splitext(uploaded_file_path)[1].lower()
        processing_func = self._file_processing_func_map.get(ext)
        if not processing_func:
            logger.info(f"Unsupported file type: {ext}. File not processed.")
            return False
        if not os.path.exists(uploaded_file_path):
            logger.error(f"File not found: {uploaded_file_path}")
            return False

        logger.info(f"Processing file: {uploaded_file_path}")
        try:
            # Process or configure backing data store
            processing_func(uploaded_file_path, file_id)

            # Create a per-file tool wrapper (bind file_id)
            if ext == '.pdf':
                tool_name = f"pdf_tool_{file_id}"
                new_tool = self._create_pdf_tool(file_id)
            elif ext == '.csv':
                tool_name = f"csv_tool_{file_id}"
                new_tool = self._create_csv_tool(file_id)
            else:  # SQL-like extensions
                tool_name = f"sql_tool_{file_id}"
                new_tool = self._create_sql_tool(file_id)

            # Register and rebuild graph
            self._available_tools[tool_name] = new_tool
            with self._rebuild_lock:
                self._agent_graph = build_graph(list(self._available_tools.values()))

            logger.info(f"Successfully processed file and rebuilt agent with new tool: {tool_name}")
            return True
        except Exception as e:
            logger.info(f"Error processing file: {e}")
            return False

    def get_agent_response(self, query: str, thread_id: str = "default_thread") -> str:
        """Run a user query through the agent and return the response text."""
        if not self._agent_graph:
            logger.info("Warning: Agent graph not found, reinitializing...")
            self._initialize_agent()

        inputs = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": thread_id}}
        try:
            response = self._agent_graph.invoke(inputs, config=config)
            messages = response.get('messages', [])
            if messages:
                return messages[-1].content
            return "No response generated by the agent."
        except Exception as e:
            logger.info(f"Error invoking agent: {e}")
            return "Sorry, I am unable to process your request at this time."


# Global instance and thin public API
agent_manager = Manager()

def process_file_for_agent(uploaded_file_path: str, file_id: int) -> bool:
    return agent_manager.process_uploaded_file(uploaded_file_path, file_id)

def get_answer_from_agent(query: str, thread_id: str = "default_thread") -> str:
    return agent_manager.get_agent_response(query, thread_id=thread_id)
