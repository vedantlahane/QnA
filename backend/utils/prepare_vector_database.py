import os
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv


class PrepareVectorDB:

    def __init__(self,
                doc_dir : str,
                chunk_size : int,
                chunk_overlap : int,
                embedding_model : str,
                vectordb_dir : str,
                collection_name : str
                )-> None:
    
        self.doc_dir = doc_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.vectordb_dir = vectordb_dir
        self.collection_name = collection_name


    def path_maker(self, file_name: str, doc_dir: str):


        return os.path.join(doc_dir, file_name)


    def run(self): 
        
        if not os.path.exists(self.vectordb_dir):
            os.makedirs(self.vectordb_dir)
            print(f"Created directory: {self.vectordb_dir}")
        
    