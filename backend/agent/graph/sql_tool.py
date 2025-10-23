import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.tools import tool
from sqlalchemy import create_engine, text

load_dotenv()

@dataclass(frozen=True)
class SQLConnectionDetails:
    mode: str
    identifier: str
    uri: str
    label: str
    sqlite_path: Optional[str] = None


AVAILABLE_DATABASE_MODES = ("sqlite", "url")
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_CURRENT_CONNECTION: ContextVar[Optional[SQLConnectionDetails]] = ContextVar(
    "current_sql_connection", default=None
)
_TOOLKIT_CACHE: Dict[str, SQLDatabaseToolkit] = {}


def _require_openai_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")


def _normalise_sqlite_path(raw_path: Optional[str]) -> Path:
    candidate = (raw_path or "").strip()
    if not candidate:
        raise ValueError("A SQLite database path is required.")
    path = Path(candidate)
    if not path.is_absolute():
        path = _BACKEND_ROOT / path
    return path.resolve()


def get_environment_connection() -> Optional[SQLConnectionDetails]:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        label = os.getenv("DATABASE_LABEL") or "Environment database"
        return SQLConnectionDetails(
            mode="url",
            identifier=database_url,
            uri=database_url,
            label=label,
            sqlite_path=None,
        )

    sqlite_env_path = os.getenv("SQLITE_DB_PATH")
    if sqlite_env_path:
        sqlite_path = _normalise_sqlite_path(sqlite_env_path)
        label = os.getenv("DATABASE_LABEL") or f"SQLite ({sqlite_path.name})"
        return SQLConnectionDetails(
            mode="sqlite",
            identifier=str(sqlite_path),
            uri=f"sqlite:///{sqlite_path}",
            label=label,
            sqlite_path=str(sqlite_path),
        )

    return None


def resolve_connection_details(
    mode: str,
    *,
    sqlite_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    display_name: Optional[str] = None,
) -> SQLConnectionDetails:
    cleaned_mode = (mode or "").strip().lower()
    if cleaned_mode in {"sqlite", "local", "file"}:
        resolved_path = _normalise_sqlite_path(sqlite_path)
        label = (display_name or "").strip() or f"SQLite ({resolved_path.name})"
        return SQLConnectionDetails(
            mode="sqlite",
            identifier=str(resolved_path),
            uri=f"sqlite:///{resolved_path}",
            label=label,
            sqlite_path=str(resolved_path),
        )

    if cleaned_mode in {"url", "remote", "external"}:
        if not isinstance(connection_url, str) or not connection_url.strip():
            raise ValueError("A connection string is required for remote databases.")
        uri = connection_url.strip()
        label = (display_name or "").strip() or "Remote SQL database"
        return SQLConnectionDetails(
            mode="url",
            identifier=uri,
            uri=uri,
            label=label,
            sqlite_path=None,
        )

    raise ValueError("Unsupported database mode. Use 'sqlite' or 'url'.")


@contextmanager
def use_sql_connection(connection: Optional[SQLConnectionDetails]):
    token = _CURRENT_CONNECTION.set(connection)
    try:
        yield
    finally:
        _CURRENT_CONNECTION.reset(token)


def clear_sql_toolkit_cache(identifier: Optional[str] = None) -> None:
    if identifier is None:
        _TOOLKIT_CACHE.clear()
    else:
        _TOOLKIT_CACHE.pop(identifier, None)


def build_sql_tool(connection: Optional[SQLConnectionDetails] = None) -> SQLDatabaseToolkit:
    _require_openai_api_key()
    target = connection or _CURRENT_CONNECTION.get()
    if target is None:
        raise RuntimeError("No SQL connection configured.")
    llm = init_chat_model("openai:gpt-4o", temperature=0)
    db = SQLDatabase.from_uri(target.uri)
    return SQLDatabaseToolkit(db=db, llm=llm)


def get_sql_toolkit(force_rebuild: bool = False) -> Optional[SQLDatabaseToolkit]:
    connection = _CURRENT_CONNECTION.get()
    target = connection
    if target is None:
        return None
    cache_key = target.identifier

    if force_rebuild:
        _TOOLKIT_CACHE.pop(cache_key, None)

    toolkit = _TOOLKIT_CACHE.get(cache_key)
    if toolkit is not None:
        return toolkit

    try:
        toolkit = build_sql_tool(target)
    except EnvironmentError as exc:
        print(f"SQL tool unavailable: {exc}")
        return None
    except Exception as exc:
        print(f"Failed to initialise SQL toolkit: {exc}")
        return None

    _TOOLKIT_CACHE[cache_key] = toolkit
    return toolkit


def test_sql_connection(connection: SQLConnectionDetails) -> None:
    engine = None
    try:
        engine = create_engine(connection.uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass


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
    try:
        return query_tool.run(query)
    except Exception as exc:
        return f"SQL query failed: {exc}"
