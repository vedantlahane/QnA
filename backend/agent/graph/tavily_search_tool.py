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

    results = searcher.run(query)
    if not results:
        return "No results found."
    # Format results as needed; here joining texts
    return "\n\n".join(result.summary for result in results)
