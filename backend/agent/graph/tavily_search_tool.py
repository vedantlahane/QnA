from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

import getpass
import os

if not os.environ.get("TAVILY_API_KEY"):
    os.environ["TAVILY_API_KEY"] = getpass.getpass("Tavily API key:\n")

def load_tavily_search_tool(max_results: int = 3):
    """
    This function initializes and returns a Tavily search tool.
    Args:
        max_results (int): The maximum number of search results to return. Default is 3.

    Returns:
        TavilySearchResults: An instance of the TavilySearchResults tool.
    """

    return TavilySearch(max_results=max_results)