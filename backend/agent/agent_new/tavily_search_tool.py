import os
from typing import Literal, Optional
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langchain_core.tools import tool

load_dotenv()


def _require_tavily_api_key() -> None:
    """Validate that Tavily API key is set."""
    if not os.getenv("TAVILY_API_KEY"):
        raise EnvironmentError(
            "TAVILY_API_KEY environment variable is not set. "
            "Get your API key from https://tavily.com"
        )


# Global instance cache
_tavily_search: Optional[TavilySearch] = None


def get_tavily_search_tool(
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    search_depth: Literal["basic", "advanced"] = "basic",
) -> TavilySearch:
    """
    Get or create a cached Tavily search tool instance.
    
    Args:
        max_results: Maximum number of search results (1-10, default: 3)
        topic: Search category (default: "general")
        search_depth: Search thoroughness (default: "basic")
    
    Returns:
        TavilySearch: Configured Tavily search tool
    """
    global _tavily_search
    _require_tavily_api_key()
    
    if _tavily_search is None:
        _tavily_search = TavilySearch(
            max_results=max_results,
            topic=topic,
            search_depth=search_depth,
        )
    
    return _tavily_search


@tool
def tavily_search(query: str) -> str:
    """
    Search the web for current, real-time information using Tavily Search API.
    
    Use this tool when you need:
    - Current events or breaking news
    - Recent developments or updates
    - Real-time data (weather, stock prices, etc.)
    - Facts that may have changed since your knowledge cutoff
    - Up-to-date information about people, companies, or topics
    
    Args:
        query (str): The search query for finding current information.
    
    Returns:
        str: Formatted search results with relevant, current information from the web.
    """
    try:
        searcher = get_tavily_search_tool()
    except EnvironmentError as exc:
        return f"Web search unavailable: {exc}"

    try:
        # Use invoke for v1.0 compatibility
        raw = searcher.invoke(query)
    except Exception as e:
        return f"Search failed: {type(e).__name__}: {e}"
    
    if raw is None:
        return "No search results were returned."

    # Parse response format
    if isinstance(raw, dict):
        results = raw.get("results") or []
        if not results:
            # Check for direct answer
            answer = raw.get("answer")
            if isinstance(answer, str) and answer.strip():
                return f"**Answer:** {answer.strip()}"
            return "No results found for your query."
    else:
        results = raw

    # Format results
    formatted_chunks = []
    for idx, item in enumerate(results, 1):
        # Handle object-style results (has attributes)
        if hasattr(item, "summary") and isinstance(item.summary, str) and item.summary.strip():
            formatted_chunks.append(f"**Result {idx}:**\n{item.summary.strip()}")
            continue
        
        # Handle dict-style results
        if isinstance(item, dict):
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            content = (
                item.get("content") or 
                item.get("summary") or 
                item.get("snippet") or 
                ""
            ).strip()
            
            parts = []
            if title:
                parts.append(f"**{title}**")
            if content:
                # Limit content length
                max_content_len = 500
                if len(content) > max_content_len:
                    content = content[:max_content_len] + "..."
                parts.append(content)
            if url:
                parts.append(f"Source: {url}")
            
            if parts:
                formatted_chunks.append("\n".join(parts))
            continue
        
        # Handle plain string results
        if isinstance(item, str) and item.strip():
            formatted_chunks.append(item.strip())

    if not formatted_chunks:
        return "No useful search results were found."

    return "\n\n---\n\n".join(formatted_chunks)


def reset_tavily_tool():
    """Reset the cached Tavily tool instance (useful for testing)."""
    global _tavily_search
    _tavily_search = None
