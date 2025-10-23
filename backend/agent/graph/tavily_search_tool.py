import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langchain_core.tools import tool

load_dotenv()

def _require_tavily_api_key() -> None:
    if not os.getenv("TAVILY_API_KEY"):
        raise EnvironmentError("TAVILY_API_KEY environment variable is not set")

# Initialize TavilySearch instance once and reuse
_tavily_search = None

def get_tavily_search_tool(max_results: int = 3) -> TavilySearch:
    global _tavily_search
    _require_tavily_api_key()
    if _tavily_search is None:
        _tavily_search = TavilySearch(max_results=max_results)
    return _tavily_search

@tool
def tavily_search(query: str) -> str:
    """
    Search using Tavily API and return top results as string.
    """
    try:
        searcher = get_tavily_search_tool()
    except EnvironmentError as exc:
        return f"Tavily search is unavailable: {exc}"

    raw = searcher.run(query)
    if raw is None:
        return "No Tavily results were returned."

    if isinstance(raw, dict):
        results = raw.get("results") or []
        if not results:
            answer = raw.get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
            return "No results found."
    else:
        results = raw

    formatted_chunks = []
    for item in results:
        if hasattr(item, "summary") and isinstance(item.summary, str) and item.summary.strip():
            formatted_chunks.append(item.summary.strip())
            continue
        if isinstance(item, dict):
            parts = []
            for key in ("title", "url", "content", "summary", "snippet"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
            if parts:
                formatted_chunks.append(" — ".join(parts))
            continue
        if isinstance(item, str) and item.strip():
            formatted_chunks.append(item.strip())

    if not formatted_chunks:
        return "No useful Tavily results were returned."

    return "\n\n".join(formatted_chunks)
