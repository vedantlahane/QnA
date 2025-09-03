import os
import pandas as pd
import fitz
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# Directory for FAISS indexes
"""
it is used to store the vector indexes created from uploaded files
vector indexes means the numerical representations of the data in the files
"""
INDEX_DIR = "vector_stores" # directory to store FAISS indexes
os.makedirs(INDEX_DIR, exist_ok=True) # create directory if it doesn't exist

# Embeddings + LLM
"""
embeddings are numerical representations of text data
here we use OpenAI's embeddings model to confert text to vectors
LLM is a large language model, here we use OpenAI's gpt-4o-mini model for generating responses
"""
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # temperature=0 for deterministic responses

def process_file(file_path, file_id):
    """Parse and vectorize a file, save FAISS index"""
    if file_path.endswith(".pdf"):
        text = parse_pdf(file_path)
    elif file_path.endswith(".csv"):
        text = parse_csv(file_path)
    else:
        text = ""

    # Split text into chunks
    """
    this splits the text into smaller chunks of 500 characters with an overlap of 50 characters
    this helps in better context retention when querying the vector store
    500 characters is a good size for embeddings, balancing context and performance
    50 characters overlap ensures that important context isn't lost between chunks
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.create_documents([text])

    # Build FAISS index
    """
    this creates a FAISS vector store from the document chunks and their embeddings
    """
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(os.path.join(INDEX_DIR, f"store_{file_id}"))

def parse_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def parse_csv(path):
    df = pd.read_csv(path)
    return df.to_string()

def answer_question(question, file_id=None):
    """Query FAISS vectorstore with an LLM"""
    if not file_id:
        return "No file uploaded yet."

    store_path = os.path.join(INDEX_DIR, f"store_{file_id}")
    if not os.path.exists(store_path):
        return "No vector store found. Please upload a file first."

    vectorstore = FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    response = qa_chain.run(question)

    return response
