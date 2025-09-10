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

Author: Q&A Agent System
Created: 2025
"""

import os
import threading
import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool

# Import core agent components
from .agent_core.agent_graph import build_graph
from .agent_core.tools import pdf_rag_tool, sql_tool, csv_rag_tool, tavily_search_tool

logger = logging.getLogger('data_app.manager')


class Manager:
    """
    Singleton manager for the Q&A agent's lifecycle and operations.

    Responsibilities:
    - Agent graph initialization and rebuilding
    - Dynamic tool registration for uploaded files
    - File processing coordination
    - Query processing and response generation
    """

    # Singleton and agent state
    _instance = None
    _agent_graph = None

    # Lock to guard graph rebuilds in multi-threaded servers
    _rebuild_lock = threading.Lock()

    # Tool registry: Key: tool name, Value: callable tool function
    _available_tools: Dict[str, Any] = {}

    # Mapping of file extensions to processing functions
    _file_processing_func_map = {
        '.pdf': pdf_rag_tool.process_and_vectorize,
        '.sql': sql_tool.configure_database,
        '.csv': csv_rag_tool.process_and_vectorize,
    }

    def __new__(cls, *args, **kwargs) -> 'Manager':
        # Create or return the singleton instance of Manager
        if not cls._instance:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_agent()
        return cls._instance

    def _initialize_agent(self) -> None:
        """
        Initialize the agent with default tools and build the initial graph.
        Start with internet search (Tavily) and compile the graph.
        """
        # Default tool: internet search capability
        self._available_tools = {
            'tavily_search': tavily_search_tool.search_internet
        }

        # Build the initial agent graph with default tools
        with self._rebuild_lock:
            self._agent_graph = build_graph(list(self._available_tools.values()))
        logger.info("Agent manager initialized. Agent graph is ready.")

    def process_uploaded_file(self, uploaded_file_path: str, file_id: int) -> bool:
        """
        Process an uploaded file and make it available as a tool to the agent.
        Returns True on success, False on failure.
        Supports .pdf (RAG), .csv (RAG), and .sql/.db/.sqlite (SQL querying).
        """
        # Extract and normalize file extension
        file_extension = os.path.splitext(uploaded_file_path)[1].lower()

        processing_func = self._file_processing_func_map.get(file_extension)
        if not processing_func:
            logger.info(f"Unsupported file type: {file_extension}. File not processed.")
            return False

        if not os.path.exists(uploaded_file_path):
            logger.error(f"File not found: {uploaded_file_path}")
            return False

        logger.info(f"Processing file: {uploaded_file_path}")
        try:
            # Execute file processing/vectorization/configuration
            processing_func(uploaded_file_path, file_id)

            # Select the appropriate tool to answer queries for this file
            if file_extension == '.pdf':
                tool_name = f"pdf_tool_{file_id}"
                # Create a tool instance with bound file_id
                def create_pdf_tool(fid):
                    @tool
                    def pdf_tool(query: str) -> str:
                        """Answer questions based on a specific PDF using RAG with basic source citations."""
                        try:
                            from langchain_openai import OpenAIEmbeddings, ChatOpenAI
                            from langchain_community.vectorstores import FAISS
                            from langchain.chains import RetrievalQA
                            from .agent_core.config import LoadToolsConfig
                            import logging
                            logger = logging.getLogger('data_app.manager')
                            TOOLS_CFG = LoadToolsConfig()
                            
                            embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
                            index_path = f"data/faiss_index_{fid}"
                            vector_store = FAISS.load_local(
                                index_path,
                                embeddings,
                                allow_dangerous_deserialization=True,
                            )
                            retriever = vector_store.as_retriever(
                                search_type="similarity",
                                search_kwargs={"k": TOOLS_CFG.pdf_rag_k},
                            )
                            llm = ChatOpenAI(temperature=TOOLS_CFG.pdf_rag_llm_temperature, model=TOOLS_CFG.pdf_rag_llm)
                            qa_chain = RetrievalQA.from_chain_type(
                                llm=llm,
                                retriever=retriever,
                                return_source_documents=True,
                            )
                            result = qa_chain.invoke({"query": query})
                            answer = result.get('result') if isinstance(result, dict) else str(result)
                            sources = result.get('source_documents', []) if isinstance(result, dict) else []
                            citations = []
                            for d in sources:
                                meta = getattr(d, 'metadata', {}) or {}
                                page = meta.get('page')
                                citations.append(f"[page {page+1}]" if page is not None else "[source]")
                            citation_str = ' '.join(citations) if citations else ''
                            return f"{answer}\n\nSources: {citation_str}"
                        except FileNotFoundError:
                            return (
                                "Sorry, the PDF with the specified ID has not been processed yet. "
                                "Please ensure the file has been uploaded and processed before asking questions."
                            )
                        except Exception as e:
                            return (
                                "Sorry, I could not find information on this topic in the specified PDF. "
                                f"Error details: {str(e)}. "
                                "The document may not contain relevant information about your question."
                            )
                    pdf_tool.name = f"answer_pdf_{fid}"
                    pdf_tool.description = f"Answer questions about the content of PDF file {fid} using retrieval-augmented generation."
                    return pdf_tool
                
                new_tool = create_pdf_tool(file_id)
                
            elif file_extension == '.csv':
                tool_name = f"csv_tool_{file_id}"
                # Create a tool instance with bound file_id
                def create_csv_tool(fid):
                    @tool
                    def csv_tool(query: str) -> str:
                        """Answer questions about CSV content using RAG with basic source citations."""
                        try:
                            from langchain_openai import OpenAIEmbeddings, ChatOpenAI
                            from langchain_community.vectorstores import FAISS
                            from langchain.chains import RetrievalQA
                            from .agent_core.config import LoadToolsConfig
                            import logging
                            logger = logging.getLogger('data_app.manager')
                            TOOLS_CFG = LoadToolsConfig()
                            
                            embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
                            vector_store = FAISS.load_local(
                                f"data/faiss_index_csv_{fid}",
                                embeddings,
                                allow_dangerous_deserialization=True,
                            )
                            retriever = vector_store.as_retriever(
                                search_type="similarity",
                                search_kwargs={"k": TOOLS_CFG.csv_rag_k},
                            )
                            llm = ChatOpenAI(temperature=TOOLS_CFG.csv_rag_llm_temperature, model=TOOLS_CFG.csv_rag_llm)
                            qa_chain = RetrievalQA.from_chain_type(
                                llm=llm,
                                retriever=retriever,
                                return_source_documents=True,
                            )
                            result = qa_chain.invoke({"query": query})
                            answer = result.get('result') if isinstance(result, dict) else str(result)
                            sources = result.get('source_documents', []) if isinstance(result, dict) else []
                            citations = []
                            for d in sources:
                                meta = getattr(d, 'metadata', {}) or {}
                                row = meta.get('row')
                                citations.append(f"[row {row}]" if row is not None else "[source]")
                            citation_str = ' '.join(citations) if citations else ''
                            return f"{answer}\n\nSources: {citation_str}"
                        except FileNotFoundError:
                            return (
                                "Sorry, the CSV with the specified ID has not been processed yet. "
                                "Please ensure the file has been uploaded and processed before asking questions."
                            )
                        except Exception as e:
                            return (
                                "Sorry, I could not find information on this topic in the specified CSV. "
                                f"Error details: {str(e)}. "
                                "The document may not contain relevant information about your question."
                            )
                    csv_tool.name = f"answer_csv_{fid}"
                    csv_tool.description = f"Answer questions about the content of CSV file {fid} using retrieval-augmented generation."
                    return csv_tool
                
                new_tool = create_csv_tool(file_id)
                
            elif file_extension == '.sql':
                tool_name = f"sql_tool_{file_id}"
                new_tool = sql_tool.query_sql_database
            else:
                logger.info(f"Unexpected file extension: {file_extension}")
                return False

            # Register the new tool and rebuild the agent graph
            self._available_tools[tool_name] = new_tool
            with self._rebuild_lock:
                self._agent_graph = build_graph(list(self._available_tools.values()))

            logger.info(f"Successfully processed file and rebuilt agent with new tool: {tool_name}")
            return True
        except Exception as e:
            logger.info(f"Error processing file: {e}")
            return False

    def get_agent_response(self, query: str, thread_id: str = "default_thread") -> str:
        """
        Process a user query through the agent and return the response.
        The thread_id parameter isolates conversation memory per session.
        """
        # Ensure agent graph is available
        if not self._agent_graph:
            logger.info("Warning: Agent graph not found, reinitializing...")
            self._initialize_agent()

        # Prepare inputs and config
        inputs = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": thread_id}}

        try:
            response = self._agent_graph.invoke(inputs, config=config)
            messages = response.get('messages', [])
            if messages:
                last_message = messages[-1]
                return last_message.content
            return "No response generated by the agent."
        except Exception as e:
            logger.info(f"Error invoking agent: {e}")
            return "Sorry, I am unable to process your request at this time."


# --- Global Manager Instance ---
agent_manager = Manager()


def process_file_for_agent(uploaded_file_path: str, file_id: int) -> bool:
    """Public interface to process uploaded files. Returns True on success."""
    return agent_manager.process_uploaded_file(uploaded_file_path, file_id)


def get_answer_from_agent(query: str, thread_id: str = "default_thread") -> str:
    """
    Public interface to get agent responses.
    Allows passing a thread_id for per-session memory.
    """
    return agent_manager.get_agent_response(query, thread_id=thread_id)
