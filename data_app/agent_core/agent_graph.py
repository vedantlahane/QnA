# data_app/agent_core/agent_graph.py

import json
import logging
from typing import Annotated, Literal, List, Any, Dict, Optional, Union
from typing_extensions import TypedDict
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .config import LoadToolsConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Enhanced State Management ---
class State(TypedDict):
    """
    Represents the enhanced state structure containing messages and metadata.
    """
    messages: Annotated[list, add_messages]
    user_id: Optional[str]
    session_id: Optional[str]
    tool_call_count: int
    max_tool_calls: int
    error_count: int
    context_metadata: Dict[str, Any]

class EnhancedToolNode:
    """
    An enhanced node that runs tools with better error handling and logging.
    """
    
    def __init__(self, tools: List[BaseTool], max_concurrent_tools: int = 5) -> None:
        """
        Initializes the EnhancedToolNode with available tools.
        
        Args:
            tools: List of available tools
            max_concurrent_tools: Maximum number of tools to execute concurrently
        """
        self.tools_by_name = {tool.name: tool for tool in tools}
        self.max_concurrent_tools = max_concurrent_tools
        logger.info(f"Initialized ToolNode with {len(tools)} tools: {list(self.tools_by_name.keys())}")
    
    def _execute_single_tool(self, tool_call: Dict[str, Any]) -> ToolMessage:
        """Execute a single tool call with error handling."""
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        
        try:
            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            
            if tool_name not in self.tools_by_name:
                error_msg = f"Tool '{tool_name}' not found in available tools: {list(self.tools_by_name.keys())}"
                logger.error(error_msg)
                return ToolMessage(
                    content=json.dumps({"error": error_msg}),
                    name=tool_name,
                    tool_call_id=tool_call_id,
                )
            
            tool = self.tools_by_name[tool_name]
            tool_result = tool.invoke(tool_args)
            
            # Ensure result is JSON serializable
            if isinstance(tool_result, str):
                content = tool_result
            else:
                try:
                    content = json.dumps(tool_result)
                except (TypeError, ValueError):
                    content = str(tool_result)
            
            logger.info(f"Tool {tool_name} executed successfully")
            return ToolMessage(
                content=content,
                name=tool_name,
                tool_call_id=tool_call_id,
            )
            
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            return ToolMessage(
                content=json.dumps({"error": error_msg}),
                name=tool_name,
                tool_call_id=tool_call_id,
            )
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tools based on the tool calls in the last message.
        """
        try:
            if messages := state.get("messages", []):
                message = messages[-1]
            else:
                raise ValueError("No message found in input state")
            
            if not hasattr(message, "tool_calls") or not message.tool_calls:
                logger.warning("No tool calls found in message")
                return state
            
            tool_calls = message.tool_calls
            logger.info(f"Processing {len(tool_calls)} tool calls")
            
            # Limit the number of concurrent tool calls
            if len(tool_calls) > self.max_concurrent_tools:
                logger.warning(f"Too many tool calls ({len(tool_calls)}), limiting to {self.max_concurrent_tools}")
                tool_calls = tool_calls[:self.max_concurrent_tools]
            
            # Execute tools
            outputs = []
            for tool_call in tool_calls:
                result = self._execute_single_tool(tool_call)
                outputs.append(result)
            
            # Update state
            updated_state = {
                **state,
                "messages": outputs,
                "tool_call_count": state.get("tool_call_count", 0) + len(outputs),
            }
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in ToolNode execution: {e}")
            error_message = ToolMessage(
                content=json.dumps({"error": f"Tool execution failed: {str(e)}"}),
                name="error",
                tool_call_id="error",
            )
            return {**state, "messages": [error_message], "error_count": state.get("error_count", 0) + 1}

def enhanced_route_tools(state: State) -> Literal["tools", "safety_check", "__end__"]:
    """
    Enhanced routing function with safety checks and better logic.
    """
    try:
        # Get the last message
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            logger.error("No messages found in state")
            return "__end__"
        
        # Check if we've exceeded maximum tool calls
        tool_call_count = state.get("tool_call_count", 0)
        max_tool_calls = state.get("max_tool_calls", 10)  # Default limit
        
        if tool_call_count >= max_tool_calls:
            logger.warning(f"Maximum tool calls ({max_tool_calls}) reached")
            return "__end__"
        
        # Check for tool calls
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            # Add safety check for suspicious tool calls
            if len(ai_message.tool_calls) > 5:
                logger.warning(f"Large number of tool calls detected: {len(ai_message.tool_calls)}")
                return "safety_check"
            return "tools"
        
        return "__end__"
        
    except Exception as e:
        logger.error(f"Error in routing: {e}")
        return "__end__"

def create_system_prompt() -> str:
    """Create an enhanced system prompt for the agent."""
    return """You are an intelligent AI assistant with access to various tools for analyzing documents and searching information.

Available capabilities:
- Search the internet for current information using Tavily
- Analyze PDF documents that have been uploaded
- Query SQL databases that have been uploaded  
- Analyze CSV files that have been uploaded

Guidelines for tool usage:
1. Use internet search when you need current, real-time information or when the answer isn't in uploaded documents
2. Use document-specific tools (PDF, SQL, CSV) when the user asks about specific uploaded files
3. Be precise with file IDs when using document tools
4. If a tool fails, try alternative approaches or inform the user about limitations
5. Always provide clear, helpful responses based on the information retrieved

Remember:
- Be concise but comprehensive in your responses
- Cite sources when appropriate
- If you cannot find information, clearly state this
- Ask for clarification if the user's request is ambiguous
"""

def safety_check_node(state: State) -> Dict[str, Any]:
    """
    Safety check node to validate tool calls before execution.
    """
    try:
        messages = state.get("messages", [])
        if not messages:
            return {**state, "messages": [AIMessage(content="No messages to process.")]}
        
        last_message = messages[-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_calls = last_message.tool_calls
            
            # Check for potential issues
            if len(tool_calls) > 5:
                logger.warning("Reducing excessive tool calls")
                # Limit to first 3 tool calls
                last_message.tool_calls = tool_calls[:3]
                
                return {
                    **state, 
                    "messages": [
                        last_message,
                        AIMessage(content="Note: Limited tool calls to prevent overload.")
                    ]
                }
        
        return state
        
    except Exception as e:
        logger.error(f"Error in safety check: {e}")
        return {**state, "error_count": state.get("error_count", 0) + 1}

def create_chatbot_node(llm_with_tools: ChatOpenAI) -> callable:
    """Create an enhanced chatbot node with better prompt management."""
    
    def chatbot(state: State) -> Dict[str, Any]:
        """
        Enhanced chatbot node with better error handling and context management.
        """
        try:
            messages = state.get("messages", [])
            
            # Add system message if not present
            if not messages or not isinstance(messages[0], type(messages[0])) or "system" not in str(type(messages[0])).lower():
                system_prompt = create_system_prompt()
                system_message = AIMessage(content=system_prompt)  # Using AIMessage as placeholder
                messages = [system_message] + messages
            
            # Invoke the LLM
            response = llm_with_tools.invoke(messages)
            
            # Update context metadata
            context_metadata = state.get("context_metadata", {})
            context_metadata["last_response_length"] = len(response.content) if hasattr(response, 'content') else 0
            context_metadata["tool_calls_made"] = len(response.tool_calls) if hasattr(response, 'tool_calls') and response.tool_calls else 0
            
            return {
                **state,
                "messages": [response],
                "context_metadata": context_metadata
            }
            
        except Exception as e:
            logger.error(f"Error in chatbot node: {e}")
            error_response = AIMessage(
                content=f"I apologize, but I encountered an error while processing your request: {str(e)}"
            )
            return {
                **state,
                "messages": [error_response],
                "error_count": state.get("error_count", 0) + 1
            }
    
    return chatbot

def build_graph(available_tools: List[BaseTool]) -> StateGraph:
    """
    Builds an enhanced agent decision-making graph with better error handling and features.
    
    Args:
        available_tools (List[BaseTool]): A list of the currently available tools to bind to the LLM.
    
    Returns:
        StateGraph: The compiled state graph that represents the agent's decision-making process.
    """
    try:
        logger.info(f"Building agent graph with {len(available_tools)} tools")
        
        # Load configuration
        TOOLS_CFG = LoadToolsConfig()
        
        # Validate tools
        if not available_tools:
            logger.warning("No tools provided to build_graph")
            available_tools = []
        
        # Filter out invalid tools
        valid_tools = []
        for tool in available_tools:
            if hasattr(tool, 'name') and hasattr(tool, 'invoke'):
                valid_tools.append(tool)
            else:
                logger.warning(f"Invalid tool detected and removed: {tool}")
        
        logger.info(f"Using {len(valid_tools)} valid tools")
        
        # Initialize the primary language model (LLM) with tool-binding functionality
        primary_llm = ChatOpenAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
            max_tokens=1000,  # Reasonable limit
        )
        
        # Bind tools to LLM
        if valid_tools:
            primary_llm_with_tools = primary_llm.bind_tools(valid_tools)
        else:
            primary_llm_with_tools = primary_llm
            logger.warning("No valid tools to bind to LLM")
        
        # Create enhanced nodes
        chatbot_node = create_chatbot_node(primary_llm_with_tools)
        tool_node = EnhancedToolNode(tools=valid_tools)
        
        # Initialize the graph builder with enhanced state
        def create_initial_state() -> State:
            return State(
                messages=[],
                user_id=None,
                session_id=None,
                tool_call_count=0,
                max_tool_calls=10,
                error_count=0,
                context_metadata={}
            )
        
        graph_builder = StateGraph(State)
        
        # Add the nodes
        graph_builder.add_node("chatbot", chatbot_node)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_node("safety_check", safety_check_node)
        
        # Define the enhanced conditional routing
        graph_builder.add_conditional_edges(
            "chatbot",
            enhanced_route_tools,
            {
                "tools": "tools",
                "safety_check": "safety_check", 
                "__end__": END
            },
        )
        
        # Add safety check routing
        graph_builder.add_conditional_edges(
            "safety_check",
            lambda state: "tools" if state.get("error_count", 0) < 3 else "__end__",
            {
                "tools": "tools",
                "__end__": END
            }
        )
        
        # Define the edges for the agentic loop
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        
        # Compile the graph with enhanced memory management
        memory = MemorySaver()
        graph = graph_builder.compile(
            checkpointer=memory,
            interrupt_before=None,  # Can be used for human-in-the-loop
            interrupt_after=None,
        )
        
        logger.info("Agent graph built successfully")
        return graph
        
    except Exception as e:
        logger.error(f"Error building agent graph: {e}")
        raise RuntimeError(f"Failed to build agent graph: {str(e)}")

# Utility functions for graph management
def validate_graph_tools(tools: List[BaseTool]) -> List[BaseTool]:
    """Validate and filter tools for graph building."""
    valid_tools = []
    
    for tool in tools:
        try:
            # Check required attributes
            if not hasattr(tool, 'name'):
                logger.warning(f"Tool missing 'name' attribute: {tool}")
                continue
                
            if not hasattr(tool, 'invoke'):
                logger.warning(f"Tool missing 'invoke' method: {tool}")
                continue
                
            # Test tool invocation (basic validation)
            if hasattr(tool, 'description'):
                valid_tools.append(tool)
                logger.info(f"Validated tool: {tool.name}")
            else:
                logger.warning(f"Tool missing description: {tool.name}")
                valid_tools.append(tool)  # Still add it, but warn
                
        except Exception as e:
            logger.error(f"Error validating tool {tool}: {e}")
            continue
    
    return valid_tools

def get_graph_statistics(graph: StateGraph) -> Dict[str, Any]:
    """Get statistics about the compiled graph."""
    try:
        # This is a basic implementation - LangGraph internals may vary
        stats = {
            "nodes": len(graph.nodes) if hasattr(graph, 'nodes') else "Unknown",
            "edges": len(graph.edges) if hasattr(graph, 'edges') else "Unknown",
            "has_memory": hasattr(graph, 'checkpointer') and graph.checkpointer is not None,
            "compiled": True
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting graph statistics: {e}")
        return {"error": str(e)}

def create_default_state(user_id: Optional[str] = None, session_id: Optional[str] = None) -> State:
    """Create a default state for graph execution."""
    return State(
        messages=[],
        user_id=user_id,
        session_id=session_id,
        tool_call_count=0,
        max_tool_calls=10,
        error_count=0,
        context_metadata={}
    )

# Export main function and utilities
__all__ = [
    'build_graph',
    'State', 
    'EnhancedToolNode',
    'validate_graph_tools',
    'get_graph_statistics',
    'create_default_state'
]
