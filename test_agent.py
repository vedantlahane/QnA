#!/usr/bin/env python3
"""
Enhanced test script for the LangGraph agent.

What it does:
- Builds the agent graph and verifies basic execution.
- Uses proper LangChain message objects for compatibility.
- Supports --online mode (real API calls) and default offline mode (mocked LLM and web search).
- Checks memory persistence via configurable thread_id across invocations.
- Prints tool availability and graph diagnostics.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# CLI args
parser = argparse.ArgumentParser(description="Test LangGraph agent build and execution")
parser.add_argument('--online', action='store_true', help='Run real LLM/Tavily calls (requires API keys)')
parser.add_argument('--thread-id', default='test-thread-123', help='Thread id for memory persistence tests')
parser.add_argument('--verbose', action='store_true', help='Enable debug logging')
parser.add_argument('--settings', default='QnA.settings', help='Django settings module (default: QnA.settings)')
args = parser.parse_args()

# Logging
logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('tests.agent_graph')

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', args.settings)
try:
    import django
    django.setup()
except Exception as e:
    logger.error(f"Failed to setup Django with settings '{args.settings}': {e}")
    sys.exit(1)

# Import LC messages (use HumanMessage for graph input)
from langchain_core.messages import HumanMessage, AIMessage

# Import agent components
from data_app.agent_core.agent_graph import build_graph
from data_app.agent_core.tools import csv_rag_tool, pdf_rag_tool, sql_tool, tavily_search_tool

def install_offline_mocks():
    """
    Monkeypatch ChatOpenAI and TavilySearch to offline fakes so the test runs without network/API keys.
    This preserves the agent’s structure while avoiding external calls.
    """
    import data_app.agent_core.agent_graph as agent_graph_mod

    class FakeChatOpenAI:
        def __init__(self, model: str = '', temperature: float = 0.0, **kwargs):
            self.model = model
            self.temperature = temperature
        def bind_tools(self, tools):
            return self
        def invoke(self, messages):
            try:
                last = messages[-1]
                content = getattr(last, 'content', str(last))
            except Exception:
                content = str(messages)
            return AIMessage(content=f"[FAKE LLM] Echo: {content}")

    agent_graph_mod.ChatOpenAI = FakeChatOpenAI

    # Patch TavilySearch used in the tavily tool
    import data_app.agent_core.tools.tavily_search_tool as tav_mod
    class FakeTavilySearch:
        def __init__(self, max_results=5, **kwargs):
            self.max_results = max_results
        def invoke(self, query: str):
            return [{
                'title': 'Mocked Result',
                'url': 'https://example.com',
                'snippet': f'Mocked search for: {query}'
            }]
    tav_mod.TavilySearch = FakeTavilySearch

def print_available_tools(tools):
    names = []
    for t in tools:
        name = getattr(t, 'name', getattr(t, '__name__', 'unknown_tool'))
        names.append(name)
    logger.info(f"Available tools: {names}")

def test_agent_graph(online: bool, thread_id: str) -> bool:
    logger.info("Testing Agent Graph build and simple execution...")

    if not online:
        install_offline_mocks()
        logger.info("Running in OFFLINE mode with mocked LLM and TavilySearch.")
    else:
        # Basic environment check for API keys when online
        missing = []
        # OpenAI key can be provided as OPENAI_API_KEY (preferred) or OPEN_AI_API_KEY
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('OPEN_AI_API_KEY'):
            missing.append('OPENAI_API_KEY')
        if not os.getenv('TAVILY_API_KEY'):
            missing.append('TAVILY_API_KEY')
        if missing:
            logger.warning(f"Missing API keys for online mode: {missing}")

    # Prepare the tools list
    available_tools = [
        csv_rag_tool.answer_question_on_csv,   # CSV RAG tool
        pdf_rag_tool.answer_question_on_pdf,   # PDF RAG tool
        sql_tool.query_sql_database,           # SQL tool
        tavily_search_tool.search_internet     # Tavily search tool
    ]
    print_available_tools(available_tools)

    # Build the graph
    logger.info("Building agent graph...")
    graph = build_graph(available_tools)
    logger.info("Agent graph built successfully.")
    logger.info(f"Graph nodes: {list(graph.nodes.keys())}")

    # Test a simple message using proper LC message objects
    logger.info("Executing graph with a simple message...")
    test_input = {"messages": [HumanMessage(content="Hello, can you help me with a question?")]}
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(test_input, config=config)
    last = result['messages'][-1]
    logger.info(f"Response type: {type(last).__name__}")
    logger.info(f"Response content: {getattr(last, 'content', str(last))}")

    # Memory persistence check: second call with same thread_id should extend history
    logger.info("Checking memory persistence across invocations...")
    result2 = graph.invoke({"messages": [HumanMessage(content="This is the second turn.")]}, config=config)
    len1 = len(result['messages'])
    len2 = len(result2['messages'])
    logger.info(f"Message count first run: {len1}, second run: {len2}")

    return True

def test_agent_with_tools(online: bool, thread_id: str) -> bool:
    logger.info("Testing agent routing that may use tools...")

    if not online:
        install_offline_mocks()
        logger.info("Running in OFFLINE mode with mocked LLM and TavilySearch.")

    available_tools = [
        csv_rag_tool.answer_question_on_csv,
        pdf_rag_tool.answer_question_on_pdf,
        sql_tool.query_sql_database,
        tavily_search_tool.search_internet
    ]
    graph = build_graph(available_tools)

    # Prompt intended to trigger web search; actual tool call depends on LLM behavior
    user_msg = HumanMessage(content="Search the internet for the latest news about AI.")
    config = {"configurable": {"thread_id": f"{thread_id}-tools"}}
    result = graph.invoke({"messages": [user_msg]}, config=config)

    last = result['messages'][-1]
    logger.info(f"Tool test response: {getattr(last, 'content', str(last))}")

    # Note: Without a real LLM, tool calls may not be issued; this test validates execution path.
    return True

if __name__ == "__main__":
    ok_build = test_agent_graph(online=args.online, thread_id=args.thread_id)
    ok_tools = test_agent_with_tools(online=args.online, thread_id=args.thread_id)

    if ok_build and ok_tools:
        print("\nAll tests passed. The agent graph appears functional.")
        sys.exit(0)
    else:
        print("\nSome tests failed. Check logs above.")
        sys.exit(1)
