import os
from pathlib import Path
from typing import List, Optional
from django.conf import settings
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

def _collect_pdf_paths() -> List[Path]:
    paths: List[Path] = []
    if DEFAULT_PDF_PATH.exists():
        paths.append(DEFAULT_PDF_PATH)

    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_root:
        uploads_dir = Path(media_root) / "uploaded_docs"
        if uploads_dir.exists():
            paths.extend(sorted(uploads_dir.glob("*.pdf")))

    return paths


def _build_vector_store(paths: List[Path]) -> InMemoryVectorStore:
    _require_openai_api_key()
    documents: List[Document] = []
    for path in paths:
        try:
            documents.extend(_load_documents(path))
        except FileNotFoundError:
            continue

    if not documents:
        raise FileNotFoundError("No PDF documents available for search.")

    embeddings = OpenAIEmbeddings()
    return InMemoryVectorStore.from_documents(documents, embedding=embeddings)

# This global variable caches the vector store to avoid rebuilding every query
_vector_store: Optional[InMemoryVectorStore] = None


def build_pdf_search_tool(pdf_path: Optional[Path] = None, *, force_rebuild: bool = False) -> InMemoryVectorStore:
    global _vector_store
    if force_rebuild:
        _vector_store = None

    if _vector_store is None:
        if pdf_path:
            paths = [pdf_path]
        else:
            paths = _collect_pdf_paths()

        if not paths:
            raise FileNotFoundError("No PDF documents have been uploaded yet.")

        _vector_store = _build_vector_store(paths)

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
