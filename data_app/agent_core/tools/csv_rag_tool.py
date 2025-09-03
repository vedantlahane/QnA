# data_app/agent_core/tools/csv_rag_tool.py

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
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

def _validate_csv_file(file_path: str) -> bool:
    """Validate that the CSV file exists and is readable."""
    if not os.path.exists(file_path):
        logger.error(f"CSV file does not exist: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        logger.error(f"Path is not a file: {file_path}")
        return False
    
    if not file_path.lower().endswith('.csv'):
        logger.error(f"File is not a CSV: {file_path}")
        return False
    
    return True

def _get_faiss_index_path(file_id: int) -> str:
    """Get the standardized FAISS index path for a CSV file."""
    data_dir = _ensure_data_directory()
    return str(data_dir / f"faiss_index_csv_{file_id}")

def process_and_vectorize(file_path: str, file_id: int) -> bool:
    """
    Loads a CSV, splits it into chunks, and saves the embeddings to a FAISS vector database.
    
    Args:
        file_path (str): The full path to the uploaded CSV file.
        file_id (int): The unique ID of the uploaded file, used to name the vector DB.
    
    Returns:
        bool: True if processing was successful, False otherwise.
    """
    try:
        # Validate inputs
        if not _validate_csv_file(file_path):
            return False
        
        if file_id <= 0:
            logger.error(f"Invalid file_id: {file_id}. Must be positive integer.")
            return False
        
        logger.info(f"Starting CSV processing for file: {file_path} with ID: {file_id}")
        
        # Load the CSV document with enhanced configuration
        loader = CSVLoader(
            file_path=file_path,
            encoding='utf-8',
            autodetect_encoding=True,  # Automatically detect encoding
            csv_args={
                'delimiter': ',',
                'quotechar': '"',
                'skipinitialspace': True
            }
        )
        documents = loader.load()
        
        if not documents:
            logger.error(f"No documents loaded from CSV file: {file_path}")
            return False
        
        logger.info(f"Loaded {len(documents)} documents from CSV")
        
        # Split the document into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.csv_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.csv_rag_chunk_overlap,
            separators=["\n\n", "\n", ",", " ", ""],  # CSV-specific separators
            length_function=len,
        )
        docs = text_splitter.split_documents(documents)
        
        if not docs:
            logger.error("No chunks created from documents")
            return False
        
        logger.info(f"Split into {len(docs)} chunks")
        
        # Generate embeddings using OpenAI
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.csv_rag_embedding_model,
            show_progress_bar=True
        )
        
        # Create the FAISS vector store
        vector_store = FAISS.from_documents(docs, embeddings)
        
        # Save the vector store locally with a unique name
        index_path = _get_faiss_index_path(file_id)
        vector_store.save_local(index_path)
        
        logger.info(f"CSV file with ID {file_id} processed and vectorized successfully")
        logger.info(f"FAISS index saved to: {index_path}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"File not found during CSV processing: {e}")
        return False
    except PermissionError as e:
        logger.error(f"Permission error during CSV processing: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing CSV file: {e}")
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
            source_info = f"Row {doc.metadata.get('row', 'unknown')}"
            formatted_docs.append(f"Source {i} ({source_info}):\n{content}")
        else:
            formatted_docs.append(f"Source {i}:\n{content}")
    
    return "\n\n".join(formatted_docs)

@tool
def answer_question_on_csv(query: str, file_id: int) -> str:
    """
    Answers a question by searching a specific CSV's vector database.
    This tool is used for queries that require information from a previously
    uploaded CSV document.
    
    Args:
        query (str): The user's question about the CSV data.
        file_id (int): The ID of the specific CSV file to search within.
        
    Returns:
        str: The generated answer from the LLM based on CSV data.
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return "Please provide a valid question about the CSV data."
        
        if file_id <= 0:
            return "Invalid file ID provided. Please specify a valid CSV file ID."
        
        # Check if FAISS index exists
        if not _check_faiss_index_exists(file_id):
            return f"No processed CSV data found for file ID {file_id}. Please ensure the file has been uploaded and processed."
        
        logger.info(f"Answering question for CSV file_id {file_id}: {query}")
        
        # Load the saved FAISS vector store for the specific file
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.csv_rag_embedding_model
        )
        
        index_path = _get_faiss_index_path(file_id)
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Set up a retriever for the RAG chain
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.csv_rag_k}
        )
        
        # Initialize the LLM
        llm = ChatOpenAI(
            temperature=TOOLS_CFG.csv_rag_llm_temperature,
            model=TOOLS_CFG.csv_rag_llm
        )
        
        # Create a custom prompt template for CSV data
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are an expert data analyst. Use the following CSV data to answer the question.
            
CSV Data Context:
{context}

Question: {question}

Instructions:
- Provide a clear, accurate answer based solely on the CSV data provided
- If the data contains numbers, include specific values and calculations where relevant
- If you cannot find relevant information in the CSV data, clearly state this
- Be concise but comprehensive in your response
- Format your response in a readable manner

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
        
        logger.info(f"Successfully answered question for CSV file_id {file_id}")
        return response
        
    except FileNotFoundError:
        error_msg = f"FAISS index not found for CSV file ID {file_id}. Please ensure the file has been processed."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Sorry, I could not find information on this topic in the specified CSV. Error: {str(e)}"
        logger.error(f"Error in answer_question_on_csv: {e}")
        return error_msg

# Utility functions for debugging and maintenance
def list_processed_csv_files() -> List[int]:
    """List all file IDs that have been processed and have FAISS indices."""
    processed_files = []
    data_dir = Path("data")
    
    if not data_dir.exists():
        return processed_files
    
    for faiss_file in data_dir.glob("faiss_index_csv_*.faiss"):
        try:
            file_id = int(faiss_file.stem.split("_")[-1])
            if _check_faiss_index_exists(file_id):
                processed_files.append(file_id)
        except (ValueError, IndexError):
            continue
    
    return sorted(processed_files)

def delete_csv_index(file_id: int) -> bool:
    """Delete the FAISS index for a specific CSV file."""
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
            logger.info(f"Deleted FAISS index for CSV file_id {file_id}")
        
        return removed
    except Exception as e:
        logger.error(f"Error deleting CSV index for file_id {file_id}: {e}")
        return False

def get_csv_stats(file_id: int) -> Optional[Dict[str, Any]]:
    """Get statistics about a processed CSV file."""
    try:
        if not _check_faiss_index_exists(file_id):
            return None
        
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
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
        logger.error(f"Error getting CSV stats for file_id {file_id}: {e}")
        return None
