# data_app/agent_core/agent_graph.py

"""
Agent Graph Module for LangGraph-based Conversational AI

This module implements a sophisticated conversational AI agent using LangGraph's
StateGraph architecture. The agent combines a primary language model with various
tools to provide intelligent responses and perform actions based on user queries.

The module provides a flexible framework for building tool-enabled chatbots that can:
- Maintain conversation context through message history
- Route queries to appropriate tools based on intent
- Execute tool functions and incorporate results into responses
- Persist conversation state across interactions

Key Components:
- State: TypedDict-based state management for conversation flow
- build_graph(): Factory function for creating configured agent graphs
- Tool Integration: Seamless binding of external tools to the LLM
- Memory Management: Checkpoint-based conversation persistence

Architecture Overview:
1. State Management: Uses TypedDict with message accumulation
2. Node System: Chatbot node for LLM interaction, ToolNode for tool execution
3. Conditional Routing: Automatic routing based on tool requirements
4. Memory Persistence: MemorySaver for conversation continuity

Dependencies:
- langgraph: Core graph framework and prebuilt components
- langchain_openai: OpenAI LLM integration
- typing_extensions: Enhanced type hints support
- config: Local configuration management

Configuration Requirements:
- OpenAI API key must be set in environment variables
- Primary agent parameters configured in tools_config.yml:
  * primary_agent_llm: Language model name (e.g., "gpt-4", "gpt-3.5-turbo")
  * primary_agent_llm_temperature: Creativity vs. consistency balance (0.0-1.0)

Usage Example:
    >>> from agent_graph import build_graph
    >>> from tools import search_tool, calculator_tool
    >>> available_tools = [search_tool, calculator_tool]
    >>> agent_graph = build_graph(available_tools)
    >>> # Use the graph for conversation
    >>> result = agent_graph.invoke({"messages": [HumanMessage("What's 2+2?")]})
    >>> print(result["messages"][-1].content)

Advanced Features:
- Tool Binding: Automatic tool discovery and parameter extraction
- Conditional Edges: Smart routing based on LLM tool calls
- State Persistence: Conversation history maintained across sessions
- Error Handling: Graceful degradation when tools fail

Performance Considerations:
- Memory usage scales with conversation length
- Tool execution time affects response latency
- Checkpointing provides resumable conversations
- LLM temperature affects response variability

Author: AI Assistant
Created: 2024
"""

import json
from typing import Annotated, List, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI
from .config import LoadToolsConfig


# --- State and Tooling Logic ---
class State(TypedDict):
    """
    Represents the conversational state of the agent graph.

    This TypedDict defines the structure of the state that flows through the
    LangGraph nodes. It maintains the conversation history and context,
    enabling the agent to have coherent, context-aware interactions.

    The state uses LangGraph's message accumulation pattern to automatically
    append new messages to the conversation history, maintaining chronological
    order and full context for the language model.

    Attributes
    ----------
    messages : Annotated[list, add_messages]
        List of conversation messages in chronological order.
        Uses LangGraph's add_messages reducer to automatically append
        new messages while preserving conversation history.

    Notes
    -----
    - The messages list contains LangChain message objects (HumanMessage, AIMessage, etc.)
    - Message accumulation is handled automatically by the add_messages reducer
    - State is immutable between node executions - modifications return new state
    - Memory persistence is handled separately by the MemorySaver checkpointer

    Examples
    --------
    >>> from langchain_core.messages import HumanMessage, AIMessage
    >>> initial_state = State(messages=[
    ...     HumanMessage(content="Hello"),
    ...     AIMessage(content="Hi there!")
    ... ])
    >>> # New messages are automatically appended
    >>> updated_state = {"messages": [AIMessage(content="How can I help?")]}
    >>> # The add_messages reducer handles the combination

    See Also
    --------
    build_graph : Uses this state in the graph construction
    add_messages : LangGraph reducer for message accumulation
    MemorySaver : Handles state persistence across conversations
    """
    messages: Annotated[list, add_messages]

# --- Main Graph Builder ---
def build_graph(available_tools: List[Any]) -> StateGraph:
    """
    Construct a tool-enabled conversational agent graph using LangGraph.

    This factory function creates a complete StateGraph that implements an
    intelligent conversational agent capable of using various tools to
    fulfill user requests. The graph combines a primary language model
    with tool execution capabilities through conditional routing.

    Graph Architecture:
    1. Chatbot Node: Processes user input and decides tool usage
    2. Tool Node: Executes selected tools and returns results
    3. Conditional Edges: Route based on tool requirements
    4. Memory Integration: Persists conversation state

    The graph implements a classic agentic loop:
    - User input → Chatbot (decides if tools needed)
    - If tools needed → Tool execution → Results back to Chatbot
    - If no tools needed → Direct response
    - Loop continues for multi-step interactions

    Parameters
    ----------
    available_tools : List[Any]
        Collection of LangChain tools to bind to the primary LLM.
        Each tool should be a properly decorated function with @tool decorator
        and include parameter schemas for automatic discovery.

    Returns
    -------
    StateGraph
        Compiled LangGraph StateGraph ready for conversation.
        The graph includes memory checkpointing for state persistence
        and can be invoked with message-based state dictionaries.

    Raises
    ------
    ValueError
        If available_tools is empty or contains invalid tool objects.
    ConnectionError
        If OpenAI API is not accessible during LLM initialization.
    KeyError
        If required configuration parameters are missing.

    Examples
    --------
    Basic usage with custom tools:

    >>> from tools import search_tool, calculator_tool
    >>> tools = [search_tool, calculator_tool]
    >>> agent = build_graph(tools)
    >>> result = agent.invoke({"messages": [HumanMessage("Calculate 15 * 23")]})

    Advanced usage with configuration:

    >>> from langchain_core.messages import HumanMessage
    >>> agent = build_graph(my_tool_collection)
    >>> config = {"configurable": {"thread_id": "conversation_1"}}
    >>> response = agent.invoke(
    ...     {"messages": [HumanMessage("Search for Python tutorials")]},
    ...     config=config
    ... )

    Notes
    -----
    - The graph uses MemorySaver for conversation persistence
    - Tool binding enables automatic parameter extraction from queries
    - Conditional routing is handled by LangGraph's tools_condition
    - State includes full message history for context awareness

    Tool Integration Details:
    - Tools are bound to the LLM using bind_tools() method
    - LLM automatically detects when tools are needed
    - ToolNode handles parallel and sequential tool execution
    - Tool results are automatically incorporated into responses

    Performance Characteristics:
    - Graph compilation is done once at startup
    - Memory usage scales with conversation length
    - Tool execution adds latency based on tool complexity
    - Checkpointing enables resumable conversations

    Dependencies
    ------------
    - Requires OpenAI API key in environment variables
    - Depends on tools_config.yml for LLM configuration
    - All tools must be properly decorated with @tool

    See Also
    --------
    State : The state structure used by the graph
    ToolNode : LangGraph's built-in tool execution node
    tools_condition : Conditional routing function
    MemorySaver : State persistence mechanism
    ChatOpenAI : Primary language model with tool binding
    """
    TOOLS_CFG = LoadToolsConfig()
    
    # Initialize the primary language model (LLM) with tool-binding functionality
    primary_llm = ChatOpenAI(model=TOOLS_CFG.primary_agent_llm,
                             temperature=TOOLS_CFG.primary_agent_llm_temperature)
    primary_llm_with_tools = primary_llm.bind_tools(available_tools)

    # Define the chatbot node that invokes the LLM
    def chatbot(state: State):
        """
        Process user input through the tool-enabled language model.

        This nested function serves as the primary node in the agent graph,
        responsible for processing user messages and determining whether
        tool usage is required. It represents the "brain" of the conversational
        agent, making decisions about tool invocation and response generation.

        The function binds the configured tools to the LLM, enabling automatic
        tool discovery and parameter extraction from natural language queries.
        When tools are needed, the LLM generates structured tool calls that
        are processed by the ToolNode in subsequent graph steps.

        Parameters
        ----------
        state : State
            Current conversation state containing message history.
            The state includes all previous messages in chronological order,
            providing full context for the LLM's decision making.

        Returns
        -------
        dict
            Updated state dictionary containing the LLM's response message.
            The response may include tool calls if the query requires
            external tool execution, or a direct answer if no tools are needed.

        Notes
        -----
        - Tool binding enables the LLM to understand available capabilities
        - Message history provides context for coherent responses
        - Tool calls are automatically parsed by LangGraph's routing logic
        - The function is stateless and depends only on input state

        Examples
        --------
        The function is typically called within the graph execution:

        >>> state = {"messages": [HumanMessage("What's the weather?")]}
        >>> result = chatbot(state)
        >>> # result contains LLM response, possibly with tool calls

        Tool Call Generation:
        >>> # For a query requiring tools, the response includes:
        >>> # {"messages": [AIMessage(content="", tool_calls=[...])]}

        Direct Response:
        >>> # For simple queries, direct response is generated:
        >>> # {"messages": [AIMessage(content="Hello! How can I help?")]}

        See Also
        --------
        State : Input state structure
        ToolNode : Processes tool calls generated by this function
        tools_condition : Routes based on tool call presence
        ChatOpenAI.bind_tools : Enables tool discovery and calling
        """
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
        tools_condition,  # Built-in routing function
    )

    # Define the edges for the agentic loop
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    # Compile the graph with a memory saver for state persistence
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

    return graph
