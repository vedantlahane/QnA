# data_app/agent_core/tools/sql_tool.py

import os
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from langchain_core.tools import tool
from .config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

# We'll need a way to store the database connection for each uploaded file
_active_dbs = {}

def configure_database(file_path: str, file_id: int):
    """
    Configures a new SQL database connection for an uploaded file and makes it
    available to the agent.
    """
    try:
        db_uri = f"sqlite:///{file_path}"
        db = SQLDatabase.from_uri(db_uri)
        _active_dbs[file_id] = db
        print(f"SQL database for file ID {file_id} configured.")

    except Exception as e:
        print(f"Error configuring SQL database: {e}")


@tool
def query_sql_database(query: str, file_id: int) -> str:
    """
    Query a specific SQL Database. Input should be a search query and a file ID.
    This tool is used for queries that require information from a previously
    uploaded SQL database.
    """
    try:
        db = _active_dbs.get(file_id)
        if not db:
            return f"Error: No active SQL database found for file ID {file_id}."

        llm = ChatOpenAI(
            model=TOOLS_CFG.sql_llm,
            temperature=TOOLS_CFG.sql_llm_temperature
        )

        query_chain = create_sql_query_chain(llm, db)
        response = query_chain.invoke({"question": query})
        
        # Execute the generated SQL query and get the result
        result = db.run(response)
        
        return f"SQL Query: {response}\nResult: {result}"

    except Exception as e:
        return f"Sorry, an error occurred while querying the SQL database. Error: {e}"