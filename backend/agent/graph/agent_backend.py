import os
from pathlib import Path
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from dotenv import load_dotenv
from langgraph.graph import add_messages, StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from .pdf_tool import search_pdf          # decorated tool function
from .sql_tool import run_sql_query       # decorated SQL query tool function
from .tavily_search_tool import tavily_search  # decorated Tavily search tool function

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

class State(TypedDict):
    messages: Annotated[List[Dict[str, Any]], add_messages]


SYSTEM_PROMPT = (
    "You are Axon Copilot, an assistant that combines retrieved document knowledge with live tools. "
    "Always use the available tools when they can improve your answer. "
    "Call `tavily_search` for questions about current events, weather, general facts, or anything that "
    "requires up-to-date or external information. Only answer from prior knowledge when tools are "
    "clearly unnecessary."
)


def route_tools(state: State) -> str:
    """
    Conditional routing function that decides whether to route to the tools node
    based on the last assistant message indicating a tool call.
    """
    last_message = state["messages"][-1]
    # Handle both dict and BaseMessage objects
    if isinstance(last_message, BaseMessage):
        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls:
            tool_calls = last_message.additional_kwargs.get("tool_calls") if hasattr(last_message, "additional_kwargs") else None
        if tool_calls:
            return "tools"
        content = last_message.content
    else:
        content = last_message.get("content", "")
        tool_calls = last_message.get("tool_calls") if isinstance(last_message, dict) else None
        if tool_calls:
            return "tools"
    # You can implement your own logic to detect if a tool call is needed
    if "TOOL_CALL" in content:  # example marker indicating tool usage
        return "tools"
    return END

def build_graph():
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # List of your tool functions
    tools = [search_pdf, run_sql_query, tavily_search]

    # Bind tools to LLM to create an agent
    llm_with_tools = llm.bind_tools(tools)

    # Define chatbot node: takes state, calls llm_with_tools, returns message
    def chatbot(state: State):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(State)
    graph.add_node("chatbot", chatbot)

    # Tool execution node
    graph.add_node("tools", llm_with_tools)

    # Conditional routing based on chatbot output
    graph.add_conditional_edges(
        "chatbot",
        route_tools,
        {"tools": "tools", END: END},
    )

    # Loop from tools back to chatbot
    graph.add_edge("tools", "chatbot")
    graph.add_edge(START, "chatbot")

    return graph.compile()

# Cache graph instance
_GRAPH = None

def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
        try:
            with open("graph.png", "wb") as f:
                f.write(_GRAPH.get_graph().draw_mermaid_png())
            print("Graph saved as graph.png")
        except Exception as exc:
            print(f"Warning: unable to save graph visualization ({exc})")
    return _GRAPH

_FALLBACK_MESSAGE = "Sorry, I could not generate a response right now."

def generate_response(
    prompt: str,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    document_context: Optional[str] = None,
    external_context: Optional[str] = None,
) -> str:
    """Return the assistant reply for the provided prompt and history."""
    if not prompt:
        return _FALLBACK_MESSAGE

    prior_messages: List[Dict[str, Any]] = []
    if history:
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                prior_messages.append({"role": role, "content": content})

    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *prior_messages,
    ]

    if document_context:
        conversation.append(
            {
                "role": "system",
                "content": (
                    "Use the following excerpts from the user's uploaded documents as trusted context when you answer.\n\n"
                    f"{document_context}"
                ),
            }
        )

    if external_context:
        conversation.append(
            {
                "role": "system",
                "content": (
                    "The following information was retrieved from the web. Incorporate it into your answer when relevant.\n\n"
                    f"{external_context}"
                ),
            }
        )

    conversation.append({"role": "user", "content": prompt})

    try:
        graph = get_graph()
        result = graph.invoke({"messages": conversation})
    except Exception as exc:
        print(f"Assistant backend error: {exc}")
        fallback_chunks: List[str] = []
        if document_context:
            fallback_chunks.append(
                "I could not reach the language model, but here are excerpts from your uploaded documents:\n\n"
                f"{document_context}"
            )
        if external_context:
            fallback_chunks.append(
                "I could not reach the language model, but here are insights from a recent web search:\n\n"
                f"{external_context}"
            )
        if fallback_chunks:
            return "\n\n---\n\n".join(fallback_chunks)
        return _FALLBACK_MESSAGE

    messages = result.get("messages") if isinstance(result, dict) else None
    if not messages:
        return _FALLBACK_MESSAGE

    last_message = messages[-1]
    if isinstance(last_message, BaseMessage):
        content = last_message.content
        if isinstance(content, str):
            return content or _FALLBACK_MESSAGE
        return str(content) if content else _FALLBACK_MESSAGE

    content_value = last_message.get("content") if isinstance(last_message, dict) else None
    if isinstance(content_value, str):
        return content_value or _FALLBACK_MESSAGE
    if content_value:
        return str(content_value)

    fallback_chunks: List[str] = []
    if document_context:
        fallback_chunks.append(
            "Here are excerpts from your uploaded documents:\n\n"
            f"{document_context}"
        )
    if external_context:
        fallback_chunks.append(
            "Here are insights from a recent web search:\n\n"
            f"{external_context}"
        )

    if fallback_chunks:
        return "\n\n---\n\n".join(fallback_chunks)

    return _FALLBACK_MESSAGE

def stream_graph_updates(messages: List[Dict[str, Any]]):
    graph = get_graph()
    for event in graph.stream({"messages": messages}):
        for value in event.values():
            msgs = value.get("messages", [])
            if msgs:
                content = msgs[-1].get("content", "")
                print("Assistant:", content)

if __name__ == "__main__":
    graph = get_graph()
    conversation: List[Any] = []

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            conversation.append({"role": "user", "content": user_input})

            assistant_responses = []
            for event in graph.stream({"messages": conversation}):
                for value in event.values():
                    msgs = value.get("messages", [])
                    if msgs:
                        last_msg = msgs[-1]
                        # Handle both dict and BaseMessage objects
                        if isinstance(last_msg, BaseMessage):
                            content = last_msg.content
                        else:
                            content = last_msg.get("content", "")
                        print("Assistant:", content)
                        assistant_responses.append(content)

            if assistant_responses:
                conversation.append({"role": "assistant", "content": assistant_responses[-1]})

        except Exception as e:
            print(f"Error occurred: {e}")
            break
