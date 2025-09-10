#!/usr/bin/env python3
"""
Combined script to process files and test RAG tools in a fresh Python process.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QnA.settings')
import django
django.setup()

from data_app.manager import process_file_for_agent, get_answer_from_agent, agent_manager

def main():
    """Process files and test RAG tools."""
    print("=== Processing Files ===")

    # Process PDF file
    pdf_path = "/home/vedant/Desktop/QnA/media/uploads/vedantlahane25.pdf"
    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        success = process_file_for_agent(pdf_path, file_id=1)
        print(f"PDF processing: {'Success' if success else 'Failed'}")
    else:
        print(f"PDF file not found: {pdf_path}")

    # Process CSV file
    csv_path = "/home/vedant/Desktop/QnA/media/uploads/2025/09/10/Outlier_Earnings_Report.csv"
    if os.path.exists(csv_path):
        print(f"Processing CSV: {csv_path}")
        success = process_file_for_agent(csv_path, file_id=1)  # Using same file_id for simplicity
        print(f"CSV processing: {'Success' if success else 'Failed'}")
    else:
        print(f"CSV file not found: {csv_path}")

    print("\n=== Testing RAG Tools ===")

    # Check what tools are registered
    print(f"Registered tools: {list(agent_manager._available_tools.keys())}")

    # Test PDF RAG
    print("\n--- Testing PDF RAG Tool ---")
    pdf_query = "Summarize the content of the PDF document about Vedant Lahane"
    try:
        result = get_answer_from_agent(pdf_query, thread_id="test_pdf")
        print(f"Query: {pdf_query}")
        print(f"Response: {result[:400]}..." if len(result) > 400 else f"Response: {result}")
    except Exception as e:
        print(f"PDF RAG test failed: {e}")

    # Test CSV RAG
    print("\n--- Testing CSV RAG Tool ---")
    csv_query = "Analyze the earnings data in the CSV file and tell me the total amount earned"
    try:
        result = get_answer_from_agent(csv_query, thread_id="test_csv")
        print(f"Query: {csv_query}")
        print(f"Response: {result[:400]}..." if len(result) > 400 else f"Response: {result}")
    except Exception as e:
        print(f"CSV RAG test failed: {e}")

    # Test direct tool invocation
    print("\n--- Testing Direct Tool Invocation ---")
    
    # Test PDF tool directly
    if 'pdf_tool_1' in agent_manager._available_tools:
        pdf_tool = agent_manager._available_tools['pdf_tool_1']
        print("Direct PDF tool test:")
        try:
            result = pdf_tool.invoke({'query': 'What are Vedant Lahane\'s main skills and experience?'})
            print(f"Result: {result[:300]}..." if len(result) > 300 else f"Result: {result}")
        except Exception as e:
            print(f"Direct PDF tool error: {e}")
    
    # Test CSV tool directly
    if 'csv_tool_1' in agent_manager._available_tools:
        csv_tool = agent_manager._available_tools['csv_tool_1']
        print("\nDirect CSV tool test:")
        try:
            result = csv_tool.invoke({'query': 'What is the total payout amount in the earnings report?'})
            print(f"Result: {result[:300]}..." if len(result) > 300 else f"Result: {result}")
        except Exception as e:
            print(f"Direct CSV tool error: {e}")

    # Test search tool
    print("\n--- Testing Search Tool ---")
    search_query = "What are the latest developments in AI technology?"
    try:
        result = get_answer_from_agent(search_query, thread_id="test_search")
        print(f"Query: {search_query}")
        print(f"Response: {result[:400]}..." if len(result) > 400 else f"Response: {result}")
    except Exception as e:
        print(f"Search test failed: {e}")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
