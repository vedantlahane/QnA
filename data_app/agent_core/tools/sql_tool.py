"""
SQL Database Tool Module for Q&A Agent System.
Supports configuring SQLite databases (including bootstrapping from .sql scripts)
and querying them using natural language converted to SQL.
"""
import os
import logging
from typing import Dict

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_core.tools import tool

from data_app.agent_core.config import LoadToolsConfig

logger = logging.getLogger('data_app.agent_core.tools.sql_tool')
TOOLS_CFG = LoadToolsConfig()

_active_dbs: Dict[int, SQLDatabase] = {}

def configure_database(file_path: str, file_id: int) -> None:
    """
    Configure a SQL database connection for an uploaded SQLite file or .sql script.
    If a .sql script is provided, a SQLite DB is created in data/sqlite_<file_id>.db.
    """
    try:
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.sql':
            os.makedirs('data', exist_ok=True)
            generated_db_path = f'data/sqlite_{file_id}.db'
            import sqlite3
            with open(file_path, 'r', encoding='utf-8') as f:
                script = f.read()
            conn = sqlite3.connect(generated_db_path)
            try:
                conn.executescript(script)
                conn.commit()
            finally:
                conn.close()
            db_uri = f"sqlite:///{generated_db_path}"
        else:
            db_uri = f"sqlite:///{file_path}"

        db = SQLDatabase.from_uri(db_uri)
        _active_dbs[file_id] = db
        logger.info(f"SQL database for file ID {file_id} configured successfully: {db_uri}")
        logger.info(f"Available tables: {db.get_table_names()}")
    except Exception as e:
        logger.info(f"Error configuring SQL database for file {file_path}: {str(e)}")


@tool
def query_sql_database(query: str, file_id: int) -> str:
    """
    Execute a natural language query against the configured SQL database for file_id.
    Returns both the generated SQL and the execution results.
    """
    try:
        db = _active_dbs.get(file_id)
        if not db:
            available = list(_active_dbs.keys())
            return (
                f"Error: No active SQL database found for file ID {file_id}. "
                f"Available database IDs: {available}. "
                "Please ensure the database file has been uploaded and configured."
            )

        llm = ChatOpenAI(model=TOOLS_CFG.sql_llm, temperature=TOOLS_CFG.sql_llm_temperature)
        query_chain = create_sql_query_chain(llm, db)
        generated_sql = query_chain.invoke({"question": query})
        execution_result = db.run(generated_sql)
        return f"SQL Query: {generated_sql}\nResult: {execution_result}"
    except Exception as e:
        return (
            "Sorry, an error occurred while querying the SQL database. "
            f"Error details: {str(e)}. "
            "Please try rephrasing your query or check the database schema."
        )
