# data_app/manager.py

import os
import uuid
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, AIMessage

# Import core agent components
from .agent_core.agent_graph import build_graph
from .agent_core.tools import pdf_rag_tool, sql_tool, csv_rag_tool, tavily_search_tool

# --- Global Agent Manager Class ---
class Manager:
    """
    Manages the agent's lifecycle, including data processing and agent invocation.
    This class is a singleton to ensure the agent graph is only built once.
    """
    _instance = None
    _agent_graph = None
    _available_tools: Dict[str, Any] = {}
    _file_processing_func_map = {
        '.pdf': pdf_rag_tool.process_and_vectorize,
        '.sql': sql_tool.configure_database,
        '.csv': csv_rag_tool.process_and_vectorize,
    }

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_agent()
        return cls._instance

    def _initialize_agent(self):
        """Builds the agent graph with all available tools."""
        self._available_tools = {
            'tavily_search': tavily_search_tool.search_internet
        }
        # The graph will be built in the answer_question method
        # for a more lazy loading approach to avoid startup delays.
        self._agent_graph = build_graph(list(self._available_tools.values()))
        print("Agent manager initialized. Agent graph is ready.")

    def process_uploaded_file(self, uploaded_file_path: str, file_id: int):
        """
        Processes a file based on its type and makes a new tool available to the agent.
        """
        file_extension = os.path.splitext(uploaded_file_path)[1].lower()

        processing_func = self._file_processing_func_map.get(file_extension)
        if not processing_func:
            print(f"Unsupported file type: {file_extension}. File not processed.")
            return

        print(f"Processing file: {uploaded_file_path}")
        try:
            processing_func(uploaded_file_path, file_id)
            
            # Dynamically add the new tool to the manager's available tools
            if file_extension == '.pdf':
                tool_name = f"pdf_tool_{file_id}"
                new_tool = pdf_rag_tool.answer_question_on_pdf
                self._available_tools[tool_name] = new_tool
            # NOTE: Similar logic would be added for SQL and CSV tools
            
            # Rebuild the agent graph with the new tool
            self._agent_graph = build_graph(list(self._available_tools.values()))
            print(f"Successfully processed file and rebuilt agent with new tool: {tool_name}")

        except Exception as e:
            print(f"Error processing file: {e}")

    def get_agent_response(self, query: str) -> str:
        """
        Invokes the agent graph with the user's query and returns the final answer.
        """
        if not self._agent_graph:
            # This shouldn't happen with the singleton pattern, but as a fallback
            self._initialize_agent()

        inputs = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": "default_thread"}}
        
        try:
            # The agent will dynamically choose the correct tool based on the query
            response = self._agent_graph.invoke(inputs, config=config)
            
            # The final answer is typically the last message in the agent's response
            last_message = response.get('messages', [])[-1]
            return last_message.content

        except Exception as e:
            print(f"Error invoking agent: {e}")
            return "Sorry, I am unable to process your request at this time."

# Expose a global instance of the manager
agent_manager = Manager()

def process_file_for_agent(uploaded_file_path: str, file_id: int):
    """
    Public function for the views to call to process a file.
    """
    agent_manager.process_uploaded_file(uploaded_file_path, file_id)
    
def get_answer_from_agent(query: str) -> str:
    """
    Public function for the views to call to get a response from the agent.
    """
    return agent_manager.get_agent_response(query)