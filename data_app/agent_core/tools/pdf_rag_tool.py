"""
PDF Retrieval-Augmented Generation (RAG) Tool Module

This module implements a complete RAG (Retrieval-Augmented Generation) system
for PDF document processing and question answering. It provides the capability
to upload PDF documents, process them into searchable vector embeddings, and
answer questions based on the document content using advanced language models.

The module consists of two main components:
1. Document Processing: Converts PDF files into vector embeddings for search
2. Question Answering: Uses RAG to provide accurate answers from document content

Architecture:
    The RAG system follows this workflow:
    1. PDF Loading → Text Extraction
    2. Text Chunking → Semantic Segmentation
    3. Embedding Generation → Vector Representation
    4. Vector Storage → FAISS Index Creation
    5. Query Processing → Similarity Search
    6. Context Retrieval → Relevant Information
    7. Answer Generation → LLM Response

Key Features:
    - PDF text extraction and processing
    - Intelligent text chunking with overlap
    - OpenAI embeddings for semantic understanding
    - FAISS vector database for efficient similarity search
    - Configurable retrieval parameters
    - Error handling and logging
    - Integration with LangChain agent system

Dependencies:
    - langchain_community: For PDF loading and vector stores
    - langchain_openai: For embeddings and LLM integration
    - langchain_core: For tool decoration
    - faiss: For vector similarity search (via langchain_community)
    - data_app.agent_core.config: For configuration management

Configuration Parameters (from tools_config.yml):
    - pdf_rag_llm: Language model for answer generation
    - pdf_rag_llm_temperature: Creativity/randomness setting
    - pdf_rag_embedding_model: Model for text embeddings
    - pdf_rag_chunk_size: Size of text chunks for processing
    - pdf_rag_chunk_overlap: Overlap between text chunks
    - pdf_rag_k: Number of similar chunks to retrieve

File Storage:
    - Vector indices stored in: data/faiss_index_{file_id}/
    - Each uploaded PDF gets its own searchable index
    - Indices persist across application restarts

Author: Q&A Agent System
Created: 2025
"""

import os
from typing import List, Optional, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain.chains import RetrievalQA
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
# Load configuration settings from the centralized config file
# This ensures all PDF RAG parameters are managed centrally
TOOLS_CFG = LoadToolsConfig()


def process_and_vectorize(file_path: str, file_id: int) -> None:
    """
    Process a PDF file and create searchable vector embeddings.

    This function implements the document processing pipeline of the RAG system.
    It loads the PDF, extracts text, splits it into semantically meaningful chunks,
    generates vector embeddings, and stores them in a FAISS vector database for
    efficient similarity search.

    The processing pipeline:
    1. Load PDF document using PyPDFLoader
    2. Split text into chunks with configurable size and overlap
    3. Generate embeddings using OpenAI's embedding model
    4. Create FAISS vector store for efficient search
    5. Persist the index to disk for future queries

    Args:
        file_path (str): Absolute path to the PDF file to be processed
        file_id (int): Unique identifier for the file, used for index naming

    Returns:
        None

    Raises:
        FileNotFoundError: If the PDF file doesn't exist at the specified path
        ValueError: If file_id is invalid or configuration is missing
        Exception: For various processing errors (PDF corruption, API failures, etc.)

    Example:
        >>> process_and_vectorize("/uploads/document.pdf", 123)
        PDF file with ID 123 processed and vectorized.

    Notes:
        - The function creates a directory structure: data/faiss_index_{file_id}/
        - Processing time depends on PDF size and complexity
        - Large PDFs may require significant memory for processing
        - The FAISS index enables fast similarity search for queries

    Configuration Dependencies:
        - TOOLS_CFG.pdf_rag_chunk_size: Controls text chunk size
        - TOOLS_CFG.pdf_rag_chunk_overlap: Controls chunk overlap
        - TOOLS_CFG.pdf_rag_embedding_model: Specifies embedding model
    """
    try:
        # Step 1: Load the PDF document
        # PyPDFLoader extracts text from all pages of the PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # Validate that we successfully loaded content
        if not documents:
            raise ValueError(f"No content extracted from PDF: {file_path}")

        # Step 2: Split the document into manageable chunks
        # RecursiveCharacterTextSplitter preserves semantic structure
        # while ensuring chunks fit within token limits
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.pdf_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.pdf_rag_chunk_overlap
        )
        docs = text_splitter.split_documents(documents)

        # Log chunking results for monitoring
        print(f"PDF split into {len(docs)} chunks")

        # Step 3: Generate embeddings for semantic understanding
        # OpenAI embeddings provide high-quality vector representations
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model
        )

        # Step 4: Create FAISS vector store
        # FAISS provides efficient similarity search capabilities
        vector_store = FAISS.from_documents(docs, embeddings)

        # Step 5: Persist the vector store to disk
        # This allows the index to be reused across application restarts
        index_path = f"data/faiss_index_{file_id}"
        vector_store.save_local(index_path)

        print(f"PDF file with ID {file_id} processed and vectorized.")
        print(f"Vector index saved to: {index_path}")

    except FileNotFoundError as e:
        error_msg = f"PDF file not found: {file_path}"
        print(f"Error: {error_msg}")
        raise FileNotFoundError(error_msg) from e

    except ValueError as e:
        error_msg = f"Invalid PDF or configuration: {str(e)}"
        print(f"Error: {error_msg}")
        raise ValueError(error_msg) from e

    except Exception as e:
        # Catch-all for unexpected errors during processing
        error_msg = f"Unexpected error processing PDF file: {str(e)}"
        print(f"Error: {error_msg}")
        raise Exception(error_msg) from e


@tool
def answer_question_on_pdf(query: str, file_id: int) -> str:
    """
    Answer questions based on content from a specific PDF document.

    This tool function implements the retrieval and generation components of RAG.
    It loads the pre-processed vector index for a specific PDF, performs semantic
    search to find relevant content, and uses an LLM to generate accurate answers
    based on the retrieved information.

    The RAG process:
    1. Load the FAISS vector store for the specified PDF
    2. Convert query to vector embedding
    3. Perform similarity search to find relevant text chunks
    4. Retrieve top-k most similar chunks as context
    5. Use LLM to generate answer based on retrieved context
    6. Return the generated answer

    Args:
        query (str): The user's question about the PDF content. Should be
                    clear and specific for optimal retrieval.
        file_id (int): Unique identifier of the PDF file to search within.
                      Must match the ID used during file processing.

    Returns:
        str: Generated answer based on the PDF content. If no relevant
             information is found or an error occurs, returns an appropriate
             error message.

    Raises:
        None: All exceptions are caught internally and returned as error strings

    Examples:
        >>> result = answer_question_on_pdf("What is the main topic?", 123)
        >>> print(result)
        "The main topic of the document is machine learning algorithms..."

        >>> result = answer_question_on_pdf("Who is the author?", 123)
        >>> print(result)
        "The author information is not available in the document content."

    Notes:
        - Requires the PDF to be pre-processed using process_and_vectorize()
        - Search quality depends on chunk size, overlap, and embedding model
        - Retrieval uses cosine similarity for finding relevant content
        - Answer generation considers the top-k most similar chunks
        - Function handles cases where no relevant information is found

    Configuration Dependencies:
        - TOOLS_CFG.pdf_rag_llm: Model used for answer generation
        - TOOLS_CFG.pdf_rag_llm_temperature: Controls answer creativity
        - TOOLS_CFG.pdf_rag_k: Number of chunks to retrieve for context
        - TOOLS_CFG.pdf_rag_embedding_model: Must match processing embeddings

    Performance Considerations:
        - Vector search is fast (milliseconds) for most queries
        - LLM generation time depends on model and context length
        - Memory usage scales with the number of retrieved chunks
        - Large PDFs may have slower retrieval due to more chunks
    """
    try:
        # Step 1: Load the pre-computed FAISS vector store
        # This contains the vector embeddings for the specific PDF
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model
        )

        index_path = f"data/faiss_index_{file_id}"
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True  # Required for FAISS loading
        )

        # Step 2: Set up the retriever for similarity search
        # Configures the search parameters for optimal retrieval
        retriever = vector_store.as_retriever(
            search_type="similarity",  # Cosine similarity search
            search_kwargs={"k": TOOLS_CFG.pdf_rag_k}  # Number of results to retrieve
        )

        # Step 3: Initialize the language model for answer generation
        # Uses the configured model with appropriate temperature settings
        llm = ChatOpenAI(
            temperature=TOOLS_CFG.pdf_rag_llm_temperature,
            model=TOOLS_CFG.pdf_rag_llm
        )

        # Step 4: Create the RAG chain
        # RetrievalQA combines retrieval and generation in a single pipeline
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=False  # Only return the answer, not source docs
        )

        # Step 5: Execute the RAG pipeline
        # This performs retrieval + generation in one step
        response = qa_chain.run(query)

        # Step 6: Return the generated answer
        return response

    except FileNotFoundError as e:
        # Handle case where vector index doesn't exist
        error_msg = (
            "Sorry, the PDF with the specified ID has not been processed yet. "
            "Please ensure the file has been uploaded and processed before asking questions."
        )
        print(f"Vector index not found for file_id {file_id}: {str(e)}")
        return error_msg

    except ValueError as e:
        # Handle configuration or data validation errors
        error_msg = (
            "Sorry, there was a configuration issue with the PDF search. "
            "Please try again or contact support if the problem persists."
        )
        print(f"Configuration error for PDF search: {str(e)}")
        return error_msg

    except Exception as e:
        # Catch-all for unexpected errors during RAG processing
        error_msg = (
            "Sorry, I could not find information on this topic in the specified PDF. "
            f"Error details: {str(e)}. "
            "The document may not contain relevant information about your question."
        )
        print(f"Unexpected error in PDF RAG: {str(e)}")
        return error_msg


"""
USAGE INFORMATION:

This module is designed to work with the Q&A agent system:

1. File Upload and Processing:
   >>> from data_app.agent_core.tools.pdf_rag_tool import process_and_vectorize
   >>> process_and_vectorize("/uploads/document.pdf", 123)
   # Creates searchable vector index for the PDF

2. Question Answering (via Agent):
   >>> from data_app.manager import get_answer_from_agent
   >>> answer = get_answer_from_agent("What is discussed in the PDF?")
   # Agent automatically uses the PDF RAG tool

3. Direct Tool Usage:
   >>> from data_app.agent_core.tools.pdf_rag_tool import answer_question_on_pdf
   >>> result = answer_question_on_pdf("Summarize the main points", 123)

INTEGRATION WITH AGENT SYSTEM:

The PDF RAG tool is automatically registered with the agent when a PDF is processed:

1. User uploads PDF → process_and_vectorize() is called
2. Vector index is created and saved
3. Tool is registered: pdf_tool_{file_id} → answer_question_on_pdf
4. Agent can now answer questions about that specific PDF
5. Multiple PDFs can be processed with different file_ids

FILE PROCESSING WORKFLOW:

1. Upload: PDF file is uploaded to the system
2. Processing: process_and_vectorize() extracts text and creates embeddings
3. Storage: FAISS index is saved to data/faiss_index_{file_id}/
4. Registration: Tool is added to agent's available tools
5. Query: User asks questions → agent uses appropriate PDF tool
6. Retrieval: Similar content chunks are found using vector search
7. Generation: LLM creates answer based on retrieved context

PERFORMANCE OPTIMIZATION:

- Chunk Size: Balance between context and precision
- Chunk Overlap: Ensures semantic continuity
- Embedding Model: Trade-off between quality and speed
- Retrieval K: Balance between comprehensiveness and speed
- Index Persistence: Avoids reprocessing on restart

TROUBLESHOOTING:

1. "Vector index not found":
   - Ensure PDF was processed with process_and_vectorize()
   - Check file_id matches between processing and querying
   - Verify data/faiss_index_{file_id}/ directory exists

2. "No relevant information found":
   - Try rephrasing the question
   - Check if the information exists in the PDF
   - Consider adjusting chunk_size or k parameters

3. "Processing failed":
   - Verify PDF is not corrupted or password-protected
   - Check file permissions and disk space
   - Ensure OpenAI API key is configured correctly

4. "Memory errors":
   - Reduce chunk_size in configuration
   - Process large PDFs in smaller batches
   - Consider using GPU for embedding generation

CONFIGURATION TUNING:

For optimal performance, adjust these parameters in tools_config.yml:

- chunk_size: 500-2000 (smaller for precision, larger for context)
- chunk_overlap: 50-200 (10-20% of chunk_size)
- k: 3-7 (more for comprehensive answers, fewer for speed)
- temperature: 0.1-0.7 (lower for factual, higher for creative answers)
"""