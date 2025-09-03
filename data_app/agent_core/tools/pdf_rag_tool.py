import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

# NOTE: This is a conceptual import. You'll need to ensure your
# LoadToolsConfig class is accessible from this file.
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
# This assumes LoadToolsConfig exists and loads settings from your
# tools_config.yml file.
TOOLS_CFG = LoadToolsConfig()

# --- Part 1: File Processing Logic ---
def process_and_vectorize(file_path: str, file_id: int):
    """
    Loads a PDF, splits it into chunks, and saves the embeddings to a FAISS vector database.
    
    Args:
        file_path (str): The full path to the uploaded PDF file.
        file_id (int): The unique ID of the uploaded file, used to name the vector DB.
    """
    try:
        # Load the PDF document
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # Split the document into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TOOLS_CFG.pdf_rag_chunk_size,
            chunk_overlap=TOOLS_CFG.pdf_rag_chunk_overlap
        )
        docs = text_splitter.split_documents(documents)

        # Generate embeddings using OpenAI
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model
        )

        # Create the FAISS vector store
        vector_store = FAISS.from_documents(docs, embeddings)

        # Save the vector store locally with a unique name
        # The 'allow_dangerous_deserialization' is necessary for loading
        # a vectorstore from disk in later versions of LangChain.
        vector_store.save_local(f"data/faiss_index_{file_id}")
        
        print(f"PDF file with ID {file_id} processed and vectorized.")
        
    except Exception as e:
        print(f"Error processing PDF file: {e}")
        # You can add error handling here, like logging or returning a status

# --- Part 2: Agent Tool ---
@tool
def answer_question_on_pdf(query: str, file_id: int) -> str:
    """
    Answers a question by searching a specific PDF's vector database.
    This tool is used for queries that require information from a previously
    uploaded PDF document.
    
    Args:
        query (str): The user's question.
        file_id (int): The ID of the specific PDF file to search within.
        
    Returns:
        str: The generated answer from the LLM.
    """
    try:
        # Load the saved FAISS vector store for the specific file
        embeddings = OpenAIEmbeddings(
            model=TOOLS_CFG.pdf_rag_embedding_model
        )
        vector_store = FAISS.load_local(
            f"data/faiss_index_{file_id}",
            embeddings,
            allow_dangerous_deserialization=True
        )

        # Set up a retriever for the RAG chain
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOOLS_CFG.pdf_rag_k}
        )

        # Initialize the LLM and the RAG chain
        llm = ChatOpenAI(
            temperature=TOOLS_CFG.pdf_rag_llm_temperature,
            model=TOOLS_CFG.pdf_rag_llm
        )
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

        # Run the chain to get the answer
        response = qa_chain.run(query)
        return response

    except Exception as e:
        return f"Sorry, I could not find information on this topic in the specified PDF. Error: {e}"