# data_app/manager.py

import os
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
    singleton pattern means that only one instance of this class can exist at any time.
    """
    _instance = None 
    _agent_graph = None
    #_avalable_tools is a dictionary to hold tool name to function mapping, so here key is of type str and value is of type Any, this will allow us to store any callable tool function.
    _available_tools: Dict[str, Any] = {} 
    # Map file extensions to their respective processing functions
    _file_processing_func_map = {
        '.pdf': pdf_rag_tool.process_and_vectorize,
        '.sql': sql_tool.configure_database,
        '.csv': csv_rag_tool.process_and_vectorize,
    }

    # __new__ method to implement sigleton pattern
    #cls is the class itself, *args and **kwargs are any additional arguments that might be passed when creating an instance.* meaning that if an instance already exists, it will return that instance instead of creating a new one.** meaning that any additional keyword arguments passed during instantiation will be accepted but not used in this case.
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_agent()
        return cls._instance

    def _initialize_agent(self):
        """Builds the agent graph with all available tools."""
        # _available_tools will be started with the tavily search tool by default
        self._available_tools = {
            'tavily_search': tavily_search_tool.search_internet
        }
        # The graph will be built in the answer_question method, that means it will be built the first time a question is asked, depending on the qustion the agent and if file is uploaded or not, agent will use the tools accordingly.
        # for a more lazy loading approach to avoid startup delays.
        self._agent_graph = build_graph(list(self._available_tools.values()))
        print("Agent manager initialized. Agent graph is ready.")

    def process_uploaded_file(self, uploaded_file_path: str, file_id: int):
        """
        Processes a file based on its type and makes a new tool available to the agent.
        """
        #[1].lower() is used to convert the file extension to lowercase to ensure that the comparison is case-sensitive.
        file_extension = os.path.splitext(uploaded_file_path)[1].lower()

        processing_func = self._file_processing_func_map.get(file_extension)
        if not processing_func:
            print(f"Unsupported file type: {file_extension}. File not processed.")
            return

        print(f"Processing file: {uploaded_file_path}")
        try:
            # Call the appropriate processing function based on file type, processing_func is a callable function that takes the uploaded file path and file id as arguments.
            processing_func(uploaded_file_path, file_id)
            
            # Dynamically add the new tool to the manager's available tools
            # The tool name is constructed using the file type and file id to ensure uniqueness
            # For example, if the file is a PDF and its ID is 123, the tool name will be "pdf_tool_123". And the corresponding tool function is assigned based on the file type. this will store the tool function in the _available_tools dictionary with the constructed tool name as the key. this allows the agent to use this specific tool when needed(e.g., when a user asks a question related to the content of that file and if there are two pdf file agent can choose accordingly).
            if file_extension == '.pdf':
                tool_name = f"pdf_tool_{file_id}"
                new_tool = pdf_rag_tool.answer_question_on_pdf
                self._available_tools[tool_name] = new_tool
            elif file_extension == '.csv':
                tool_name = f"csv_tool_{file_id}"
                new_tool = csv_rag_tool.answer_question_on_csv
                self._available_tools[tool_name] = new_tool
            elif file_extension == '.sql':
                tool_name = f"sql_tool_{file_id}"
                new_tool = sql_tool.query_sql_database
            self._available_tools[tool_name] = new_tool

            
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