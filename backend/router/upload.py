"""
Upload Router - Advanced file upload endpoints for React frontend
Provides specialized upload functionality with progress tracking and validation
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
import os
import tempfile
import shutil
from datetime import datetime
import mimetypes
import hashlib

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/upload", tags=["File Upload"])

# Upload tracking
upload_status: Dict[str, Dict[str, Any]] = {}

class UploadResponse(BaseModel):
    """Upload response model"""
    success: bool
    message: str
    file_id: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None
    upload_id: Optional[str] = None

class BatchUploadRequest(BaseModel):
    """Batch upload request model"""
    files: List[str] = Field(..., description="List of file names")
    upload_type: str = Field(..., description="Type of upload: csv, documents, mixed")

def generate_file_id(filename: str, content: bytes) -> str:
    """Generate unique file ID based on content hash"""
    hash_obj = hashlib.md5(content)
    return f"{hash_obj.hexdigest()[:8]}_{filename}"

def validate_file_size(file: UploadFile, max_size_mb: int = 50) -> bool:
    """Validate file size"""
    if hasattr(file, 'size') and file.size:
        return file.size <= max_size_mb * 1024 * 1024
    return True  # If size unknown, allow upload

def get_file_type_info(filename: str) -> Dict[str, Any]:
    """Get file type information"""
    mime_type, _ = mimetypes.guess_type(filename)
    ext = os.path.splitext(filename)[1].lower()
    
    file_types = {
        '.csv': {'category': 'data', 'description': 'Comma Separated Values'},
        '.xlsx': {'category': 'data', 'description': 'Excel Spreadsheet'},
        '.pdf': {'category': 'document', 'description': 'PDF Document'},
        '.txt': {'category': 'document', 'description': 'Text File'},
        '.md': {'category': 'document', 'description': 'Markdown File'},
        '.docx': {'category': 'document', 'description': 'Word Document'},
        '.json': {'category': 'data', 'description': 'JSON Data'},
        '.xml': {'category': 'data', 'description': 'XML Data'}
    }
    
    return {
        'extension': ext,
        'mime_type': mime_type,
        'category': file_types.get(ext, {}).get('category', 'unknown'),
        'description': file_types.get(ext, {}).get('description', 'Unknown File Type')
    }

@router.post("/csv/single")
async def upload_single_csv(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Upload single CSV file with enhanced validation"""
    try:
        from main import agent_graph
        
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Validate file type
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported for this endpoint"
            )
        
        # Validate file size
        if not validate_file_size(file, max_size_mb=100):
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 100MB"
            )
        
        # Read and process file
        content = await file.read()
        file_id = generate_file_id(file.filename, content)
        filename = name or file.filename
        
        # Get file info
        file_info = {
            "file_id": file_id,
            "original_filename": file.filename,
            "display_name": filename,
            "description": description,
            "size": len(content),
            "upload_timestamp": datetime.now().isoformat(),
            "type_info": get_file_type_info(file.filename)
        }
        
        logger.info(f"Processing CSV upload: {filename} ({len(content)} bytes)")
        
        # Process with agent graph
        result = agent_graph.load_csv_from_upload(content, filename)
        
        if result["success"]:
            # Store upload info
            upload_status[file_id] = {
                "status": "completed",
                "file_info": file_info,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse(content={
                "success": True,
                "message": f"CSV file '{filename}' uploaded and processed successfully",
                "file_id": file_id,
                "file_info": file_info,
                "data": result["data"],
                "system_status": result.get("system_status")
            })
        else:
            upload_status[file_id] = {
                "status": "failed",
                "file_info": file_info,
                "error": result.get("error"),
                "timestamp": datetime.now().isoformat()
            }
            
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "CSV processing failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading CSV: {str(e)}"
        )

@router.post("/documents/single")
async def upload_single_document(
    file: UploadFile = File(...),
    extract_text: Optional[bool] = Form(True),
    chunk_size: Optional[int] = Form(1000)
):
    """Upload single document with text extraction options"""
    try:
        from main import agent_graph
        
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Validate file type
        supported_types = ['.pdf', '.txt', '.md', '.docx']
        if not any(file.filename.lower().endswith(ext) for ext in supported_types):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {supported_types}"
            )
        
        # Validate file size
        if not validate_file_size(file, max_size_mb=50):
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 50MB"
            )
        
        # Read file
        content = await file.read()
        file_id = generate_file_id(file.filename, content)
        
        # Get file info
        file_info = {
            "file_id": file_id,
            "original_filename": file.filename,
            "size": len(content),
            "upload_timestamp": datetime.now().isoformat(),
            "type_info": get_file_type_info(file.filename),
            "processing_options": {
                "extract_text": extract_text,
                "chunk_size": chunk_size
            }
        }
        
        logger.info(f"Processing document upload: {file.filename} ({len(content)} bytes)")
        
        # Process with agent graph
        file_data = [{
            'content': content,
            'filename': file.filename,
            'content_type': file.content_type
        }]
        
        result = agent_graph.load_documents_from_upload(file_data)
        
        if result["success"]:
            upload_status[file_id] = {
                "status": "completed",
                "file_info": file_info,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse(content={
                "success": True,
                "message": f"Document '{file.filename}' uploaded and processed successfully",
                "file_id": file_id,
                "file_info": file_info,
                "data": result["data"],
                "system_status": result.get("system_status")
            })
        else:
            upload_status[file_id] = {
                "status": "failed",
                "file_info": file_info,
                "error": result.get("error"),
                "timestamp": datetime.now().isoformat()
            }
            
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Document processing failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.post("/documents/batch")
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload multiple documents in batch"""
    try:
        from main import agent_graph
        
        if agent_graph is None:
            raise HTTPException(status_code=503, detail="Agent Graph not initialized")
        
        # Validate batch size
        if len(files) > 20:
            raise HTTPException(
                status_code=400,
                detail="Too many files. Maximum batch size is 20 files"
            )
        
        # Generate batch ID
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate all files first
        supported_types = ['.pdf', '.txt', '.md', '.docx']
        file_data = []
        total_size = 0
        
        for file in files:
            if not any(file.filename.lower().endswith(ext) for ext in supported_types):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}. Supported: {supported_types}"
                )
            
            content = await file.read()
            total_size += len(content)
            
            if total_size > 200 * 1024 * 1024:  # 200MB total limit
                raise HTTPException(
                    status_code=413,
                    detail="Total batch size too large. Maximum is 200MB"
                )
            
            file_data.append({
                'content': content,
                'filename': file.filename,
                'content_type': file.content_type
            })
        
        # Initialize batch status
        upload_status[batch_id] = {
            "status": "processing",
            "batch_info": {
                "batch_id": batch_id,
                "total_files": len(files),
                "total_size": total_size,
                "start_time": datetime.now().isoformat()
            },
            "files": [f['filename'] for f in file_data],
            "progress": 0
        }
        
        logger.info(f"Processing batch upload: {len(files)} files, {total_size} bytes")
        
        # Process batch
        result = agent_graph.load_documents_from_upload(file_data)
        
        # Update batch status
        upload_status[batch_id].update({
            "status": "completed" if result["success"] else "failed",
            "result": result,
            "end_time": datetime.now().isoformat(),
            "progress": 100
        })
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": f"Batch upload completed: {result['data']['documents_loaded']} documents processed",
                "batch_id": batch_id,
                "data": result["data"],
                "system_status": result.get("system_status")
            })
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Batch upload failed")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        if 'batch_id' in locals():
            upload_status[batch_id]["status"] = "error"
            upload_status[batch_id]["error"] = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch upload: {str(e)}"
        )

@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """Get upload status by ID"""
    try:
        if upload_id not in upload_status:
            raise HTTPException(
                status_code=404,
                detail="Upload ID not found"
            )
        
        status = upload_status[upload_id]
        return JSONResponse(content={
            "success": True,
            "data": status,
            "message": "Upload status retrieved successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting upload status: {str(e)}"
        )

@router.get("/history")
async def get_upload_history(limit: int = 50):
    """Get upload history"""
    try:
        # Sort by timestamp, most recent first
        sorted_uploads = sorted(
            upload_status.items(),
            key=lambda x: x[1].get('timestamp', ''),
            reverse=True
        )[:limit]
        
        history = []
        for upload_id, status in sorted_uploads:
            history.append({
                "upload_id": upload_id,
                "status": status.get("status"),
                "timestamp": status.get("timestamp"),
                "file_info": status.get("file_info"),
                "batch_info": status.get("batch_info")
            })
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "uploads": history,
                "total_count": len(upload_status)
            },
            "message": "Upload history retrieved successfully"
        })
        
    except Exception as e:
        logger.error(f"Error getting upload history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting upload history: {str(e)}"
        )

@router.delete("/cleanup")
async def cleanup_upload_history(days_old: int = 7):
    """Clean up old upload history"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Count items to be removed
        removed_count = 0
        to_remove = []
        
        for upload_id, status in upload_status.items():
            timestamp_str = status.get('timestamp', '')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if timestamp < cutoff_date:
                        to_remove.append(upload_id)
                        removed_count += 1
                except:
                    # If timestamp parsing fails, keep the item
                    pass
        
        # Remove old items
        for upload_id in to_remove:
            del upload_status[upload_id]
        
        return JSONResponse(content={
            "success": True,
            "message": f"Cleaned up {removed_count} old upload records",
            "data": {
                "removed_count": removed_count,
                "remaining_count": len(upload_status)
            }
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up upload history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up upload history: {str(e)}"
        )

@router.get("/supported-types")
async def get_supported_file_types():
    """Get information about supported file types"""
    return JSONResponse(content={
        "success": True,
        "data": {
            "csv_files": {
                "extensions": [".csv"],
                "max_size_mb": 100,
                "description": "Comma-separated values files for data analysis"
            },
            "documents": {
                "extensions": [".pdf", ".txt", ".md", ".docx"],
                "max_size_mb": 50,
                "description": "Document files for knowledge base and Q&A"
            },
            "batch_limits": {
                "max_files_per_batch": 20,
                "max_total_size_mb": 200
            }
        },
        "message": "Supported file types retrieved successfully"
    })
