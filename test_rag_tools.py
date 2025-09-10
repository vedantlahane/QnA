#!/usr/bin/env python3
"""
Test script to verify RAG tools work with uploaded files using real API calls.
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

from data_app.manager import agent_manager, get_answer_from_agent

def test_rag_tools():
    """Test PDF and CSV RAG tools with the uploaded files."""
    print("Testing RAG tools with uploaded files...")

    # Check what tools are registered
    print(f"Registered tools: {list(agent_manager._available_tools.keys())}")

    # Test with a more specific query that should trigger RAG tools
    print("\n--- Testing PDF RAG Tool ---")
    pdf_query = "Answer questions about the PDF content in file_id 1: What is this document about?"
    try:
        result = get_answer_from_agent(pdf_query, thread_id="test_pdf")
        print(f"PDF Query: {pdf_query}")
        print(f"Response: {result[:300]}..." if len(result) > 300 else f"Response: {result}")
    except Exception as e:
        print(f"PDF RAG test failed: {e}")

    # Test CSV RAG
    print("\n--- Testing CSV RAG Tool ---")
    csv_query = "Answer questions about the CSV content in file_id 1: What data is contained in this file?"
    try:
        result = get_answer_from_agent(csv_query, thread_id="test_csv")
        print(f"CSV Query: {csv_query}")
        print(f"Response: {result[:300]}..." if len(result) > 300 else f"Response: {result}")
    except Exception as e:
        print(f"CSV RAG test failed: {e}")

    print("\nRAG tools test completed.")

if __name__ == "__main__":
    test_rag_tools()
