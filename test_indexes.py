#!/usr/bin/env python3
"""
Test script to check if FAISS indexes for uploaded files can be loaded.
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

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from data_app.agent_core.config import LoadToolsConfig

TOOLS_CFG = LoadToolsConfig()

def test_load_pdf_index(file_id: int):
    try:
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        vector_store = FAISS.load_local(
            f"data/faiss_index_{file_id}",
            embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"PDF index {file_id} loaded successfully. Documents: {vector_store.index.ntotal}")
        return True
    except Exception as e:
        print(f"Failed to load PDF index {file_id}: {e}")
        return False

def test_load_csv_index(file_id: int):
    try:
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
        vector_store = FAISS.load_local(
            f"data/faiss_index_csv_{file_id}",
            embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"CSV index {file_id} loaded successfully. Documents: {vector_store.index.ntotal}")
        return True
    except Exception as e:
        print(f"Failed to load CSV index {file_id}: {e}")
        return False

if __name__ == "__main__":
    print("Testing FAISS index loading...")

    # Test PDF indexes
    pdf_ids = [1, 4]  # Based on existing folders
    for fid in pdf_ids:
        test_load_pdf_index(fid)

    # Test CSV index
    csv_ids = [1]
    for fid in csv_ids:
        test_load_csv_index(fid)

    print("Index loading test completed.")
