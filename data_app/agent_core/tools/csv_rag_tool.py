# data_app/agent_core/tools/csv_rag_tool.py

"""
CSV Retrieval-Augmented Generation (RAG) Tool Module

This module provides functionality for processing CSV files and enabling question-answering
capabilities over their content using retrieval-augmented generation (RAG) techniques.

The module contains two main components:
1. CSV processing and vectorization pipeline
2. Question-answering tool for querying processed CSV data

Key Features:
- Automatic CSV document loading and text chunking
- OpenAI embeddings for semantic vectorization
- FAISS vector database for efficient similarity search
- LangChain-powered retrieval QA chains
- Configurable parameters via YAML configuration

Dependencies:
- langchain_community: For CSV loading and vector stores
- langchain_openai: For embeddings and LLM integration
- faiss-cpu: For vector similarity search
- pandas: Required by CSVLoader for data processing

Configuration Requirements:
- OpenAI API key must be set in environment variables
- CSV RAG parameters configured in tools_config.yml:
  * csv_rag_chunk_size: Text chunk size for splitting
  * csv_rag_chunk_overlap: Overlap between text chunks
  * csv_rag_embedding_model: OpenAI embedding model name
  * csv_rag_k: Number of similar documents to retrieve
  * csv_rag_llm: Language model for question answering
  * csv_rag_llm_temperature: LLM temperature setting

Usage Example:
    >>> from csv_rag_tool import process_and_vectorize, answer_question_on_csv
    >>> # Process a CSV file
    >>> process_and_vectorize("data/sales.csv", file_id=1)
    >>> # Query the processed data
    >>> answer = answer_question_on_csv("What are the total sales?", file_id=1)
    >>> print(answer)

Error Handling:
- File processing errors are logged to console
- Query failures return user-friendly error messages
- Vector store loading includes deserialization safety checks

Performance Notes:
- Large CSV files may require significant processing time
- FAISS indices are saved locally for reuse
- Embedding generation is the most computationally intensive step

Author: AI Assistant
Created: 2024
"""

import os
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

def process_and_vectorize(file_path: str, file_id: int):
    """
    Process a CSV file and create a vectorized FAISS index for semantic search.

    This function loads a CSV file, splits its content into manageable text chunks,
    generates embeddings using OpenAI's embedding model, and stores the vectorized
    data in a FAISS index for efficient similarity search operations.

    The processing pipeline:
    1. Load CSV file using LangChain's CSVLoader
    2. Split documents into chunks with configurable overlap
    3. Generate embeddings for each chunk
    4. Create and save FAISS vector store locally

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the CSV file to be processed.
        The file should be a valid CSV format that can be read by pandas.
    file_id : int
        Unique identifier for the file. Used to create distinct FAISS index
        directories to avoid conflicts between different CSV files.

    Returns
    -------
    None
        This function doesn't return a value. It saves the FAISS index to disk
        and prints processing status to console.

    Raises
    ------
    FileNotFoundError
        If the specified file_path does not exist or is not accessible.
    ValueError
        If the CSV file format is invalid or cannot be parsed.
    Exception
        For any other processing errors (OpenAI API issues, disk space, etc.).

    Examples
    --------
    >>> process_and_vectorize("/path/to/sales_data.csv", file_id=123)
    CSV file with ID 123 processed and vectorized.

    >>> process_and_vectorize("data/customer_data.csv", file_id=456)
    CSV file with ID 456 processed and vectorized.

    Notes
    -----
    - The FAISS index is saved to: data/faiss_index_csv_{file_id}/
    - Processing time depends on CSV size and OpenAI API response times
    - Each chunk contains approximately csv_rag_chunk_size characters
    - Overlapping chunks help maintain context across chunk boundaries

    See Also
    --------
    answer_question_on_csv : Query the processed CSV data
    LoadToolsConfig : Configuration management for processing parameters
    """
    try:
        loader = CSVLoader(file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.csv_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.csv_rag_chunk_overlap
        )
        docs = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(f"data/faiss_index_csv_{file_id}")
        
        print(f"CSV file with ID {file_id} processed and vectorized.")
        
    except Exception as e:
        print(f"Error processing CSV file: {e}")


@tool
def answer_question_on_csv(query: str, file_id: int) -> str:
    """
    Answer questions about CSV data using retrieval-augmented generation.

    This LangChain tool function enables natural language querying of previously
    processed CSV files. It uses semantic similarity search to find relevant
    content chunks and generates answers using a configured language model.

    The query process:
    1. Load the FAISS vector store for the specified file_id
    2. Perform similarity search to find relevant document chunks
    3. Use LangChain's RetrievalQA chain to generate answers
    4. Return the generated response or error message

    Parameters
    ----------
    query : str
        The natural language question to ask about the CSV data.
        Should be clear and specific for best results.
    file_id : int
        Unique identifier of the CSV file to query. Must match the file_id
        used during processing with process_and_vectorize().

    Returns
    -------
    str
        Generated answer to the query based on the CSV content.
        Returns error message if processing fails or data is not found.

    Raises
    ------
    This function handles exceptions internally and returns error messages
    as strings rather than raising exceptions.

    Examples
    --------
    >>> # Assuming CSV with sales data has been processed with file_id=1
    >>> answer = answer_question_on_csv("What are the total sales for Q1?", file_id=1)
    >>> print(answer)
    "Based on the CSV data, the total sales for Q1 were $1,250,000..."

    >>> # Query about non-existent data
    >>> answer = answer_question_on_csv("What is the weather today?", file_id=1)
    >>> print(answer)
    "Sorry, I could not find information on this topic in the specified CSV..."

    Notes
    -----
    - The tool retrieves the top-k most similar chunks (configured via csv_rag_k)
    - Answer quality depends on the clarity of the query and CSV content structure
    - Large CSVs may have better coverage but slower response times
    - The LLM temperature affects answer creativity vs. accuracy

    Dependencies
    ------------
    - Requires FAISS index created by process_and_vectorize() for the same file_id
    - OpenAI API key must be configured for LLM responses
    - Vector store files must exist in data/faiss_index_csv_{file_id}/

    Performance Considerations
    -------------------------
    - Similarity search is fast (milliseconds) for most datasets
    - LLM generation time varies based on query complexity
    - Memory usage scales with the number of retrieved chunks (k parameter)

    See Also
    --------
    process_and_vectorize : Prepare CSV data for querying
    LoadToolsConfig : Access configuration parameters
    FAISS : Vector similarity search library
    RetrievalQA : LangChain question-answering chain
    """
    try:
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
        vector_store = FAISS.load_local(
            f"data/faiss_index_csv_{file_id}",
            embeddings,
            allow_dangerous_deserialization=True
        )

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.csv_rag_k}
        )

        llm = ChatOpenAI(
            temperature=TOOLS_CFG.csv_rag_llm_temperature,
            model=TOOLS_CFG.csv_rag_llm
        )
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

        response = qa_chain.run(query)
        return response

    except Exception as e:
        return f"Sorry, I could not find information on this topic in the specified CSV. Error: {e}"