#!/usr/bin/env python3
"""
Test script to verify the agent graph functionality.
This script tests if the agent graph can be built and run without errors.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QnA.settings')
django.setup()

# Now import the agent components
from data_app.agent_core.agent_graph import build_graph
from data_app.agent_core.tools import csv_rag_tool, pdf_rag_tool, sql_tool, tavily_search_tool

def test_agent_graph():
    """Test the agent graph creation and basic functionality."""
    print("Testing Agent Graph...")

    try:
        # Prepare the tools list
        available_tools = [
            csv_rag_tool.answer_question_on_csv,
            pdf_rag_tool.answer_question_on_pdf,
            sql_tool.query_sql_database,
            tavily_search_tool.search_internet
        ]

        print(f"Available tools: {[tool.name for tool in available_tools]}")

        # Build the graph
        print("Building agent graph...")
        graph = build_graph(available_tools)

        print("✅ Agent graph built successfully!")
        print(f"Graph nodes: {list(graph.nodes.keys())}")

        # Test a simple message
        print("\nTesting graph with a simple message...")
        test_input = {
            "messages": [{"role": "user", "content": "Hello, can you help me with a question?"}]
        }

        # Run the graph with required config
        config = {"configurable": {"thread_id": "test-thread-123"}}
        result = graph.invoke(test_input, config=config)
        print("✅ Graph executed successfully!")
        print(f"Response: {result['messages'][-1].content}")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_with_tools():
    """Test the agent with tool calls."""
    print("\nTesting agent with tool usage...")

    try:
        available_tools = [
            csv_rag_tool.answer_question_on_csv,
            pdf_rag_tool.answer_question_on_pdf,
            sql_tool.query_sql_database,
            tavily_search_tool.search_internet
        ]

        graph = build_graph(available_tools)

        # Test with a message that might trigger tool usage
        test_input = {
            "messages": [{"role": "user", "content": "Search the internet for the latest news about AI."}]
        }

        config = {"configurable": {"thread_id": "test-tool-thread"}}
        result = graph.invoke(test_input, config=config)

        print("✅ Agent with tools executed successfully!")
        print(f"Response: {result['messages'][-1].content}")

        return True

    except Exception as e:
        print(f"❌ Error in tool test: {str(e)}")
        return False

if __name__ == "__main__":
    success1 = test_agent_graph()
    success2 = test_agent_with_tools()

    if success1 and success2:
        print("\n🎉 All tests passed! The agent graph is working correctly.")
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")
        sys.exit(1)
