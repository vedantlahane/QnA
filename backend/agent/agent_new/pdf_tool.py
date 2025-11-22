from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import os
from pathlib import Path
from typing import Optional

DEFAULT_PDF_PATH = "media/uploaded_docs/"
VECTOR_DB_PATH = "media/vector_db/"  # Persistent storage


def build_pdf_search_tool(
    pdf_path: str = DEFAULT_PDF_PATH,
    persist_directory: str = VECTOR_DB_PATH,
    force_rebuild: bool = False
) -> Chroma:
    """
    Builds or loads a Chroma vector store from PDF files.
    
    Args:
        pdf_path (str): Path to the directory containing PDF files.
        persist_directory (str): Path to persist the vector database.
        force_rebuild (bool): If True, rebuild the vector store even if it exists.
    
    Returns:
        Chroma: A Chroma vector store containing embedded PDF content.
    """
    embeddings = OpenAIEmbeddings()
    persist_path = Path(persist_directory)
    
    # Load existing vector store if available and not forcing rebuild
    if persist_path.exists() and not force_rebuild:
        try:
            vector_store = Chroma(
                persist_directory=str(persist_path),
                embedding_function=embeddings,
                collection_name="pdf_collection",
            )
            print(f"Loaded existing vector store from {persist_directory}")
            return vector_store
        except Exception as e:
            print(f"Warning: Could not load existing vector store: {e}")
            print("Rebuilding vector store...")
    
    # Build new vector store
    pdf_dir = Path(pdf_path)
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_path}")
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {pdf_path}")
    
    # Load all PDFs
    all_documents = []
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_file))
            documents = loader.load()
            all_documents.extend(documents)
            print(f"Loaded: {pdf_file.name}")
        except Exception as e:
            print(f"Warning: Failed to load {pdf_file.name}: {e}")
    
    if not all_documents:
        raise FileNotFoundError("No documents could be loaded from PDFs")
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    splits = text_splitter.split_documents(all_documents)
    
    # Create and persist vector store
    persist_path.mkdir(parents=True, exist_ok=True)
    vector_store = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name="pdf_collection",
        persist_directory=str(persist_path),
    )
    
    print(f"Built vector store: {len(pdf_files)} PDFs, {len(splits)} chunks")
    return vector_store


@tool
def search_pdf(query: str) -> str:
    """
    Searches uploaded PDF documents for information related to the query.
    Use this when users ask about content in their uploaded PDFs or documents.
    
    Args:
        query (str): The search query to find relevant information.

    Returns:
        str: Relevant text excerpts from the PDF documents.
    """
    try:
        vector_store = build_pdf_search_tool()
    except FileNotFoundError as e:
        return f"No PDF documents available: {str(e)}"
    except Exception as e:
        return f"Error loading PDFs: {str(e)}"
    
    try:
        # Search with relevance scores
        results = vector_store.similarity_search_with_score(query, k=3)
        
        if not results:
            return "No relevant information found in the PDF documents."
        
        # Format results
        formatted_results = []
        for i, (doc, score) in enumerate(results, 1):
            source = Path(doc.metadata.get("source", "Unknown")).name
            page = doc.metadata.get("page", "?")
            content = doc.page_content.strip()[:500]  # Limit excerpt length
            
            formatted_results.append(
                f"**Match {i}** (Source: {source}, Page: {page}, Relevance: {1-score:.2f}):\n{content}"
            )
        
        return "\n\n".join(formatted_results)
    
    except Exception as e:
        return f"Search error: {str(e)}"
