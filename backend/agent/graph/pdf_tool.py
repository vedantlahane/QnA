import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings

load_dotenv()

DEFAULT_PDF_PATH = Path(__file__).resolve().parents[3] / "docs/vedantlahane31.pdf"

def _require_openai_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

def _load_documents(pdf_path: Path) -> List[Document]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF document not found at {pdf_path}")
    loader = PyPDFLoader(str(pdf_path))
    return loader.load()

def _build_vector_store(pdf_path: Path) -> InMemoryVectorStore:
    _require_openai_api_key()
    documents = _load_documents(pdf_path)
    embeddings = OpenAIEmbeddings()
    return InMemoryVectorStore.from_documents(documents, embedding=embeddings)

# This global variable caches the vector store to avoid rebuilding every query
_vector_store: Optional[InMemoryVectorStore] = None

def build_pdf_search_tool(pdf_path: Optional[Path] = None) -> InMemoryVectorStore:
    global _vector_store
    if _vector_store is None:
        path = pdf_path if pdf_path else DEFAULT_PDF_PATH
        _vector_store = _build_vector_store(path)
    return _vector_store

@tool
def search_pdf(query: str) -> str:
    """
    Search the uploaded PDF documents for relevant information matching the query.
    
    Args:
        query (str): The search query string.
    
    Returns:
        str: Concatenated relevant content from the PDF or a message if nothing is found.
    """
    try:
        vector_store = build_pdf_search_tool()
    except (EnvironmentError, FileNotFoundError) as exc:
        return f"PDF search is unavailable: {exc}"
    docs = vector_store.similarity_search(query, k=3)
    if not docs:
        return "No relevant content found in the provided PDF."
    return "\n\n".join(doc.page_content for doc in docs)
