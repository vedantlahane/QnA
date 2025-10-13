from langchain_community.tools.tavily_search import TavilySearchResults

def load_tavily_search_tool(max_results: int = 3):
    """
    This function initializes and returns a Tavily search tool.
    Args:
        max_results (int): The maximum number of search results to return. Default is 3.

    Returns:
        TavilySearchResults: An instance of the TavilySearchResults tool.
    """

    return TavilySearchResults(max_results=max_results)