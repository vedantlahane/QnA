# data_app/agent_core/tools/tavily_search_tool.py

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

@tool
def search_internet(query: str) -> str:
    """
    Performs an internet search using Tavily and returns a summary of the results.
    This tool is used when the answer cannot be found in uploaded documents.
    """
    try:
        search_tool = TavilySearchResults(
            max_results=TOOLS_CFG.tavily_search_max_results
        )
        results = search_tool.invoke(query)
        # Summarize the results for the LLM
        return "Search results: " + str(results)
    except Exception as e:
        return f"Sorry, an error occurred while performing an internet search. Error: {e}"