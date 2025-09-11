# data_app/agent_core/agent_graph.py
"""
Agent Graph Module for LangGraph-based Conversational AI.
Builds a LangGraph StateGraph agent that binds available tools to a primary LLM,
maintains conversation state with memory checkpoints, and conditionally routes
between the chatbot node and tool execution. 
"""
import logging
from typing import Annotated, List, Any
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START

from langchain_openai import ChatOpenAI
from .config import LoadToolsConfig

logger = logging.getLogger('data_app.agent_core.agent_graph')

# --- State and Tooling Logic ---
class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph(available_tools: List[Any]) -> StateGraph:
    """
    Construct a tool-enabled conversational agent graph using LangGraph.
    """
    TOOLS_CFG = LoadToolsConfig()

    # Initialize the primary LLM and bind tools
    primary_llm = ChatOpenAI(
        model=TOOLS_CFG.primary_agent_llm,
        temperature=TOOLS_CFG.primary_agent_llm_temperature,
    )
    primary_llm_with_tools = primary_llm.bind_tools(available_tools)

    # Chatbot node invokes the tool-enabled LLM
    def chatbot(state: State):
        return {"messages": [primary_llm_with_tools.invoke(state["messages"]) ]}

    # Assemble the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    tool_node = ToolNode(tools=available_tools)
    graph_builder.add_node("tools", tool_node)

    # Conditional routing: if tools are called, go to tools, else finish at chatbot
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )

    # Agentic loop
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    # Compile with in-memory checkpointing
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    return graph
