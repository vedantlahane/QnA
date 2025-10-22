import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.tools import tool

load_dotenv()

def _require_openai_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

def build_sql_tool(
    sqlite_db_path: Optional[str | Path] = None,
    model_name: str = "openai:gpt-4o",
    temperature: float = 0,
) -> SQLDatabaseToolkit:
    _require_openai_api_key()

    backend_dir = Path(__file__).resolve().parents[2]
    db_path = Path(sqlite_db_path) if sqlite_db_path else backend_dir / "db.sqlite3"

    llm = init_chat_model(model_name, temperature=temperature)
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect,
    top_k=5,
)

    return toolkit

# Build toolkit instance globally or per usage
_sql_toolkit: Optional[SQLDatabaseToolkit] = None

def get_sql_toolkit() -> Optional[SQLDatabaseToolkit]:
    global _sql_toolkit
    if _sql_toolkit is None:
        try:
            _sql_toolkit = build_sql_tool()
        except EnvironmentError as exc:
            print(f"SQL tool unavailable: {exc}")
            _sql_toolkit = None
    return _sql_toolkit

@tool
def run_sql_query(query: str) -> str:
    """Run query using the SQL toolkit and return formatted results."""
    toolkit = get_sql_toolkit()
    if not toolkit:
        return "SQL assistant is not configured yet."

    tools = toolkit.get_tools()
    if not tools:
        return "SQL assistant is ready but no query tool is available."

    query_tool = tools[0]
    return query_tool.run(query)
