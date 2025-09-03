# data_app/agent_core/tools/sql_tool.py

import os
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain.schema.runnable import RunnableMap
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread-safe storage for database connections
_active_dbs = {}
_db_lock = threading.Lock()

def _validate_sql_file(file_path: str) -> bool:
    """Validate that the SQL database file exists and is accessible."""
    if not os.path.exists(file_path):
        logger.error(f"SQL database file does not exist: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        logger.error(f"Path is not a file: {file_path}")
        return False
    
    # Check if file is not empty
    if os.path.getsize(file_path) == 0:
        logger.error(f"SQL database file is empty: {file_path}")
        return False
    
    # Try to connect to verify it's a valid database
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        if not tables:
            logger.warning(f"SQL database has no tables: {file_path}")
            return False
        
        return True
    except sqlite3.Error as e:
        logger.error(f"Invalid SQLite database file: {file_path}. Error: {e}")
        return False

def _test_database_connection(db: SQLDatabase) -> bool:
    """Test if database connection is working."""
    try:
        # Try a simple query to test connection
        result = db.run("SELECT 1;")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def configure_database(file_path: str, file_id: int) -> bool:
    """
    Configures a new SQL database connection for an uploaded file and makes it
    available to the agent.
    
    Args:
        file_path (str): The full path to the uploaded SQL database file.
        file_id (int): The unique ID of the uploaded file.
    
    Returns:
        bool: True if configuration was successful, False otherwise.
    """
    try:
        # Validate inputs
        if not _validate_sql_file(file_path):
            return False
        
        if file_id <= 0:
            logger.error(f"Invalid file_id: {file_id}. Must be positive integer.")
            return False
        
        logger.info(f"Configuring SQL database for file: {file_path} with ID: {file_id}")
        
        # Create database URI - support for different database types
        if file_path.lower().endswith('.db') or file_path.lower().endswith('.sqlite') or file_path.lower().endswith('.sqlite3'):
            db_uri = f"sqlite:///{file_path}"
        else:
            # Assume SQLite for other extensions
            db_uri = f"sqlite:///{file_path}"
        
        # Create database connection
        db = SQLDatabase.from_uri(
            db_uri,
            include_tables=None,  # Include all tables
            sample_rows_in_table_info=3,  # Show sample rows for context
            custom_table_info=None
        )
        
        # Test the connection
        if not _test_database_connection(db):
            return False
        
        # Thread-safe storage
        with _db_lock:
            _active_dbs[file_id] = db
        
        logger.info(f"SQL database for file ID {file_id} configured successfully")
        
        # Log database schema info for debugging
        try:
            schema_info = db.get_table_info()
            logger.info(f"Database schema for file_id {file_id}:\n{schema_info}")
        except Exception as e:
            logger.warning(f"Could not retrieve schema info: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error configuring SQL database: {e}")
        return False

def _format_sql_result(query: str, result: Any) -> str:
    """Format SQL query results for better readability."""
    try:
        if result is None:
            return f"SQL Query: {query}\nResult: No results returned"
        
        if isinstance(result, str):
            # If result is already a string, format it nicely
            if len(result) > 1000:
                truncated_result = result[:1000] + "... (truncated)"
                return f"SQL Query: {query}\nResult: {truncated_result}"
            return f"SQL Query: {query}\nResult: {result}"
        
        if isinstance(result, (list, tuple)):
            if len(result) == 0:
                return f"SQL Query: {query}\nResult: No results returned"
            
            # Format list/tuple results
            formatted_result = str(result)
            if len(formatted_result) > 1000:
                formatted_result = formatted_result[:1000] + "... (truncated)"
            
            return f"SQL Query: {query}\nResult: {formatted_result}\nRows returned: {len(result)}"
        
        # For other types, convert to string
        result_str = str(result)
        if len(result_str) > 1000:
            result_str = result_str[:1000] + "... (truncated)"
        
        return f"SQL Query: {query}\nResult: {result_str}"
        
    except Exception as e:
        logger.error(f"Error formatting SQL result: {e}")
        return f"SQL Query: {query}\nResult: {result} (formatting error occurred)"

def _validate_sql_query(query: str) -> bool:
    """Basic validation to prevent dangerous SQL operations."""
    dangerous_keywords = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE'
    ]
    
    query_upper = query.upper()
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            logger.warning(f"Potentially dangerous SQL keyword detected: {keyword}")
            return False
    
    return True

@tool
def query_sql_database(query: str, file_id: int) -> str:
    """
    Query a specific SQL Database. Input should be a natural language query and a file ID.
    This tool is used for queries that require information from a previously
    uploaded SQL database.
    
    Args:
        query (str): The natural language question about the database.
        file_id (int): The ID of the specific SQL database file to query.
        
    Returns:
        str: The formatted result of the SQL query execution.
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return "Please provide a valid question about the database."
        
        if file_id <= 0:
            return "Invalid file ID provided. Please specify a valid database file ID."
        
        # Get database connection (thread-safe)
        with _db_lock:
            db = _active_dbs.get(file_id)
        
        if not db:
            return f"Error: No active SQL database found for file ID {file_id}. Please ensure the database file has been uploaded and configured."
        
        logger.info(f"Processing SQL query for file_id {file_id}: {query}")
        
        # Initialize the LLM
        llm = ChatOpenAI(
            model=TOOLS_CFG.sql_llm,
            temperature=TOOLS_CFG.sql_llm_temperature
        )
        
        # Create enhanced prompt for SQL generation
        sql_prompt = PromptTemplate(
            input_variables=["input", "table_info", "top_k"],
            template="""Given an input question, create a syntactically correct SQLite query to run.

Database Schema:
{table_info}

Important Guidelines:
- Only use SELECT statements (no INSERT, UPDATE, DELETE, DROP, etc.)
- Limit results to {top_k} rows unless specifically asked for more
- Use proper SQLite syntax
- Include column names in results when possible
- Handle NULL values appropriately
- Use LIMIT clause to prevent overwhelming results

Question: {input}

SQL Query:"""
        )
        
        # Create the SQL query generation chain
        query_chain = create_sql_query_chain(llm, db, prompt=sql_prompt)
        
        # Generate SQL query
        sql_query = query_chain.invoke({
            "question": query,
            "top_k": 10  # Default limit
        })
        
        # Basic validation of generated SQL
        if not _validate_sql_query(sql_query):
            return "Error: Generated SQL query contains potentially dangerous operations. Only SELECT queries are allowed."
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        # Execute the SQL query
        try:
            result = db.run(sql_query)
            formatted_result = _format_sql_result(sql_query, result)
            
            logger.info(f"Successfully executed SQL query for file_id {file_id}")
            return formatted_result
            
        except Exception as sql_error:
            error_msg = f"SQL Execution Error: {str(sql_error)}\nGenerated Query: {sql_query}"
            logger.error(f"SQL execution failed for file_id {file_id}: {sql_error}")
            return error_msg
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred while querying the SQL database. Error: {str(e)}"
        logger.error(f"Error in query_sql_database for file_id {file_id}: {e}")
        return error_msg

# Utility functions for debugging and maintenance
def list_active_databases() -> List[int]:
    """List all file IDs that have active database connections."""
    with _db_lock:
        return list(_active_dbs.keys())

def close_database_connection(file_id: int) -> bool:
    """Close and remove a database connection."""
    try:
        with _db_lock:
            if file_id in _active_dbs:
                # Close the connection if possible
                db = _active_dbs[file_id]
                try:
                    # SQLDatabase doesn't have a close method, but the underlying connection might
                    if hasattr(db, '_engine') and hasattr(db._engine, 'dispose'):
                        db._engine.dispose()
                except Exception as e:
                    logger.warning(f"Could not properly close database connection: {e}")
                
                del _active_dbs[file_id]
                logger.info(f"Closed database connection for file_id {file_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error closing database connection for file_id {file_id}: {e}")
        return False

def get_database_info(file_id: int) -> Optional[Dict[str, Any]]:
    """Get information about a specific database."""
    try:
        with _db_lock:
            db = _active_dbs.get(file_id)
        
        if not db:
            return None
        
        try:
            table_info = db.get_table_info()
            table_names = db.get_usable_table_names()
            
            return {
                "file_id": file_id,
                "database_type": "SQLite",
                "table_names": table_names,
                "table_count": len(table_names),
                "schema_info": table_info
            }
        except Exception as e:
            logger.error(f"Error getting database info for file_id {file_id}: {e}")
            return {
                "file_id": file_id,
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Error accessing database for file_id {file_id}: {e}")
        return None

def test_database_query(file_id: int, test_query: str = "SELECT 1") -> Dict[str, Any]:
    """Test a database connection with a simple query."""
    try:
        with _db_lock:
            db = _active_dbs.get(file_id)
        
        if not db:
            return {"success": False, "error": "Database not found"}
        
        result = db.run(test_query)
        return {
            "success": True,
            "query": test_query,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "query": test_query,
            "error": str(e)
        }

def get_table_schema(file_id: int, table_name: str) -> Optional[str]:
    """Get detailed schema information for a specific table."""
    try:
        with _db_lock:
            db = _active_dbs.get(file_id)
        
        if not db:
            return None
        
        # Get table schema using PRAGMA
        schema_query = f"PRAGMA table_info({table_name})"
        result = db.run(schema_query)
        
        return f"Schema for table '{table_name}':\n{result}"
    except Exception as e:
        logger.error(f"Error getting table schema for {table_name} in file_id {file_id}: {e}")
        return None

def close_all_database_connections():
    """Close all active database connections. Useful for cleanup."""
    try:
        with _db_lock:
            file_ids = list(_active_dbs.keys())
            for file_id in file_ids:
                close_database_connection(file_id)
        logger.info("Closed all database connections")
    except Exception as e:
        logger.error(f"Error closing all database connections: {e}")
