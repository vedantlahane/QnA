import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI




def process_and_vectorize(file_path:str , file_id:int):
    """
    Loads a PDF file, splits its content into manageble chunks, generates embeddings from these chunks, and stores them in a FAISS vector store.
    
    Args:
        file_path (str) : The path to the PDF file to be processed.
        file_id (int) : The unique identifier for the file, used to name the FAISS index file.
    """

    try:
        loader = PyPDFLoader(file_path)
        documents  = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 500,
            chunk_overlap = 50
        )

        docs = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings(
            model = "text-embedding-3-large"
        )

        vector_store = FAISS.from_documents( docs, embeddings)

        vector_store.save_local(f"data/faiss_index_{file_id}")

        print(f"PDF file with ID {file_id} processed and vectorized")

    except Exception as e:
        print(f"Error processing PDF file: {e}")

@tool
def answer_questions_on_pdf(query: str, file_id: int) ->str:
    """
    Answers a question by searching a specific PDF's vector database.
    This tool is used for queries that require information from a previously
    uploaded PDF document.
    
    Args:
        query (str): The user's question.
        file_id (int): The ID of the specific PDF file to search within.
        
    Returns:
        
    """
    

    try:
        embeddings = OpenAIEmbeddings(
            model = "text-embeddings=3-large"
        )

        vector_store = FAISS.load_local(
            f"data/faiss_index_(file_id)",
            embeddings,
            allow_dangerous_deserialization=True #this 
        )

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"3"}
        )

        llm = ChatOpenAI(
            temperature=1,
            model="OpenAI-4o-mini"
        )

        qa_chain = RetrievalQA.from_chain_type(llm = llm, retriever = retriever)

        respond= qa_chain.run(query)
        return respond
    

    except Exception as e:
        return f"Sorry, I could not process your request due to an error: {e}"
