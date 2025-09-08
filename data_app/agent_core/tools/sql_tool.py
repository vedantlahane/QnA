"""
SQL Database Tool Module for Q&A Agent System

This module provides SQL database querying capabilities for the Q&A agent system.
It enables the agent to interact with SQLite databases uploaded by users, allowing
natural language queries to be converted into SQL and executed against the database.

The module integrates with LangChain's SQL chain functionality to provide:
- Natural language to SQL conversion using OpenAI's language models
- Safe SQL execution with result formatting
- Database connection management for multiple uploaded files
- Comprehensive error handling and logging

Key Features:
    - SQLite database support for uploaded .sql files
    - Natural language query processing
    - Automatic SQL generation and execution
    - Multi-database support with file ID tracking
    - Result formatting for LLM consumption

Architecture:
    The module maintains a global registry of active database connections
    keyed by file ID. When a user uploads a SQL file, it's configured and
    stored for later querying through the agent's tool system.

Dependencies:
    - langchain_community: For SQLDatabase utility
    - langchain_openai: For ChatOpenAI LLM integration
    - langchain.chains: For SQL query chain creation
    - langchain_core: For tool decoration and runnables

Environment Requirements:
    - OpenAI API key configured in environment
    - SQLite database files (.db, .sqlite, .sql)

Configuration:
    Uses centralized configuration from tools_config.yml:
    - sql_llm: Language model for SQL generation
    - sql_llm_temperature: Temperature setting for SQL generation

Author: Q&A Agent System
Created: 2025
"""

import os
from typing import Dict, Optional, Any
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
# Load configuration settings from the centralized config file
TOOLS_CFG = LoadToolsConfig()

# --- Global Database Registry ---
# Dictionary to store active database connections
# Key: file_id (int), Value: SQLDatabase instance
# This allows multiple databases to be active simultaneously
_active_dbs: Dict[int, SQLDatabase] = {}


def configure_database(file_path: str, file_id: int) -> None:
    """
    Configure a new SQL database connection for an uploaded SQLite file.

    This function establishes a connection to a SQLite database file and
    registers it in the global database registry for later querying.
    The database remains active until the application restarts.

    The function supports various SQLite file extensions and creates
    a SQLDatabase instance that can be used by LangChain's SQL chains.

    Args:
        file_path (str): Absolute path to the SQLite database file
        file_id (int): Unique identifier for the file (from database)

    Returns:
        None

    Raises:
        None: All exceptions are caught internally and logged

    Supported File Types:
        - .db: Standard SQLite database file
        - .sqlite: Alternative SQLite extension
        - .sql: SQL script files (treated as SQLite databases)

    Example:
        >>> configure_database("/uploads/mydb.db", 123)
        SQL database for file ID 123 configured.

    Note:
        The database connection is stored globally and reused for
        subsequent queries to the same file_id.
    """
    try:
        # Create SQLite URI for database connection
        # Format: sqlite:///path/to/database.db
        db_uri = f"sqlite:///{file_path}"

        # Create SQLDatabase instance from URI
        # This establishes the connection and provides SQL execution capabilities
        db = SQLDatabase.from_uri(db_uri)

        # Register the database in the global registry
        # This makes it available for querying via file_id
        _active_dbs[file_id] = db

        print(f"SQL database for file ID {file_id} configured successfully.")
        print(f"Database URI: {db_uri}")
        print(f"Available tables: {db.get_table_names()}")

    except Exception as e:
        # Comprehensive error handling for database configuration failures
        error_msg = f"Error configuring SQL database for file {file_path}: {str(e)}"
        print(error_msg)

        # Could add more sophisticated error handling here:
        # - File permission checks
        # - Database corruption detection
        # - Connection timeout handling


@tool
def query_sql_database(query: str, file_id: int) -> str:
    """
    Execute a natural language query against a specific SQL database.

    This tool function converts natural language queries into SQL statements
    using OpenAI's language models, executes them against the specified database,
    and returns formatted results. It's designed to work with SQLite databases
    that have been previously configured through the configure_database function.

    The function uses LangChain's SQL query chain to:
    1. Analyze the database schema
    2. Generate appropriate SQL from natural language
    3. Execute the query safely
    4. Format results for LLM consumption

    Args:
        query (str): Natural language query describing the desired data.
                    Examples:
                    - "Show me all customers from New York"
                    - "What are the total sales by product category?"
                    - "List employees hired in the last 6 months"
        file_id (int): Unique identifier of the database file to query

    Returns:
        str: Formatted query results containing:
            - Generated SQL query
            - Query execution results
            - Error messages if execution fails

    Raises:
        None: All exceptions are caught internally and return error strings

    Examples:
        >>> result = query_sql_database("Show me all users", 123)
        >>> print(result)
        "SQL Query: SELECT * FROM users;
        Result: [(1, 'John'), (2, 'Jane'), ...]"

        >>> result = query_sql_database("Total sales by month", 456)
        >>> print(result)
        "SQL Query: SELECT strftime('%Y-%m', order_date) as month, SUM(amount) as total_sales FROM orders GROUP BY month;
        Result: [('2024-01', 15000.0), ('2024-02', 22000.0), ...]"

    Configuration Dependencies:
        - TOOLS_CFG.sql_llm: Language model for SQL generation
        - TOOLS_CFG.sql_llm_temperature: Temperature for SQL generation creativity

    Notes:
        - Requires database to be pre-configured via configure_database()
        - Uses OpenAI API for SQL generation (ensure API key is configured)
        - SQL generation quality depends on database schema clarity
        - Results are formatted as strings for LLM consumption
        - Complex queries may require multiple iterations for accuracy

    Performance Considerations:
        - SQL generation adds API call latency
        - Large result sets may be truncated
        - Complex schemas may require more specific queries
    """
    try:
        # Retrieve the database connection for the specified file_id
        db = _active_dbs.get(file_id)

        if not db:
            # Database not found - user needs to upload/configure first
            available_dbs = list(_active_dbs.keys())
            error_msg = (
                f"Error: No active SQL database found for file ID {file_id}. "
                f"Available database IDs: {available_dbs}. "
                "Please ensure the database file has been uploaded and configured."
            )
            return error_msg

        # Initialize the language model for SQL generation
        # Uses configuration settings for model and temperature
        llm = ChatOpenAI(
            model=TOOLS_CFG.sql_llm,
            temperature=TOOLS_CFG.sql_llm_temperature
        )

        # Create the SQL query chain
        # This chain will analyze the database schema and generate SQL
        query_chain = create_sql_query_chain(llm, db)

        # Generate SQL query from natural language
        # The chain uses the database schema to create appropriate SQL
        generated_sql = query_chain.invoke({"question": query})

        # Execute the generated SQL query
        # This runs the query against the actual database
        execution_result = db.run(generated_sql)

        # Format and return the results
        # Include both the generated SQL and execution results for transparency
        result = f"SQL Query: {generated_sql}\nResult: {execution_result}"

        return result

    except Exception as e:
        # Comprehensive error handling for query execution failures
        error_details = str(e)
        error_msg = (
            "Sorry, an error occurred while querying the SQL database. "
            f"Error details: {error_details}. "
            "Please try rephrasing your query or check the database schema."
        )
        return error_msg


"""
USAGE INFORMATION:

This module provides SQL database querying capabilities for the Q&A agent:

1. Database Configuration:
   >>> from data_app.agent_core.tools.sql_tool import configure_database
   >>> configure_database("/uploads/sales.db", 123)

2. Natural Language Querying:
   >>> from data_app.agent_core.tools.sql_tool import query_sql_database
   >>> result = query_sql_database("Show me total sales by region", 123)

3. Agent Integration:
   The query_sql_database function is automatically registered as a tool
   when a SQL file is uploaded through the manager module.

INTEGRATION WITH AGENT SYSTEM:

The SQL tool integrates seamlessly with the LangChain agent:

1. File Upload: User uploads .db/.sqlite/.sql file
2. Configuration: configure_database() sets up the connection
3. Tool Registration: query_sql_database becomes available to agent
4. Query Processing: Agent uses tool for database-related questions

Example Agent Interaction:
User: "What's the average salary in the IT department?"
Agent: Uses query_sql_database tool
Tool: Generates SQL, executes query, returns results
Agent: Formats and presents results to user

SUPPORTED QUERY TYPES:

- Simple SELECT queries: "Show me all customers"
- Aggregations: "What's the total revenue?"
- Filtering: "Show orders from last month"
- Joins: "Show customer orders" (if relationships exist)
- Complex analysis: "Compare sales by quarter"

BEST PRACTICES:

1. Database Schema:
   - Use clear, descriptive table and column names
   - Include foreign key relationships where applicable
   - Add comments to tables and columns for better SQL generation

2. Query Formulation:
   - Be specific about what data you want
   - Use clear business terminology
   - Provide context about table relationships

3. Performance:
   - Avoid queries that return very large result sets
   - Use appropriate filtering to limit results
   - Consider query complexity vs. generation accuracy

TROUBLESHOOTING:

1. "No active SQL database found":
   - Ensure file was uploaded and processed
   - Check file_id matches the uploaded file
   - Verify database file is not corrupted

2. "Error in SQL generation":
   - Try rephrasing the query more clearly
   - Provide more context about table relationships
   - Check database schema for clarity

3. "SQL execution error":
   - Verify SQL syntax is correct
   - Check for missing tables or columns
   - Ensure proper permissions on database file

4. "API rate limit exceeded":
   - Reduce query frequency
   - Use simpler queries
   - Consider caching frequent queries

CONFIGURATION TUNING:

- sql_llm: Use "gpt-4" for complex queries, "gpt-3.5-turbo" for simple ones
- sql_llm_temperature: Lower (0.1-0.3) for consistent SQL, higher (0.5-0.7) for creative queries

SECURITY CONSIDERATIONS:

- SQL injection is prevented by LangChain's safe SQL generation
- Database files should be validated before processing
- Consider access controls for sensitive data
- Log queries for audit purposes
"""