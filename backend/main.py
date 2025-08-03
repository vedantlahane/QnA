"""
Main FastAPI application for the QnA Agent Graph System
Provides REST API endpoints for React frontend integration
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

# Import our agent graph
from agents.agent_graph import create_agent_graph, AgentGraph

# Import routers
from router.chat import router as chat_router
from router.upload import router as upload_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent graph instance
agent_graph: Optional[AgentGraph] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup the agent graph"""
    global agent_graph
    
    # Startup
    logger.info("Initializing Agent Graph...")
    try:
        agent_graph = create_agent_graph(
            vector_store_path="./vector_store",
            enable_memory=True
        )
        logger.info("Agent Graph initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Agent Graph: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Agent Graph...")
    agent_graph = None

# Create FastAPI app with lifespan management
app = FastAPI(
    title="QnA Agent Graph API",
    description="Intelligent Q&A system with multi-agent capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(upload_router)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for chat queries"""
    query: str = Field(..., description="User's question or request")
    thread_id: Optional[str] = Field(default="default", description="Conversation thread ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    stream: Optional[bool] = Field(default=False, description="Enable streaming response")

class DatabaseConnectionRequest(BaseModel):
    """Request model for database connection"""
    database_url: str = Field(..., description="Database connection string")
    connection_name: Optional[str] = Field(default=None, description="Name for this connection")

class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: str

# API Routes

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for health check"""
    return {
        "message": "QnA Agent Graph API",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        health = agent_graph.health_check()
        
        if health["success"]:
            return JSONResponse(
                status_code=200,
                content=health
            )
        else:
            return JSONResponse(
                status_code=503,
                content=health
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Health check failed"
            }
        )

@app.post("/api/query", tags=["Chat"])
async def process_query(request: QueryRequest):
    """Process a user query through the agent graph"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        logger.info(f"Processing query: {request.query[:100]}...")
        
        response = await agent_graph.process_query(
            query=request.query,
            context=request.context,
            thread_id=request.thread_id,
            stream=request.stream
        )
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/api/status", tags=["System"])
async def get_system_status():
    """Get comprehensive system status"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        status = agent_graph.get_comprehensive_status()
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting system status: {str(e)}"
        )

@app.get("/api/suggestions", tags=["Chat"])
async def get_query_suggestions():
    """Get query suggestions based on available data sources"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        suggestions = agent_graph.get_query_suggestions()
        return JSONResponse(content=suggestions)
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting suggestions: {str(e)}"
        )

# Database Management Endpoints

@app.post("/api/database/connect", tags=["Database"])
async def connect_database(request: DatabaseConnectionRequest):
    """Connect to a SQL database"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        logger.info(f"Connecting to database: {request.database_url}")
        
        result = agent_graph.connect_sql_database(request.database_url)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Database connection failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting database: {str(e)}"
        )

@app.delete("/api/database/disconnect", tags=["Database"])
async def disconnect_database():
    """Disconnect from the SQL database"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        result = agent_graph.clear_data_source("sql")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error disconnecting database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error disconnecting database: {str(e)}"
        )

# File Upload Endpoints

@app.post("/api/upload/csv", tags=["File Upload"])
async def upload_csv_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None)
):
    """Upload and process CSV file"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Validate file type
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported"
            )
        
        # Read file content
        content = await file.read()
        filename = name or file.filename
        
        logger.info(f"Processing CSV upload: {filename}")
        
        result = agent_graph.load_csv_from_upload(content, filename)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "CSV upload failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading CSV: {str(e)}"
        )

@app.post("/api/upload/documents", tags=["File Upload"])
async def upload_documents(
    files: List[UploadFile] = File(...)
):
    """Upload and process document files"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Supported file types
        supported_types = ['.pdf', '.txt', '.md', '.docx']
        
        file_data = []
        for file in files:
            # Validate file type
            if not any(file.filename.lower().endswith(ext) for ext in supported_types):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}. Supported: {supported_types}"
                )
            
            content = await file.read()
            file_data.append({
                'content': content,
                'filename': file.filename,
                'content_type': file.content_type
            })
        
        logger.info(f"Processing document uploads: {[f['filename'] for f in file_data]}")
        
        result = agent_graph.load_documents_from_upload(file_data)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Document upload failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading documents: {str(e)}"
        )

@app.delete("/api/data/{source_type}", tags=["Data Management"])
async def clear_data_source(source_type: str):
    """Clear a specific data source (sql, csv, documents)"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        if source_type not in ["sql", "csv", "documents"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type. Must be one of: sql, csv, documents"
            )
        
        result = agent_graph.clear_data_source(source_type)
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing data source: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing data source: {str(e)}"
        )

# Development and Testing Endpoints

@app.post("/api/dev/create-sample-db", tags=["Development"])
async def create_sample_database():
    """Create a sample SQLite database for testing"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Create sample database using SQL agent
        from agents.sql_agent import SQLAgent
        sql_agent = SQLAgent()
        db_url = sql_agent.create_sample_database("sample_business.db")
        
        # Connect to the sample database
        result = agent_graph.connect_sql_database(db_url)
        
        return JSONResponse(content={
            "success": True,
            "message": "Sample database created and connected",
            "database_url": db_url,
            "data": result.get("data", {})
        })
        
    except Exception as e:
        logger.error(f"Error creating sample database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating sample database: {str(e)}"
        )

@app.get("/api/dev/test-agents", tags=["Development"])
async def test_all_agents():
    """Test all agents with sample queries"""
    try:
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        test_results = {}
        test_queries = [
            ("general", "Hello, what can you help me with?"),
            ("sql", "How many customers do we have?"),
            ("csv", "What's the average value in the data?"),
            ("rag", "What information is available in the documents?")
        ]
        
        for agent_type, query in test_queries:
            try:
                response = await agent_graph.process_query(
                    query=query,
                    thread_id=f"test_{agent_type}"
                )
                test_results[agent_type] = {
                    "success": response["success"],
                    "agent_used": response.get("agent_type"),
                    "message": response["message"][:100] + "..." if len(response["message"]) > 100 else response["message"]
                }
            except Exception as e:
                test_results[agent_type] = {
                    "success": False,
                    "error": str(e)
                }
        
        return JSONResponse(content={
            "success": True,
            "message": "Agent testing completed",
            "data": test_results
        })
        
    except Exception as e:
        logger.error(f"Error testing agents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing agents: {str(e)}"
        )

# Error Handlers

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
