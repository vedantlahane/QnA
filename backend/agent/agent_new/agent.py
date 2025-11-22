import os
from typing import List, Dict, Any, Optional, Sequence, cast
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig  # Import for type hints
from .pdf_tool import search_pdf       
from .sql_tool import run_sql_query      
from .tavily_search_tool import tavily_search  


load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key


SYSTEM_PROMPT = (
    "You are Axon Copilot, an assistant that combines retrieved document knowledge with live tools. "
    "Always use the available tools when they can improve your answer. "
    "Call `tavily_search` for questions about current events, weather, general facts, or anything that "
    "requires up-to-date or external information. Only answer from prior knowledge when tools are "
    "clearly unnecessary."
)


# Create the agent - that's it!
_AGENT = None


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = create_agent(
            model="gpt-4o",
            tools=[search_pdf, run_sql_query, tavily_search],
            system_prompt=SYSTEM_PROMPT
        )
        print("Agent created successfully")
    return _AGENT


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

    # Build conversation
    conversation = []
    
    if history:
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role == "user":
                conversation.append(HumanMessage(content=content))
            elif role == "assistant":
                conversation.append(AIMessage(content=content))

    # Add context via system messages
    context_parts = []
    if document_context:
        context_parts.append(
            f"Use the following excerpts from the user's uploaded documents as trusted context:\n\n{document_context}"
        )
    if external_context:
        context_parts.append(
            f"The following information was retrieved from the web:\n\n{external_context}"
        )
    
    if context_parts:
        conversation.append(SystemMessage(content="\n\n---\n\n".join(context_parts)))

    conversation.append(HumanMessage(content=prompt))

    try:
        agent = get_agent()
        # Properly typed config for RunnableConfig
        config: RunnableConfig = {"configurable": {"thread_id": "default"}}
        result = agent.invoke({"messages": conversation}, config)
        
        # Extract response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content or _FALLBACK_MESSAGE
            return last_message.get("content", _FALLBACK_MESSAGE)
        
    except Exception as exc:
        print(f"Assistant backend error: {exc}")
        fallback_chunks = []
        if document_context:
            fallback_chunks.append(f"Excerpts from your documents:\n\n{document_context}")
        if external_context:
            fallback_chunks.append(f"Insights from web search:\n\n{external_context}")
        if fallback_chunks:
            return "\n\n---\n\n".join(fallback_chunks)

    return _FALLBACK_MESSAGE


def stream_response(messages: List):
    """Stream agent responses."""
    agent = get_agent()
    # Properly typed config
    config: RunnableConfig = {"configurable": {"thread_id": "default"}}
    
    for event in agent.stream({"messages": messages}, config, stream_mode="values"):
        msgs = event.get("messages", [])
        if msgs:
            last_msg = msgs[-1]
            content = getattr(last_msg, 'content', '') or last_msg.get("content", "")
            if content:
                yield content


if __name__ == "__main__":
    agent = get_agent()
    conversation = []

    print("Axon Copilot ready! (type 'quit' to exit)")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            conversation.append(HumanMessage(content=user_input))
            
            # Properly typed config
            config: RunnableConfig = {"configurable": {"thread_id": "cli_session"}}
            result = agent.invoke({"messages": conversation}, config)
            
            # Get last message
            messages = result.get("messages", [])
            if messages:
                assistant_msg = messages[-1]
                response = getattr(assistant_msg, 'content', '') or assistant_msg.get("content", "")
                print(f"\nAssistant: {response}")
                conversation.append(AIMessage(content=response))

        except Exception as e:
            print(f"Error: {e}")
            break
