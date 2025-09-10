#!/usr/bin/env python3
"""
Script to manually process uploaded files and register RAG tools.
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

from data_app.manager import process_file_for_agent

def process_files():
    """Process the uploaded files to register RAG tools."""
    print("Processing uploaded files...")

    # Process PDF file
    pdf_path = "/home/vedant/Desktop/QnA/media/uploads/vedantlahane25.pdf"
    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        success = process_file_for_agent(pdf_path, file_id=1)
        if success:
            print("PDF processed successfully")
        else:
            print("PDF processing failed")
    else:
        print(f"PDF file not found: {pdf_path}")

    # Process CSV file
    csv_path = "/home/vedant/Desktop/QnA/media/uploads/2025/09/10/Outlier_Earnings_Report.csv"
    if os.path.exists(csv_path):
        print(f"Processing CSV: {csv_path}")
        success = process_file_for_agent(csv_path, file_id=1)  # Using same file_id for simplicity
        if success:
            print("CSV processed successfully")
        else:
            print("CSV processing failed")
    else:
        print(f"CSV file not found: {csv_path}")

if __name__ == "__main__":
    process_files()
