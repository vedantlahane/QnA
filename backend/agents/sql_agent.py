"""
SQL Agent for Database Query Processing
This agent handles SQL database queries, data analysis, and business intelligence tasks.
"""

from typing import Dict, Any, List, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
    QuerySQLDataBaseTool,
    QuerySQLCheckerTool
)
from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLAgent:
    """
    SQL Agent that processes natural language queries and converts them to SQL operations.
    Handles database connections, query generation, execution, and result interpretation.
    """
    
    def __init__(
        self, 
        database_url: str = None,
        llm: ChatOpenAI = None,
        max_iterations: int = 15,
        verbose: bool = True
    ):
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.database_url = database_url
        self.db = None
        self.agent = None
        self.toolkit = None
        
        if database_url:
            self._initialize_database(database_url)
    
    def _initialize_database(self, database_url: str) -> None:
        """Initialize database connection and agent"""
        try:
            # Create database connection
            self.db = SQLDatabase.from_uri(database_url)
            
            # Create SQL toolkit
            self.toolkit = SQLDatabaseToolkit(
                db=self.db,
                llm=self.llm
            )
            
            # Create SQL agent
            self.agent = create_sql_agent(
                llm=self.llm,
                toolkit=self.toolkit,
                verbose=self.verbose,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                max_iterations=self.max_iterations,
                max_execution_time=None,
                early_stopping_method="force"
            )
            
            logger.info(f"SQL Agent initialized with database: {database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQL database: {e}")
            raise
    
    def connect_to_database(self, database_url: str) -> bool:
        """
        Connect to a database
        
        Args:
            database_url: Database connection string
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._initialize_database(database_url)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the connected database
        
        Returns:
            Dictionary with database schema information
        """
        if not self.db:
            return {"error": "No database connected"}
        
        try:
            # Get table names
            table_info = self.db.get_table_names()
            
            # Get sample data from each table
            tables_info = {}
            for table in table_info[:5]:  # Limit to first 5 tables
                try:
                    sample_query = f"SELECT * FROM {table} LIMIT 3"
                    sample_data = self.db.run(sample_query)
                    tables_info[table] = {
                        "sample_data": sample_data,
                        "table_info": self.db.get_table_info([table])
                    }
                except Exception as e:
                    tables_info[table] = {"error": str(e)}
            
            return {
                "tables": table_info,
                "table_details": tables_info,
                "dialect": str(self.db.dialect)
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}
    
    def validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate SQL query without executing it
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dictionary with validation results
        """
        if not self.db:
            return {"valid": False, "error": "No database connected"}
        
        try:
            # Basic SQL injection check
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
            query_upper = sql_query.upper()
            
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return {
                        "valid": False,
                        "error": f"Query contains potentially dangerous keyword: {keyword}"
                    }
            
            # Try to parse the query (this doesn't execute it)
            try:
                engine = create_engine(self.database_url)
                with engine.connect() as conn:
                    # Prepare the statement without executing
                    stmt = text(sql_query)
                    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
                    
                return {
                    "valid": True,
                    "compiled_query": str(compiled)
                }
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"SQL syntax error: {str(e)}"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query directly
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Dictionary with query results
        """
        if not self.db:
            return {"error": "No database connected"}
        
        try:
            # Validate query first
            validation = self.validate_sql_query(sql_query)
            if not validation["valid"]:
                return {"error": f"Invalid query: {validation['error']}"}
            
            # Execute query
            result = self.db.run(sql_query)
            
            return {
                "success": True,
                "result": result,
                "query": sql_query
            }
            
        except SQLAlchemyError as e:
            logger.error(f"SQL execution error: {e}")
            return {"error": f"SQL error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error executing SQL: {e}")
            return {"error": f"Execution error: {str(e)}"}
    
    async def process_natural_language_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process natural language query and convert to SQL
        
        Args:
            query: Natural language question about the database
            context: Additional context for the query
            
        Returns:
            Dictionary with SQL query, results, and explanation
        """
        if not self.agent:
            return {"error": "SQL agent not initialized. Please connect to a database first."}
        
        try:
            # Add context to the query if provided
            enhanced_query = query
            if context:
                if context.get("table_hints"):
                    enhanced_query += f"\n\nFocus on these tables: {', '.join(context['table_hints'])}"
                if context.get("column_hints"):
                    enhanced_query += f"\n\nRelevant columns might include: {', '.join(context['column_hints'])}"
            
            # Execute the agent
            result = await self.agent.arun(enhanced_query)
            
            # Extract SQL query if present in the result
            sql_pattern = r'```sql\n(.*?)\n```'
            sql_match = re.search(sql_pattern, result, re.DOTALL | re.IGNORECASE)
            executed_sql = sql_match.group(1) if sql_match else None
            
            return {
                "success": True,
                "answer": result,
                "sql_query": executed_sql,
                "original_query": query,
                "agent_response": result
            }
            
        except Exception as e:
            logger.error(f"Error processing natural language query: {e}")
            return {
                "error": f"Failed to process query: {str(e)}",
                "original_query": query
            }
    
    def get_query_suggestions(self, partial_query: str = None) -> List[str]:
        """
        Get query suggestions based on database schema
        
        Args:
            partial_query: Partial query to base suggestions on
            
        Returns:
            List of suggested queries
        """
        if not self.db:
            return ["No database connected"]
        
        try:
            tables = self.db.get_table_names()
            suggestions = []
            
            # General analytical queries
            base_suggestions = [
                "Show me the total number of records in each table",
                "What are the column names and types for each table?",
                "Give me a summary of the data in the database",
                "Show me the first 5 rows from each table",
                "What are the most common values in each column?"
            ]
            
            # Table-specific suggestions
            for table in tables[:3]:  # Limit to first 3 tables
                suggestions.extend([
                    f"How many records are in the {table} table?",
                    f"Show me the structure of the {table} table",
                    f"What are the unique values in the {table} table?",
                    f"Give me statistics about the {table} table"
                ])
            
            suggestions.extend(base_suggestions)
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return ["Error generating suggestions"]
    
    def create_sample_database(self, db_path: str = "sample_business.db") -> str:
        """
        Create a sample SQLite database for testing
        
        Args:
            db_path: Path where to create the database
            
        Returns:
            Database URL string
        """
        try:
            import sqlite3
            
            # Create sample business database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create customers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    city TEXT,
                    country TEXT,
                    created_date DATE
                )
            """)
            
            # Create products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    price REAL,
                    stock_quantity INTEGER
                )
            """)
            
            # Create orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    product_id INTEGER,
                    quantity INTEGER,
                    order_date DATE,
                    total_amount REAL,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                    FOREIGN KEY (product_id) REFERENCES products (product_id)
                )
            """)
            
            # Insert sample data
            customers_data = [
                (1, 'John Doe', 'john@email.com', 'New York', 'USA', '2024-01-15'),
                (2, 'Jane Smith', 'jane@email.com', 'London', 'UK', '2024-01-20'),
                (3, 'Bob Wilson', 'bob@email.com', 'Toronto', 'Canada', '2024-02-01'),
                (4, 'Alice Brown', 'alice@email.com', 'Sydney', 'Australia', '2024-02-10'),
                (5, 'Charlie Davis', 'charlie@email.com', 'Berlin', 'Germany', '2024-02-15')
            ]
            
            products_data = [
                (1, 'Laptop', 'Electronics', 999.99, 50),
                (2, 'Smartphone', 'Electronics', 699.99, 100),
                (3, 'Headphones', 'Electronics', 199.99, 75),
                (4, 'Book', 'Education', 29.99, 200),
                (5, 'Desk Chair', 'Furniture', 299.99, 25)
            ]
            
            orders_data = [
                (1, 1, 1, 1, '2024-03-01', 999.99),
                (2, 2, 2, 2, '2024-03-02', 1399.98),
                (3, 3, 3, 1, '2024-03-03', 199.99),
                (4, 1, 4, 3, '2024-03-04', 89.97),
                (5, 4, 5, 1, '2024-03-05', 299.99),
                (6, 2, 1, 1, '2024-03-06', 999.99),
                (7, 5, 3, 2, '2024-03-07', 399.98)
            ]
            
            cursor.executemany("INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers_data)
            cursor.executemany("INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?)", products_data)
            cursor.executemany("INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders_data)
            
            conn.commit()
            conn.close()
            
            database_url = f"sqlite:///{db_path}"
            logger.info(f"Sample database created at: {database_url}")
            
            return database_url
            
        except Exception as e:
            logger.error(f"Error creating sample database: {e}")
            raise

# Factory function for easy instantiation
def create_sql_agent(database_url: str = None, llm: ChatOpenAI = None) -> SQLAgent:
    """Create a configured SQL agent instance"""
    return SQLAgent(database_url=database_url, llm=llm)

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test_sql_agent():
        # Create sample database
        agent = SQLAgent()
        db_url = agent.create_sample_database("test_business.db")
        
        # Initialize agent with sample database
        agent.connect_to_database(db_url)
        
        # Test database info
        print("Database Info:")
        db_info = agent.get_database_info()
        print(f"Tables: {db_info.get('tables', [])}")
        
        # Test natural language queries
        test_queries = [
            "How many customers do we have?",
            "What's the total revenue from all orders?",
            "Show me the top 3 products by total sales",
            "Which customers have made more than one order?",
            "What's the average order value?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = await agent.process_natural_language_query(query)
            if result.get("success"):
                print(f"Answer: {result['answer']}")
                if result.get("sql_query"):
                    print(f"SQL: {result['sql_query']}")
            else:
                print(f"Error: {result.get('error')}")
    
    # Run test
    # asyncio.run(test_sql_agent())
