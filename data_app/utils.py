import os
import pandas as pd
import fitz
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# Directory for FAISS indexes
INDEX_DIR = "vector_stores"
os.makedirs(INDEX_DIR, exist_ok=True)

# Embeddings + LLM
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def process_file(file_path, file_id):
    """Parse and vectorize a file, save FAISS index"""
    if file_path.endswith(".pdf"):
        text = parse_pdf(file_path)
    elif file_path.endswith(".csv"):
        text = parse_csv(file_path)
    else:
        text = ""

    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.create_documents([text])

    # Build FAISS index
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
