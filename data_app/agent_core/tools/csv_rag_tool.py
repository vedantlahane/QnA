"""
CSV Retrieval-Augmented Generation (RAG) Tool Module.
Processes CSVs into FAISS indexes and answers questions with source attributions.
"""
import logging
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

logger = logging.getLogger('data_app.agent_core.tools.csv_rag_tool')
TOOLS_CFG = LoadToolsConfig()


def process_and_vectorize(file_path: str, file_id: int) -> None:
    """Load CSV, chunk, embed, and persist FAISS index at data/faiss_index_csv_<file_id>."""
    try:
        loader = CSVLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.csv_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.csv_rag_chunk_overlap,
        )
        docs = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(f"data/faiss_index_csv_{file_id}")
        logger.info(f"CSV file with ID {file_id} processed and vectorized.")
    except Exception as e:
        logger.info(f"Error processing CSV file: {e}")


@tool
def answer_question_on_csv(query: str, file_id: int) -> str:
    """Answer questions about CSV content using RAG with basic source citations."""
    try:
        embeddings = OpenAIEmbeddings(model=TOOLS_CFG.csv_rag_embedding_model)
        vector_store = FAISS.load_local(
            f"data/faiss_index_csv_{file_id}",
            embeddings,
            allow_dangerous_deserialization=True,
        )
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.csv_rag_k},
        )
        llm = ChatOpenAI(temperature=TOOLS_CFG.csv_rag_llm_temperature, model=TOOLS_CFG.csv_rag_llm)
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
            row = meta.get('row')
            citations.append(f"[row {row}]" if row is not None else "[source]")
        citation_str = ' '.join(citations) if citations else ''
        return f"{answer}\n\nSources: {citation_str}"
    except Exception as e:
        return f"Sorry, I could not find information on this topic in the specified CSV. Error: {e}"
