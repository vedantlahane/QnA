# data_app/agent_core/agent_graph.py

import json
from typing import Annotated, Literal, List, Any
from typing_extensions import TypedDict
from langchain_core.messages import ToolMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from .config import LoadToolsConfig

# NOTE: You will need to import your specific tools here from the tools directory
from .tools import csv_rag_tool, pdf_rag_tool, sql_tool, tavily_search_tool

# --- State and Tooling Logic ---
class State(TypedDict):
    """Represents the state structure containing a list of messages.
    """
    messages: Annotated[list, add_messages]


def route_tools(
    state: State,
) -> Literal["tools", "__end__"]:
    """
    Determines whether to route to the ToolNode or end the flow.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(
            f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"

# --- Main Graph Builder ---
def build_graph(available_tools: List[Any]) -> StateGraph:
    """
    Builds an agent decision-making graph by combining an LLM with various tools.

    Args:
        available_tools (List[Any]): A list of the currently available tools to bind to the LLM.
    
    Returns:
        StateGraph: The compiled state graph that represents the agent's decision-making process.
    """
    TOOLS_CFG = LoadToolsConfig()
    
    # Initialize the primary language model (LLM) with tool-binding functionality
    primary_llm = ChatOpenAI(model=TOOLS_CFG.primary_agent_llm,
                             temperature=TOOLS_CFG.primary_agent_llm_temperature)
    primary_llm_with_tools = primary_llm.bind_tools(available_tools)

    # Define the chatbot node that invokes the LLM
    def chatbot(state: State):
        """Executes the primary language model with tools bound and returns the generated message."""
        return {"messages": [primary_llm_with_tools.invoke(state["messages"])]}

    # Initialize the graph builder
    graph_builder = StateGraph(State)

    # Add the nodes
    graph_builder.add_node("chatbot", chatbot)
    tool_node = ToolNode(tools=available_tools)
    graph_builder.add_node("tools", tool_node)

    # Define the conditional routing from the chatbot
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {"tools": "tools", "__end__": "__end__"},
    )

    # Define the edges for the agentic loop
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    # Compile the graph with a memory saver for state persistence
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

    return graph
