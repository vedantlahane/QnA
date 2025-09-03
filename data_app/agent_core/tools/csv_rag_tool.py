# data_app/agent_core/tools/csv_rag_tool.py

import os
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.tools import tool
from .config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

def process_and_vectorize(file_path: str, file_id: int):
    """
    Loads a CSV, splits it into chunks, and saves the embeddings to a FAISS vector database.
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
    Answers a question by searching a specific CSV's vector database.
    This tool is used for queries that require information from a previously
    uploaded CSV document.
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