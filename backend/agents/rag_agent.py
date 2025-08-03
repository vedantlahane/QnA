"""
RAG Agent for Document Retrieval and Generation
This agent handles document processing, vector storage, and retrieval-augmented generation.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
    UnstructuredFileLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
import logging
from pathlib import Path
import tempfile
import shutil
import os

logger = logging.getLogger(__name__)

class RAGAgent:
    """
    RAG (Retrieval-Augmented Generation) Agent that processes documents,
    creates vector embeddings, and answers questions using retrieved context.
    """
    
    def __init__(
        self,
        llm: ChatOpenAI = None,
        embeddings: OpenAIEmbeddings = None,
        vector_store_path: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.embeddings = embeddings or OpenAIEmbeddings(
            model="text-embedding-3-small"
        )
        self.vector_store_path = vector_store_path or "./vector_store"
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize components
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.vector_store = None
        self.retriever = None
        self.rag_chain = None
        self.documents = []
        
        # Try to load existing vector store
        self._load_vector_store()
        
        # Create RAG chain
        self._create_rag_chain()
    
    def _load_vector_store(self) -> None:
        """Load existing vector store if available"""
        try:
            if os.path.exists(self.vector_store_path):
                self.vector_store = Chroma(
                    persist_directory=self.vector_store_path,
                    embedding_function=self.embeddings
                )
                self.retriever = self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}
                )
                logger.info(f"Loaded existing vector store from {self.vector_store_path}")
            else:
                logger.info("No existing vector store found, will create new one")
        except Exception as e:
            logger.warning(f"Could not load existing vector store: {e}")
    
    def _create_rag_chain(self) -> None:
        """Create the RAG processing chain"""
        # Define the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that answers questions based on the provided context. 
            Use the following pieces of context to answer the user's question. 
            If you cannot find the answer in the context, say that you don't have enough information to answer the question.
            
            Context: {context}
            
            Guidelines:
            - Be accurate and only use information from the provided context
            - If the context doesn't contain enough information, be honest about it
            - Provide specific details when available
            - If asked about sources, mention the document or section if available in the context
            """),
            ("human", "{question}")
        ])
        
        # Create the RAG chain
        if self.retriever:
            self.rag_chain = (
                {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
    
    def _format_docs(self, docs: List[Document]) -> str:
        """Format retrieved documents for the prompt"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content
            metadata = doc.metadata
            
            # Add source information if available
            source = metadata.get("source", "Unknown source")
            formatted.append(f"Document {i} (Source: {source}):\n{content}")
        
        return "\n\n".join(formatted)
    
    def load_documents_from_directory(
        self, 
        directory_path: str,
        file_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Load documents from a directory
        
        Args:
            directory_path: Path to directory containing documents
            file_types: List of file extensions to include (e.g., ['.pdf', '.txt'])
            
        Returns:
            Dictionary with loading results
        """
        try:
            if not os.path.exists(directory_path):
                return {"error": f"Directory not found: {directory_path}"}
            
            # Default file types
            if file_types is None:
                file_types = ['.pdf', '.txt', '.md', '.docx']
            
            # Create glob pattern
            glob_pattern = f"**/*{{{','.join(file_types)}}}"
            
            # Load documents
            loader = DirectoryLoader(
                directory_path,
                glob=glob_pattern,
                loader_cls=UnstructuredFileLoader,
                show_progress=True
            )
            
            documents = loader.load()
            
            if not documents:
                return {"error": "No documents found in the specified directory"}
            
            # Process documents
            result = self.add_documents(documents)
            result["directory"] = directory_path
            result["file_types"] = file_types
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading documents from directory: {e}")
            return {"error": str(e)}
    
    def load_document_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load a single document from file
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with loading results
        """
        try:
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
            
            # Determine file type and use appropriate loader
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_ext in ['.txt', '.md']:
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                loader = UnstructuredFileLoader(file_path)
            
            documents = loader.load()
            
            if not documents:
                return {"error": "Failed to load document content"}
            
            # Process documents
            result = self.add_documents(documents)
            result["file_path"] = file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading document from file: {e}")
            return {"error": str(e)}
    
    def load_document_from_text(
        self, 
        text_content: str, 
        source_name: str = "manual_input"
    ) -> Dict[str, Any]:
        """
        Load document from text string
        
        Args:
            text_content: The text content to process
            source_name: Name to identify this document
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Create document object
            document = Document(
                page_content=text_content,
                metadata={"source": source_name}
            )
            
            # Process document
            result = self.add_documents([document])
            result["source_name"] = source_name
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading document from text: {e}")
            return {"error": str(e)}
    
    def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Add documents to the vector store
        
        Args:
            documents: List of Document objects to add
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            if not chunks:
                return {"error": "No chunks created from documents"}
            
            # Create or update vector store
            if self.vector_store is None:
                self.vector_store = Chroma.from_documents(
                    documents=chunks,
                    embedding=self.embeddings,
                    persist_directory=self.vector_store_path
                )
            else:
                self.vector_store.add_documents(chunks)
            
            # Persist the vector store
            self.vector_store.persist()
            
            # Update retriever
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Recreate RAG chain
            self._create_rag_chain()
            
            # Store documents for reference
            self.documents.extend(documents)
            
            logger.info(f"Added {len(documents)} documents ({len(chunks)} chunks) to vector store")
            
            return {
                "success": True,
                "documents_added": len(documents),
                "chunks_created": len(chunks),
                "total_documents": len(self.documents)
            }
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return {"error": str(e)}
    
    def search_documents(
        self, 
        query: str, 
        k: int = 5,
        score_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            k: Number of documents to return
            score_threshold: Minimum similarity score
            
        Returns:
            Dictionary with search results
        """
        if not self.vector_store:
            return {"error": "No vector store available. Please add documents first."}
        
        try:
            # Perform similarity search with scores
            results = self.vector_store.similarity_search_with_score(
                query, k=k
            )
            
            # Filter by score threshold
            filtered_results = [
                (doc, score) for doc, score in results 
                if score >= score_threshold
            ]
            
            # Format results
            search_results = []
            for doc, score in filtered_results:
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                })
            
            return {
                "success": True,
                "query": query,
                "results": search_results,
                "total_found": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"error": str(e)}
    
    async def answer_question(
        self, 
        question: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG
        
        Args:
            question: The question to answer
            context: Additional context for the question
            
        Returns:
            Dictionary with answer and supporting information
        """
        if not self.rag_chain:
            return {"error": "RAG system not initialized. Please add documents first."}
        
        try:
            # Enhance question with context if provided
            enhanced_question = question
            if context:
                if context.get("document_filter"):
                    enhanced_question += f"\n\nFocus on documents related to: {context['document_filter']}"
                if context.get("specific_sections"):
                    enhanced_question += f"\n\nLook specifically in sections about: {', '.join(context['specific_sections'])}"
            
            # Get answer from RAG chain
            answer = await self.rag_chain.ainvoke(enhanced_question)
            
            # Get supporting documents
            supporting_docs = self.search_documents(question, k=3)
            
            return {
                "success": True,
                "question": question,
                "answer": answer,
                "supporting_documents": supporting_docs.get("results", []),
                "source_count": len(self.documents)
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "error": str(e),
                "question": question
            }
    
    def get_document_summary(self) -> Dict[str, Any]:
        """
        Get summary of loaded documents
        
        Returns:
            Dictionary with document statistics
        """
        try:
            if not self.documents:
                return {"message": "No documents loaded"}
            
            # Analyze documents
            sources = {}
            total_chars = 0
            
            for doc in self.documents:
                source = doc.metadata.get("source", "unknown")
                if source not in sources:
                    sources[source] = {"count": 0, "characters": 0}
                sources[source]["count"] += 1
                sources[source]["characters"] += len(doc.page_content)
                total_chars += len(doc.page_content)
            
            # Vector store info
            vector_store_info = {}
            if self.vector_store:
                try:
                    # Get collection info
                    collection = self.vector_store._collection
                    vector_store_info = {
                        "total_chunks": collection.count(),
                        "embedding_dimension": len(self.embeddings.embed_query("test")) if self.embeddings else "unknown"
                    }
                except:
                    vector_store_info = {"status": "vector store active but details unavailable"}
            
            return {
                "total_documents": len(self.documents),
                "total_characters": total_chars,
                "average_document_size": total_chars // len(self.documents) if self.documents else 0,
                "sources": sources,
                "vector_store": vector_store_info,
                "vector_store_path": self.vector_store_path
            }
            
        except Exception as e:
            logger.error(f"Error getting document summary: {e}")
            return {"error": str(e)}
    
    def clear_vector_store(self) -> Dict[str, Any]:
        """
        Clear the vector store and reset the agent
        
        Returns:
            Dictionary with operation status
        """
        try:
            # Remove vector store directory
            if os.path.exists(self.vector_store_path):
                shutil.rmtree(self.vector_store_path)
            
            # Reset internal state
            self.vector_store = None
            self.retriever = None
            self.rag_chain = None
            self.documents = []
            
            logger.info("Vector store cleared successfully")
            
            return {"success": True, "message": "Vector store cleared"}
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            return {"error": str(e)}
    
    def get_query_suggestions(self) -> List[str]:
        """
        Get query suggestions based on loaded documents
        
        Returns:
            List of suggested queries
        """
        if not self.documents:
            return ["No documents loaded. Please add documents first."]
        
        suggestions = [
            "What is the main topic of the documents?",
            "Can you summarize the key points?",
            "What are the most important findings?",
            "Are there any specific recommendations mentioned?",
            "What methodologies or approaches are discussed?",
            "What are the main conclusions?",
            "Are there any statistics or data mentioned?",
            "What problems or challenges are identified?",
            "What solutions are proposed?",
            "Are there any future directions mentioned?"
        ]
        
        # Add source-specific suggestions
        sources = set(doc.metadata.get("source", "unknown") for doc in self.documents)
        for source in list(sources)[:3]:  # Limit to first 3 sources
            source_name = Path(source).stem if source != "unknown" else source
            suggestions.append(f"What does {source_name} say about this topic?")
            suggestions.append(f"Summarize the content from {source_name}")
        
        return suggestions[:15]  # Return top 15 suggestions

# Factory function for easy instantiation
def create_rag_agent(
    llm: ChatOpenAI = None,
    embeddings: OpenAIEmbeddings = None,
    vector_store_path: str = None
) -> RAGAgent:
    """Create a configured RAG agent instance"""
    return RAGAgent(
        llm=llm,
        embeddings=embeddings,
        vector_store_path=vector_store_path
    )

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test_rag_agent():
        # Initialize RAG agent
        agent = RAGAgent(vector_store_path="./test_vector_store")
        
        # Sample document content
        sample_docs = [
            Document(
                page_content="""
                Artificial Intelligence (AI) is a branch of computer science that deals with creating 
                intelligent machines that can perform tasks that typically require human intelligence. 
                These tasks include learning, reasoning, problem-solving, perception, and language understanding.
                """,
                metadata={"source": "ai_introduction.txt"}
            ),
            Document(
                page_content="""
                Machine Learning is a subset of AI that focuses on algorithms that can learn and improve 
                from experience without being explicitly programmed. It includes supervised learning, 
                unsupervised learning, and reinforcement learning approaches.
                """,
                metadata={"source": "ml_basics.txt"}
            ),
            Document(
                page_content="""
                Natural Language Processing (NLP) is a field of AI that focuses on the interaction between 
                computers and human language. It involves developing algorithms that can understand, 
                interpret, and generate human language in a meaningful way.
                """,
                metadata={"source": "nlp_overview.txt"}
            )
        ]
        
        # Add documents
        result = agent.add_documents(sample_docs)
        print("Add documents result:", result)
        
        # Get document summary
        summary = agent.get_document_summary()
        print("\nDocument summary:", summary)
        
        # Test questions
        test_questions = [
            "What is Artificial Intelligence?",
            "How does Machine Learning relate to AI?",
            "What are the main approaches in Machine Learning?",
            "What is NLP and what does it focus on?",
            "Explain the relationship between AI, ML, and NLP"
        ]
        
        for question in test_questions:
            print(f"\nQuestion: {question}")
            result = await agent.answer_question(question)
            if result.get("success"):
                print(f"Answer: {result['answer']}")
                print(f"Supporting docs: {len(result.get('supporting_documents', []))}")
            else:
                print(f"Error: {result.get('error')}")
    
    # Run test
    # asyncio.run(test_rag_agent())
