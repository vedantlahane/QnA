"""
PDF Retrieval-Augmented Generation (RAG) Tool Module.
Processes PDFs into FAISS indexes and answers questions with source attributions.
"""
import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain.chains import RetrievalQA
from data_app.agent_core.config import LoadToolsConfig

logger = logging.getLogger('data_app.agent_core.tools.pdf_rag_tool')
TOOLS_CFG = LoadToolsConfig()


def process_and_vectorize(file_path: str, file_id: int) -> None:
    """Load PDF, split text, embed, and persist FAISS index at data/faiss_index_<file_id>."""
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        if not documents:
            raise ValueError(f"No content extracted from PDF: {file_path}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.pdf_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.pdf_rag_chunk_overlap,
        )
        docs = text_splitter.split_documents(documents)
        logger.info(f"PDF split into {len(docs)} chunks")

        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        vector_store = FAISS.from_documents(docs, embeddings)
        index_path = f"data/faiss_index_{file_id}"
        vector_store.save_local(index_path)
        logger.info(f"PDF file with ID {file_id} processed and vectorized at {index_path}")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"PDF file not found: {file_path}") from e
    except Exception as e:
        raise Exception(f"Unexpected error processing PDF file: {str(e)}") from e


@tool
def answer_question_on_pdf(query: str, file_id: int) -> str:
    """Answer questions based on a specific PDF using RAG with basic source citations."""
    try:
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.pdf_rag_embedding_model)
        index_path = f"data/faiss_index_{file_id}"
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.pdf_rag_k},
        )
        llm = ChatOpenAI(temperature=TOOLS_CFG.pdf_rag_llm_temperature, model=TOOLS_CFG.pdf_rag_llm)
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
        )
        result = qa_chain({"query": query})
        answer = result.get('result') if isinstance(result, dict) else str(result)
        sources = result.get('source_documents', []) if isinstance(result, dict) else []
        citations = []
        for d in sources:
            meta = getattr(d, 'metadata', {}) or {}
            page = meta.get('page')
            citations.append(f"[page {page+1}]" if page is not None else "[source]")
        citation_str = ' '.join(citations) if citations else ''
        return f"{answer}\n\nSources: {citation_str}"
    except FileNotFoundError:
        return (
            "Sorry, the PDF with the specified ID has not been processed yet. "
            "Please ensure the file has been uploaded and processed before asking questions."
        )
    except Exception as e:
        return (
            "Sorry, I could not find information on this topic in the specified PDF. "
            f"Error details: {str(e)}. "
            "The document may not contain relevant information about your question."
        )
