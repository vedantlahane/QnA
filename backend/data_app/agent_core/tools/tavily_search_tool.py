"""
Tavily Search Tool Module.
Provides a simple internet search capability via Tavily for the agent.
"""
import logging
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

logger = logging.getLogger('data_app.agent_core.tools.tavily_search_tool')

TOOLS_CFG = LoadToolsConfig()

@tool
def search_internet(query: str) -> str:
    """Perform an internet search using Tavily Search API."""
    try:
        search_tool = TavilySearch(max_results=TOOLS_CFG.tavily_search_max_results)
        results = search_tool.invoke(query)
        return "Search results: " + str(results)
    except Exception as e:
        error_msg = (
            "Sorry, an error occurred while performing an internet search. "
            f"Error details: {str(e)}. "
            "Please try rephrasing your query or check your internet connection."
        )
        return error_msg
