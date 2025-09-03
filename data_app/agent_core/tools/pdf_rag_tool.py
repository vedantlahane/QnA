# data_app/agent_core/tools/pdf_rag_tool.py

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _ensure_data_directory():
    """Ensure the data directory exists for storing FAISS indices."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir

def _validate_pdf_file(file_path: str) -> bool:
    """Validate that the PDF file exists and is readable."""
    if not os.path.exists(file_path):
        logger.error(f"PDF file does not exist: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        logger.error(f"Path is not a file: {file_path}")
        return False
    
    if not file_path.lower().endswith('.pdf'):
        logger.error(f"File is not a PDF: {file_path}")
        return False
    
    # Check if file is not empty
    if os.path.getsize(file_path) == 0:
        logger.error(f"PDF file is empty: {file_path}")
        return False
    
    return True

def _get_faiss_index_path(file_id: int) -> str:
    """Get the standardized FAISS index path for a PDF file."""
    data_dir = _ensure_data_directory()
    return str(data_dir / f"faiss_index_pdf_{file_id}")

def process_and_vectorize(file_path: str, file_id: int) -> bool:
    """
    Loads a PDF, splits it into chunks, and saves the embeddings to a FAISS vector database.
    
    Args:
        file_path (str): The full path to the uploaded PDF file.
        file_id (int): The unique ID of the uploaded file, used to name the vector DB.
    
    Returns:
        bool: True if processing was successful, False otherwise.
    """
    try:
        # Validate inputs
        if not _validate_pdf_file(file_path):
            return False
        
        if file_id <= 0:
            logger.error(f"Invalid file_id: {file_id}. Must be positive integer.")
            return False
        
        logger.info(f"Starting PDF processing for file: {file_path} with ID: {file_id}")
        
        # Load the PDF document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        if not documents:
            logger.error(f"No documents loaded from PDF file: {file_path}")
            return False
        
        logger.info(f"Loaded {len(documents)} pages from PDF")
        
        # Filter out empty pages
        non_empty_documents = [doc for doc in documents if doc.page_content.strip()]
        if not non_empty_documents:
            logger.error("No non-empty pages found in PDF")
            return False
        
        logger.info(f"Found {len(non_empty_documents)} non-empty pages")
        
        # Split the document into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.pdf_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.pdf_rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            length_function=len,
            add_start_index=True,  # Add start index for better tracking
        )
        docs = text_splitter.split_documents(non_empty_documents)
        
        if not docs:
            logger.error("No chunks created from documents")
            return False
        
        logger.info(f"Split into {len(docs)} chunks")
        
        # Generate embeddings using OpenAI
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model,
            show_progress_bar=True
        )
        
        # Create the FAISS vector store
        vector_store = FAISS.from_documents(docs, embeddings)
        
        # Save the vector store locally with a unique name
        index_path = _get_faiss_index_path(file_id)
        vector_store.save_local(index_path)
        
        logger.info(f"PDF file with ID {file_id} processed and vectorized successfully")
        logger.info(f"FAISS index saved to: {index_path}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"File not found during PDF processing: {e}")
        return False
    except PermissionError as e:
        logger.error(f"Permission error during PDF processing: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing PDF file: {e}")
        return False

def _check_faiss_index_exists(file_id: int) -> bool:
    """Check if FAISS index exists for the given file_id."""
    index_path = _get_faiss_index_path(file_id)
    return os.path.exists(f"{index_path}.faiss") and os.path.exists(f"{index_path}.pkl")

def _format_documents(docs: List[Any]) -> str:
    """Format retrieved documents for better context."""
    formatted_docs = []
    for i, doc in enumerate(docs, 1):
        content = doc.page_content.strip()
        if hasattr(doc, 'metadata') and doc.metadata:
            page_num = doc.metadata.get('page', 'unknown')
            source_info = f"Page {page_num}"
            if 'start_index' in doc.metadata:
                source_info += f", Position {doc.metadata['start_index']}"
            formatted_docs.append(f"Source {i} ({source_info}):\n{content}")
        else:
            formatted_docs.append(f"Source {i}:\n{content}")
    
    return "\n\n".join(formatted_docs)

@tool
def answer_question_on_pdf(query: str, file_id: int) -> str:
    """
    Answers a question by searching a specific PDF's vector database.
    This tool is used for queries that require information from a previously
    uploaded PDF document.
    
    Args:
        query (str): The user's question about the PDF content.
        file_id (int): The ID of the specific PDF file to search within.
        
    Returns:
        str: The generated answer from the LLM based on PDF content.
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return "Please provide a valid question about the PDF content."
        
        if file_id <= 0:
            return "Invalid file ID provided. Please specify a valid PDF file ID."
        
        # Check if FAISS index exists
        if not _check_faiss_index_exists(file_id):
            return f"No processed PDF data found for file ID {file_id}. Please ensure the file has been uploaded and processed."
        
        logger.info(f"Answering question for PDF file_id {file_id}: {query}")
        
        # Load the saved FAISS vector store for the specific file
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model
        )
        
        index_path = _get_faiss_index_path(file_id)
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Set up a retriever for the RAG chain with enhanced search
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.pdf_rag_k}
        )
        
        # Initialize the LLM
        llm = ChatOpenAI(
            temperature=TOOLS_CFG.pdf_rag_llm_temperature,
            model=TOOLS_CFG.pdf_rag_llm
        )
        
        # Create a custom prompt template for PDF content
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are an expert document analyst. Use the following PDF content to answer the question.

PDF Content:
{context}

Question: {question}

Instructions:
- Provide a clear, accurate answer based solely on the PDF content provided
- Include specific page references when available
- If you cannot find relevant information in the PDF content, clearly state this
- Be comprehensive but concise in your response
- If the question asks for specific details, quotes, or data points, include them exactly as they appear in the document
- Maintain the original formatting and structure when relevant

Answer:"""
        )
        
        # Create the RAG chain using the newer LCEL approach
        def format_docs(docs):
            return _format_documents(docs)
        
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt_template
            | llm
            | StrOutputParser()
        )
        
        # Get the answer
        response = rag_chain.invoke(query)
        
        logger.info(f"Successfully answered question for PDF file_id {file_id}")
        return response
        
    except FileNotFoundError:
        error_msg = f"FAISS index not found for PDF file ID {file_id}. Please ensure the file has been processed."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Sorry, I could not find information on this topic in the specified PDF. Error: {str(e)}"
        logger.error(f"Error in answer_question_on_pdf: {e}")
        return error_msg

# Utility functions for debugging and maintenance
def list_processed_pdf_files() -> List[int]:
    """List all file IDs that have been processed and have FAISS indices."""
    processed_files = []
    data_dir = Path("data")
    
    if not data_dir.exists():
        return processed_files
    
    for faiss_file in data_dir.glob("faiss_index_pdf_*.faiss"):
        try:
            file_id = int(faiss_file.stem.split("_")[-1])
            if _check_faiss_index_exists(file_id):
                processed_files.append(file_id)
        except (ValueError, IndexError):
            continue
    
    return sorted(processed_files)

def delete_pdf_index(file_id: int) -> bool:
    """Delete the FAISS index for a specific PDF file."""
    try:
        index_path = _get_faiss_index_path(file_id)
        
        # Remove FAISS files
        faiss_file = f"{index_path}.faiss"
        pkl_file = f"{index_path}.pkl"
        
        removed = False
        if os.path.exists(faiss_file):
            os.remove(faiss_file)
            removed = True
        
        if os.path.exists(pkl_file):
            os.remove(pkl_file)
            removed = True
        
        if removed:
            logger.info(f"Deleted FAISS index for PDF file_id {file_id}")
        
        return removed
    except Exception as e:
        logger.error(f"Error deleting PDF index for file_id {file_id}: {e}")
        return False

def get_pdf_stats(file_id: int) -> Optional[Dict[str, Any]]:
    """Get statistics about a processed PDF file."""
    try:
        if not _check_faiss_index_exists(file_id):
            return None
        
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        index_path = _get_faiss_index_path(file_id)
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        return {
            "file_id": file_id,
            "total_vectors": vector_store.index.ntotal,
            "embedding_dimension": vector_store.index.d,
            "index_path": index_path
        }
    except Exception as e:
        logger.error(f"Error getting PDF stats for file_id {file_id}: {e}")
        return None

def search_pdf_similarity(query: str, file_id: int, k: int = 5) -> List[Dict[str, Any]]:
    """
    Perform similarity search on a PDF without generating an answer.
    Useful for debugging and understanding what content is being retrieved.
    """
    try:
        if not _check_faiss_index_exists(file_id):
            return []
        
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        index_path = _get_faiss_index_path(file_id)
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Perform similarity search
        docs = vector_store.similarity_search_with_score(query, k=k)
        
        results = []
        for doc, score in docs:
            result = {
                "content": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata
            }
            results.append(result)
        
        return results
    except Exception as e:
        logger.error(f"Error performing similarity search on PDF file_id {file_id}: {e}")
        return []

def get_pdf_page_count(file_id: int) -> Optional[int]:
    """Get the number of pages in a processed PDF."""
    try:
        if not _check_faiss_index_exists(file_id):
            return None
        
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        index_path = _get_faiss_index_path(file_id)
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Get all documents and find unique pages
        all_docs = vector_store.docstore._dict.values()
        pages = set()
        
        for doc in all_docs:
            if hasattr(doc, 'metadata') and 'page' in doc.metadata:
                pages.add(doc.metadata['page'])
        
        return len(pages) if pages else None
    except Exception as e:
        logger.error(f"Error getting page count for PDF file_id {file_id}: {e}")
        return None
