import asyncio
from langchain_community.document_loaders import PyPDFLoader
from typing import List
from dotenv import load_dotenv


from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings

import getpass
import os
load_dotenv()


if os.getenv("OPENAI_API_KEY") is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

async def load_pages() -> List:
    file_path = "/home/vedant/Desktop/Axon/docs/vedantlahane31.pdf"
    loader = PyPDFLoader(file_path)

    pages = []
    async for page in loader.alazy_load():
        pages.append(page)
    return pages


pages = asyncio.run(load_pages())

# print(f"Metadata of first page:\n{pages[0].metadata}\n")
# print(f"Content of first page:\n{pages[0].page_content}")


vector_store = InMemoryVectorStore.from_documents(pages, embedding=OpenAIEmbeddings())
query = "What is this document about?"
docs = vector_store.similarity_search(query, k=3)
for doc in docs:
    print(f"Content:\n{doc.page_content}\n")