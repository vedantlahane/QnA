import os
import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

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
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = (_BACKEND_ROOT / path).resolve()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError:
        raise ValueError(f"SQLite database file not found: {path}")
    if not resolved.is_file():
        raise ValueError(f"SQLite database path must point to a file: {resolved}")
    return resolved


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
    """Build SQL toolkit with LangChain v1.0 model initialization."""
    _require_openai_api_key()
    target = connection or _CURRENT_CONNECTION.get()
    if target is None:
        raise RuntimeError("No SQL connection configured.")
    
    # v1.0 style model initialization - FIX #1
    llm = init_chat_model("gpt-4o", model_provider="openai", temperature=0)
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
    """
    Execute a SQL query against the connected database and return formatted results.
    Use this tool when the user asks questions about data in the database or wants 
    to query the database tables.
    
    Args:
        query (str): The SQL query to execute (e.g., SELECT, INSERT, UPDATE, DELETE).
    
    Returns:
        str: Formatted query results or error message.
    """
    toolkit = get_sql_toolkit()
    if not toolkit:
        return (
            "SQL database is not configured. Please ensure a database connection "
            "has been established before attempting queries."
        )

    tools = toolkit.get_tools()
    if not tools:
        return "SQL toolkit initialized but no query tool is available."

    query_tool = tools[0]
    try:
        # v1.0: Use invoke instead of run - FIX #2
        result = query_tool.invoke(query)
        return result if result else "Query executed successfully but returned no results."
    except Exception as exc:
        return f"SQL query failed: {type(exc).__name__}: {exc}"


def _create_engine(connection: SQLConnectionDetails) -> Engine:
    return create_engine(connection.uri)


def _serialise_sql_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.hex()
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def execute_raw_sql_query(
    connection: SQLConnectionDetails, 
    query: str, 
    *, 
    limit: int = 200
) -> Dict[str, Any]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("A SQL query is required.")
    if limit <= 0:
        raise ValueError("Result limit must be greater than zero.")

    engine = _create_engine(connection)
    start = perf_counter()
    try:
        with engine.begin() as conn:
            result = conn.execute(text(cleaned_query))
            if result.returns_rows:
                fetched = list(result.fetchmany(limit + 1))
                has_more = len(fetched) > limit
                rows = [
                    [_serialise_sql_value(value) for value in row]
                    for row in fetched[:limit]
                ]
                return {
                    "type": "rows",
                    "columns": list(result.keys()),
                    "rows": rows,
                    "rowCount": len(rows),
                    "hasMore": has_more,
                    "executionTimeMs": round((perf_counter() - start) * 1000, 2),
                }

            row_count = result.rowcount if result.rowcount is not None else 0
            return {
                "type": "ack",
                "rowCount": row_count,
                "message": "Query executed successfully.",
                "executionTimeMs": round((perf_counter() - start) * 1000, 2),
            }
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


def describe_sql_schema(connection: SQLConnectionDetails) -> Dict[str, Any]:
    engine = _create_engine(connection)
    try:
        inspector = inspect(engine)
        tables: List[Dict[str, Any]] = []
        for table_name in inspector.get_table_names():
            column_definitions = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name) or {}
            pk_columns = set(pk_constraint.get("constrained_columns") or [])

            columns = [
                {
                    "name": column.get("name"),
                    "type": str(column.get("type")),
                    "nullable": bool(column.get("nullable", True)),
                    "default": column.get("default"),
                    "primaryKey": column.get("name") in pk_columns,
                }
                for column in column_definitions
            ]

            foreign_keys = []
            for fk in inspector.get_foreign_keys(table_name):
                referred_table = fk.get("referred_table")
                if not referred_table:
                    continue
                constrained_cols = fk.get("constrained_columns") or []
                referred_cols = fk.get("referred_columns") or []
                for col_name, ref_col in zip(constrained_cols, referred_cols):
                    foreign_keys.append(
                        {
                            "column": col_name,
                            "referencedTable": referred_table,
                            "referencedColumn": ref_col,
                        }
                    )

            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "foreignKeys": foreign_keys,
                }
            )

        views = []
        try:
            view_names = inspector.get_view_names()
        except NotImplementedError:
            view_names = []
        for view_name in view_names:
            columns = [
                {
                    "name": column.get("name"),
                    "type": str(column.get("type")),
                    "nullable": bool(column.get("nullable", True)),
                    "primaryKey": False,
                }
                for column in inspector.get_columns(view_name)
            ]
            views.append({"name": view_name, "columns": columns})

        return {
            "schema": inspector.default_schema_name,
            "tables": tables,
            "views": views,
        }
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


def _summarise_schema(
    schema_payload: Dict[str, Any], 
    *, 
    table_limit: int = 8, 
    column_limit: int = 6
) -> str:
    tables = schema_payload.get("tables") or []
    lines: List[str] = []
    for index, table in enumerate(tables):
        if index >= table_limit:
            lines.append("...")
            break
        name = str(table.get("name") or f"table_{index}")
        columns = table.get("columns") or []
        column_chunks: List[str] = []
        for column_index, column in enumerate(columns):
            if column_index >= column_limit:
                column_chunks.append("...")
                break
            column_name = str(column.get("name") or f"col_{column_index}")
            column_type = str(column.get("type") or "unknown")
            descriptor = (
                "PK" if column.get("primaryKey") 
                else ("NULL" if column.get("nullable", True) else "NOT NULL")
            )
            column_chunks.append(f"{column_name} {column_type} {descriptor}")
        lines.append(f"{name}: {', '.join(column_chunks) if column_chunks else 'no columns'}")
    
    if not lines:
        return "No tables discovered."
    return "\n".join(lines)


def generate_sql_suggestions(
    connection: SQLConnectionDetails,
    query: str,
    *,
    schema_snapshot: Optional[Dict[str, Any]] = None,
    max_suggestions: int = 3,
) -> Dict[str, Any]:
    """Generate SQL query suggestions using LangChain v1.0."""
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("A SQL query is required.")

    if max_suggestions <= 0:
        raise ValueError("max_suggestions must be greater than zero.")

    _require_openai_api_key()
    
    # v1.0 style model initialization - FIX #3
    llm = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0.2)

    schema_summary = None
    if schema_snapshot:
        try:
            schema_summary = _summarise_schema(schema_snapshot)
        except Exception:
            schema_summary = None

    system_message = SystemMessage(
        content=(
            "You are an expert SQL reviewer. Analyse the provided SQL statement and return JSON with the "
            "following structure: {\"analysis\": string | null, \"suggestions\": array}. Each suggestion "
            "object must contain keys: title (string), summary (string), query (string), rationale (string), "
            "warnings (array of strings, may be empty). Ensure the improved query is syntactically valid SQL "
            "for the described schema. If the original query is already optimal, return an empty suggestions array "
            "but include a helpful analysis."
        )
    )

    user_sections = [f"Original query:\n{cleaned_query}"]
    if schema_summary:
        user_sections.append(f"Schema overview:\n{schema_summary}")
    user_sections.append(f"Return at most {max_suggestions} suggestions.")

    response = llm.invoke([system_message, HumanMessage(content="\n\n".join(user_sections))])
    
    # v1.0 compatible content extraction - FIX #4
    raw_content = ""
    if response is not None:
        content = getattr(response, "content", None)
        if content is not None:
            if isinstance(content, str):
                raw_content = content
            elif isinstance(content, list):
                # Handle content blocks (v1.0 feature)
                raw_content = "\n".join(
                    block.get("text", str(block)) if isinstance(block, dict) else str(block)
                    for block in content
                )
            else:
                raw_content = str(content)

    analysis_text: Optional[str] = None
    suggestions_payload: List[Dict[str, Any]] = []

    try:
        parsed = json.loads(raw_content)
        if isinstance(parsed, dict):
            analysis_value = parsed.get("analysis")
            if isinstance(analysis_value, str) and analysis_value.strip():
                analysis_text = analysis_value.strip()
            suggestions_value = parsed.get("suggestions")
            if isinstance(suggestions_value, list):
                for item in suggestions_value[:max_suggestions]:
                    if not isinstance(item, dict):
                        continue
                    suggestion_query = str(item.get("query") or "").strip()
                    if not suggestion_query:
                        continue
                    suggestion = {
                        "id": str(uuid4()),
                        "title": str(item.get("title") or "Improved query").strip() or "Improved query",
                        "summary": str(item.get("summary") or item.get("description") or "").strip(),
                        "query": suggestion_query,
                        "rationale": str(item.get("rationale") or item.get("reasoning") or "").strip(),
                        "warnings": [
                            str(warning).strip()
                            for warning in (item.get("warnings") or [])
                            if isinstance(warning, str) and warning.strip()
                        ],
                    }
                    suggestions_payload.append(suggestion)
    except json.JSONDecodeError:
        analysis_text = raw_content.strip() or None

    return {
        "analysis": analysis_text,
        "suggestions": suggestions_payload,
        "raw": raw_content,
    }
